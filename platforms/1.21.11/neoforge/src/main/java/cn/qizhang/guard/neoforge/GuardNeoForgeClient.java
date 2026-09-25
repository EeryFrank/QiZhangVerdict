// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.neoforge;

import cn.qizhang.guard.client.ClientReporter;
import cn.qizhang.guard.minecraft.GuardPayload;
import net.minecraft.client.Minecraft;
import net.minecraft.network.Connection;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.network.protocol.common.ServerboundCustomPayloadPacket;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModList;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.client.network.event.RegisterClientPayloadHandlersEvent;
import net.neoforged.neoforge.network.registration.HandlerThread;

/** A separate physical-client entrypoint, never loaded on a dedicated server. */
@Mod(value = "qizhangverdict", dist = Dist.CLIENT)
public final class GuardNeoForgeClient {
    private static final ClientReporter REPORTER = new ClientReporter();

    public GuardNeoForgeClient(IEventBus modBus) { modBus.addListener(this::network); }

    private void network(RegisterClientPayloadHandlersEvent event) {
        event.register(GuardPayload.TYPE, HandlerThread.MAIN, (payload, context) -> {
            if (context.flow() == PacketFlow.CLIENTBOUND) receive(payload.data(), context.connection());
        });
    }

    private static void receive(byte[] payload, Connection origin) {
        Minecraft client = Minecraft.getInstance();
        // Resolve the current listener only when the game-thread work runs;
        // do not capture a player snapshot before queued login completes.
        ClientChallengeDispatch.enqueue(client::execute, origin, () -> {
            var connection = client.getConnection();
            return connection == null || !connection.getConnection().isConnected() ? null : connection.getConnection();
        }, () -> collect(client, payload, origin));
    }

    private static void collect(Minecraft client, byte[] payload, Connection origin) {
        var connection = client.getConnection();
        if (connection == null || !origin.isConnected() || client.player == null || connection.getConnection() != origin) return;
        var mods = ModList.get().getMods().stream().map(mod -> mod.getModId()).sorted().toList();
        var packs = client.getResourcePackRepository().getSelectedPacks().stream().map(pack -> pack.getId()).toList();
        REPORTER.respond(payload, mods, packs, FMLPaths.CONFIGDIR.get().resolve("qizhangverdict"), client::execute, response -> {
            if (client.getConnection() == connection && origin.isConnected() && connection.getConnection() == origin) {
                connection.send(new ServerboundCustomPayloadPacket(new GuardPayload(response)));
            }
        });
    }
}
