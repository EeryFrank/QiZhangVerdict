const mc = require('minecraft-protocol');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const [version, rawPort, folder] = process.argv.slice(2);
const port = Number(rawPort);
const pause = ms => new Promise(r => setTimeout(r, ms));
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const cases = [], active = new Set();
const orePalette = new Set();
const chunkErrors = [];
let maxChunkZeroPadding = 0;
const mcData = require('minecraft-data')(version);
let sequence = 0;
const defaults = { 'limits.max-online-per-ip':3, 'limits.max-online-per-ip-device':1, 'limits.max-accounts-per-ip':100, 'limits.account-window-hours':720, 'limits.attempts-per-minute':1000, 'ip.allow':'', 'ip.deny':'', 'companion.required':true, 'companion.timeout-seconds':4, 'device.required':true, 'vm.action':'ALERT', 'blacklist.action':'DENY', 'sanctions.on-deny':'BAN' };
const dataFolder = process.env.QV_DATA_DIR || path.join(folder, 'plugins', 'QiZhangVerdict');
async function command(text) {
  fs.appendFileSync(path.join(folder, 'commands.queue'), text + '\n');
  await pause(1300);
}
async function configure(overrides = {}) {
  fs.writeFileSync(path.join(dataFolder, 'guard.properties'), Object.entries({...defaults, ...overrides}).map(([k,v])=>`${k}=${v}`).join('\n') + '\n');
  await command('qzverdict reload');
}
function str(value) { const data = Buffer.from(value); const length = Buffer.alloc(2); length.writeUInt16BE(data.length); return Buffer.concat([length,data]); }
function list(values) { const count = Buffer.alloc(2); count.writeUInt16BE(values.length); return Buffer.concat([count,...values.map(str)]); }
function report(challenge, opts) {
  const nonce = challenge.subarray(8,72).toString();
  const header = Buffer.from([0x51,0x5a,0x47,0x31,2,2]);
  const out = Buffer.concat([header,str(nonce),Buffer.from([1]),list(opts.mods||['qizhangverdict']),list(opts.packs||[]),list(opts.vm||[]),str(opts.device||hash(opts.name))]);
  return opts.malformed ? Buffer.concat([out,Buffer.from([1])]) : out;
}
async function connect(options = {}) {
  const name = options.name || `QVBot${++sequence}`;
  const opts = {...options,name};
  const state = {name, kicked:'', ended:false, joined:false, sent:false, error:''};
  const client = mc.createClient({host:'127.0.0.1',port,username:name,auth:'offline',version,checkTimeoutInterval:10000,disableChatSigning:true});
  state.client = client; active.add(client);
  // Fabric's configuration handshake waits for the standard ping response.
  client.on('ping',p=>client.write('pong',{id:p.id}));
  client.on('error',e=>{state.error=String(e);});
  client.on('kick_disconnect',p=>{state.kicked=JSON.stringify(p);});
  client.on('disconnect',p=>{state.kicked=JSON.stringify(p);});
  client.on('end',r=>{state.ended=true;state.endReason=String(r);active.delete(client);});
  client.on('login',()=>{state.joined=true;client.write('custom_payload',{channel:'minecraft:register',data:Buffer.from('qzguard:main')});});
  client.on('position',p=>{if(p.teleportId !== undefined)client.write('teleport_confirm',{teleportId:p.teleportId});});
  client.on('map_chunk',p=>{if(process.env.QV_TEST_ANTIXRAY === '1')inspectChunkPalettes(p.chunkData);});
  client.on('custom_payload',p=>{
    if (p.channel !== 'qzguard:main' || opts.silent || state.sent) return;
    if (opts.hold) {state.challenge=p.data;return;}
    state.sent=true;
    client.write('custom_payload',{channel:p.channel,data:report(p.data,opts)});
  });
  const end=Date.now()+10000;
  while (!state.ended && !state.sent && !state.joined && Date.now()<end) await pause(30);
  await pause(opts.silent ? 5200 : 1200);
  return state;
}
async function close(...players) { for(const p of players) if(p && !p.ended) p.client.end('test complete'); await pause(500); }
function allowed(p,label) { assert(p.joined && !p.ended && p.sent,`${label}: ${JSON.stringify({...p,client:undefined})}`); cases.push(label); }
function denied(p,label,fragment) { assert(p.ended,`${label}: connection still open`); if(fragment) assert(p.kicked.toLowerCase().includes(fragment.toLowerCase()),`${label}: ${p.kicked}`); cases.push(label); }
async function main() {
  await configure();
  const okay=await connect(); allowed(okay,'normal companion joins'); await close(okay);
  if(process.env.QV_TEST_ANTIXRAY === '1') { assert(!chunkErrors.length,chunkErrors[0]); assert(orePalette.size>=3,`flat world network chunks must contain fake ores; got ${[...orePalette]}`); cases.push('Anti-Xray sends fake ore palettes in controlled ore-free flat world'); }
  if(process.env.QV_TEST_COMMAND_GATE === '1') {
    await configure({'companion.timeout-seconds':10});
    const gate=await connect({name:'GateAccount',hold:true});
    assert(gate.challenge && !gate.ended,'gate client has pending challenge');
    // Vanilla offline servers resolve names case-insensitively before first join.
    // Grant the connected UUID, so this assertion really exercises an operator.
    await command('op GateAccount');
    gate.client.chat('/say QZ_PRE_GATE'); await pause(400);
    const before=fs.readFileSync(path.join(folder,'console.log'),'utf8');
    assert(!/\[GateAccount\] QZ_PRE_GATE/.test(before),'unverified player command must not execute');
    gate.sent=true;gate.client.write('custom_payload',{channel:'qzguard:main',data:report(gate.challenge,{name:'GateAccount'})});
    await pause(700);gate.client.chat('/say QZ_POST_GATE');await pause(500);
    assert(/\[GateAccount\] QZ_POST_GATE/.test(fs.readFileSync(path.join(folder,'console.log'),'utf8')),'verified player command must execute');
    cases.push('privileged commands blocked before report and restored afterward');
    await close(gate);await command('deop GateAccount');await configure();
  }
  const missing=await connect({silent:true}); denied(missing,'missing companion expires','timed out');
  const malformed=await connect({name:'BadWire',malformed:true}); denied(malformed,'malformed report rejected');
  const recovered=await connect({name:'BadWire'}); allowed(recovered,'malformed report does not permanently ban account'); await close(recovered);

  const first=await connect({device:hash('shared-device')}); allowed(first,'first account on device allowed');
  const same=await connect({device:hash('shared-device')}); denied(same,'same IP same device second account rejected');
  const second=await connect({device:hash('second-device')}); allowed(second,'same IP second different device allowed');
  const third=await connect({device:hash('third-device')}); allowed(third,'same IP third different device allowed');
  const fourth=await connect({device:hash('fourth-device')}); denied(fourth,'same IP fourth account rejected','simultaneous');
  await close(first,second,third);
  const released=await connect({device:hash('shared-device')}); allowed(released,'disconnect releases device and IP quota'); await close(released);

  const cheat=await connect({name:'CheatAccount',device:hash('banned-device'),mods:['meteor-client']}); denied(cheat,'known cheat denied and sanctioned');
  const linked=await connect({name:'LinkedAccount',device:hash('banned-device')}); denied(linked,'same banned device different account denied');
  const old=await connect({name:'CheatAccount',device:hash('fresh-device')}); denied(old,'banned account denied with new device');
  await command('qzverdict unban ' + offlineUUID('CheatAccount'));
  await command('qzverdict unban device:' + hash('banned-device'));
  const unbanned=await connect({name:'CheatAccount',device:hash('banned-device')}); allowed(unbanned,'administrator account and device unban restores access'); await close(unbanned);

  await command('qzverdict rule add BLACK MOD GLOB test*cheat');
  const fuzzy=await connect({mods:['test_example_cheat']}); denied(fuzzy,'administrator glob rule enforced');
  await command('qzverdict rule add WHITE MOD EXACT test_example_cheat');
  const whitelisted=await connect({mods:['test_example_cheat']}); allowed(whitelisted,'whitelist overrides matching blacklist item'); await close(whitelisted);
  const rules=fs.readFileSync(path.join(dataFolder,'rules.tsv'),'utf8').split(/\r?\n/).filter(l=>l.includes('test_example_cheat'));
  assert.equal(rules.length,1,'find exactly one whitelist rule');
  await command('qzverdict rule remove ' + rules[0].split('\t')[0]);
  const removed=await connect({mods:['test_example_cheat']}); denied(removed,'removed whitelist takes effect');

  await command('qzverdict rule remove legacy:mod:meteor-client');
  const defaultRemoved=await connect({mods:['meteor-client']}); allowed(defaultRemoved,'administrator removes default rule with colon ID'); await close(defaultRemoved);
  await command('qzverdict rule add BLACK MOD EXACT meteor-client');
  const defaultRestored=await connect({mods:['meteor-client']}); denied(defaultRestored,'administrator restores removed blacklist entry');

  await configure({'ip.deny':'127.0.0.0/8'});
  const ip=await connect(); denied(ip,'CIDR deny rejects login','IP');
  await configure({'vm.action':'DENY'});
  const vm=await connect({vm:['vmware']}); denied(vm,'known VM signal denied');
  const vbs=await connect({vm:['hypervisor-present']}); allowed(vbs,'VBS hypervisor alone does not ban physical machine'); await close(vbs);
  await configure({'limits.max-online-per-ip':2});
  const twoA=await connect(); allowed(twoA,'two-device setting first account');
  const twoB=await connect(); allowed(twoB,'two-device setting second account');
  const twoC=await connect(); denied(twoC,'two-device setting rejects third account'); await close(twoA,twoB);
  await command('qzverdict bans'); await command('qzverdict rule list');
  const result={passed:cases.length,cases,orePalette:[...orePalette],maxChunkZeroPadding,kind:'real TCP clients using synthetic self-reports; not rendered mod client or real VM',version};
  fs.writeFileSync(path.join(folder,'protocol-result.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify(result));
}
function inspectChunkPalettes(data) {
  let pos=0;
  function vint(){let value=0,shift=0;for(;;){if(pos>=data.length||shift>28)throw Error('bad varint');const b=data[pos++];value|=(b&127)<<shift;if(!(b&128))return value;shift+=7;}}
  function palette(maxBits, blocks){
    const bits=data[pos++]; const ids=[];
    if(bits===0)ids.push(vint());
    else if(bits<=maxBits){const count=vint();if(count<0||count>4096)throw Error('bad palette');for(let i=0;i<count;i++)ids.push(vint());}
    const count=vint();if(count<0||pos+count*8>data.length)throw Error('bad longs');pos+=count*8;
    if(blocks)for(const id of ids){const block=mcData.blocksByStateId[id];if(block && /(^|_)ore$/.test(block.name))orePalette.add(block.name);}
  }
  try {
    // This fixture stays in the vanilla Overworld: 384 blocks / 16 = 24 sections.
    // Paper 1.20.1 may leave zero padding in its preallocated Anti-Xray buffer;
    // vanilla reads the dimension's section count rather than until EOF.
    for(let section=0;section<24;section++){pos+=2;palette(8,true);palette(3,false);}
    if(pos>data.length || data.subarray(pos).some(byte=>byte!==0))throw Error('unexpected trailing section bytes');
    maxChunkZeroPadding=Math.max(maxChunkZeroPadding,data.length-pos);
  }catch(error){
    // Preserve the failing bytes without throwing into the network decompressor.
    if(!chunkErrors.length)fs.writeFileSync(path.join(folder,'first-invalid-chunk.bin'),data);
    chunkErrors.push(`Chunk palette verification failed at ${pos}/${data.length}: ${error.message}`);
  }
}
function offlineUUID(name) {
  const bytes=crypto.createHash('md5').update('OfflinePlayer:'+name).digest(); bytes[6]=(bytes[6]&15)|48; bytes[8]=(bytes[8]&63)|128;
  const hex=bytes.toString('hex'); return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}
main().catch(error=>{console.error(error);process.exitCode=1;}).finally(async()=>{for(const client of active)client.end('test finished');await pause(300);});
