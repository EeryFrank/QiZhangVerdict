const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const {EventEmitter}=require('node:events');
const path=require('node:path');
const root='E:/Codex_work/QiZhangVerdict';
const cache='E:/CodexTemp/QiZhangVerdict/compat-1.20.6/protocol-forge-investigation-01';
const file=path.join(root,'scripts/protocol_smoke.cjs');
const original=fs.readFileSync(path.join(cache,'protocol_smoke.before.cjs'),'utf8');
const source=fs.readFileSync(file,'utf8');
let testClock=0, sideEffects=0;
const safeRequire=id=>{
 if(id==='minecraft-protocol')return {createClient(){sideEffects++;throw Error('network forbidden in pure QA');}};
 if(id==='minecraft-data')return ()=>({});
 if(id==='./protocol_disconnect_observer.cjs')return {observeDisconnects(){throw Error('unused in pure QA');}};
 if(id==='./protocol_player_loaded.cjs')return {attachPositionAcknowledgements(){throw Error('unused in pure QA');}};
 if(id==='node:perf_hooks')return {performance:{now:()=>testClock}};
 return require(id);
};
const context={require:safeRequire,process:{argv:['node','test','1.20.6','25733',cache],env:{}},console,Buffer,setTimeout,clearTimeout};
vm.createContext(context);
const prefix=source.slice(0,source.indexOf('main().catch('));
new vm.Script(prefix+'\nglobalThis.api={awaitConnectionObservation,createHandshakeTrace};',{filename:file}).runInContext(context);
const checks=[];
function pass(name){checks.push(name);}
function unchanged(start,end){assert.equal(source.slice(source.indexOf(start),source.indexOf(end,source.indexOf(start))),original.slice(original.indexOf(start),original.indexOf(end,original.indexOf(start))));}
unchanged('async function main()', 'function inspectChunkPalettes');pass('all 26 acceptance cases and command-gate sequence byte-identical');
unchanged('function allowed(', 'async function main()');pass('allowed and denied assertions byte-identical');
const reportOld=original.slice(original.indexOf('function report('),original.indexOf('async function connect(')).trim();
const reportNew=source.slice(source.indexOf('function report('),source.indexOf('async function awaitConnectionObservation(')).trim();
assert.equal(reportNew,reportOld);pass('wire-report serialization byte-identical');

async function waitCase(name,opts,initial,events,expectedTime,expectedState){
 let now=0;const state={ended:false,sent:false,joined:false,...initial};
 const scheduled=[...events];
 const sleep=async ms=>{assert(ms>=0 && ms<=5200);now+=ms;while(scheduled.length&&scheduled[0].at<=now)Object.assign(state,scheduled.shift().set);};
 await context.api.awaitConnectionObservation(state,opts,sleep,()=>now);
 assert.equal(now,expectedTime);for(const [key,value]of Object.entries(expectedState))assert.equal(state[key],value);pass(name);
}
(async()=>{
 await waitCase('normal login alone does not end report wait; delayed report at 1700ms succeeds',{}, {},[{at:90,set:{joined:true}},{at:1700,set:{sent:true}}],2910,{joined:true,sent:true});
 await waitCase('normal delayed registration/report at 3500ms retained within bound',{}, {},[{at:90,set:{joined:true}},{at:3500,set:{sent:true}}],4710,{sent:true});
 await waitCase('normal report retains full 1200ms denial observation',{}, {},[{at:60,set:{joined:true,sent:true}},{at:800,set:{ended:true}}],1260,{ended:true,sent:true});
 await waitCase('pre-login rejection returns but remains rejected',{}, {},[{at:60,set:{ended:true}}],1260,{ended:true,joined:false,sent:false});
 await waitCase('server required-report timeout remains a failure, never synthetic send',{}, {},[{at:90,set:{joined:true}},{at:4000,set:{ended:true}}],5220,{ended:true,sent:false});
 await waitCase('no report and no disconnect has hard 10000+1200ms bound',{}, {joined:true},[],11200,{sent:false});
 await waitCase('silent retains join+5200ms observation and never waits for report',{silent:true},{},[{at:90,set:{joined:true}},{at:4100,set:{ended:true}}],5290,{ended:true,sent:false});
 await waitCase('hold retains join+1200ms observation without automatic report',{hold:true},{},[{at:90,set:{joined:true}},{at:500,set:{challenge:true}}],1290,{challenge:true,sent:false});
 await waitCase('silent missing login retains original 10s+5200ms bound',{silent:true},{},[],15200,{sent:false,joined:false});
 await waitCase('hold missing login retains original 10s+1200ms bound',{hold:true},{},[],11200,{sent:false,joined:false});
 const client=new EventEmitter();client.state='configuration';client.deserializer=new EventEmitter();
 const first=client.deserializer;const before=first.listenerCount('data');
 const trace=context.api.createHandshakeTrace(client,1);
 const secret='DO_NOT_PUBLISH_DEVICE_NONCE_SCOPE';
 const packet={metadata:{name:'custom_payload',state:'configuration'}};
 Object.defineProperty(packet,'data',{get(){throw Error('observer read payload');}});
 testClock=100;first.emit('data',packet);
 client.emit('packet',{secret},{name:'custom_payload',state:'configuration'});
 trace.record('register-write','custom_payload');
 client.state='play';client.deserializer=new EventEmitter();client.emit('state','play','configuration');
 testClock=200;client.deserializer.emit('data',{metadata:{name:'custom_payload',state:'play'},data:{secret}});
 first.emit('error',new Error(secret));
 for(let i=0;i<250;i++)trace.record('challenge-public','custom_payload');
 const out=trace.finish();
 assert.equal(out.events.length,200);assert(out.eventsDropped>0);assert.equal(first.listenerCount('data'),before);assert.equal(client.deserializer.listenerCount('data'),0);assert.equal(client.listenerCount('packet'),0);
 assert(out.events.some(e=>e.event==='decoded-packet'&&e.packetState==='play'));assert(out.events.some(e=>e.event==='public-packet'));assert(out.events.some(e=>e.event==='decoder-error'));
 for(const e of out.events)assert.deepEqual(Object.keys(e).sort(),['clientState','elapsedMs','event','packetName','packetState']);
 assert(!JSON.stringify(out).includes(secret));pass('bounded trace separates decoder/public, handles phase swaps, cleans listeners, never reads payload/error text');
 assert.equal(sideEffects,0);pass('pure harness never creates a Minecraft connection');
 const sha=data=>crypto.createHash('sha256').update(data).digest('hex');
 const result={passed:true,kind:'pure Node fake-clock/event-emitter QA; no Java or TCP',checks,checkCount:checks.length,
 script:{path:file,sha256:sha(fs.readFileSync(file)),bytes:fs.statSync(file).size},before:{sha256:sha(Buffer.from(original)),bytes:Buffer.byteLength(original)},
 validator:{path:__filename,sha256:sha(fs.readFileSync(__filename))},runtimeExecuted:false,serverExecuted:false,
 noAssertionWeakened:true,silentAndHoldTimingUnchanged:true,normalWaitLimitMs:10000,postReportDenialObservationMs:1200};
 fs.writeFileSync(path.join(cache,'pure-qa-result.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
