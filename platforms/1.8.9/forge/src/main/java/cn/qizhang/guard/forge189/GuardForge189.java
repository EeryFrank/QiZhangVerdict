// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge189;

import cn.qizhang.guard.minecraft.MinecraftGuard;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import java.nio.file.Path;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.network.NetHandlerPlayServer;
import net.minecraft.network.PacketBuffer;
import net.minecraft.network.play.server.S3FPacketCustomPayload;
import net.minecraft.server.MinecraftServer;
import net.minecraft.util.ChatComponentText;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.CommandEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.FMLCommonHandler;
import net.minecraftforge.fml.common.SidedProxy;
import net.minecraftforge.fml.common.event.FMLPreInitializationEvent;
import net.minecraftforge.fml.common.event.FMLServerStartingEvent;
import net.minecraftforge.fml.common.event.FMLServerStoppingEvent;
import net.minecraftforge.fml.common.eventhandler.EventPriority;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import net.minecraftforge.fml.common.gameevent.PlayerEvent;
import net.minecraftforge.fml.common.gameevent.TickEvent;
import net.minecraftforge.fml.common.network.FMLEventChannel;
import net.minecraftforge.fml.common.network.FMLNetworkEvent;
import net.minecraftforge.fml.common.network.NetworkRegistry;

@Mod(modid = "qizhangverdict", name = "QiZhang's Verdict", version = "0.2.0-test.1",
        acceptedMinecraftVersions = "[1.8.9]", acceptableRemoteVersions = "*")
public final class GuardForge189 {
    public static final String CHANNEL = "QZGuard";
    @SidedProxy(clientSide = "cn.qizhang.guard.forge189.ClientProxy", serverSide = "cn.qizhang.guard.forge189.CommonProxy")
    public static CommonProxy proxy;
    private Path directory;
    private MinecraftGuard guard;
    private MinecraftServer server;

    @Mod.EventHandler
    public void prepare(FMLPreInitializationEvent event) {
        directory = event.getModConfigurationDirectory().toPath().resolve("qizhangverdict");
        FMLEventChannel channel = NetworkRegistry.INSTANCE.newEventDrivenChannel(CHANNEL);
        channel.register(this);
        MinecraftForge.EVENT_BUS.register(this);
        proxy.register(channel);
    }
    @Mod.EventHandler
    public void start(FMLServerStartingEvent event) {
        server = event.getServer();
        guard = new MinecraftGuard(directory, new MinecraftGuard.Transport() {
            public boolean available(EntityPlayerMP player) { return player.playerNetServerHandler != null; }
            public void send(EntityPlayerMP player, byte[] bytes) {
                player.playerNetServerHandler.sendPacket(new S3FPacketCustomPayload(CHANNEL, new PacketBuffer(Unpooled.wrappedBuffer(bytes))));
            }
        });
        event.registerServerCommand(new LegacyGuardCommand(() -> guard));
    }
    @Mod.EventHandler
    public void stop(FMLServerStoppingEvent event) {
        if (guard != null && server != null) guard.stop(server);
        guard = null; server = null;
    }
    @SubscribeEvent
    public void serverPayload(FMLNetworkEvent.ServerCustomPacketEvent event) {
        // In 1.8.9 these names refer to the receiving side, unlike modern Forge payload events.
        if (!(event.handler instanceof NetHandlerPlayServer)) return;
        final EntityPlayerMP player = ((NetHandlerPlayServer) event.handler).playerEntity;
        ByteBuf buffer = event.packet.payload();
        if (buffer == null || player == null) return;
        if (buffer.readableBytes() > 30000) {
            FMLCommonHandler.instance().getWorldThread(event.handler).addScheduledTask(() -> player.playerNetServerHandler.kickPlayerFromServer("QiZhangVerdict payload too large"));
            return;
        }
        final byte[] bytes = new byte[buffer.readableBytes()];
        buffer.getBytes(buffer.readerIndex(), bytes);
        FMLCommonHandler.instance().getWorldThread(event.handler).addScheduledTask(() -> { if (guard != null) guard.report(player, bytes); });
    }
    @SubscribeEvent
    public void joined(PlayerEvent.PlayerLoggedInEvent event) {
        if (event.player instanceof EntityPlayerMP && guard != null) guard.joined((EntityPlayerMP) event.player);
    }
    @SubscribeEvent
    public void left(PlayerEvent.PlayerLoggedOutEvent event) {
        if (event.player instanceof EntityPlayerMP && guard != null) guard.disconnected((EntityPlayerMP) event.player);
    }
    @SubscribeEvent
    public void tick(TickEvent.ServerTickEvent event) {
        if (event.phase == TickEvent.Phase.END && guard != null && server != null) guard.tick(server);
    }
    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public void command(CommandEvent event) {
        if (event.sender.getCommandSenderEntity() instanceof EntityPlayerMP
                && MinecraftGuard.isWaiting((EntityPlayerMP) event.sender.getCommandSenderEntity())) {
            event.setCanceled(true);
            event.sender.addChatMessage(new ChatComponentText("QiZhangVerdict: waiting for required companion report"));
        }
    }
}
