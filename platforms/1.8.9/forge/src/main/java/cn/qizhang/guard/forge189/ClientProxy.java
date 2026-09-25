// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge189;

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
import net.minecraft.network.play.client.C17PacketCustomPayload;
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
        NetHandlerPlayClient connection = client.getNetHandler();
        if (connection == null || client.thePlayer == null || client.theWorld == null) { registered = null; return; }
        if (registered == connection.getNetworkManager()) return;
        // Bukkit's legacy messenger uses this exact case-sensitive registration.
        connection.addToSendQueue(new C17PacketCustomPayload("REGISTER", new PacketBuffer(Unpooled.wrappedBuffer(GuardForge189.CHANNEL.getBytes(StandardCharsets.UTF_8)))));
        registered = connection.getNetworkManager();
    }
    @SubscribeEvent
    public void clientPayload(FMLNetworkEvent.ClientCustomPacketEvent event) {
        ByteBuf buffer = event.packet.payload();
        if (buffer == null || buffer.readableBytes() > 30000) return;
        final byte[] bytes = new byte[buffer.readableBytes()];
        buffer.getBytes(buffer.readerIndex(), bytes);
        final NetworkManager origin = event.manager;
        final Minecraft client = Minecraft.getMinecraft();
        client.addScheduledTask(() -> {
            final NetHandlerPlayClient connection = client.getNetHandler();
            if (connection == null || connection.getNetworkManager() != origin) return;
            List<String> mods = Loader.instance().getActiveModList().stream().map(mod -> mod.getModId()).sorted().collect(Collectors.toList());
            List<String> packs = client.getResourcePackRepository().getRepositoryEntries().stream().map(pack -> pack.getResourcePackName()).collect(Collectors.toList());
            reporter.respond(bytes, mods, packs, client.mcDataDir.toPath().resolve("config/qizhangverdict"), client::addScheduledTask, response -> {
                if (client.getNetHandler() == connection && connection.getNetworkManager() == origin) {
                    connection.addToSendQueue(new C17PacketCustomPayload(GuardForge189.CHANNEL, new PacketBuffer(Unpooled.wrappedBuffer(response))));
                }
            });
        });
    }
}
