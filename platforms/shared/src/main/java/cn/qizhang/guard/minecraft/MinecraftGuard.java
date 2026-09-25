package cn.qizhang.guard.minecraft;

import cn.qizhang.guard.core.Decision;
import cn.qizhang.guard.core.GuardService;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.GameType;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.List;
import java.util.function.Consumer;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** All Minecraft state access runs on the logical server thread. Disk writes have a separate executor. */
public final class MinecraftGuard {
    public interface Transport { boolean available(ServerPlayer player); void send(ServerPlayer player, byte[] bytes); }
    private static final Logger LOG = LoggerFactory.getLogger("QiZhangVerdict");
    private static volatile MinecraftGuard active;
    private final GuardService service;
    private final Transport transport;
    private final Map<UUID, Pending> pending = new java.util.concurrent.ConcurrentHashMap<>();
    private final Map<UUID, Integer> reportCount = new HashMap<>();
    private final Map<UUID, ServerPlayer> owners = new java.util.concurrent.ConcurrentHashMap<>();
    private final ExecutorService saver = Executors.newSingleThreadExecutor(task -> { Thread t = new Thread(task, "QiZhangGuard-save"); t.setDaemon(true); return t; });
    private final AtomicBoolean saving = new AtomicBoolean();
    private long lastCheck;

