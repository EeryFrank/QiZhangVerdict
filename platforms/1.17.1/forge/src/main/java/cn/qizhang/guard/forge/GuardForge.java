// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge;

import cn.qizhang.guard.minecraft.GuardCommands;
import cn.qizhang.guard.minecraft.MinecraftGuard;
import net.minecraft.network.Connection;
import net.minecraft.network.PacketListener;
import net.minecraft.network.chat.TextComponent;
import net.minecraft.network.protocol.game.ClientboundCustomPayloadPacket;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.ServerGamePacketListenerImpl;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.loading.FMLPaths;
import net.minecraftforge.fmllegacy.network.NetworkDirection;
import net.minecraftforge.fmllegacy.network.NetworkEvent;
import net.minecraftforge.fmllegacy.network.NetworkRegistry;
import net.minecraftforge.fmllegacy.network.event.EventNetworkChannel;
import net.minecraftforge.fmlserverevents.FMLServerStartingEvent;
import net.minecraftforge.fmlserverevents.FMLServerStoppingEvent;
import org.apache.logging.log4j.LogManager;

@Mod("qizhangverdict")
public final class GuardForge {
    public static final ResourceLocation CHANNEL_ID = new ResourceLocation("qzguard", "main");
    private final EventNetworkChannel channel = NetworkRegistry.newEventChannel(CHANNEL_ID, () -> "2", version -> true, version -> true);
    private MinecraftGuard guard;
    private MinecraftServer activeServer;
    private static volatile ClientReceiver clientReceiver;

    /** No physical-client class appears in this dedicated-server-loaded bridge. */
    interface ClientReceiver { void receive(byte[] bytes, Connection origin, PacketListener listener); }
    static void bindClientReceiver(ClientReceiver receiver) { clientReceiver = receiver; }

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

    // Forge 37 names payload events for the sender; LOGIN subclasses must be excluded.
    private void serverboundPayload(NetworkEvent.ClientCustomPayloadEvent event) {
        var context = event.getSource().get();
        if (context.getDirection() != NetworkDirection.PLAY_TO_SERVER) return;
        context.setPacketHandled(true);
        var origin = context.getNetworkManager();
        var listener = origin.getPacketListener();
        if (!origin.isConnected() || !(listener instanceof ServerGamePacketListenerImpl playListener)) return;
        var player = playListener.player;
        var buffer = event.getPayload();
        if (buffer == null) return;
        if (buffer.readableBytes() > ForgeWire.MAX_BYTES) {
            enqueueServer(context, origin, playListener, player,
                () -> player.connection.disconnect(new TextComponent("QiZhangVerdict payload too large")));
            return;
        }
        byte[] bytes = ForgeWire.capture(buffer);
        enqueueServer(context, origin, playListener, player, () -> {
            if (guard != null) guard.report(player, bytes);
        });
    }

    private void enqueueServer(NetworkEvent.Context context, Connection origin,
                               ServerGamePacketListenerImpl listener, ServerPlayer player, Runnable action) {
        ConnectionDispatch.enqueue(task -> context.enqueueWork(task), origin, listener,
            () -> player.connection.connection, () -> player.connection, origin::getPacketListener,
            origin::isConnected, () -> context.getDirection() == NetworkDirection.PLAY_TO_SERVER,
            () -> {
                if (activeServer != null && activeServer.getPlayerList().getPlayer(player.getUUID()) == player) action.run();
            });
    }

    private void clientboundPayload(NetworkEvent.ServerCustomPayloadEvent event) {
        var context = event.getSource().get();
        if (context.getDirection() != NetworkDirection.PLAY_TO_CLIENT) return;
        context.setPacketHandled(true);
        var origin = context.getNetworkManager();
        var listener = origin.getPacketListener();
        var buffer = event.getPayload();
        if (!origin.isConnected() || buffer == null || buffer.readableBytes() > ForgeWire.MAX_BYTES) return;
        var receiver = clientReceiver;
        if (receiver != null) receiver.receive(ForgeWire.capture(buffer), origin, listener);
    }

    private void start(FMLServerStartingEvent event) {
        activeServer = event.getServer();
        LogManager.getLogger("QiZhangVerdict").info("External mod presence only: grimac={}, antixray={}; actual function must be tested separately",
            ModList.get().isLoaded("grimac"), ModList.get().isLoaded("antixray"));
        guard = new MinecraftGuard(FMLPaths.CONFIGDIR.get().resolve("qizhangverdict"), new MinecraftGuard.Transport() {
            @Override public boolean available(ServerPlayer player) {
                var origin = player.connection.connection;
                // Forge 37's isRemotePresent reads FML login metadata, not minecraft:register.
                // Send the bounded challenge to every live PLAY session; only a valid report
                // releases isolation. Missing companions still face the normal strict timeout.
                return origin.isConnected() && origin.getPacketListener() == player.connection;
            }
            @Override public void send(ServerPlayer player, byte[] bytes) {
                player.connection.send(new ClientboundCustomPayloadPacket(CHANNEL_ID, ForgeWire.outbound(bytes)));
            }
        });
    }

    private void stop(FMLServerStoppingEvent event) {
        if (guard != null) guard.stop(event.getServer());
        guard = null;
        activeServer = null;
    }
    private void joined(PlayerEvent.PlayerLoggedInEvent event) {
        if (event.getPlayer() instanceof ServerPlayer player) {
            if (guard == null) player.connection.disconnect(new TextComponent("QiZhangVerdict is not ready"));
            else guard.joined(player);
        }
    }
    private void left(PlayerEvent.PlayerLoggedOutEvent event) {
        if (event.getPlayer() instanceof ServerPlayer player && guard != null) guard.disconnected(player);
    }
    private void tick(TickEvent.ServerTickEvent event) {
        if (event.phase == TickEvent.Phase.END && guard != null && activeServer != null) guard.tick(activeServer);
    }
    private void commands(RegisterCommandsEvent event) { GuardCommands.register(event.getDispatcher(), () -> guard); }
}
