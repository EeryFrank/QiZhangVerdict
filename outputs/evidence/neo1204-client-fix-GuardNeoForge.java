// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.neoforge;

import cn.qizhang.guard.minecraft.GuardCommands;
import cn.qizhang.guard.minecraft.GuardPayload;
import cn.qizhang.guard.minecraft.MinecraftGuard;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.loading.FMLEnvironment;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.TickEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.event.server.ServerStartingEvent;
import net.neoforged.neoforge.event.server.ServerStoppingEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlerEvent;
import net.neoforged.neoforge.network.registration.NetworkRegistry;

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
    private void network(RegisterPayloadHandlerEvent event) {
        // 20.4 registrar takes a namespace; handlers initially run on the network thread.
        event.registrar("qzguard").versioned("1").optional().play(GuardPayload.ID, GuardPayload::read,
            (payload, context) -> {
                // NeoForge 20.4 snapshots context.player() on the network thread.
                // An initial challenge can arrive before the queued login packet
                // creates the local player, so bind it to its original channel.
                if (context.flow() == PacketFlow.CLIENTBOUND && FMLEnvironment.dist.isClient()) {
                    GuardNeoForgeClient.receive(payload.data(), context.channelHandlerContext().channel());
                } else if (context.flow() == PacketFlow.SERVERBOUND) {
                    context.workHandler().execute(() -> context.player().ifPresent(player -> {
                        if (player instanceof ServerPlayer serverPlayer && guard != null) guard.report(serverPlayer, payload.data());
                    }));
                }
            });
    }
    private void start(ServerStartingEvent event) {
        org.slf4j.LoggerFactory.getLogger("QiZhangVerdict").info("External mod presence only: grimac={}, antixray={}; actual function must be tested separately", net.neoforged.fml.ModList.get().isLoaded("grimac"), net.neoforged.fml.ModList.get().isLoaded("antixray"));
        guard = new MinecraftGuard(FMLPaths.CONFIGDIR.get().resolve("qizhangverdict"), new MinecraftGuard.Transport() {
            public boolean available(ServerPlayer player) { return NetworkRegistry.getInstance().isConnected(player.connection, GuardPayload.ID); }
            public void send(ServerPlayer player, byte[] bytes) { PacketDistributor.PLAYER.with(player).send(new GuardPayload(bytes)); }
        });
    }
    private void stop(ServerStoppingEvent event) { if (guard != null) { guard.stop(event.getServer()); guard = null; } }
    private void joined(PlayerEvent.PlayerLoggedInEvent event) { if (event.getEntity() instanceof ServerPlayer player && guard != null) guard.joined(player); }
    private void left(PlayerEvent.PlayerLoggedOutEvent event) { if (event.getEntity() instanceof ServerPlayer player && guard != null) guard.disconnected(player); }
    private void tick(TickEvent.ServerTickEvent event) { if (event.phase == TickEvent.Phase.END && guard != null) guard.tick(event.getServer()); }
    private void commands(RegisterCommandsEvent event) { GuardCommands.register(event.getDispatcher(), () -> guard); }
}
