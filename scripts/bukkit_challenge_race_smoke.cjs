// SPDX-License-Identifier: GPL-3.0-only
// Real TCP, latest-request coalescing model; deliberately not the production ClientReporter process.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { performance } = require('node:perf_hooks');
const mc = require('minecraft-protocol');
const folder = process.argv[2];
const fixture = JSON.parse(fs.readFileSync(path.join(folder, 'fixture.json')));
assert.equal(require('minecraft-protocol/package.json').version, '1.66.2');
assert.equal(fixture.version, '1.21.1');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const device = hash('qizhang-challenge-race-synthetic-device');
const policyFile = path.join(folder, 'plugins', 'QiZhangVerdict', 'guard.properties');
const logFile = path.join(folder, 'console.log');
const stateFile = path.join(folder, 'plugins', 'QiZhangVerdict', 'accounts.state');
const result = { expectedOutcomeConfirmed: false, passed: false, knownBugReproduced: false,
  expected: fixture.expectedOutcome, packets: [], controls: [], checks: [], syntheticReport: true };
let client, ended = false, kick = '', error = '', enteredPlay = false, windowOpen = false;
let current = null, latest = null, checkpoint = false, timingFailure = false, joinedAt = null, endedAt = null;
let reportsSent = 0, sentAt = null;
function offlineUuid(name) {
  const b = crypto.createHash('md5').update('OfflinePlayer:' + name).digest();
  b[6] = (b[6] & 15) | 48; b[8] = (b[8] & 63) | 128;
  const h = b.toString('hex'); return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;
}
const id = offlineUuid('QVRace');
function str(text) { const b = Buffer.from(text); const n = Buffer.alloc(2); n.writeUInt16BE(b.length); return Buffer.concat([n,b]); }
function list(values) { const n = Buffer.alloc(2); n.writeUInt16BE(values.length); return Buffer.concat([n,...values.map(str)]); }
async function until(fn, label, ms = 15000) {
  const end = performance.now() + ms;
  while (!fn()) { if (performance.now() > end) throw Error('Timeout: ' + label); await pause(25); }
}
function record(name) { result.checks.push(name); console.log('PASS ' + result.checks.length + ' ' + name); }
function associated() {
  if (!fs.existsSync(stateFile)) return false;
  return fs.readFileSync(stateFile, 'utf8').split(/\r?\n/).some(row => row === `D\t${id}\t${device}`);
}
function bans() {
  return fs.existsSync(stateFile) ? fs.readFileSync(stateFile, 'utf8').split(/\r?\n/).filter(row => /^[BV]\t/.test(row)).length : 0;
}
function policy() { assert.equal(hash(fs.readFileSync(policyFile)), fixture.policySha256, 'All default guard policy bytes must remain unchanged'); }
async function main() {
  policy(); record('complete default policy unchanged before join');
  client = mc.createClient({ host: fixture.host, port: fixture.port, username: 'QVRace', version: fixture.version,
    auth: 'offline', disableChatSigning: true, checkTimeoutInterval: 30000 });
  client.on('error', e => { error = String(e); });
  client.on('end', () => { ended = true; endedAt = performance.now(); });
  client.on('kick_disconnect', p => { kick = JSON.stringify(p.reason); });
  client.on('disconnect', p => { kick = JSON.stringify(p.reason); });
  client.on('ping', p => client.write('pong', { id: p.id }));
  client.on('login', () => {
    joinedAt = performance.now(); enteredPlay = true;
    // Separate packets preserve registration order, without relying on an unordered channel set.
    client.write('custom_payload', { channel: 'minecraft:register', data: Buffer.from('qzqa:control') });
    client.write('custom_payload', { channel: 'minecraft:register', data: Buffer.from('qzguard:main') });
  });
  client.on('position', p => {
    if (p.teleportId !== undefined) client.write('teleport_confirm', { teleportId: p.teleportId });
  });
  client.on('custom_payload', p => {
    try {
      if (p.channel === 'qzqa:control') {
        const fields = p.data.toString('ascii').split('|');
        const stage = fields[0];
        result.controls.push({ stage, tick: Number(fields[1]), joinedTick: Number(fields[2]), timeMs: performance.now() });
        if (stage === 'BEFORE_RELOAD') { assert(!windowOpen && current === null); windowOpen = true; }
        else if (stage === 'AFTER_RELOAD') { assert(windowOpen && current !== null); windowOpen = false; }
        else if (stage === 'CHECKPOINT') checkpoint = true;
        else if (stage === 'TIMING_NOT_ESTABLISHED') timingFailure = true;
        else throw Error('Unexpected QA marker');
        return;
      }
      if (p.channel !== 'qzguard:main') return;
      const b = p.data;
      assert.equal(b.length, 138); assert.equal(b.readUInt32BE(0), 0x515a4731);
      assert.equal(b[4], 2); assert.equal(b[5], 1); assert.equal(b.readUInt16BE(6), 64); assert.equal(b.readUInt16BE(72), 64);
      const nonce = b.subarray(8,72).toString('ascii');
      assert(/^[0-9a-f]{64}$/.test(nonce)); assert(/^[0-9a-f]{64}$/.test(b.subarray(74).toString('ascii')));
      latest = { nonce, payloadHash: hash(b) };
      if (windowOpen) { assert.equal(current, null, 'Exactly one challenge must be sent inside the reload window'); current = latest; }
      result.packets.push({ index: result.packets.length, duringReload: windowOpen, afterCheckpoint: checkpoint,
        payloadSha256: hash(b), timeMs: performance.now() });
    } catch (e) { error = String(e); }
  });
  await until(() => checkpoint || timingFailure || ended || error, 'QA checkpoint', 15000);
  assert(!timingFailure && !ended && !error, 'Timing was not established or connection failed: ' + (error || kick));
  assert(enteredPlay && current && latest && !windowOpen);
  assert(result.controls.some(c => c.stage === 'BEFORE_RELOAD' && c.tick - c.joinedTick < 2));
  assert(result.controls.some(c => c.stage === 'CHECKPOINT' && c.tick - c.joinedTick >= 3));
  await pause(200);
  const text = fs.readFileSync(logFile, 'utf8');
  assert(/QA_RELOADED .*command=true/.test(text));
  assert(/configuration reloaded.*companion=required, vm=DENY/.test(text));
  assert(/deviceRequired=true/.test(text));
  record('actual reload completed before original two-tick callback with strict policy');
  assert(result.packets.length >= 3, 'Require initial, reload, and actual delayed challenge packets');
  assert(result.packets[0].payloadSha256 !== current.payloadHash, 'Reload must issue a different nonce');
  const lastMatchesCurrent = latest.nonce === current.nonce;
  result.lastChallengeMatchesReload = lastMatchesCurrent;
  assert.equal(lastMatchesCurrent, fixture.expectedOutcome === 'fixed', 'Unexpected actual last challenge order');
  record(fixture.expectedOutcome === 'fixed' ? 'actual delayed send preserves current B' : 'frozen product actually sends superseded A after B');
  const report = Buffer.concat([Buffer.from([0x51,0x5a,0x47,0x31,2,2]), str(latest.nonce), Buffer.from([1]),
    list(['qizhangverdict']), list([]), list([]), str(device)]);
  // Simulate a slow/coalesced probe: only the last received challenge is answered, once, after the real timer fires.
  client.write('custom_payload', { channel: 'qzguard:main', data: report }); reportsSent++; sentAt = performance.now();
  if (fixture.expectedOutcome === 'fixed') {
    await until(() => associated() || ended || error, 'real persisted synthetic D association');
    assert(associated() && !ended && !error, 'Current challenge did not create an accepted association');
    record('server persists the exact synthetic account/device association');
    await pause(Math.max(0, 22000 - (performance.now() - sentAt)));
    assert(!ended && !error && reportsSent === 1 && associated());
    const offset = fs.readFileSync(logFile, 'utf8').length;
    fs.appendFileSync(path.join(folder, 'commands.queue'), 'qzverdict status\n');
    await until(() => /QiZhangVerdict sessions=1,.*companion=required, vm=DENY.*accountBans=0, deviceBans=0, deviceRequired=true/.test(fs.readFileSync(logFile, 'utf8').slice(offset)), 'fresh online strict status');
    result.onlineSecondsAfterReport = Number(((performance.now() - sentAt) / 1000).toFixed(3));
    assert(result.onlineSecondsAfterReport >= 22); record('one accepted report stays online past the unmodified twenty-second deadline');
  } else {
    await until(() => ended || error, 'actual strict report timeout', 30000);
    assert(ended && !error && /Required companion report timed out/i.test(kick), 'Expected actual plugin timeout kick: ' + (error || kick));
    assert(!associated(), 'A stale report must not create a device association');
    result.secondsJoinToTimeout = Number(((endedAt - joinedAt) / 1000).toFixed(3));
    assert(result.secondsJoinToTimeout >= 19.5, 'Unexpected early disconnect');
    record('superseded last report actually expires without accepted device association');
  }
  policy(); assert.equal(bans(), 0); record('default policy remains byte-identical and timeout does not create bans');
  result.reportsSent = reportsSent; result.deviceAssociationPersisted = associated(); result.kick = kick;
  result.expectedOutcomeConfirmed = true; result.passed = fixture.expectedOutcome === 'fixed';
  result.knownBugReproduced = fixture.expectedOutcome === 'old-bug';
}
main().catch(e => { result.error = String(e.stack || e); console.error(result.error); process.exitCode = 1; })
  .finally(async () => {
    if (client && !ended) { client.end('QA complete'); await until(() => ended, 'client close', 5000).catch(() => { result.expectedOutcomeConfirmed = false; result.passed = false; process.exitCode = 1; }); }
    if (error) { result.expectedOutcomeConfirmed = false; result.passed = false; result.knownBugReproduced = false; process.exitCode = 1; }
    result.clientEnded = ended; result.transportError = error; result.timingNotEstablished = timingFailure;
    fs.writeFileSync(path.join(folder, 'protocol-result.json'), JSON.stringify(result, null, 2) + '\n');
  });
