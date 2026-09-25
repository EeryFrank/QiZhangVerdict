// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge;

import cn.qizhang.guard.minecraft.GuardCommands;
import cn.qizhang.guard.minecraft.MinecraftGuard;
import io.netty.buffer.Unpooled;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.game.ClientboundCustomPayloadPacket;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStartingEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.loading.FMLEnvironment;
import net.minecraftforge.fml.loading.FMLPaths;
import net.minecraftforge.network.NetworkEvent;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.event.EventNetworkChannel;

@Mod("qizhangverdict")
public final class GuardForge {
    public static final ResourceLocation CHANNEL_ID = new ResourceLocation("qzguard", "main");
    private final EventNetworkChannel channel = NetworkRegistry.newEventChannel(CHANNEL_ID, () -> "1", version -> true, version -> true);
    private MinecraftGuard guard;
    public GuardForge() {
        channel.addListener(this::serverboundPayload);
        channel.addListener(this::clientboundPayload);
        MinecraftForge.EVENT_BUS.addListener(this::start);
        MinecraftForge.EVENT_BUS.addListener(this::stop);
        MinecraftForge.EVENT_BUS.addListener(this::joined);
        MinecraftForge.EVENT_BUS.addListener(this::left);
        MinecraftForge.EVENT_BUS.addListener(this::tick);
        MinecraftForge.EVENT_BUS.addListener(this::commands);
    }
    // Forge names these events for the sending side, not the receiving side.
    // PLAY_TO_SERVER creates ClientCustomPayloadEvent; PLAY_TO_CLIENT creates
    // ServerCustomPayloadEvent. Also exclude their login-phase subclasses.
    private void serverboundPayload(NetworkEvent.ClientCustomPayloadEvent event) {
        var context = event.getSource().get(); var buffer = event.getPayload();
        if (context.getDirection() != NetworkDirection.PLAY_TO_SERVER) return;
        if (buffer == null) return;
        context.setPacketHandled(true);
        if (buffer.readableBytes() > 30000) { context.enqueueWork(() -> { var p = context.getSender(); if (p != null) p.connection.disconnect(Component.literal("QiZhangVerdict payload too large")); }); return; }
        byte[] bytes = new byte[buffer.readableBytes()]; buffer.readBytes(bytes);
        context.enqueueWork(() -> { var p = context.getSender(); if (p != null && guard != null) guard.report(p, bytes); });
    }
    private void clientboundPayload(NetworkEvent.ServerCustomPayloadEvent event) {
        var context = event.getSource().get(); var buffer = event.getPayload();
        if (context.getDirection() != NetworkDirection.PLAY_TO_CLIENT) return;
        if (buffer == null || buffer.readableBytes() > 30000) return;
        context.setPacketHandled(true);
        byte[] bytes = new byte[buffer.readableBytes()]; buffer.readBytes(bytes);
        context.enqueueWork(() -> { if (FMLEnvironment.dist.isClient()) GuardForgeClient.receive(bytes, context.getNetworkManager()); });
    }
    private void start(ServerStartingEvent event) {
        org.slf4j.LoggerFactory.getLogger("QiZhangVerdict").info("External mod presence only: grimac={}, antixray={}; actual function must be tested separately", net.minecraftforge.fml.ModList.get().isLoaded("grimac"), net.minecraftforge.fml.ModList.get().isLoaded("antixray"));
        guard = new MinecraftGuard(FMLPaths.CONFIGDIR.get().resolve("qizhangverdict"), new MinecraftGuard.Transport() {
            public boolean available(ServerPlayer p) { return channel.isRemotePresent(p.connection.connection); }
            public void send(ServerPlayer p, byte[] bytes) { p.connection.send(new ClientboundCustomPayloadPacket(CHANNEL_ID, new FriendlyByteBuf(Unpooled.wrappedBuffer(bytes)))); }
        });
    }
    private void stop(ServerStoppingEvent event) { if (guard != null) guard.stop(event.getServer()); }
    private void joined(PlayerEvent.PlayerLoggedInEvent event) { if (event.getEntity() instanceof ServerPlayer p && guard != null) guard.joined(p); }
    private void left(PlayerEvent.PlayerLoggedOutEvent event) { if (event.getEntity() instanceof ServerPlayer p && guard != null) guard.disconnected(p); }
    private void tick(TickEvent.ServerTickEvent event) { if (event.phase == TickEvent.Phase.END && guard != null) guard.tick(event.getServer()); }
    private void commands(RegisterCommandsEvent event) { GuardCommands.register(event.getDispatcher(), () -> guard); }
}
