'use strict';
// SPDX-License-Identifier: GPL-3.0-only

/**
 * Observe actual decoded disconnect packets before minecraft-protocol's bundle
 * queue releases its public packet events. Never flushes or changes that queue.
 *
 * Client.state creates a fresh deserializer before emitting the state event.
 * Attach once to each such decoder, including the already-created initial one.
 * This does not listen to socket/end events or use server logs as a reason.
 */
function observeDisconnects(client, onObserved) {
  if (!client || typeof client.on !== 'function' || typeof onObserved !== 'function') {
    throw new TypeError('Expected minecraft-protocol client and callback');
  }
  const decoders = new Set();
  let detached = false;

  function decoded(packet) {
    const name = packet?.metadata?.name;
    const state = packet?.metadata?.state;
    if (name !== 'disconnect' && name !== 'kick_disconnect') return;
    if (!['login', 'configuration', 'play'].includes(state)) return;
    const payload = packet.data;
    if (!payload || !Object.prototype.hasOwnProperty.call(payload, 'reason') || payload.reason === undefined) return;

    // minecraft-protocol's earlier data listener has already transformed
    // packet.data into params and set metadata.name/state. Clone the reason so
    // an observer callback cannot mutate the decoded packet or queued bundle.
    const reason = structuredClone(payload.reason);
    const reasonJson = JSON.stringify(reason, (_key, value) =>
      typeof value === 'bigint' ? { $bigint: value.toString() } : value);
    onObserved({
      source: 'minecraft-protocol.deserializer.data',
      packetName: name,
      packetState: state,
      clientState: client.state,
      reason,
      reasonJson
    });
  }

  function attach() {
    if (detached) return;
    const decoder = client.deserializer;
    if (!decoder || typeof decoder.on !== 'function') throw new TypeError('Client has no active deserializer');
    if (decoders.has(decoder)) return;
    decoders.add(decoder);
    decoder.on('data', decoded);
  }

  client.on('state', attach);
  attach();
  return function detach() {
    if (detached) return;
    detached = true;
    client.removeListener('state', attach);
    for (const decoder of decoders) decoder.removeListener('data', decoded);
    decoders.clear();
  };
}

module.exports = { observeDisconnects };
