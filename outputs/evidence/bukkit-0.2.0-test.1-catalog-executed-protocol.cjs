// SPDX-License-Identifier: GPL-3.0-only
// Two-phase, real TCP regression for the new catalog/defaults and automation sanctions.
const mc = require('minecraft-protocol');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');
const [version, port, folder, phase] = process.argv.slice(2);
assert(['1.20.1', '1.21.1'].includes(version));
assert(['initial', 'restart'].includes(phase));
assert.equal(require('minecraft-protocol/package.json').version, '1.66.2');
const fixture = JSON.parse(fs.readFileSync(path.join(folder, 'fixture.json')));
const dataFolder = path.join(folder, 'plugins', 'QiZhangVerdict');
const policyFile = path.join(dataFolder, 'guard.properties');
const blacklistFile = path.join(dataFolder, 'blacklist.tsv');
const consoleFile = path.join(folder, `console-${phase}.log`);
const clients = new Set(), cases = [];
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const device = label => hash('qizhang-catalog-020-synthetic-' + label);
const sharedBan = device('automation-ban'), sharedKick = device('automation-kick');
function uuid(name) {
  const b = crypto.createHash('md5').update('OfflinePlayer:' + name).digest();
  b[6] = (b[6] & 15) | 48; b[8] = (b[8] & 63) | 128;
  const h = b.toString('hex'); return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;
}
function str(s) { const b = Buffer.from(s), n = Buffer.alloc(2); n.writeUInt16BE(b.length); return Buffer.concat([n,b]); }
function list(a) { const n = Buffer.alloc(2); n.writeUInt16BE(a.length); return Buffer.concat([n,...a.map(str)]); }
function properties() {
  return Object.fromEntries(fs.readFileSync(policyFile,'utf8').split(/\r?\n/).filter(s => s && !s.startsWith('#')).map(s => [s.slice(0,s.indexOf('=')),s.slice(s.indexOf('=')+1)]));
}
function assertPolicy(sanctions = 'BAN') {
  assert.deepEqual(properties(), {...fixture.expectedQaPolicy, 'sanctions.on-deny':sanctions}, 'only the declared quota changes and explicit KICK control are allowed');
}
function rows(file) {
  const values = fs.readFileSync(file,'utf8').split(/\r?\n/).filter(s => s.trim() && !s.trim().startsWith('#'));
  for (const line of values) assert.equal(line.split('\t').length,4);
  return values.sort();
}
function state() {
  const p = path.join(dataFolder,'accounts.state'); return fs.existsSync(p) ? fs.readFileSync(p,'utf8') : '';
}
function bans() { return state().split(/\r?\n/).filter(s => /^[BV]\t/.test(s)).sort(); }
function hasBan(type, target, reason) { return bans().includes(`${type}\t${target}\t${Buffer.from(reason).toString('base64')}`); }
function associated(s) { return state().split(/\r?\n/).includes(`D\t${uuid(s.name)}\t${s.device}`); }
async function until(predicate, label, timeout=15000) {
  const end=performance.now()+timeout;
  while (!predicate() && performance.now()<end) await pause(50);
  assert(predicate(),label);
}
async function command(text, marker) {
  const offset=fs.readFileSync(consoleFile,'utf8').length;
  fs.appendFileSync(path.join(folder,'commands.queue'),text+'\n');
  await until(() => marker.test(fs.readFileSync(consoleFile,'utf8').slice(offset)), 'console response: '+text);
}
function record(name, details={}) { cases.push({name,...details}); console.log(JSON.stringify({passed:true,case:cases.length,name,...details})); }
async function connect(name, mods=[], id=device(name)) {
  const s={name,device:id,joined:false,sent:false,ended:false,error:'',kick:'',sentAt:0};
  const c=s.client=mc.createClient({host:'127.0.0.1',port:Number(port),version,username:name,auth:'offline',disableChatSigning:true,checkTimeoutInterval:30000});
  clients.add(c);
  c.on('error',e => {s.error=String(e);});
  for (const event of ['disconnect','kick_disconnect']) c.on(event,p => {s.kick=JSON.stringify(p);});
  c.on('end',()=>{s.ended=true;clients.delete(c);});
  c.on('ping',p=>c.write('pong',{id:p.id}));
  c.on('transaction',p=>c.write('transaction',{...p,accepted:true}));
  c.on('position',p=>{if(p.teleportId!==undefined)c.write('teleport_confirm',{teleportId:p.teleportId});});
  c.on('login',()=>{s.joined=true;c.write('custom_payload',{channel:'minecraft:register',data:Buffer.from('qzguard:main')});});
  c.on('custom_payload',p=>{
    if(p.channel!=='qzguard:main'||s.sent)return;
    try {
      assert.equal(p.data.length,138);assert.equal(p.data.readUInt32BE(0),0x515a4731);
      assert.equal(p.data[4],2);assert.equal(p.data[5],1);assert.equal(p.data.readUInt16BE(6),64);
      assert.equal(p.data.readUInt16BE(72),64);
      const nonce=p.data.subarray(8,72).toString();assert(/^[0-9a-f]{64}$/.test(nonce));
      assert(/^[0-9a-f]{64}$/.test(p.data.subarray(74).toString()));
      c.write('custom_payload',{channel:p.channel,data:Buffer.concat([Buffer.from([0x51,0x5a,0x47,0x31,2,2]),str(nonce),Buffer.from([1]),list(['qizhangverdict',...mods]),list([]),list([]),str(id)])});
      s.sent=true;s.sentAt=performance.now();
    }catch(e){s.error=String(e);c.end('QA malformed challenge');}
  });
  await until(()=>s.sent||s.ended,'challenge or login rejection for '+name);
  return s;
}
async function close(s) {
  if(!s.ended)s.client.end('QA complete');
  await until(()=>s.ended,'client clean disconnect'); await pause(350);
}
async function accepted(s, minimumMs=0) {
  await until(()=>associated(s)||s.ended,'new report device association saved');
  const wait=minimumMs-(performance.now()-s.sentAt);if(wait>0)await pause(wait);
  assert(s.joined&&s.sent&&!s.ended&&!s.error,`expected accepted synthetic client ${s.name}: ${s.kick||s.error}`);
  assert(associated(s),'accepted client device association must persist');
  return {onlineSecondsAfterReport:Number(((performance.now()-s.sentAt)/1000).toFixed(3)),deviceAssociationPersisted:true};
}
async function denied(s, reason) {
  await until(()=>s.ended,'expected denial for '+s.name);
  assert(reason.test(s.kick),`unexpected denial for ${s.name}: ${s.kick}`);
}
async function replaceAction(id, before, after) {
  const lines=fs.readFileSync(blacklistFile,'utf8').split(/\r?\n/);let changed=0;
  const result=lines.map(line=>{const f=line.split('\t');if(f.length===4&&f[1]===id){assert.equal(f[2],before);f[2]=after;changed++;return f.join('\t');}return line;}).join('\n');
  assert.equal(changed,1);fs.writeFileSync(blacklistFile,result);
  await command('qzverdict reload',/configuration reloaded/);
}
async function setSanctions(value) {
  const text=fs.readFileSync(policyFile,'utf8');assert.equal((text.match(/^sanctions\.on-deny=/gm)||[]).length,1);
  fs.writeFileSync(policyFile,text.replace(/^sanctions\.on-deny=.*$/m,'sanctions.on-deny='+value));
  await command('qzverdict reload',/configuration reloaded/);assertPolicy(value);
}
async function main() {
  assertPolicy();
  if(phase==='initial') {
    const catalog=path.join(folder,'catalog-snapshot.tsv');assert.equal(hash(fs.readFileSync(catalog)),fixture.catalogSha256);
    assert.deepEqual(rows(blacklistFile),rows(catalog));assert.equal(rows(blacklistFile).length,37);
    assert.equal(rows(blacklistFile).filter(s=>s.split('\t')[2]==='DENY').length,33);
    assert.equal(rows(blacklistFile).filter(s=>s.split('\t')[2]==='ALERT').length,4);
    fs.copyFileSync(blacklistFile,path.join(folder,'blacklist-first-install.tsv'));
    record('first install generates all 37 exact catalog rows with pinned kind/action/source', {deny:33,alert:4});
    const ids=['cheatutils','cigarette','gamesense','krs','meteorplus','nightx'];
    for(let i=0;i<ids.length;i++) {
      const before=bans().length,s=await connect('QVCatD'+i,[ids[i]]);
      await denied(s,/matches an exact server blacklist rule/);
      await until(()=>hasBan('B',uuid(s.name),'BLACKLIST_DENIED')&&hasBan('V',s.device,'BLACKLIST_DENIED'),'exact account and device records for new catalog DENY');
      assert.equal(bans().length,before+2);record('new catalog DENY '+ids[i]+' persists account and device bans');await close(s);
    }
    for(const [i,id] of ['baritoe','baritone','atianxray','keystrokesmod'].entries()) {
      const before=bans(),offset=fs.readFileSync(consoleFile,'utf8').length,s=await connect('QVCatA'+i,[id]);
      const details=await accepted(s);
      const code=i<2?'AUTOMATION_ALERT':'BLACKLIST_ALERT';
      assert(fs.readFileSync(consoleFile,'utf8').slice(offset).includes('Client policy '+code+' player='+uuid(s.name)));
      assert.deepEqual(bans(),before);record('default '+id+' remains ALERT without bans',{...details,decision:code});await close(s);
    }
    let before=bans(),s=await connect('QVCatOrd',['bigrat','template','antixray','sodium','iris','jei','fabricloader','meteor-client-helper']);
    const normal=await accepted(s,22000);assert.deepEqual(bans(),before);record('ordinary identifiers survive the strict report deadline without bans',normal);await close(s);
    await replaceAction('meteor-client','DENY','OFF');
    await command('qzverdict rule remove legacy:mod:xray',/Removed rule\./);
    assert(!rows(blacklistFile).some(line=>line.split('\t')[1]==='xray'));
    s=await connect('QVCatEdit',['meteor-client','xray']);await accepted(s);assert.deepEqual(bans(),before);await close(s);
    record('administrator OFF and command API deletion take effect before restart');
    await replaceAction('baritone','ALERT','DENY');
    before=bans();s=await connect('QVCatHist',[],sharedBan);await accepted(s);await close(s);
    s=await connect('QVCatBan',['baritone'],sharedBan);await denied(s,/matches an exact server blacklist rule/);
    await until(()=>hasBan('B',uuid('QVCatHist'),'AUTOMATION_DENIED')&&hasBan('B',uuid('QVCatBan'),'AUTOMATION_DENIED')&&hasBan('V',sharedBan,'AUTOMATION_DENIED'),'automation BAN must persist exactly two accounts and shared device');
    assert.equal(bans().length,before.length+3);record('explicit automation DENY with BAN links historical two accounts and one device',{addedBanRows:3,reason:'AUTOMATION_DENIED'});
    fs.copyFileSync(blacklistFile,path.join(folder,'blacklist-after-administrator.tsv'));
    fs.writeFileSync(path.join(folder,'restart-expectations.json'),JSON.stringify({blacklistSha256:hash(fs.readFileSync(blacklistFile)),banRows:bans().length,automationReasonRows:3},null,2));
    await close(s);
  } else {
    const expected=JSON.parse(fs.readFileSync(path.join(folder,'restart-expectations.json')));
    assert.equal(hash(fs.readFileSync(blacklistFile)),expected.blacklistSha256);
    assert.equal(bans().length,expected.banRows);
    assert(rows(blacklistFile).some(s=>s.startsWith('mod\tmeteor-client\tOFF\t')));
    assert(!rows(blacklistFile).some(s=>s.split('\t')[1]==='xray'));
    record('administrator OFF and removed rule remain byte-identical after normal server restart');
    for(const [name,label] of [['QVCatHist','historical linked account remains banned'],['QVCatBan','automation offender remains banned with changed device']]) {
      const s=await connect(name,[],device('different-'+name));await denied(s,/account is banned/);record(label);await close(s);
    }
    let s=await connect('QVCatFresh',[],sharedBan);await denied(s,/device identifier is banned/);
    await until(()=>hasBan('B',uuid(s.name),'DEVICE_BANNED'),'new account on banned device is also associated');record('new account on the banned device is rejected after restart');await close(s);
    let before=bans();s=await connect('QVCatEdit2',['meteor-client','xray']);const kept=await accepted(s,22000);
    assert.deepEqual(bans(),before);record('preserved administrator OFF and deletion still allow reports beyond deadline',kept);await close(s);
    await setSanctions('KICK');before=bans();
    s=await connect('QVCatKHist',[],sharedKick);await accepted(s);await close(s);
    s=await connect('QVCatKick',['baritone'],sharedKick);await denied(s,/matches an exact server blacklist rule/);
    await until(()=>associated(s),'KICK report association was persisted');assert.deepEqual(bans(),before);
    record('explicit automation DENY with KICK rejects without adding permanent bans');await close(s);
    s=await connect('QVCatKick',[],sharedKick);const kicked=await accepted(s,22000);assert.deepEqual(bans(),before);
    record('KICK account and same device can reconnect beyond the strict report deadline',kicked);await close(s);
    s=await connect('QVCatKHist',[],sharedKick);await accepted(s);assert.deepEqual(bans(),before);record('KICK does not ban the historical associated account');await close(s);
    await setSanctions('BAN');assert.deepEqual(bans(),before);
    assert.equal(hash(fs.readFileSync(blacklistFile)),expected.blacklistSha256);
    record('BAN policy restored and administrator blacklist edits remain unchanged');
  }
  assertPolicy();assert.equal(hash(fs.readFileSync(policyFile)),fixture.qaPolicySha256);
  assert.equal(cases.length,phase==='initial'?14:9);
}
main().then(()=>{
  fs.writeFileSync(path.join(folder,`protocol-${phase}.json`),JSON.stringify({passed:true,phase,version,cases,caseCount:cases.length,
    exactDefaultCatalogChecked:phase==='initial',scope:'Real loopback TCP and server state assertions; synthetic accounts/devices; two explicitly raised batch quotas; KICK only in named control window.'},null,2));
}).catch(e=>{
  console.error(e);process.exitCode=1;
  fs.writeFileSync(path.join(folder,`protocol-${phase}.json`),JSON.stringify({passed:false,phase,version,cases,caseCount:cases.length,error:String(e)},null,2));
}).finally(async()=>{for(const c of clients)c.end('QA complete');await pause(300);});
