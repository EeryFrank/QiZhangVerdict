package cn.qizhang.guard.forge;

import cn.qizhang.guard.client.ClientReporter;
import io.netty.buffer.Unpooled;
import java.util.List;
import java.util.stream.Collectors;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.network.Connection;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.protocol.game.ServerboundCustomPayloadPacket;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.loading.FMLPaths;

/** GPL-3.0-only. Called only on the physical client game thread. */
final class GuardForgeClient {
    private static final ClientReporter REPORTER = new ClientReporter();
    static void receive(byte[] payload, Connection origin) {
        final Minecraft client = Minecraft.getInstance();
        final ClientPacketListener connection = client.getConnection();
        if (connection == null || connection.getConnection() != origin) return;
        List<String> mods = ModList.get().getMods().stream().map(mod -> mod.getModId()).sorted().collect(Collectors.toList());
        List<String> packs = client.getResourcePackRepository().getSelectedPacks().stream().map(pack -> pack.getId()).collect(Collectors.toList());
        REPORTER.respond(payload, mods, packs, FMLPaths.CONFIGDIR.get().resolve("qizhangverdict"), client::execute, response -> {
            if (client.getConnection() == connection)
                connection.send(new ServerboundCustomPayloadPacket(GuardForge.CHANNEL_ID, new FriendlyByteBuf(Unpooled.wrappedBuffer(response))));
        });
    }
}
