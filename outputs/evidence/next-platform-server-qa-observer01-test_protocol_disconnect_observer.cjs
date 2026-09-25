'use strict';
// SPDX-License-Identifier: GPL-3.0-only
// Real dependency serializer/parser replay. No sockets, Java or Minecraft.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const Client = require('minecraft-protocol/src/client');
const { createSerializer } = require('minecraft-protocol/src/transforms/serializer');
const { observeDisconnects } = require('./protocol_disconnect_observer.cjs');

const output = path.resolve(process.argv[2] || 'E:/CodexTemp/QiZhangVerdict/next-platforms/protocol-observer/01');
const base = path.resolve('E:/CodexTemp/QiZhangVerdict/next-platforms/protocol-observer');
const relative = path.relative(base, output);
assert(relative && !relative.startsWith('..') && !path.isAbsolute(relative), 'Use a new output under protocol-observer');
assert(!fs.existsSync(output), 'Preserve earlier outputs; choose a fresh directory');
fs.mkdirSync(output, { recursive: true });
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const cases = [];
const clients = [];
const flush = () => new Promise(resolve => setImmediate(resolve));
const reasonText = 'Too many simultaneous accounts from this IP';
const modernReason = () => ({ type: 'string', value: reasonText });

function fixture(version, state) {
  const client = new Client(false, version);
  client.state = state;
  const observed = [], named = [], errors = [];
  client.on('error', e => errors.push(String(e)));
  client.on('kick_disconnect', p => named.push({ name: 'kick_disconnect', packet: p }));
  client.on('disconnect', p => named.push({ name: 'disconnect', packet: p }));
  const detach = observeDisconnects(client, entry => observed.push(entry));
  clients.push({ client, detach });
  return { client, observed, named, errors, detach };
}

async function send(f, name, params) {
  const serializer = createSerializer({ isServer: true, version: f.client.version, state: f.client.state });
  let encoded = false;
  serializer.on('error', e => { throw e; });
  serializer.on('data', buffer => { encoded = true; f.client.deserializer.write(buffer); });
  serializer.end({ name, params });
  await flush();
  assert(encoded, 'Packet must pass through real serializer');
  assert.deepEqual(f.errors, [], 'No parser errors allowed');
}

function check(name, body) {
  body(); cases.push({ name, passed: true });
}

