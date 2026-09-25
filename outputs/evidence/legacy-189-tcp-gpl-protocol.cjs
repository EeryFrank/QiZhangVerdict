
const mc = require('minecraft-protocol');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');
const [version, rawPort, folder] = process.argv.slice(2);
assert.equal(version, '1.8.9');
const protocolData = require('minecraft-data')(version);
assert.equal(protocolData.version.version,47);
const channel = 'QZGuard', registerChannel = 'REGISTER';
const active = new Set(), cases = [], waits = [];
const pause = ms => new Promise(r => setTimeout(r, ms));
const hash = s => crypto.createHash('sha256').update(s).digest('hex');
function str(s) { const d = Buffer.from(s); const n = Buffer.alloc(2); n.writeUInt16BE(d.length); return Buffer.concat([n,d]); }
function list(a) { const n=Buffer.alloc(2); n.writeUInt16BE(a.length); return Buffer.concat([n,...a.map(str)]); }
function report(bytes, opts) {
  assert.equal(bytes.readUInt32BE(0),0x515a4731);
  assert.equal(bytes[4],2); assert.equal(bytes[5],1);
  assert.equal(bytes.readUInt16BE(6),64); assert.equal(bytes.readUInt16BE(72),64);
  assert.equal(bytes.length,138); assert(/^[0-9a-f]{64}$/.test(bytes.subarray(74).toString()));
  const nonce=bytes.subarray(8,72).toString();
  const device=opts.missingDevice ? '' : hash('synthetic-legacy-device-'+opts.device);
  const r=Buffer.concat([Buffer.from([0x51,0x5a,0x47,0x31,2,2]),str(nonce),Buffer.from([1]),list(['qizhangverdict']),list([]),list([]),str(device)]);
  return opts.malformed ? Buffer.concat([r,Buffer.from([1])]) : r;
}
async function connect(name, device, options={}) {
  const opts={name,device,...options};
  const s={name,joined:false,sent:false,ended:false,kick:'',error:'',challenge:false,chats:[],started:performance.now()};
  const c=mc.createClient({host:'127.0.0.1',port:Number(rawPort),version,username:name,auth:'offline',checkTimeoutInterval:30000,disableChatSigning:true});
  s.client=c; active.add(c);
  c.on('error',e=>{s.error=String(e);});
  c.on('chat',p=>{s.chats.push(JSON.stringify(p));});
  c.on('kick_disconnect',p=>{s.kick=JSON.stringify(p);});
  c.on('disconnect',p=>{s.kick=JSON.stringify(p);});
  c.on('end',()=>{s.ended=true;s.elapsed=performance.now()-s.started;active.delete(c);});
  c.on('login',()=>{s.joined=true;c.write('custom_payload',{channel:registerChannel,data:Buffer.from(channel)});});
  c.on('position',p=>{if(p.teleportId!==undefined)c.write('teleport_confirm',{teleportId:p.teleportId});});
  c.on('custom_payload',p=>{
    if(p.channel!==channel||s.sent)return;
    s.challenge=true;
    if(opts.silent)return;
    if(opts.hold){s.challengeBytes=p.data;return;}
    try { const bytes=report(p.data,opts); s.sent=true; c.write('custom_payload',{channel,data:bytes}); }
    catch(e) {s.error=String(e);c.end('invalid server challenge');}
  });
  const until=performance.now()+(opts.silent?26000:12000);
  while(!s.ended && !s.sent && !(opts.hold&&s.challenge) && (!opts.silent || performance.now()<until) && performance.now()<until)await pause(25);
  if(!opts.silent)await pause(900);
  return s;
}
function snapshot(s){return {name:s.name,joined:s.joined,sent:s.sent,ended:s.ended,kick:s.kick,error:s.error,challenge:s.challenge};}
function allowed(s, title) {assert(s.joined&&s.sent&&!s.ended&&!s.error,title+': '+JSON.stringify(snapshot(s)));cases.push(title);}
function denied(s, title, fragment) {assert(s.ended,title+': still connected '+JSON.stringify(snapshot(s)));if(fragment)assert(s.kick.toLowerCase().includes(fragment.toLowerCase()),title+': '+s.kick);cases.push(title);}
async function close(...clients){for(const s of clients)if(s&&!s.ended)s.client.end('legacy test complete');await pause(500);}
async function command(text){fs.appendFileSync(path.join(folder,'commands.queue'),text+'\n');await pause(700);}
async function main(){
  const gate=await connect('QVLegacyGate','gate',{hold:true});
  assert(gate.challengeBytes && !gate.ended,'operator gate has a pending report');
  await command('op QVLegacyGate');
  assert(/Opped QVLegacyGate/.test(fs.readFileSync(path.join(folder,'console.log'),'utf8')),'console confirms actual operator grant');
  const gateOffset=fs.readFileSync(path.join(folder,'console.log'),'utf8').length;
  gate.client.chat('/say QZ189_PRE_GATE');await pause(600);
  assert(gate.chats.some(t=>t.includes('waiting for required companion report')),'pending OP receives the explicit Guard command-denial response');
  assert(!/\[QVLegacyGate\] QZ189_PRE_GATE/.test(fs.readFileSync(path.join(folder,'console.log'),'utf8').slice(gateOffset)),'pending operator command must not execute');
  gate.sent=true;gate.client.write('custom_payload',{channel,data:report(gate.challengeBytes,{name:gate.name,device:'gate'})});await pause(700);
  assert(!gate.ended && !gate.error,'operator report accepted');
  gate.client.chat('/say QZ189_POST_GATE');await pause(600);
  assert(/\[QVLegacyGate\] QZ189_POST_GATE/.test(fs.readFileSync(path.join(folder,'console.log'),'utf8').slice(gateOffset)),'verified operator command executes');
  cases.push('real operator command blocked while pending and restored after native QZGuard report');
  await close(gate);await command('deop QVLegacyGate');
  const a=await connect('QVLegacyA','a');allowed(a,'strict default companion report accepted on native Forge QZGuard channel');
  const observedFrom=fs.readFileSync(path.join(folder,'console.log'),'utf8').length;
  const sustainedAt=performance.now();await pause(22000);
  assert(!a.ended&&!a.error,'valid companion must survive beyond the default report deadline');
  fs.appendFileSync(path.join(folder,'commands.queue'),'qzverdict status\n');
  let status='';const statusEnd=performance.now()+3000;
  do {await pause(50);status=fs.readFileSync(path.join(folder,'console.log'),'utf8').slice(observedFrom);}
  while(!/QiZhangVerdict sessions=1,.*companion=required, vm=DENY,.*deviceRequired=true/.test(status)&&performance.now()<statusEnd);
  assert(/QiZhangVerdict sessions=1,.*companion=required, vm=DENY,.*deviceRequired=true/.test(status),'post-deadline console status must show the live strict session');
  assert(!a.ended,'valid client must still be connected at the status response');
  cases.push('valid report keeps account online for at least 22 seconds with strict server status');
  waits.push({case:'valid companion stays online beyond default deadline',elapsedMilliseconds:performance.now()-sustainedAt});
  const same=await connect('QVLegacyB','a');denied(same,'same IP and same device second account rejected','same IP and device');
  const b=await connect('QVLegacyB','b');allowed(b,'same IP second distinct device accepted');
  const c=await connect('QVLegacyC','c');allowed(c,'same IP third distinct device accepted');
  const fourth=await connect('QVLegacyD','d');denied(fourth,'default fourth concurrent account rejected','simultaneous');
  await close(a);
  const reuse=await connect('QVLegacyD','a');allowed(reuse,'disconnect releases IP and device concurrent slots');
  await close(b,c,reuse);
  const sixth=await connect('QVLegacyE','e');denied(sixth,'default sixth distinct rolling account rejected after five successful accounts','rolling account limit');
  const empty=await connect('QVLegacyA','a',{missingDevice:true});denied(empty,'strict default rejects missing device identifier','device identifier');
  const malformed=await connect('QVLegacyA','a',{malformed:true});denied(malformed,'malformed report rejected','malformed');
  const recovered=await connect('QVLegacyA','a');allowed(recovered,'invalid report does not permanently ban account');await close(recovered);
  const silent=await connect('QVLegacyA','a',{silent:true});denied(silent,'default required companion timeout enforced','timed out');
  assert(silent.challenge,'server sent a challenge to silent client');
  assert(silent.elapsed>=19000&&silent.elapsed<26000,'default 20-second timeout timing: '+silent.elapsed);
  waits.push({case:'default required report timeout',elapsedMilliseconds:silent.elapsed});
  const after=await connect('QVLegacyA','a');allowed(after,'timeout releases session and does not permanently ban account');await close(after);
  fs.appendFileSync(path.join(folder,'commands.queue'),'qzverdict status\n');
  await pause(600);
  assert.equal(cases.length,14,'all expected assertion groups must complete');
  const result={passed:true,cases,caseCount:cases.length,version,protocolVersion:47,protocolDataAlias:protocolData.version.minecraftVersion,channel,registerChannel,defaultPolicyUnmodified:true,waits,loader:'Forge 11.15.1.2318',
    scope:'Real loopback TCP clients with synthetic self-reports; not a rendered companion, real VM, external anticheat or general gameplay compatibility test.'};
  fs.writeFileSync(path.join(folder,'protocol-result.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}
if(process.argv.includes('--self-check')) {
  const serializer=mc.createSerializer({state:'play',isServer:false,version});
  const parser=mc.createDeserializer({state:'play',isServer:true,version});
  const nonce='a'.repeat(64), scope='b'.repeat(64);
  const challenge=Buffer.concat([Buffer.from([0x51,0x5a,0x47,0x31,2,1]),str(nonce),str(scope)]);
  const payload=report(challenge,{device:'offline-self-check'});
  for(const [name,data] of [[channel,payload],[registerChannel,Buffer.from(channel)]]) {
    const encoded=serializer.createPacketBuffer({name:'custom_payload',params:{channel:name,data}});
    const decoded=parser.parsePacketBuffer(encoded).data;
    assert.equal(decoded.name,'custom_payload');assert.equal(decoded.params.channel,name);assert.deepEqual(decoded.params.data,data);
  }
  const chat=serializer.createPacketBuffer({name:'chat',params:{message:'/say QZ189_SELF_CHECK'}});
  assert.equal(parser.parsePacketBuffer(chat).data.params.message,'/say QZ189_SELF_CHECK');
  console.log(JSON.stringify({passed:true,syntheticOnly:true,noTcpConnection:true,version,protocolVersion:47,protocolDataAlias:protocolData.version.minecraftVersion,packetChecks:['QZGuard report custom_payload','REGISTER custom_payload','legacy chat command'],minecraftProtocol:require('minecraft-protocol/package.json').version}));
} else main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{for(const c of active)c.end('test finished');await pause(300);});
