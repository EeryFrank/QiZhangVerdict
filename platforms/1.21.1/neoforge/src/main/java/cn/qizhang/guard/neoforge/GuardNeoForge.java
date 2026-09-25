package cn.qizhang.guard.neoforge;

import cn.qizhang.guard.minecraft.GuardCommands;
import cn.qizhang.guard.minecraft.GuardPayload;
import cn.qizhang.guard.minecraft.MinecraftGuard;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.loading.FMLEnvironment;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.event.server.ServerStartingEvent;
import net.neoforged.neoforge.event.server.ServerStoppingEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;

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
        event.registrar("1").optional().playBidirectional(GuardPayload.TYPE, GuardPayload.CODEC, (payload, context) -> {
            if (context.player() instanceof ServerPlayer player) { if (guard != null) guard.report(player, payload.data()); }
            else if (FMLEnvironment.dist.isClient()) GuardNeoForgeClient.receive(payload.data(), context.player());
        });
    }
    private void start(ServerStartingEvent event) {
        org.slf4j.LoggerFactory.getLogger("QiZhangVerdict").info("External mod presence only: grimac={}, antixray={}; actual function must be tested separately", net.neoforged.fml.ModList.get().isLoaded("grimac"), net.neoforged.fml.ModList.get().isLoaded("antixray"));
        guard = new MinecraftGuard(FMLPaths.CONFIGDIR.get().resolve("qizhangverdict"), new MinecraftGuard.Transport() {
            public boolean available(ServerPlayer p) { return p.connection.hasChannel(GuardPayload.TYPE); }
            public void send(ServerPlayer p, byte[] bytes) { PacketDistributor.sendToPlayer(p, new GuardPayload(bytes)); }
        });
    }
    private void stop(ServerStoppingEvent event) { if (guard != null) guard.stop(event.getServer()); }
    private void joined(PlayerEvent.PlayerLoggedInEvent event) { if (event.getEntity() instanceof ServerPlayer p && guard != null) guard.joined(p); }
    private void left(PlayerEvent.PlayerLoggedOutEvent event) { if (event.getEntity() instanceof ServerPlayer p && guard != null) guard.disconnected(p); }
    private void tick(ServerTickEvent.Post event) { if (guard != null) guard.tick(event.getServer()); }
    private void commands(RegisterCommandsEvent event) { GuardCommands.register(event.getDispatcher(), () -> guard); }
}
