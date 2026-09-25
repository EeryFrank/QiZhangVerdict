// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.fabric;

import cn.qizhang.guard.minecraft.GuardCommands;
import cn.qizhang.guard.minecraft.GuardPayload;
import cn.qizhang.guard.minecraft.MinecraftGuard;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.PayloadTypeRegistry;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;

/** Dedicated-server-safe entry point; client classes are loaded only by the client entry point. */
public final class GuardFabric implements ModInitializer {
    private MinecraftGuard guard;

    @Override public void onInitialize() {
        org.slf4j.LoggerFactory.getLogger("QiZhangVerdict").info(
            "External mod presence only: grimac={}, antixray={}; actual function must be tested separately",
            FabricLoader.getInstance().isModLoaded("grimac"), FabricLoader.getInstance().isModLoaded("antixray"));
        PayloadTypeRegistry.playC2S().register(GuardPayload.TYPE, GuardPayload.CODEC);
        PayloadTypeRegistry.playS2C().register(GuardPayload.TYPE, GuardPayload.CODEC);
        ServerLifecycleEvents.SERVER_STARTING.register(server -> guard = new MinecraftGuard(
            FabricLoader.getInstance().getConfigDir().resolve("qizhangverdict"), new MinecraftGuard.Transport() {
                @Override public boolean available(ServerPlayer player) {
                    return player.connection.isAcceptingMessages() && ServerPlayNetworking.canSend(player, GuardPayload.TYPE);
                }
                @Override public void send(ServerPlayer player, byte[] data) {
                    ServerPlayNetworking.send(player, new GuardPayload(data));
                }
            }));
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
            if (guard != null) guard.stop(server);
            guard = null;
        });
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> {
            if (guard == null) {
                handler.disconnect(Component.literal("QiZhangVerdict is not ready"));
                return;
            }
            guard.joined(handler.player);
        });
        ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> {
            if (guard != null) guard.disconnected(handler.player);
        });
        ServerTickEvents.END_SERVER_TICK.register(server -> { if (guard != null) guard.tick(server); });
        // Fabric invokes this callback on the server thread. Reject an obsolete session
        // even if the same account has already joined through a different connection.
        ServerPlayNetworking.registerGlobalReceiver(GuardPayload.TYPE, (payload, context) -> {
            var player = context.player();
            if (guard == null || !player.connection.isAcceptingMessages()
                    || context.server().getPlayerList().getPlayer(player.getUUID()) != player
                    || ServerPlayNetworking.getSender(player) != context.responseSender()) return;
            guard.report(player, payload.data());
        });
        CommandRegistrationCallback.EVENT.register((dispatcher, registry, environment) ->
            GuardCommands.register(dispatcher, () -> guard));
    }
}
