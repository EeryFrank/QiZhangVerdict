package cn.qizhang.guard.forge112;

import cn.qizhang.guard.client.ClientReporter;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.stream.Collectors;
import net.minecraft.client.Minecraft;
import net.minecraft.client.network.NetHandlerPlayClient;
import net.minecraft.network.NetworkManager;
import net.minecraft.network.PacketBuffer;
import net.minecraft.network.play.client.CPacketCustomPayload;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.fml.common.Loader;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import net.minecraftforge.fml.common.gameevent.TickEvent;
import net.minecraftforge.fml.common.network.FMLEventChannel;
import net.minecraftforge.fml.common.network.FMLNetworkEvent;
import net.minecraftforge.fml.relauncher.Side;
import net.minecraftforge.fml.relauncher.SideOnly;

@SideOnly(Side.CLIENT)
public final class ClientProxy extends CommonProxy {
    private final ClientReporter reporter = new ClientReporter();
    private NetworkManager registered;
    @Override public void register(FMLEventChannel channel) {
        channel.register(this);
        MinecraftForge.EVENT_BUS.register(this);
    }
    @SubscribeEvent
    public void registerAfterPlay(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Minecraft client = Minecraft.getMinecraft();
        NetHandlerPlayClient connection = client.getConnection();
        if (connection == null || client.player == null || client.world == null) { registered = null; return; }
        if (registered == connection.getNetworkManager()) return;
        // Bukkit's legacy messenger uses this exact case-sensitive registration.
        connection.sendPacket(new CPacketCustomPayload("REGISTER", new PacketBuffer(Unpooled.wrappedBuffer(GuardForge112.CHANNEL.getBytes(StandardCharsets.UTF_8)))));
        registered = connection.getNetworkManager();
    }
    @SubscribeEvent
    public void clientPayload(FMLNetworkEvent.ClientCustomPacketEvent event) {
        ByteBuf buffer = event.getPacket().payload();
        if (buffer == null || buffer.readableBytes() > 30000) return;
        final byte[] bytes = new byte[buffer.readableBytes()];
        buffer.getBytes(buffer.readerIndex(), bytes);
        final NetworkManager origin = event.getManager();
        final Minecraft client = Minecraft.getMinecraft();
        client.addScheduledTask(() -> {
            final NetHandlerPlayClient connection = client.getConnection();
            if (connection == null || connection.getNetworkManager() != origin) return;
            List<String> mods = Loader.instance().getActiveModList().stream().map(mod -> mod.getModId()).sorted().collect(Collectors.toList());
            List<String> packs = client.getResourcePackRepository().getRepositoryEntries().stream().map(pack -> pack.getResourcePackName()).collect(Collectors.toList());
            reporter.respond(bytes, mods, packs, client.mcDataDir.toPath().resolve("config/qizhangverdict"), client::addScheduledTask, response -> {
                if (client.getConnection() == connection && connection.getNetworkManager() == origin) {
                    connection.sendPacket(new CPacketCustomPayload(GuardForge112.CHANNEL, new PacketBuffer(Unpooled.wrappedBuffer(response))));
                }
            });
        });
    }
}
