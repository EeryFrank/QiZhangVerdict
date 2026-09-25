package cn.qizhang.guard.forge;

import cn.qizhang.guard.minecraft.GuardCommands;
import cn.qizhang.guard.minecraft.MinecraftGuard;
import io.netty.buffer.Unpooled;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.TextComponent;
import net.minecraft.network.protocol.game.ClientboundCustomPayloadPacket;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.server.FMLServerStartingEvent;
import net.minecraftforge.fml.event.server.FMLServerStoppingEvent;
import net.minecraftforge.fml.loading.FMLEnvironment;
import net.minecraftforge.fml.loading.FMLPaths;
import net.minecraftforge.fml.network.NetworkDirection;
import net.minecraftforge.fml.network.NetworkEvent;
import net.minecraftforge.fml.network.NetworkRegistry;
import net.minecraftforge.fml.network.event.EventNetworkChannel;

/** GPL-3.0-only. Forge 36 uses fml.network; Loom remaps Minecraft types to full Mojmap. */
@Mod("qizhangverdict")
public final class GuardForge {
    public static final ResourceLocation CHANNEL_ID = new ResourceLocation("qzguard", "main");
    private final EventNetworkChannel channel = NetworkRegistry.newEventChannel(CHANNEL_ID, () -> "1", version -> true, version -> true);
    private MinecraftGuard guard;
    private MinecraftServer activeServer;
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
    // Official NetworkDirection: ClientCustomPayloadEvent is PLAY_TO_SERVER (sender-named).
    private void serverboundPayload(NetworkEvent.ClientCustomPayloadEvent event) {
        final NetworkEvent.Context context = event.getSource().get();
        FriendlyByteBuf buffer = event.getPayload();
        if (context.getDirection() != NetworkDirection.PLAY_TO_SERVER || buffer == null) return;
        context.setPacketHandled(true);
        if (buffer.readableBytes() > 30000) {
            context.enqueueWork(() -> { ServerPlayer player = context.getSender(); if (player != null) player.connection.disconnect(new TextComponent("QiZhangVerdict payload too large")); });
            return;
        }
        byte[] bytes = new byte[buffer.readableBytes()]; buffer.readBytes(bytes);
        context.enqueueWork(() -> { ServerPlayer player = context.getSender(); if (player != null && guard != null) guard.report(player, bytes); });
    }
    private void clientboundPayload(NetworkEvent.ServerCustomPayloadEvent event) {
        final NetworkEvent.Context context = event.getSource().get();
        FriendlyByteBuf buffer = event.getPayload();
        if (context.getDirection() != NetworkDirection.PLAY_TO_CLIENT || buffer == null || buffer.readableBytes() > 30000) return;
        context.setPacketHandled(true);
        byte[] bytes = new byte[buffer.readableBytes()]; buffer.readBytes(bytes);
        context.enqueueWork(() -> { if (FMLEnvironment.dist.isClient()) GuardForgeClient.receive(bytes, context.getNetworkManager()); });
    }
    private void start(FMLServerStartingEvent event) {
        activeServer = event.getServer();
        org.apache.logging.log4j.LogManager.getLogger("QiZhangVerdict").info(
                "External mod presence only: grimac={}, antixray={}; actual function must be tested separately",
                ModList.get().isLoaded("grimac"), ModList.get().isLoaded("antixray"));
        guard = new MinecraftGuard(FMLPaths.CONFIGDIR.get().resolve("qizhangverdict"), new MinecraftGuard.Transport() {
            public boolean available(ServerPlayer player) { return channel.isRemotePresent(player.connection.connection); }
            public void send(ServerPlayer player, byte[] bytes) {
                player.connection.send(new ClientboundCustomPayloadPacket(CHANNEL_ID, new FriendlyByteBuf(Unpooled.wrappedBuffer(bytes))));
            }
        });
    }
    private void stop(FMLServerStoppingEvent event) {
        if (guard != null) guard.stop(event.getServer());
        guard = null; activeServer = null;
    }
    private void joined(PlayerEvent.PlayerLoggedInEvent event) {
        if (event.getPlayer() instanceof ServerPlayer && guard != null) guard.joined((ServerPlayer) event.getPlayer());
    }
    private void left(PlayerEvent.PlayerLoggedOutEvent event) {
        if (event.getPlayer() instanceof ServerPlayer && guard != null) guard.disconnected((ServerPlayer) event.getPlayer());
    }
    private void tick(TickEvent.ServerTickEvent event) {
        if (event.phase == TickEvent.Phase.END && guard != null && activeServer != null) guard.tick(activeServer);
    }
    private void commands(RegisterCommandsEvent event) { GuardCommands.register(event.getDispatcher(), () -> guard); }
}
