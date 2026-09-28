// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge;

import cn.qizhang.guard.client.ClientReporter;
import net.minecraft.client.Minecraft;
import net.minecraft.network.Connection;
import net.minecraft.network.PacketListener;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import net.minecraftforge.fml.loading.FMLPaths;
import net.minecraftforge.network.EventNetworkChannel;

/** AutomaticEventSubscriber checks physical Dist before loading this class. */
@Mod.EventBusSubscriber(modid = "qizhangverdict", value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.MOD)
public final class GuardForgeClient {
    private static final ClientReporter REPORTER = new ClientReporter();

    @SubscribeEvent
    public static void setup(FMLClientSetupEvent event) {
        GuardForge.bindClientReceiver(GuardForgeClient::receive);
    }

    private static void receive(byte[] bytes, Connection origin, PacketListener listener, EventNetworkChannel channel) {
        var client = Minecraft.getInstance();
        ConnectionDispatch.enqueue(client::execute, origin, listener,
            () -> client.getConnection() == null ? null : client.getConnection().getConnection(),
            client::getConnection, origin::getPacketListener, origin::isConnected, () -> GuardForge.play(origin, listener),
            () -> collect(client, bytes, origin, listener, channel));
    }

    private static boolean current(Minecraft client, Connection origin, PacketListener listener) {
        var connection = client.getConnection();
        return ConnectionDispatch.current(origin, listener, connection == null ? null : connection.getConnection(),
            connection, origin.getPacketListener(), origin.isConnected(), GuardForge.play(origin, listener));
    }

    private static void collect(Minecraft client, byte[] bytes, Connection origin, PacketListener listener, EventNetworkChannel channel) {
        if (client.player == null || !current(client, origin, listener)) return;
        var mods = ModList.get().getMods().stream().map(mod -> mod.getModId()).sorted().toList();
        var packs = client.getResourcePackRepository().getSelectedPacks().stream().map(pack -> pack.getId()).toList();
        REPORTER.respond(bytes, mods, packs, FMLPaths.CONFIGDIR.get().resolve("qizhangverdict"), client::execute, response -> {
            if (current(client, origin, listener)) channel.send(ForgeWire.outbound(response), origin);
        });
    }
}
