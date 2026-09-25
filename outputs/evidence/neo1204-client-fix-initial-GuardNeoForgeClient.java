// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.neoforge;

import cn.qizhang.guard.client.ClientReporter;
import cn.qizhang.guard.minecraft.GuardPayload;
import java.util.List;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.neoforged.fml.ModList;
import net.neoforged.neoforge.network.PacketDistributor;

/** Loaded only by the guarded physical-client branch. */
final class GuardNeoForgeClient {
    private static final ClientReporter REPORTER = new ClientReporter();
    static void receive(byte[] payload, net.minecraft.world.entity.player.Player origin) {
        Minecraft client = Minecraft.getInstance(); var connection = client.getConnection();
        if (client.player != origin || connection == null) return;
        var mods = ModList.get().getMods().stream().map(mod -> mod.getModId()).sorted().toList();
        var packs = client.getResourcePackRepository().getSelectedPacks().stream().map(pack -> pack.getId()).toList();
        REPORTER.respond(payload, mods, packs, net.neoforged.fml.loading.FMLPaths.CONFIGDIR.get().resolve("qizhangverdict"), client::execute, response -> {
            if (client.getConnection() == connection) PacketDistributor.SERVER.noArg().send(new GuardPayload(response));
        });
    }
}
