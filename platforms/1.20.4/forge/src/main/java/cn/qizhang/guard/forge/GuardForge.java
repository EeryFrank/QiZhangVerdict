// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge;

import cn.qizhang.guard.minecraft.GuardCommands;
import cn.qizhang.guard.minecraft.MinecraftGuard;
import io.netty.buffer.Unpooled;
import net.minecraft.network.ConnectionProtocol;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.network.CustomPayloadEvent;
import net.minecraftforge.event.server.ServerStartingEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.loading.FMLEnvironment;
import net.minecraftforge.fml.loading.FMLPaths;
import net.minecraftforge.network.ChannelBuilder;
import net.minecraftforge.network.EventNetworkChannel;
import net.minecraftforge.network.NetworkDirection;

@Mod("qizhangverdict")
public final class GuardForge {
    public static final ResourceLocation CHANNEL_ID = new ResourceLocation("qzguard", "main");
    // Optional at the Forge handshake; the configured companion policy enforces admission after join.
    // EventNetworkChannel preserves the raw Wire body, without a SimpleChannel message discriminator.
    private final EventNetworkChannel channel = ChannelBuilder.named(CHANNEL_ID)
            .networkProtocolVersion(2).optional().eventNetworkChannel();
    private MinecraftGuard guard;

    public GuardForge() {
        channel.addListener(this::payload);
        MinecraftForge.EVENT_BUS.addListener(this::start);
        MinecraftForge.EVENT_BUS.addListener(this::stop);
        MinecraftForge.EVENT_BUS.addListener(this::joined);
        MinecraftForge.EVENT_BUS.addListener(this::left);
        MinecraftForge.EVENT_BUS.addListener(this::tick);
        MinecraftForge.EVENT_BUS.addListener(this::commands);
    }

    private void payload(CustomPayloadEvent event) {
        var context = event.getSource();
        var origin = context.getConnection();
        var direction = context.getDirection();
        // Forge 49 uses one event for both sides, including the common configuration packet type.
        // Never treat configuration/login payloads as an authenticated player report.
        if (!CHANNEL_ID.equals(event.getChannel()) || origin.getProtocol() != ConnectionProtocol.PLAY
                || (direction != NetworkDirection.PLAY_TO_SERVER && direction != NetworkDirection.PLAY_TO_CLIENT)) return;
        context.setPacketHandled(true);
        var buffer = event.getPayload();
        if (buffer == null) return;
        if (buffer.readableBytes() > 30000) {
            if (direction == NetworkDirection.PLAY_TO_SERVER) context.enqueueWork(() -> {
                var player = context.getSender();
                if (player != null && player.connection.getConnection() == origin)
                    player.connection.disconnect(Component.literal("QiZhangVerdict payload too large"));
            });
            return;
        }
        byte[] bytes = new byte[buffer.readableBytes()];
        buffer.getBytes(buffer.readerIndex(), bytes);
        context.enqueueWork(() -> {
            if (direction == NetworkDirection.PLAY_TO_SERVER) {
                var player = context.getSender();
                if (player != null && player.connection.getConnection() == origin && guard != null)
                    guard.report(player, bytes);
            } else if (FMLEnvironment.dist.isClient()) GuardForgeClient.receive(bytes, origin, channel);
        });
    }

    private void start(ServerStartingEvent event) {
        org.slf4j.LoggerFactory.getLogger("QiZhangVerdict").info(
                "External mod presence only: grimac={}, antixray={}; actual function must be tested separately",
                net.minecraftforge.fml.ModList.get().isLoaded("grimac"), net.minecraftforge.fml.ModList.get().isLoaded("antixray"));
        guard = new MinecraftGuard(FMLPaths.CONFIGDIR.get().resolve("qizhangverdict"), new MinecraftGuard.Transport() {
            public boolean available(ServerPlayer player) { return channel.isRemotePresent(player.connection.getConnection()); }
            public void send(ServerPlayer player, byte[] bytes) {
                channel.send(new FriendlyByteBuf(Unpooled.wrappedBuffer(bytes)), player.connection.getConnection());
            }
        });
    }
    private void stop(ServerStoppingEvent event) {
        if (guard != null) { guard.stop(event.getServer()); guard = null; }
    }
    private void joined(PlayerEvent.PlayerLoggedInEvent event) {
        if (event.getEntity() instanceof ServerPlayer player && guard != null) guard.joined(player);
    }
    private void left(PlayerEvent.PlayerLoggedOutEvent event) {
        if (event.getEntity() instanceof ServerPlayer player && guard != null) guard.disconnected(player);
    }
    private void tick(TickEvent.ServerTickEvent event) {
        if (event.phase == TickEvent.Phase.END && guard != null) guard.tick(event.getServer());
    }
    private void commands(RegisterCommandsEvent event) { GuardCommands.register(event.getDispatcher(), () -> guard); }
}
