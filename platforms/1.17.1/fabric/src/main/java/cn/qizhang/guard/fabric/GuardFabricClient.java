// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.fabric;

import cn.qizhang.guard.client.ClientReporter;
import io.netty.buffer.Unpooled;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.protocol.game.ServerboundCustomPayloadPacket;

public final class GuardFabricClient implements ClientModInitializer {
    private final ClientReporter reporter = new ClientReporter();

    @Override public void onInitializeClient() {
        ClientPlayNetworking.registerGlobalReceiver(GuardFabric.CHANNEL, (client, handler, buffer, sender) -> {
            if (buffer.readableBytes() > 30000) return;
            byte[] data = new byte[buffer.readableBytes()];
            buffer.readBytes(data);
            var connection = handler.getConnection();
            ConnectionDispatch.enqueue(client::execute, connection, handler,
                () -> client.getConnection() == null ? null : client.getConnection().getConnection(),
                client::getConnection, connection::getPacketListener, connection::isConnected,
                () -> connection.getPacketListener() instanceof ClientPacketListener, () -> {
                    var mods = FabricLoader.getInstance().getAllMods().stream()
                        .map(mod -> mod.getMetadata().getId()).sorted().toList();
                    var packs = client.getResourcePackRepository().getSelectedPacks().stream()
                        .map(pack -> pack.getId()).toList();
                    reporter.respond(data, mods, packs, FabricLoader.getInstance().getConfigDir().resolve("qizhangverdict"),
                        client::execute, response -> {
                            var live = client.getConnection();
                            if (ConnectionDispatch.current(connection, handler,
                                    live == null ? null : live.getConnection(), live, connection.getPacketListener(),
                                    connection.isConnected(), connection.getPacketListener() instanceof ClientPacketListener)) {
                                connection.send(new ServerboundCustomPayloadPacket(GuardFabric.CHANNEL,
                                    new FriendlyByteBuf(Unpooled.wrappedBuffer(response))));
                            }
                        });
                });
        });
    }
}