async function main() {
  const dependency = require('minecraft-protocol/package.json');
  assert.equal(dependency.version, '1.66.2', 'This proof is scoped to the reviewed dependency version');
  const normal = fixture('1.20.4', 'play');
  await send(normal, 'kick_disconnect', { reason: modernReason() });
  check('1.20.4 normal PLAY event and observer both receive exact decoded reason', () => {
    assert.equal(normal.named.length, 1); assert.equal(normal.observed.length, 1);
    assert.deepEqual(normal.observed[0].reason, modernReason());
    assert.equal(normal.observed[0].packetName, 'kick_disconnect');
    assert.equal(normal.observed[0].packetState, 'play');
    assert.equal(normal.observed[0].source, 'minecraft-protocol.deserializer.data');
    assert(normal.observed[0].reasonJson.includes(reasonText));
  });
  check('Observer payload is detached from the library event payload', () => {
    normal.observed[0].reason.value = 'observer-only mutation';
    assert.equal(normal.named[0].packet.reason.value, reasonText);
  });

  const bundled = fixture('1.20.4', 'play');
  await send(bundled, 'bundle_delimiter', {});
  await send(bundled, 'kick_disconnect', { reason: modernReason() });
  const withheld = {
    publicDisconnectEvents: bundled.named.length,
    decodedDisconnectObservations: bundled.observed.length,
    queuedPacketNames: bundled.client._mcBundle.map(p => p.metadata.name)
  };
  check('Unclosed bundle withholds normal event while observer captures actual decoded kick', () => {
    assert.equal(bundled.named.length, 0); assert.equal(bundled.observed.length, 1);
    assert.equal(bundled.observed[0].reason.value, reasonText);
    assert.deepEqual(withheld.queuedPacketNames, ['bundle_delimiter', 'kick_disconnect']);
    assert.equal(bundled.client._hasBundlePacket, true);
  });
  bundled.client.emit('end', 'socketClosed');
  check('Socket end neither fabricates another reason nor flushes the library queue', () => {
    assert.equal(bundled.observed.length, 1); assert.equal(bundled.named.length, 0);
    assert.equal(bundled.client._mcBundle.length, 2);
  });
  await send(bundled, 'bundle_delimiter', {});
  check('Closing bundle retains normal library delivery without duplicate observer capture', () => {
    assert.equal(bundled.named.length, 1); assert.equal(bundled.observed.length, 1);
    assert.equal(bundled.client._mcBundle.length, 0);
  });

  const transitioned = fixture('1.20.4', 'login');
  await send(transitioned, 'disconnect', { reason: JSON.stringify({ text: 'login reason' }) });
  transitioned.client.state = 'configuration';
  await send(transitioned, 'disconnect', { reason: { type: 'string', value: 'config reason' } });
  transitioned.client.state = 'play';
  await send(transitioned, 'kick_disconnect', { reason: modernReason() });
  check('Fresh LOGIN CONFIGURATION PLAY deserializers are observed once each', () => {
    assert.deepEqual(transitioned.observed.map(x => x.packetState), ['login', 'configuration', 'play']);
    assert.deepEqual(transitioned.observed.map(x => x.packetName), ['disconnect', 'disconnect', 'kick_disconnect']);
    assert.equal(transitioned.named.length, 3);
  });
  transitioned.client.emit('state', 'play', 'play');
  await send(transitioned, 'kick_disconnect', { reason: modernReason() });
  check('Repeated state notification does not add a duplicate decoder listener', () => {
    assert.equal(transitioned.observed.length, 4); assert.equal(transitioned.named.length, 4);
  });

  for (const version of ['1.12.2', '1.19.2']) {
    const old = fixture(version, 'play');
    await send(old, 'kick_disconnect', { reason: JSON.stringify({ text: 'legacy exact reason' }) });
    check(version + ' legacy string reason and normal event remain unchanged', () => {
      assert.equal(old.named.length, 1); assert.equal(old.observed.length, 1);
      assert.equal(old.observed[0].reason, JSON.stringify({ text: 'legacy exact reason' }));
      assert.equal(old.named[0].packet.reason, old.observed[0].reason);
    });
  }
  const empty = fixture('1.20.4', 'play');
  empty.client.emit('end', 'socketClosed');
  empty.client.emit('disconnect', { reason: 'manually emitted event is not wire evidence' });
  await send(empty, 'keep_alive', { keepAliveId: 1n });
  check('End-only, fabricated named event and actual unrelated packet produce no observation', () => {
    assert.equal(empty.observed.length, 0);
  });
  empty.detach(); empty.detach();
  await send(empty, 'kick_disconnect', { reason: modernReason() });
  empty.client.state = 'configuration';
  await send(empty, 'disconnect', { reason: { type: 'string', value: 'after detach' } });
  check('Idempotent detach stops current and future decoder observation without altering normal delivery', () => {
    assert.equal(empty.observed.length, 0); assert.equal(empty.named.length, 3);
  });
  return { withheldBundleProof: withheld, dependencyVersion: dependency.version };
}

(async () => {
  const report = {
    schemaVersion: 1,
    scope: 'In-memory official dependency serializer/deserializer tests; no sockets, Java, Minecraft or original-run packet replay.',
    passed: false, javaStarted: false, minecraftStarted: false, socketsOpened: false,
    syntheticReasonsOnly: true, originalFabricFailureRootCauseConfirmed: false,
    originalFailureBoundary: 'This proves the dependency bundle/event behavior, not that the original fabric-01 run contained an unfinished bundle; that run had no decoder trace.',
    cases,
    files: [__filename, path.join(__dirname, 'protocol_disconnect_observer.cjs'),
      require.resolve('minecraft-protocol/src/client'), require.resolve('minecraft-protocol/src/client/play'),
      require.resolve('minecraft-protocol/package.json')].map(file => ({ path: file, sha256: hash(file), bytes: fs.statSync(file).size }))
  };
  try {
    Object.assign(report, await main());
    report.passed = true;
  } catch (error) {
    report.error = String(error.stack || error); process.exitCode = 1;
  } finally {
    for (const f of clients) f.detach();
    for (const file of [__filename, path.join(__dirname, 'protocol_disconnect_observer.cjs')]) {
      fs.copyFileSync(file, path.join(output, path.basename(file)), fs.constants.COPYFILE_EXCL);
    }
    report.completedAt = new Date().toISOString();
    fs.writeFileSync(path.join(output, 'result.json'), JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
    console.log(JSON.stringify({ passed: report.passed, cases: cases.length, output, error: report.error }));
  }
})();
