// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.neoforge;

import cn.qizhang.guard.minecraft.GuardCommands;
import cn.qizhang.guard.minecraft.GuardPayload;
import cn.qizhang.guard.minecraft.MinecraftGuard;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModList;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.event.server.ServerStartingEvent;
import net.neoforged.neoforge.event.server.ServerStoppingEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.registration.HandlerThread;

/** Common entrypoint: it deliberately has no references to client-only classes. */
@Mod("qizhangverdict")
public final class GuardNeoForge {
    private MinecraftGuard guard;

    public GuardNeoForge(IEventBus modBus) {
        modBus.addListener(this::network);
        NeoForge.EVENT_BUS.addListener(this::start);
        NeoForge.EVENT_BUS.addListener(this::stop);
        NeoForge.EVENT_BUS.addListener(this::joined);
        NeoForge.EVENT_BUS.addListener(this::left);
        NeoForge.EVENT_BUS.addListener(this::tick);
        NeoForge.EVENT_BUS.addListener(this::commands);
    }

    private void network(RegisterPayloadHandlersEvent event) {
        // Optional channel negotiation permits Bukkit connections; admission is
        // still controlled by the shared required-report/device configuration.
        event.registrar("2").optional().executesOn(HandlerThread.MAIN)
            .playBidirectional(GuardPayload.TYPE, GuardPayload.CODEC, (payload, context) -> {
                if (context.flow() != PacketFlow.SERVERBOUND || guard == null) return;
                if (context.player() instanceof ServerPlayer player
                        && player.connection == context.listener()
                        && player.connection.getConnection() == context.connection()
                        && context.connection().isConnected()) {
                    guard.report(player, payload.data());
                }
            });
    }

    private void start(ServerStartingEvent event) {
        org.slf4j.LoggerFactory.getLogger("QiZhangVerdict").info(
            "External mod presence only: grimac={}, antixray={}; actual function must be tested separately",
            ModList.get().isLoaded("grimac"), ModList.get().isLoaded("antixray"));
        guard = new MinecraftGuard(FMLPaths.CONFIGDIR.get().resolve("qizhangverdict"), new MinecraftGuard.Transport() {
            @Override
            public boolean available(ServerPlayer player) { return player.connection.hasChannel(GuardPayload.TYPE); }
            @Override
            public void send(ServerPlayer player, byte[] bytes) { PacketDistributor.sendToPlayer(player, new GuardPayload(bytes)); }
        });
    }

    private void stop(ServerStoppingEvent event) {
        if (guard != null) {
            guard.stop(event.getServer());
            guard = null;
        }
    }
    private void joined(PlayerEvent.PlayerLoggedInEvent event) {
        if (event.getEntity() instanceof ServerPlayer player && guard != null) guard.joined(player);
    }
    private void left(PlayerEvent.PlayerLoggedOutEvent event) {
        if (event.getEntity() instanceof ServerPlayer player && guard != null) guard.disconnected(player);
    }
    private void tick(ServerTickEvent.Post event) { if (guard != null) guard.tick(event.getServer()); }
    private void commands(RegisterCommandsEvent event) { GuardCommands.register(event.getDispatcher(), () -> guard); }
}
