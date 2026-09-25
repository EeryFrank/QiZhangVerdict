// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.fabric;

import cn.qizhang.guard.client.ClientReporter;
import cn.qizhang.guard.minecraft.GuardPayload;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.networking.v1.PacketSender;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientPacketListener;

public final class GuardFabricClient implements ClientModInitializer {
    private final ClientReporter reporter = new ClientReporter();

    @Override public void onInitializeClient() {
        ClientPlayNetworking.registerGlobalReceiver(GuardPayload.TYPE, (payload, context) -> {
            var client = context.client();
            // The response sender belongs to the receiving listener. context.player()
            // reads the current client player and is not an origin-connection proof.
            PacketSender originSender = context.responseSender();
            byte[] challenge = payload.data();
            ClientChallengeDispatch.enqueue(client::execute, originSender, () -> liveSender(client),
                () -> collect(client, originSender, challenge));
        });
    }

    private static PacketSender liveSender(Minecraft client) {
        var connection = client.getConnection();
        return connection == null || client.player == null || !connection.getConnection().isConnected()
            ? null : ClientPlayNetworking.getSender();
    }

    private static boolean current(Minecraft client, PacketSender originSender, ClientPacketListener originConnection) {
        var active = client.getConnection();
        return ClientChallengeDispatch.isCurrentConnection(originSender, originConnection,
            liveSender(client), active, active != null && active.getConnection().isConnected());
    }

    private void collect(Minecraft client, PacketSender originSender, byte[] challenge) {
        var connection = client.getConnection();
        if (!current(client, originSender, connection)) return;
        var mods = FabricLoader.getInstance().getAllMods().stream()
            .map(mod -> mod.getMetadata().getId()).sorted().toList();
        var packs = client.getResourcePackRepository().getSelectedPacks().stream()
            .map(pack -> pack.getId()).toList();
        reporter.respond(challenge, mods, packs, FabricLoader.getInstance().getConfigDir().resolve("qizhangverdict"),
            client::execute, response -> {
                if (current(client, originSender, connection)) originSender.sendPacket(new GuardPayload(response));
            });
    }
}