    public MinecraftGuard(Path directory, Transport transport) {
        try { this.service = new GuardService(directory); } catch (Exception failure) { throw new IllegalStateException("QiZhangGuard cannot load policy", failure); }
        this.transport = transport;
        active = this;
        LOG.info("QiZhangGuard started: {}. Reports are self-reported, not trusted attestation.", service.status());
    }
    public void joined(ServerPlayer player) {
        String ip = player.getIpAddress();
        // Vanilla's in-memory singleplayer connection has no InetSocketAddress.
        // Only the authenticated integrated-server owner receives this local mapping.
        if ("<unknown>".equals(ip) && !player.getServer().isDedicatedServer()
                && player.getServer().isSingleplayerOwner(player.getGameProfile())) ip = "127.0.0.1";
        Decision decision = service.openSession(player.getUUID(), ip, System.currentTimeMillis());
        if (!decision.allowed()) { player.connection.disconnect(Component.literal(decision.message())); return; }
        owners.put(player.getUUID(), player);
        try {
            service.confirmSession(player.getUUID(), System.currentTimeMillis());
            byte[] challenge = service.challenge(player.getUUID(), System.currentTimeMillis());
            Pending gate = new Pending(player, challenge, service.requiresCompanion());
            pending.put(player.getUUID(), gate);
            reportCount.put(player.getUUID(), 0);
            if (gate.isolated) player.setGameMode(GameType.SPECTATOR);
            send(player, gate);
        } catch (Exception failure) { LOG.error("Cannot initialize guard session", failure); kick(player, "QiZhangVerdict: session verification failed"); }
    }
    public void report(ServerPlayer player, byte[] payload) {
        UUID id = player.getUUID();
        if (owners.get(id) != player) return;
        Integer seen = reportCount.get(id);
        if (seen == null || seen >= 4 || payload.length > 30000) { kick(player, "QiZhangGuard: unsolicited or excessive report"); return; }
        reportCount.put(id, seen + 1);
        Decision result = service.acceptReport(id, payload, System.currentTimeMillis());
        if ("STALE_REPORT".equals(result.code())) return;
        if (!result.allowed()) { kick(player, result.message()); return; }
        restore(player, pending.remove(id));
        if (!"OK".equalsIgnoreCase(result.code())) LOG.info("Report decision player={} code={} message={}", id, result.code(), result.message());
    }
    public boolean waiting(ServerPlayer player) { Pending gate = pending.get(player.getUUID()); return gate != null && gate.isolated; }
    public static boolean isWaiting(ServerPlayer player) { return active != null && active.owners.get(player.getUUID()) == player && active.waiting(player); }
    public void disconnected(ServerPlayer player) {
        if (owners.get(player.getUUID()) != player) return;
        owners.remove(player.getUUID());
        restore(player, pending.remove(player.getUUID()));
        reportCount.remove(player.getUUID());
        service.closeSession(player.getUUID());
    }
    public void tick(MinecraftServer server) {
        for (Map.Entry<UUID, Pending> entry : pending.entrySet()) {
            ServerPlayer player = server.getPlayerList().getPlayer(entry.getKey());
            if (player == null) continue;
            Pending gate = entry.getValue();
            if (gate.isolated) {
                if (!player.isSpectator()) player.setGameMode(GameType.SPECTATOR);
                player.setCamera(player);
                if (player.serverLevel() != gate.level) player.teleportTo(gate.level, gate.x, gate.y, gate.z, gate.yaw, gate.pitch);
                else player.connection.teleport(gate.x, gate.y, gate.z, gate.yaw, gate.pitch);
            }
        }
        long now = System.currentTimeMillis();
        if (now - lastCheck < 1000) return;
        lastCheck = now;
        for (UUID banned : service.bannedSessions()) {
            ServerPlayer player = server.getPlayerList().getPlayer(banned);
            if (player != null) kick(player, "QiZhangVerdict: account or associated device is banned");
        }
        for (UUID expired : service.expiredReports(now)) {
            ServerPlayer player = server.getPlayerList().getPlayer(expired);
            if (player != null) kick(player, "QiZhangGuard: required companion report timed out");
        }
        for (Map.Entry<UUID, Pending> entry : pending.entrySet()) {
            ServerPlayer player = server.getPlayerList().getPlayer(entry.getKey());
            if (player != null) send(player, entry.getValue());
        }
        if (service.isDirty() && saving.compareAndSet(false, true)) saver.execute(() -> {
            try { service.save(); } catch (Exception failure) { LOG.error("Cannot save QiZhangGuard state", failure); }
            finally { saving.set(false); }
        });
    }
    public String status() { return service.status(); }
    public void admin(MinecraftServer server, String operation, List<String> args, Consumer<String> result) {
        final List<String> values = new java.util.ArrayList<>(args);
        if ("ban".equals(operation)) {
            try { UUID.fromString(values.get(0)); }
            catch (IllegalArgumentException invalidUuid) {
                ServerPlayer target = server.getPlayerList().getPlayerByName(values.get(0));
                if (target == null || !target.getGameProfile().getName().equals(values.get(0))) { result.accept("Ban requires a UUID or an exact online player name"); return; }
                values.set(0, target.getUUID().toString());
            }
        }
        saver.execute(() -> {
            String message; boolean refresh = false;
            try {
                switch (operation) {
                    case "reload": service.reload(); message = service.status(); refresh = true; break;
                    case "rules": message = page(service.listRules(), Integer.parseInt(values.get(0))); break;
                    case "bans": message = page(service.listBans(), Integer.parseInt(values.get(0))); break;
                    case "add": message = "Added rule: " + service.addRule(values.get(0), values.get(1), values.get(2), values.get(3)); refresh = true; break;
                    case "remove": message = "Removed: " + service.removeRule(values.get(0)); refresh = true; break;
                    case "ban": service.ban(UUID.fromString(values.get(0)), values.get(1)); message = "Account and known associated device banned"; break;
                    case "unban": message = "Unbanned: " + service.unban(values.get(0)); break;
                    default: throw new IllegalArgumentException("Unknown operation");
                }
            } catch (Exception failure) { message = "Operation rejected: " + failure.getMessage(); }
            String completed = message; boolean recheck = refresh;
            server.execute(() -> { if (recheck) revalidate(server); result.accept(completed); });
        });
    }
    private static String page(List<String> rows, int requested) {
        int count = Math.max(1, (rows.size() + 9) / 10); int page = Math.max(1, Math.min(requested, count));
        return "Page " + page + "/" + count + "\n" + String.join("\n", rows.subList(Math.min(rows.size(), (page - 1) * 10), Math.min(rows.size(), page * 10)));
    }
    private void revalidate(MinecraftServer server) {
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            if (!reportCount.containsKey(player.getUUID())) continue;
            Decision decision = service.recheckSession(player.getUUID(), System.currentTimeMillis());
            if (!decision.allowed()) { kick(player, decision.message()); continue; }
            Pending old = pending.get(player.getUUID());
            byte[] challenge = service.challenge(player.getUUID(), System.currentTimeMillis());
            Pending gate = old == null || !old.isolated ? new Pending(player, challenge, service.requiresCompanion()) : old;
            gate.challenge = challenge; gate.sent = false;
            if (service.requiresCompanion() && !gate.isolated) { gate.isolated = true; player.setGameMode(GameType.SPECTATOR); }
            else if (gate.isolated && !service.requiresCompanion()) { restore(player, gate); gate.isolated = false; }
            pending.put(player.getUUID(), gate); reportCount.put(player.getUUID(), 0); send(player, gate);
            if (gate.isolated) player.setGameMode(GameType.SPECTATOR);
        }
    }
    public void stop(MinecraftServer server) {
        for (ServerPlayer player : server.getPlayerList().getPlayers()) disconnected(player);
        saver.shutdown();
        try { if (!saver.awaitTermination(10, TimeUnit.SECONDS)) LOG.warn("State saver still finishing during shutdown"); service.save(); }
        catch (Exception failure) { LOG.error("Cannot flush QiZhangGuard state", failure); }
        if (active == this) active = null;
    }
    private void send(ServerPlayer player, Pending gate) {
        if (!gate.sent && transport.available(player)) { transport.send(player, gate.challenge); gate.sent = true; }
    }
    private void kick(ServerPlayer player, String reason) {
        disconnected(player);
        player.connection.disconnect(Component.literal(reason));
    }
    private void restore(ServerPlayer player, Pending gate) { if (gate != null && gate.isolated) player.setGameMode(gate.mode); }
    private static final class Pending {
        byte[] challenge; volatile boolean isolated; final GameType mode;
        final ServerLevel level;
        final double x, y, z; final float yaw, pitch; boolean sent;
        Pending(ServerPlayer p, byte[] bytes, boolean isolation) { challenge = bytes; isolated = isolation; mode = p.gameMode.getGameModeForPlayer(); level = p.serverLevel(); x = p.getX(); y = p.getY(); z = p.getZ(); yaw = p.getYRot(); pitch = p.getXRot(); }
    }
}
