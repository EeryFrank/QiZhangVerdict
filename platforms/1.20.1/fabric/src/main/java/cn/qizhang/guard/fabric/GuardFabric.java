package cn.qizhang.guard.fabric;

import cn.qizhang.guard.minecraft.GuardCommands;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.network.FriendlyByteBuf;
import io.netty.buffer.Unpooled;
import cn.qizhang.guard.minecraft.MinecraftGuard;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;

import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.server.level.ServerPlayer;

public final class GuardFabric implements ModInitializer {
    public static final ResourceLocation CHANNEL = new ResourceLocation("qzguard", "main");
    private MinecraftGuard guard;
    @Override public void onInitialize() {
        org.slf4j.LoggerFactory.getLogger("QiZhangVerdict").info("External mod presence only: grimac={}, antixray={}; actual function must be tested separately", FabricLoader.getInstance().isModLoaded("grimac"), FabricLoader.getInstance().isModLoaded("antixray"));
        ServerLifecycleEvents.SERVER_STARTING.register(server -> guard = new MinecraftGuard(FabricLoader.getInstance().getConfigDir().resolve("qizhangverdict"), new MinecraftGuard.Transport() {
            public boolean available(ServerPlayer p) { return ServerPlayNetworking.canSend(p, CHANNEL); }
            public void send(ServerPlayer p, byte[] data) { ServerPlayNetworking.send(p, CHANNEL, new FriendlyByteBuf(Unpooled.wrappedBuffer(data))); }
        }));
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> { if (guard != null) guard.stop(server); });
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> guard.joined(handler.player));
        ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> { if (guard != null) guard.disconnected(handler.player); });
        ServerTickEvents.END_SERVER_TICK.register(server -> { if (guard != null) guard.tick(server); });
        ServerPlayNetworking.registerGlobalReceiver(CHANNEL, (server, player, handler, buffer, sender) -> {
            int size = buffer.readableBytes();
            if (size > 30000) { server.execute(() -> player.connection.disconnect(net.minecraft.network.chat.Component.literal("QiZhangVerdict payload too large"))); return; }
            byte[] data = new byte[size]; buffer.readBytes(data);
            server.execute(() -> { if (guard != null) guard.report(player, data); });
        });
        CommandRegistrationCallback.EVENT.register((dispatcher, registry, environment) -> GuardCommands.register(dispatcher, () -> guard));
    }
}
