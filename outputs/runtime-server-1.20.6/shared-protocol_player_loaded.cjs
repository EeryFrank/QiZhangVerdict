'use strict';
// SPDX-License-Identifier: GPL-3.0-only

/** Synthetic TCP client lifecycle acknowledgements; no terrain rendering is implied. */
function attachPositionAcknowledgements(client, sendsPlayerLoaded) {
  let awaitingLoaded = true;
  client.on('login', () => { awaitingLoaded = true; });
  client.on('respawn', () => { awaitingLoaded = true; });
  client.on('position', packet => {
    if (packet.teleportId === undefined) return;
    client.write('teleport_confirm', { teleportId: packet.teleportId });
    if (sendsPlayerLoaded && awaitingLoaded) {
      client.write('player_loaded', {});
      awaitingLoaded = false;
    }
  });
}

module.exports = { attachPositionAcknowledgements };
