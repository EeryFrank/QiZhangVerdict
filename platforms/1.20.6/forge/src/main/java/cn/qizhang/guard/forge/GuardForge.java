// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge;

import cn.qizhang.guard.minecraft.GuardCommands;
import cn.qizhang.guard.minecraft.MinecraftGuard;
import java.util.Objects;
import net.minecraft.network.Connection;
import net.minecraft.network.ConnectionProtocol;
import net.minecraft.network.PacketListener;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.ServerGamePacketListenerImpl;
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

/** Common entrypoint. The client-only subscriber binds a bridge without common client-class linkage. */
@Mod("qizhangverdict")
public final class GuardForge {
    public static final ResourceLocation CHANNEL_ID = new ResourceLocation("qzguard", "main");
    interface ClientReceiver { void receive(byte[] bytes, Connection origin, PacketListener listener, EventNetworkChannel channel); }
    private static volatile ClientReceiver clientReceiver = (bytes, origin, listener, channel) -> {
        throw new IllegalStateException("QiZhangVerdict client receiver was not initialized");
    };
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

    static void bindClientReceiver(ClientReceiver receiver) { clientReceiver = Objects.requireNonNull(receiver); }

    /** getProtocol() favors outbound state in Forge 50, so check the received phase explicitly. */
    static boolean play(Connection origin, PacketListener listener) {
        var protocol = origin.getInboundProtocolInfo();
        return origin.getPacketListener() == listener && protocol != null && protocol.id() == ConnectionProtocol.PLAY
            && listener != null && listener.protocol() == ConnectionProtocol.PLAY;
    }

    private void payload(CustomPayloadEvent event) {
        if (!CHANNEL_ID.equals(event.getChannel())) return;
        var context = event.getSource();
        context.setPacketHandled(true);
        var origin = context.getConnection();
        var listener = origin.getPacketListener();
        if (!origin.isConnected() || !play(origin, listener)) return;
        boolean serverbound = context.isServerSide();
        if (!serverbound && (!context.isClientSide() || !FMLEnvironment.dist.isClient())) return;
        if (serverbound && !(listener instanceof ServerGamePacketListenerImpl)) return;
        var buffer = event.getPayload();
        if (buffer == null) return;
        if (buffer.readableBytes() > ForgeWire.MAX_BYTES) {
            if (serverbound) enqueue(context, origin, listener, () -> {
                var player = sender(context, origin, listener);
                if (player != null) player.connection.disconnect(Component.literal("QiZhangVerdict payload too large"));
            });
            return;
        }
        byte[] bytes = ForgeWire.capture(buffer);
        enqueue(context, origin, listener, () -> {
            if (serverbound) {
                var player = sender(context, origin, listener);
                if (player != null && guard != null) guard.report(player, bytes);
            } else clientReceiver.receive(bytes, origin, listener, channel);
        });
    }

    private static void enqueue(CustomPayloadEvent.Context context, Connection origin, PacketListener listener, Runnable task) {
        ConnectionDispatch.enqueue(work -> context.enqueueWork(work), origin, listener,
            context::getConnection, origin::getPacketListener, origin::getPacketListener,
            origin::isConnected, () -> play(origin, listener), task);
    }

    private static ServerPlayer sender(CustomPayloadEvent.Context context, Connection origin, PacketListener listener) {
        var player = context.getSender();
        return player != null && player.connection == listener && player.connection.getConnection() == origin
            && player.getServer() != null && player.getServer().getPlayerList().getPlayer(player.getUUID()) == player ? player : null;
    }

    private void start(ServerStartingEvent event) {
        org.slf4j.LoggerFactory.getLogger("QiZhangVerdict").info(
            "External mod presence only: grimac={}, antixray={}; actual function must be tested separately",
            net.minecraftforge.fml.ModList.get().isLoaded("grimac"), net.minecraftforge.fml.ModList.get().isLoaded("antixray"));
        guard = new MinecraftGuard(FMLPaths.CONFIGDIR.get().resolve("qizhangverdict"), new MinecraftGuard.Transport() {
            @Override public boolean available(ServerPlayer player) {
                var connection = player.connection.getConnection();
                return connection.isConnected() && play(connection, player.connection) && channel.isRemotePresent(connection);
            }
            @Override public void send(ServerPlayer player, byte[] bytes) {
                channel.send(ForgeWire.outbound(bytes), player.connection.getConnection());
            }
        });
    }
    private void stop(ServerStoppingEvent event) {
        if (guard != null) { guard.stop(event.getServer()); guard = null; }
    }
    private void joined(PlayerEvent.PlayerLoggedInEvent event) {
        if (event.getEntity() instanceof ServerPlayer player) {
            if (guard == null) player.connection.disconnect(Component.literal("QiZhangVerdict is not ready"));
            else guard.joined(player);
        }
    }
    private void left(PlayerEvent.PlayerLoggedOutEvent event) {
        if (event.getEntity() instanceof ServerPlayer player && guard != null) guard.disconnected(player);
    }
    private void tick(TickEvent.ServerTickEvent event) {
        if (event.phase == TickEvent.Phase.END && guard != null) guard.tick(event.getServer());
    }
    private void commands(RegisterCommandsEvent event) { GuardCommands.register(event.getDispatcher(), () -> guard); }
}
