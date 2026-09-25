'use strict';
// SPDX-License-Identifier: GPL-3.0-only
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { attachPositionAcknowledgements } = require('./protocol_player_loaded.cjs');

function fixture(enabled) {
  const client = new EventEmitter();
  const writes = [];
  client.write = (packet, data) => writes.push({ packet, data });
  attachPositionAcknowledgements(client, enabled);
  return { client, writes };
}
const checks = [];
function check(name, operation) { operation(); checks.push(name); }
const modern = fixture(true);
modern.client.emit('login');
check('login alone does not claim loaded', () => assert.equal(modern.writes.length, 0));
modern.client.emit('position', { teleportId: 42 });
check('first position confirms teleport before empty loaded packet', () => assert.deepEqual(modern.writes, [
  { packet: 'teleport_confirm', data: { teleportId: 42 } }, { packet: 'player_loaded', data: {} }
]));
modern.client.emit('position', { teleportId: 43 });
check('later correction confirms teleport without duplicate loaded', () => assert.deepEqual(modern.writes.slice(2), [
  { packet: 'teleport_confirm', data: { teleportId: 43 } }
]));
modern.client.emit('respawn');
check('respawn waits for next position', () => assert.equal(modern.writes.length, 3));
modern.client.emit('position', { teleportId: 44 });
check('respawn next position emits one loaded packet', () => assert.deepEqual(modern.writes.slice(3), [
  { packet: 'teleport_confirm', data: { teleportId: 44 } }, { packet: 'player_loaded', data: {} }
]));
modern.client.emit('login'); modern.client.emit('position', { teleportId: 45 });
check('new login resets lifecycle', () => assert.equal(modern.writes.filter(x => x.packet === 'player_loaded').length, 3));
const old = fixture(false);
old.client.emit('login'); old.client.emit('position', { teleportId: 1 });
old.client.emit('respawn'); old.client.emit('position', { teleportId: 2 });
check('feature-disabled versions keep only existing teleport acknowledgements', () => assert.deepEqual(old.writes, [
  { packet: 'teleport_confirm', data: { teleportId: 1 } }, { packet: 'teleport_confirm', data: { teleportId: 2 } }
]));
const incomplete = fixture(true);
incomplete.client.emit('position', {});
check('missing teleport does not invent acknowledgement or loaded event', () => assert.equal(incomplete.writes.length, 0));
incomplete.client.emit('position', { teleportId: 0 });
check('zero teleport ID is valid and completes pending lifecycle', () => assert.deepEqual(incomplete.writes, [
  { packet: 'teleport_confirm', data: { teleportId: 0 } }, { packet: 'player_loaded', data: {} }
]));
console.log(JSON.stringify({ passed: checks.length, checks, scope: 'In-memory EventEmitter client tests of production QA helper; no TCP or game executed' }, null, 2));
