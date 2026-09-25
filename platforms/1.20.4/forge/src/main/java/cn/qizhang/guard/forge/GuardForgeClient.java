// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge;

import cn.qizhang.guard.client.ClientReporter;
import io.netty.buffer.Unpooled;
import net.minecraft.client.Minecraft;
import net.minecraft.network.Connection;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.loading.FMLPaths;
import net.minecraftforge.network.EventNetworkChannel;

/** Loaded only by the physical-client branch, with a connection-bound asynchronous response. */
final class GuardForgeClient {
    private static final ClientReporter REPORTER = new ClientReporter();

    static void receive(byte[] payload, Connection origin, EventNetworkChannel channel) {
        Minecraft client = Minecraft.getInstance();
        var connection = client.getConnection();
        if (connection == null || connection.getConnection() != origin) return;
        var mods = ModList.get().getMods().stream().map(mod -> mod.getModId()).sorted().toList();
        var packs = client.getResourcePackRepository().getSelectedPacks().stream().map(pack -> pack.getId()).toList();
        REPORTER.respond(payload, mods, packs, FMLPaths.CONFIGDIR.get().resolve("qizhangverdict"), client::execute, response -> {
            if (client.getConnection() == connection && connection.getConnection() == origin)
                channel.send(new FriendlyByteBuf(Unpooled.wrappedBuffer(response)), origin);
        });
    }
}
