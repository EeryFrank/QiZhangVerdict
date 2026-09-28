// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.fabric;

import cn.qizhang.guard.minecraft.GuardCommands;
import cn.qizhang.guard.minecraft.MinecraftGuard;
import io.netty.buffer.Unpooled;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v1.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.TextComponent;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.ServerGamePacketListenerImpl;

public final class GuardFabric implements ModInitializer {
    public static final ResourceLocation CHANNEL = new ResourceLocation("qzguard", "main");
    private MinecraftGuard guard;

    @Override public void onInitialize() {
        org.slf4j.LoggerFactory.getLogger("QiZhangVerdict").info(
            "External mod presence only: grimac={}, antixray={}; actual function must be tested separately",
            FabricLoader.getInstance().isModLoaded("grimac"), FabricLoader.getInstance().isModLoaded("antixray"));
        ServerLifecycleEvents.SERVER_STARTING.register(server -> guard = new MinecraftGuard(
            FabricLoader.getInstance().getConfigDir().resolve("qizhangverdict"), new MinecraftGuard.Transport() {
                public boolean available(ServerPlayer player) { return ServerPlayNetworking.canSend(player, CHANNEL); }
                public void send(ServerPlayer player, byte[] data) {
                    ServerPlayNetworking.send(player, CHANNEL, new FriendlyByteBuf(Unpooled.wrappedBuffer(data)));
                }
            }));
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
            if (guard != null) { guard.stop(server); guard = null; }
        });
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> {
            if (guard == null) handler.disconnect(new TextComponent("QiZhangVerdict is not ready"));
            else guard.joined(handler.player);
        });
        ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> {
            if (guard != null) guard.disconnected(handler.player);
        });
        ServerTickEvents.END_SERVER_TICK.register(server -> { if (guard != null) guard.tick(server); });
        ServerPlayNetworking.registerGlobalReceiver(CHANNEL, (server, player, handler, buffer, sender) -> {
            var connection = handler.getConnection();
            int size = buffer.readableBytes();
            // Copy on the network callback; never retain Fabric's released buffer in queued work.
            byte[] data = size <= 30000 ? new byte[size] : null;
            if (data != null) buffer.readBytes(data);
            ConnectionDispatch.enqueue(server::execute, connection, handler,
                () -> player.connection == null ? null : player.connection.getConnection(),
                () -> player.connection, connection::getPacketListener, connection::isConnected,
                () -> connection.getPacketListener() instanceof ServerGamePacketListenerImpl, () -> {
                    if (data == null) handler.disconnect(new TextComponent("QiZhangVerdict payload too large"));
                    else if (guard != null) guard.report(player, data);
                });
        });
        CommandRegistrationCallback.EVENT.register((dispatcher, dedicated) -> GuardCommands.register(dispatcher, () -> guard));
    }
}
