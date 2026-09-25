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
import net.minecraft.server.level.ServerPlayer;

public final class GuardFabric implements ModInitializer {
    private MinecraftGuard guard;
    @Override public void onInitialize() {
        org.slf4j.LoggerFactory.getLogger("QiZhangVerdict").info("External mod presence only: grimac={}, antixray={}; actual function must be tested separately", FabricLoader.getInstance().isModLoaded("grimac"), FabricLoader.getInstance().isModLoaded("antixray"));
        PayloadTypeRegistry.playC2S().register(GuardPayload.TYPE, GuardPayload.CODEC);
        PayloadTypeRegistry.playS2C().register(GuardPayload.TYPE, GuardPayload.CODEC);
        ServerLifecycleEvents.SERVER_STARTING.register(server -> guard = new MinecraftGuard(FabricLoader.getInstance().getConfigDir().resolve("qizhangverdict"), new MinecraftGuard.Transport() {
            public boolean available(ServerPlayer p) { return ServerPlayNetworking.canSend(p, GuardPayload.TYPE); }
            public void send(ServerPlayer p, byte[] data) { ServerPlayNetworking.send(p, new GuardPayload(data)); }
        }));
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> { if (guard != null) guard.stop(server); });
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> guard.joined(handler.player));
        ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> { if (guard != null) guard.disconnected(handler.player); });
        ServerTickEvents.END_SERVER_TICK.register(server -> { if (guard != null) guard.tick(server); });
        ServerPlayNetworking.registerGlobalReceiver(GuardPayload.TYPE, (payload, context) -> { if (guard != null) guard.report(context.player(), payload.data()); });
        CommandRegistrationCallback.EVENT.register((dispatcher, registry, environment) -> GuardCommands.register(dispatcher, () -> guard));
    }
}
