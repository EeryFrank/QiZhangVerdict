
'use strict';
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const assert = require('node:assert/strict');
const mc = require('minecraft-protocol');
const Chunk = require('prismarine-chunk')('1.16.5');
const data = require('minecraft-data')('1.16.5');
const [folder, portText] = process.argv.slice(2);
const port = Number(portText), name = 'QVAxGate';
const pause = ms => new Promise(r => setTimeout(r, ms));
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const evidence = path.join(folder, 'evidence');
const logFile = path.join(folder, 'integration-console.log');
const readLog = () => fs.readFileSync(logFile, 'utf8');
const cases = [];
const result = {passed:false, syntheticProtocolClient:true, graphicalClient:false, version:'1.16.5', cases};
let client, ended = false, kick = '', challenge, device, capture = false, packet, updates = [];
const clients = new Set();
function check(ok, label) { assert(ok, label); cases.push(label); console.log('PASS ' + label); }
async function until(predicate, label, timeout=12000) {
  const end = performance.now() + timeout;
  while (!predicate()) { assert(performance.now()<end, 'timeout: '+label); await pause(40); }
}
async function command(text, expected, timeout=12000) {
  const before=readLog().length;
  fs.appendFileSync(path.join(folder, 'commands.queue'), text+'\n');
  if(expected) await until(()=>readLog().slice(before).includes(expected), text, timeout);
  else await pause(250);
  return readLog().slice(before);
}
function str(v) { const b=Buffer.from(v), n=Buffer.alloc(2); n.writeUInt16BE(b.length);return Buffer.concat([n,b]); }
function list(v) { const n=Buffer.alloc(2);n.writeUInt16BE(v.length);return Buffer.concat([n,...v.map(str)]); }
function makeReport(b) {
  assert(b.subarray(0,6).equals(Buffer.from([0x51,0x5a,0x47,0x31,2,1])));
  const n=b.readUInt16BE(6), nonce=b.subarray(8,8+n).toString();
  const s=b.readUInt16BE(8+n), scope=b.subarray(10+n,10+n+s).toString();
  assert(n===64 && scope.length>0 && b.length===10+n+s);
  device=sha('synthetic-antixray-QA|'+scope+'|'+name);
  return Buffer.concat([Buffer.from([0x51,0x5a,0x47,0x31,2,2]),str(nonce),Buffer.from([1]),
                        list(['qizhangverdict']),list([]),list([]),str(device)]);
}
function offlineUUID(v) {
  const b=crypto.createHash('md5').update('OfflinePlayer:'+v).digest();b[6]=(b[6]&15)|48;b[8]=(b[8]&63)|128;
  const h=b.toString('hex');return [h.slice(0,8),h.slice(8,12),h.slice(12,16),h.slice(16,20),h.slice(20)].join('-');
}
function association() {
  const file=path.join(folder,'config','qizhangverdict','accounts.state');
  return fs.existsSync(file) && fs.readFileSync(file,'utf8').split(/\r?\n/).includes('D\t'+offlineUUID(name)+'\t'+device);
}
function nameAt(chunk, pos) {return data.blocksByStateId[chunk.getBlockStateId(pos)].name;}
function readChunk(p) {
  const chunk=new Chunk();chunk.load(p.chunkData,p.bitMap);if(p.biomes)chunk.loadBiomes(p.biomes);
  return chunk;
}
async function main() {
  // World controls are set before any player sees the target chunk.
  await command('gamerule spawnRadius 0');
  await command('gamerule doMobSpawning false');
  await command('setworldspawn 8 61 8');
  await command('forceload add 0 0');
  await command('fill 4 28 4 14 36 12 minecraft:stone');
  await command('setblock 8 32 8 minecraft:diamond_ore');
  await command('setblock 12 32 8 minecraft:diamond_ore');
  await command('setblock 13 32 8 minecraft:air');
  const real=[['hidden',[8,32,8],'diamond_ore'],['exposed',[12,32,8],'diamond_ore'],
              ['exposed_air',[13,32,8],'air'],['control',[9,32,8],'stone'],
              ...[[7,32,8],[8,31,8],[8,33,8],[8,32,7],[8,32,9]].map((p,i)=>['neighbor'+i,p,'stone'])];
  for(const [key,p,block] of real) await command(`execute if block ${p.join(' ')} minecraft:${block} run say AX_REAL_${key}`,`[Server] AX_REAL_${key}`);
  result.authoritativeScene=real.map(([role,position,block])=>({role,position,block,consoleVerified:true}));
  check(true,'authoritative hidden/exposed ore and six-face stone controls verified');
  client=mc.createClient({host:'127.0.0.1',port,username:name,auth:'offline',version:'1.16.5',checkTimeoutInterval:15000});
  clients.add(client);
  client.on('error',e=>{result.clientError=String(e)});
  client.on('kick_disconnect',p=>{kick=JSON.stringify(p)});
  client.on('end',()=>{ended=true;clients.delete(client)});
  client.on('login',()=>client.write('custom_payload',{channel:'minecraft:register',data:Buffer.from('qzguard:main')}));
  client.on('position',p=>{if(p.teleportId!==undefined)client.write('teleport_confirm',{teleportId:p.teleportId})});
  client.on('custom_payload',p=>{if(p.channel==='qzguard:main')challenge=p.data});
  client.on('map_chunk',p=>{if(capture && p.x===0 && p.z===0)packet=p});
  client.on('block_change',p=>updates.push({kind:'single',position:p.location,stateId:p.type}));
  client.on('multi_block_change',p=>{
    for(const v of p.records) {
      const bits=Number(v), local=bits&4095;
      updates.push({kind:'multi',position:{x:p.chunkCoordinates.x*16+(local>>8),
        y:p.chunkCoordinates.y*16+(local&15),z:p.chunkCoordinates.z*16+((local>>4)&15)},stateId:Math.floor(bits/4096)});
    }
  });
  await until(()=>challenge || ended,'held challenge');
  check(!!challenge && !ended,'companion challenge received with default 20s timeout');
  await command('op '+name,'Made '+name+' a server operator');
  const before=readLog().length;
  client.write('chat',{message:'/say AX_BEFORE_REPORT'});
  await pause(1200);
  check(!readLog().slice(before).includes('['+name+'] AX_BEFORE_REPORT'),'operator command blocked before report');
  client.write('custom_payload',{channel:'qzguard:main',data:makeReport(challenge)});
  await pause(750);
  const after=readLog().length;
  client.write('chat',{message:'/say AX_AFTER_REPORT'});
  await until(()=>readLog().slice(after).includes('['+name+'] AX_AFTER_REPORT'),'operator command after report');
  check(!ended,'same operator command allowed after valid report');
  await command('deop '+name,'Made '+name+' no longer a server operator');
  await command('execute if entity @a[name='+name+',gamemode=survival] run say AX_SURVIVAL','[Server] AX_SURVIVAL');
  await until(association,'exact synthetic UUID device association');
  result.exactSyntheticUUIDDeviceAssociation=true;result.syntheticUUID=offlineUUID(name);
  const verifiedAt=performance.now();
  await command('tp '+name+' 512.5 70 512.5','Teleported '+name);
  await pause(1500);
  capture=true;packet=undefined;
  await command('tp '+name+' 8.5 61 8.5','Teleported '+name);
  await until(()=>packet,'fresh sent target chunk after report');
  const chunk=readChunk(packet);
  const positions=[['hidden',{x:8,y:32,z:8},'stone'],['exposed',{x:12,y:32,z:8},'diamond_ore'],
                   ['stoneControl',{x:9,y:32,z:8},'stone'],['exposedAir',{x:13,y:32,z:8},'air']];
  result.sentChunk={x:packet.x,z:packet.z,bitMap:packet.bitMap,groundUp:packet.groundUp,
    chunkDataSha256:sha(packet.chunkData),chunkDataBytes:packet.chunkData.length,
    positions:positions.map(([role,p,expected])=>({role,position:p,expected,actual:nameAt(chunk,p)}))};
  fs.writeFileSync(path.join(evidence,'sent-chunk-0-0.bin'),packet.chunkData);
  fs.writeFileSync(path.join(evidence,'sent-chunk-0-0.json'),JSON.stringify(result.sentChunk,null,2)+'\n');
  for(const item of result.sentChunk.positions)check(item.actual===item.expected,'sent chunk '+item.role+' = '+item.expected);
  updates=[];
  await command('setblock 8 32 7 minecraft:air');
  await until(()=>updates.some(p=>p.position.x===8 && p.position.y===32 && p.position.z===8 && data.blocksByStateId[p.stateId]?.name==='diamond_ore'),
              'real diamond revealed in block update after neighboring stone is removed');
  result.revealUpdates=updates.filter(p=>p.position.x===8&&p.position.y===32&&p.position.z===8)
    .map(p=>({...p,block:data.blocksByStateId[p.stateId]?.name}));
  check(true,'opening neighboring stone reveals true diamond in actual block update');
  while(performance.now()-verifiedAt<22000) {assert(!ended,'unexpected disconnect: '+kick);await pause(100);}
  result.onlineAfterReportSeconds=(performance.now()-verifiedAt)/1000;
  await command('execute if entity @a[name='+name+',gamemode=survival] run say AX_FRESH_SURVIVAL','[Server] AX_FRESH_SURVIVAL');
  await command('qzverdict status','QiZhangVerdict sessions=');
  check(!ended && association(),'legal player remains online beyond default timeout with exact device association and fresh survival query');
  client.end('integration QA complete');
  await until(()=>ended,'normal client close');
  result.normalClientDisconnect=true;result.passed=true;
}
main().catch(e=>{result.error=String(e.stack||e);process.exitCode=1;console.error(result.error)}).finally(async()=>{
  for(const c of clients)c.end('QA cleanup');
  await pause(250);
  fs.writeFileSync(path.join(folder,'protocol-result.json'),JSON.stringify(result,null,2)+'\n');
});
