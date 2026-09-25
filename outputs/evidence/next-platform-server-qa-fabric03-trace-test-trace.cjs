'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const vm=require('node:vm');
const Client=require('minecraft-protocol/src/client');
const {createSerializer}=require('minecraft-protocol/src/transforms/serializer');
const hash=value=>crypto.createHash('sha256').update(value).digest('hex');
const functionFile=path.join(__dirname,'trace-function.cjs.txt');
const createTrace=vm.runInNewContext(fs.readFileSync(functionFile,'utf8')+'\ncreateMetadataTrace', {process,hash});
const marker='DO_NOT_COPY_FAKE_PACKET_SCOPE_NONCE_DEVICE_OR_CREDENTIAL';
const checks=[];
const check=(name,body)=>{body();checks.push({name,passed:true});};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function send(client,name,params){
  const encoder=createSerializer({isServer:true,state:client.state,version:client.version});
  encoder.on('error',error=>{throw error});
  encoder.on('data',bytes=>client.deserializer.write(bytes));
  encoder.end({name,params});await tick();
}
async function main(){
  const client=new Client(false,'1.20.4');client.state='play';
  const named=[];client.on('kick_disconnect',p=>named.push(p.reason));
  const trace=createTrace(client,'QVBot14',()=>({joined:true,sent:false,ended:true,kickedPresent:false,errorPresent:true}));
  await send(client,'custom_payload',{channel:'example:private',data:Buffer.from(marker)});
  await send(client,'kick_disconnect',{reason:{type:'string',value:marker}});
  const error=new Error(marker);error.field='play.toClient.packet.reason';error.code='ETEST';client.emit('error',error);
  client.emit('end',marker);
  await send(client,'kick_disconnect',{reason:{type:'string',value:marker}});
  client.state='configuration';
  await send(client,'disconnect',{reason:{type:'string',value:marker}});
  const first=trace.finish();
  check('Real serializer/deserializer packet names are recorded without payload or reason values',()=>{
    assert(first.events.some(e=>e.packetName==='custom_payload'));
    assert(first.events.some(e=>e.packetName==='kick_disconnect'));
    assert(!JSON.stringify(first).includes(marker));
    assert(first.packetBodiesRecorded===false && first.reasonTextRecorded===false);
  });
  check('Original named events and reason payload remain unchanged',()=>{
    assert.equal(named.length,2);assert(named.every(reason=>reason.value===marker));
  });
  check('Actual decoder events after end remain visible without fabricating reason',()=>{
    assert(first.events.some(e=>e.event==='decoder-data' && e.afterClientEnd && e.packetName==='kick_disconnect'));
    assert(!first.events.some(e=>Object.hasOwn(e,'reason')));
  });
  check('Recreated configuration decoder records its actual state',()=>{
    assert.equal(first.totalDecoderInstances,2);
    assert(first.events.some(e=>e.packetName==='disconnect' && e.packetState==='configuration'));
  });
  check('Errors and unknown end strings cannot copy sensitive text',()=>{
    const e=first.events.find(e=>e.event==='client-error');
    assert.equal(e.code,'ETEST');assert.equal(e.messageSha256,hash(marker));
    assert.equal(first.events.find(e=>e.event==='client-end').endKind,'other (not copied)');
  });
  const before=client.deserializer.listenerCount('data');
  const limited=createTrace(client,'CheatAccount',()=>({joined:false,sent:false,ended:false,kickedPresent:false,errorPresent:false}));
  for(let i=0;i<250;i++)await send(client,'disconnect',{reason:{type:'string',value:marker}});
  const capped=limited.finish();
  check('Trace retains at most 200 latest events with explicit dropped count',()=>{
    assert.equal(capped.events.length,200);assert(capped.eventCount>250);assert(capped.eventsDropped>0);
    assert(capped.events[0].sequence>1);assert.equal(capped.events.at(-1).event,'trace-final-state');
  });
  check('Finalization removes only trace listeners without changing library listeners',()=>{
    assert.equal(client.deserializer.listenerCount('data'),before);
    assert.equal(client.listenerCount('state'),0);
  });
  check('Every decoded-event record contains metadata only',()=>{
    const keys=new Set(['sequence','elapsedMs','event','clientState','afterClientEnd','decoderId','packetName','packetState','decodedBytes']);
    for(const e of [...first.events,...capped.events])if(e.event==='decoder-data')assert(Object.keys(e).every(k=>keys.has(k)));
  });
  const source=fs.readFileSync(path.join(__dirname,'protocol_smoke.cjs'),'utf8');
  const base=fs.readFileSync(path.join(__dirname,'protocol_smoke.base-d133f0.cjs'),'utf8');
  const assertionLines=s=>s.split(/\r?\n/).filter(line=>line.includes('assert(')||line.includes('assert.equal('));
  check('All original full-suite assertion lines remain byte-identical',()=>assert.deepEqual(assertionLines(source),assertionLines(base)));
  const result={passed:true,cases:checks,scope:'In-memory actual minecraft-protocol1.66.2 serializer/parser trace-only tests; not a Minecraft/network replay.',
    javaStarted:false,minecraftStarted:false,socketsOpened:false,syntheticPrivateMarkerExcluded:true,
    candidateSha256:hash(fs.readFileSync(path.join(__dirname,'protocol_smoke.cjs'))),
    observerSha256:hash(fs.readFileSync(path.join(__dirname,'protocol_disconnect_observer.cjs'))),
    traceFunctionSha256:hash(fs.readFileSync(functionFile)),testSha256:hash(fs.readFileSync(__filename))};
  fs.writeFileSync(path.join(__dirname,'trace-selftest.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({passed:true,cases:checks.length,candidateSha256:result.candidateSha256}));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
