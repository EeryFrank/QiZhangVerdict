// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.neoforge;

import cn.qizhang.guard.client.ClientReporter;
import cn.qizhang.guard.minecraft.GuardPayload;
import io.netty.channel.Channel;
import net.minecraft.client.Minecraft;
import net.neoforged.fml.ModList;
import net.neoforged.neoforge.network.PacketDistributor;

/** Loaded only by the guarded physical-client branch. */
final class GuardNeoForgeClient {
    private static final ClientReporter REPORTER = new ClientReporter();
    static void receive(byte[] payload, Channel originChannel) {
        Minecraft client = Minecraft.getInstance();
        ClientChallengeDispatch.enqueue(client::execute, originChannel, () -> {
            var connection = client.getConnection();
            return connection == null || !connection.getConnection().isConnected() ? null : connection.getConnection().channel();
        }, () -> collect(client, payload, originChannel));
    }
    private static void collect(Minecraft client, byte[] payload, Channel originChannel) {
        var connection = client.getConnection();
        if (connection == null || !connection.getConnection().isConnected() || client.player == null
                || connection.getConnection().channel() != originChannel) return;
        var mods = ModList.get().getMods().stream().map(mod -> mod.getModId()).sorted().toList();
        var packs = client.getResourcePackRepository().getSelectedPacks().stream().map(pack -> pack.getId()).toList();
        REPORTER.respond(payload, mods, packs, net.neoforged.fml.loading.FMLPaths.CONFIGDIR.get().resolve("qizhangverdict"), client::execute, response -> {
            if (client.getConnection() == connection && connection.getConnection().isConnected()
                    && connection.getConnection().channel() == originChannel)
                PacketDistributor.SERVER.noArg().send(new GuardPayload(response));
        });
    }
}
