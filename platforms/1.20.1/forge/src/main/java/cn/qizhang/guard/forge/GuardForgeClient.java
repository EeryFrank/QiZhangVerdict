package cn.qizhang.guard.forge;

import cn.qizhang.guard.client.ClientReporter;
import io.netty.buffer.Unpooled;
import net.minecraft.client.Minecraft;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.protocol.game.ServerboundCustomPayloadPacket;
import net.minecraftforge.fml.ModList;

final class GuardForgeClient {
    private static final ClientReporter REPORTER = new ClientReporter();
    static void receive(byte[] payload, net.minecraft.network.Connection origin) {
        Minecraft client = Minecraft.getInstance(); var connection = client.getConnection();
        if (connection == null || connection.getConnection() != origin) return;
        var mods = ModList.get().getMods().stream().map(mod -> mod.getModId()).sorted().toList();
        var packs = client.getResourcePackRepository().getSelectedPacks().stream().map(pack -> pack.getId()).toList();
        REPORTER.respond(payload, mods, packs, net.minecraftforge.fml.loading.FMLPaths.CONFIGDIR.get().resolve("qizhangverdict"), client::execute, response -> {
            if (client.getConnection() == connection && connection != null) connection.send(new ServerboundCustomPayloadPacket(GuardForge.CHANNEL_ID, new FriendlyByteBuf(Unpooled.wrappedBuffer(response))));
        });
    }
}
