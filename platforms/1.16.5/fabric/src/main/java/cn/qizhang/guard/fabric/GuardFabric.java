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

/** GPL-3.0-only. Fabric 0.42 networking v1 and command v1 for Minecraft 1.16.5. */
public final class GuardFabric implements ModInitializer {
    public static final ResourceLocation CHANNEL = new ResourceLocation("qzguard", "main");
    private MinecraftGuard guard;

    @Override public void onInitialize() {
        org.apache.logging.log4j.LogManager.getLogger("QiZhangVerdict").info(
                "External mod presence only: grimac={}, antixray={}; actual function must be tested separately",
                FabricLoader.getInstance().isModLoaded("grimac"), FabricLoader.getInstance().isModLoaded("antixray"));
        ServerLifecycleEvents.SERVER_STARTING.register(server -> guard = new MinecraftGuard(
                FabricLoader.getInstance().getConfigDir().resolve("qizhangverdict"), new MinecraftGuard.Transport() {
            public boolean available(ServerPlayer player) { return ServerPlayNetworking.canSend(player, CHANNEL); }
            public void send(ServerPlayer player, byte[] bytes) {
                ServerPlayNetworking.send(player, CHANNEL, new FriendlyByteBuf(Unpooled.wrappedBuffer(bytes)));
            }
        }));
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> { if (guard != null) guard.stop(server); guard = null; });
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> guard.joined(handler.player));
        ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> { if (guard != null) guard.disconnected(handler.player); });
        ServerTickEvents.END_SERVER_TICK.register(server -> { if (guard != null) guard.tick(server); });
        ServerPlayNetworking.registerGlobalReceiver(CHANNEL, (server, player, handler, buffer, sender) -> {
            int size = buffer.readableBytes();
            if (size > 30000) { server.execute(() -> player.connection.disconnect(new TextComponent("QiZhangVerdict payload too large"))); return; }
            byte[] bytes = new byte[size]; buffer.readBytes(bytes);
            server.execute(() -> { if (guard != null) guard.report(player, bytes); });
        });
        CommandRegistrationCallback.EVENT.register((dispatcher, dedicated) -> GuardCommands.register(dispatcher, () -> guard));
    }
}
