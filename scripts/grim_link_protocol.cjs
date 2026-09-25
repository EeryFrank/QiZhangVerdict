// Isolated loopback QA: exercise a real Grim check and the shipped punishment template.
const mc = require('minecraft-protocol');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');
const [version, port, folder, phase] = process.argv.slice(2);
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const hash = s => crypto.createHash('sha256').update(s).digest('hex');
const shared = hash('qizhang-verdict-synthetic-grim-device');
const clients = new Set(), cases = [];
const dataFolder = path.join(folder, 'plugins', 'QiZhangVerdict');
const defaultPolicySha = '47310c31b47287ab805bfdbf8ddddf80e8169385bd9c862239a0a0075644da4e';
function str(s) { const data = Buffer.from(s); const n = Buffer.alloc(2); n.writeUInt16BE(data.length); return Buffer.concat([n, data]); }
function list(a) { const n = Buffer.alloc(2); n.writeUInt16BE(a.length); return Buffer.concat([n, ...a.map(str)]); }
function uuid(name) {
  const b = crypto.createHash('md5').update('OfflinePlayer:' + name).digest();
  b[6] = (b[6] & 15) | 48; b[8] = (b[8] & 63) | 128;
  const h = b.toString('hex'); return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;
}
async function until(test, message, timeout = 12000) {
  const end = performance.now() + timeout;
  while (!test() && performance.now() < end) await pause(40);
  assert(test(), message);
}
async function command(s) { fs.appendFileSync(path.join(folder, 'commands.queue'), s + '\n'); await pause(1200); }
async function connect(name, device = shared) {
  const s = {name, joined:false, sent:false, ended:false, kick:'', error:''};
  const c = s.client = mc.createClient({host:'127.0.0.1', port:Number(port), version, username:name,
    auth:'offline', disableChatSigning:true, checkTimeoutInterval:30000});
  clients.add(c);
  c.on('error', e => { s.error = String(e); });
  for (const event of ['disconnect', 'kick_disconnect']) c.on(event, p => { s.kick = JSON.stringify(p); });
  c.on('end', () => { s.ended = true; clients.delete(c); });
  c.on('ping', p => c.write('pong', {id:p.id}));
  c.on('transaction', p => c.write('transaction', p));
  c.on('login', () => { s.joined = true; c.write('custom_payload', {channel:'minecraft:register', data:Buffer.from('qzguard:main')}); });
  c.on('position', p => { if (p.teleportId !== undefined) c.write('teleport_confirm', {teleportId:p.teleportId}); });
  c.on('custom_payload', p => {
    if (p.channel !== 'qzguard:main' || s.sent) return;
    try {
      assert.equal(p.data.length, 138); assert.equal(p.data.readUInt32BE(0), 0x515a4731);
      assert.equal(p.data[4], 2); assert.equal(p.data[5], 1); assert.equal(p.data.readUInt16BE(6), 64);
      const nonce = p.data.subarray(8,72).toString(); assert(/^[0-9a-f]{64}$/.test(nonce));
      assert.equal(p.data.readUInt16BE(72), 64); assert(/^[0-9a-f]{64}$/.test(p.data.subarray(74).toString()));
      c.write('custom_payload', {channel:p.channel, data:Buffer.concat([Buffer.from([0x51,0x5a,0x47,0x31,2,2]),
        str(nonce), Buffer.from([1]), list(['qizhangverdict']), list([]), list([]), str(device)])}); s.sent = true;
    } catch(e) { s.error = String(e); c.end('QA invalid challenge'); }
  });
  await until(() => s.ended || s.sent, 'report or rejection must arrive'); await pause(1000); return s;
}
function allowed(s, label) { assert(s.joined && s.sent && !s.ended && !s.error, `${label}: ${JSON.stringify({...s,client:undefined})}`); cases.push(label); }
async function close(s) { if (!s.ended) s.client.end('QA complete'); await pause(700); }
async function denied(s, label, reason = /banned/i) {
  await until(() => s.ended, label);
  assert(reason.test(s.kick), `${label}: ${s.kick}`); cases.push(label);
}
function stateText() { return fs.readFileSync(path.join(dataFolder, 'accounts.state'), 'utf8'); }
function banRows() { return stateText().split(/\r?\n/).filter(s => /^[BV]\t/.test(s)); }
function grimViolationAlerts(text) {
  return text.replace(/\u001b\[[0-9;]*m|§./g, '').split(/\r?\n/)
    .filter(line => /QVGrimMain\s+failed\s+BadPacketsA\b/.test(line));
}
function thresholdObserved(alerts) {
  return alerts.some(line => { const vl = /\(x([0-9]+(?:\.[0-9]+)?)\)/.exec(line); return vl && Number(vl[1]) >= 120; });
}
async function main() {
  const policyBefore = hash(fs.readFileSync(path.join(dataFolder, 'guard.properties')));
  assert.equal(policyBefore, defaultPolicySha, 'every byte of the pinned Guard default policy must match');
  if (phase === 'trigger') {
    const linked = await connect('QVGrimLinked'); allowed(linked, 'historical linked account accepted'); await close(linked);
    const player = await connect('QVGrimMain'); allowed(player, 'trigger account accepted before violations');
    await pause(22000); allowed(player, 'clean connection survives default 20 second companion deadline');
    assert.equal(banRows().length, 0, 'no bans before injected violation');
    const consoleFile = path.join(folder, `console-${phase}.log`);
    const triggerOffset = fs.readFileSync(consoleFile, 'utf8').length;
    // The upstream BadPacketsA check flags duplicate held-item slot packets in both locked Grim versions.
    // Space packets apart: exercise the actual shipped 120:0 threshold, not a reduced test threshold.
    let packets = 0;
    while (!player.ended && packets < 150) {
      player.client.write('held_item_slot', {slotId:1}); packets++; await pause(160);
    }
    await denied(player, 'real Grim violation executes the QiZhangVerdict ban command', /\[QiZhangVerdict\] Grim-BadPackets/);
    assert(packets >= 120, 'ban must not precede the shipped violation threshold');
    await until(() => thresholdObserved(grimViolationAlerts(fs.readFileSync(consoleFile, 'utf8').slice(triggerOffset))),
      'actual Grim console alert must identify BadPacketsA at or above 120 violations');
    const alerts = grimViolationAlerts(fs.readFileSync(consoleFile, 'utf8').slice(triggerOffset));
    cases.push('Grim console independently identifies BadPacketsA reaching the shipped threshold');
    await until(() => banRows().length === 3, 'two linked accounts and one device must be persisted');
    const rows = banRows();
    for (const id of [uuid('QVGrimMain'), uuid('QVGrimLinked'), shared]) assert(rows.some(r => r.includes('\t' + id + '\t')), 'expected linked ban target');
    assert(rows.every(r => r.endsWith(Buffer.from('Grim-BadPackets').toString('base64'))), 'all bans originate from the Grim punishment reason');
    cases.push('real Grim punishment persists both historical accounts and their shared synthetic device');
    fs.writeFileSync(path.join(folder, 'trigger-details.json'), JSON.stringify({packets, threshold:120, intervalMilliseconds:160, grimAlerts:alerts}, null, 2));
  } else if (phase === 'restart') {
    await denied(await connect('QVGrimMain', hash('new-device')), 'account ban survives restart and a new device');
    await denied(await connect('QVGrimLinked', hash('new-device')), 'historical linked account remains banned after restart');
    await denied(await connect('QVGrimFresh'), 'new account using banned device is denied after restart');
    const clean = await connect('QVGrimClean', hash('independent-device')); allowed(clean, 'unrelated device remains allowed on the same IP'); await close(clean);
    for (const name of ['QVGrimMain', 'QVGrimLinked', 'QVGrimFresh']) await command('qzverdict unban ' + uuid(name));
    await command('qzverdict unban device:' + shared);
    const restored = await connect('QVGrimMain'); allowed(restored, 'explicit account and device unban restores access'); await close(restored);
    await until(() => banRows().length === 0, 'explicit unban clears this synthetic test group');
    cases.push('all synthetic account and device bans are cleared on disk after explicit unban');
  } else throw Error('Unknown phase');
  assert.equal(hash(fs.readFileSync(path.join(dataFolder, 'guard.properties'))), policyBefore, 'strict default Guard policy was never edited');
  assert.equal(cases.length, 6, 'all expected assertion groups must finish');
  fs.writeFileSync(path.join(folder, `protocol-${phase}.json`), JSON.stringify({passed:true, phase, version, cases, caseCount:cases.length,
    scope:'Real loopback TCP and upstream Grim BadPacketsA, synthetic device reports; not real hardware attestation or detection accuracy across cheats.'}, null, 2));
  console.log(JSON.stringify({passed:true, phase, cases}));
}
main().catch(e => {console.error(e); process.exitCode = 1;}).finally(async () => { for (const c of clients) c.end('QA complete'); await pause(300); });
