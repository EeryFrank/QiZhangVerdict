package cn.qizhang.guard.bukkit;

import cn.qizhang.guard.core.Decision;
import cn.qizhang.guard.core.GuardService;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.entity.Projectile;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.block.BlockPlaceEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryDragEvent;
import org.bukkit.event.player.*;
import org.bukkit.plugin.Plugin;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.plugin.messaging.PluginMessageListener;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** Bukkit API only: avoids NMS linkage across server versions. Folia is not supported. */
public final class QiZhangVerdictPlugin extends JavaPlugin implements Listener, PluginMessageListener {
    private GuardService guard;
    private String channel;
    private String brandChannel;
    private final Map<UUID, byte[]> challenges = new HashMap<>();
    private final Set<UUID> waiting = new HashSet<>();
    private final Map<UUID, Integer> messageCounts = new HashMap<>();
    private final Map<UUID, String> brands = new HashMap<>();
    private final Set<PlayerLoginEvent> admittedEvents = Collections.newSetFromMap(new IdentityHashMap<PlayerLoginEvent, Boolean>());
    private final AtomicBoolean saving = new AtomicBoolean();
    private ScheduledExecutorService persistence;

    @Override public void onEnable() {
        Bukkit.getPluginManager().registerEvents(this, this);
        try { guard = new GuardService(getDataFolder().toPath()); }
        catch (Exception ex) {
            getLogger().severe("QiZhangVerdict configuration/state invalid. ALL LOGINS BLOCKED until configuration is repaired and server restarted: " + ex.getMessage());
            for (Player player : Bukkit.getOnlinePlayers()) player.kickPlayer("QiZhangVerdict unavailable: administrator must repair guard configuration.");
            return;
        }
        boolean modern = modernChannels(Bukkit.getBukkitVersion());
        channel = modern ? "qzguard:main" : "QZGuard";
        brandChannel = modern ? "minecraft:brand" : "MC|Brand";
        Bukkit.getMessenger().registerIncomingPluginChannel(this, channel, this);
        Bukkit.getMessenger().registerOutgoingPluginChannel(this, channel);
        Bukkit.getMessenger().registerIncomingPluginChannel(this, brandChannel, this);
        persistence = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "QiZhangVerdict-persistence"); t.setDaemon(true); return t;
        });
        persistence.scheduleWithFixedDelay(this::saveSafely, 5, 5, TimeUnit.SECONDS);
        Bukkit.getScheduler().runTaskTimer(this, () -> {
            for (UUID id : guard.bannedSessions()) {
                Player p = Bukkit.getPlayer(id);
                if (p != null) p.kickPlayer("[QiZhangVerdict] Account or associated device is banned.");
                cleanup(id);
            }
            for (UUID id : guard.expiredReports(System.currentTimeMillis())) {
                Player p = Bukkit.getPlayer(id);
                if (p != null) p.kickPlayer("[QiZhangVerdict] Required companion report timed out.");
                cleanup(id);
            }
        }, 20L, 20L);
        // Bukkit /reload may enable us with players already online.
        for (Player p : Bukkit.getOnlinePlayers()) {
            Decision d = guard.openSession(p.getUniqueId(), p.getAddress().getAddress().getHostAddress(), System.currentTimeMillis());
            if (!d.allowed()) p.kickPlayer(d.message());
            else { joined(p); }
        }
        if (!Bukkit.getOnlineMode()) getLogger().warning("Offline mode: UUID/account ownership needs external authentication; IP limits are not proof of identity. Secure proxy forwarding and firewall the backend.");
        getLogger().info(guard.status());
        getLogger().info(integrations());
    }

    static boolean modernChannels(String version) {
        try { String[] parts = version.split("[.-]"); return Integer.parseInt(parts[0]) > 1 || Integer.parseInt(parts[1]) >= 13; }
        catch (RuntimeException ex) { return true; }
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void login(PlayerLoginEvent event) {
        if (guard == null) { event.disallow(PlayerLoginEvent.Result.KICK_OTHER, "QiZhangVerdict unavailable: logins blocked until configuration is repaired."); return; }
        if (event.getResult() != PlayerLoginEvent.Result.ALLOWED) return;
        UUID id = event.getPlayer().getUniqueId();
        Decision d = guard.openSession(id, event.getAddress().getHostAddress(), System.currentTimeMillis());
        if (!d.allowed()) event.disallow(PlayerLoginEvent.Result.KICK_OTHER, d.message());
        else admittedEvents.add(event);
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void cancelledLogin(PlayerLoginEvent event) {
        boolean admitted = admittedEvents.remove(event);
        if (event.getResult() != PlayerLoginEvent.Result.ALLOWED && admitted) {
            guard.closeSession(event.getPlayer().getUniqueId());
        }
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void join(PlayerJoinEvent event) { joined(event.getPlayer()); }

    private void joined(Player player) {
        if (guard == null) { player.kickPlayer("QiZhangVerdict unavailable."); return; }
        UUID id = player.getUniqueId();
        try {
            guard.confirmSession(id, System.currentTimeMillis());
            if (guard.requiresCompanion()) waiting.add(id);
            byte[] challenge = guard.challenge(id, System.currentTimeMillis());
            challenges.put(id, challenge);
            Bukkit.getScheduler().runTaskLater(this, new PendingChallengeTask(player,
                    () -> Bukkit.getPlayer(id), player::isOnline, () -> challenges.get(id),
                    current -> player.sendPluginMessage(this, channel, current)), 2L);
        } catch (RuntimeException ex) {
            cleanup(id); player.kickPlayer("QiZhangVerdict: admission expired; reconnect.");
            getLogger().warning("Could not confirm session " + id + ": " + ex.getMessage());
        }
    }

    @EventHandler public void channelRegistered(PlayerRegisterChannelEvent event) {
        if (channel == null || !channel.equals(event.getChannel())) return;
        byte[] pending = challenges.get(event.getPlayer().getUniqueId());
        if (pending != null) event.getPlayer().sendPluginMessage(this, channel, pending);
    }

    @EventHandler public void quit(PlayerQuitEvent event) { cleanup(event.getPlayer().getUniqueId()); }
    private void cleanup(UUID id) {
        if (guard != null) guard.closeSession(id);
        challenges.remove(id); waiting.remove(id); messageCounts.remove(id); brands.remove(id);
    }

    @Override public void onPluginMessageReceived(String incoming, Player player, byte[] bytes) {
        UUID id = player.getUniqueId();
        int count = messageCounts.containsKey(id) ? messageCounts.get(id) + 1 : 1;
        messageCounts.put(id, count);
        if (count > 12 || bytes.length > 30000) { player.kickPlayer("[QiZhangVerdict] Invalid or excessive client reports."); return; }
        if (channel.equals(incoming)) {
            if (!challenges.containsKey(id)) return;
            Decision d = guard.acceptReport(id, bytes, System.currentTimeMillis());
            if ("STALE_REPORT".equals(d.code())) return;
            if (!d.allowed()) { player.kickPlayer("[QiZhangVerdict] " + d.message()); return; }
            challenges.remove(id); waiting.remove(id);
            if (!"OK".equals(d.code()) && !"ALLOW".equals(d.code())) getLogger().warning("Client policy " + d.code() + " player=" + id + " " + d.message());
        } else if (brandChannel.equals(incoming)) {
            try {
                String brand = readBrand(bytes); brands.put(id, brand);
                Decision d = guard.checkBrand(id, brand);
                if (!d.allowed()) player.kickPlayer("[QiZhangVerdict] " + d.message());
            } catch (IOException ex) { player.kickPlayer("[QiZhangVerdict] Malformed client brand."); }
        }
    }

    private static String readBrand(byte[] bytes) throws IOException {
        int value = 0, shift = 0, index = 0;
        while (true) {
            if (index >= bytes.length || shift >= 35) throw new IOException("Invalid VarInt");
            int next = bytes[index++] & 255; value |= (next & 127) << shift;
            if ((next & 128) == 0) break;
            shift += 7;
        }
        if (value < 0 || value > 256 || bytes.length - index != value) throw new IOException("Invalid brand size");
        try { return StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes, index, value)).toString(); }
        catch (CharacterCodingException ex) { throw new IOException(ex); }
    }

    private boolean waiting(Player player) { return waiting.contains(player.getUniqueId()); }
    @EventHandler(ignoreCancelled = true) public void move(PlayerMoveEvent e) {
        if (!waiting(e.getPlayer()) || e.getTo() == null) return;
        Location from = e.getFrom(), to = e.getTo();
        if (from.getX() != to.getX() || from.getY() != to.getY() || from.getZ() != to.getZ()) e.setTo(from);
    }
    @EventHandler(ignoreCancelled = true) public void interact(PlayerInteractEvent e) { if (waiting(e.getPlayer())) e.setCancelled(true); }
    @EventHandler(ignoreCancelled = true) public void interactEntity(PlayerInteractEntityEvent e) { if (waiting(e.getPlayer())) e.setCancelled(true); }
    @EventHandler(ignoreCancelled = true) public void breakBlock(BlockBreakEvent e) { if (waiting(e.getPlayer())) e.setCancelled(true); }
    @EventHandler(ignoreCancelled = true) public void placeBlock(BlockPlaceEvent e) { if (waiting(e.getPlayer())) e.setCancelled(true); }
    @EventHandler(ignoreCancelled = true) public void inventory(InventoryClickEvent e) { if (waiting.contains(e.getWhoClicked().getUniqueId())) e.setCancelled(true); }
    @EventHandler(ignoreCancelled = true) public void drag(InventoryDragEvent e) { if (waiting.contains(e.getWhoClicked().getUniqueId())) e.setCancelled(true); }
    @EventHandler(ignoreCancelled = true) public void pickup(PlayerPickupItemEvent e) { if (waiting(e.getPlayer())) e.setCancelled(true); }
    @EventHandler(ignoreCancelled = true) public void fillBucket(PlayerBucketFillEvent e) { if (waiting(e.getPlayer())) e.setCancelled(true); }
    @EventHandler(ignoreCancelled = true) public void emptyBucket(PlayerBucketEmptyEvent e) { if (waiting(e.getPlayer())) e.setCancelled(true); }
    @EventHandler(ignoreCancelled = true) public void drop(PlayerDropItemEvent e) { if (waiting(e.getPlayer())) e.setCancelled(true); }
    @EventHandler(ignoreCancelled = true) public void command(PlayerCommandPreprocessEvent e) { if (waiting(e.getPlayer())) e.setCancelled(true); }
    @EventHandler(ignoreCancelled = true) public void damage(EntityDamageEvent e) {
        if (waiting.contains(e.getEntity().getUniqueId())) e.setCancelled(true);
        if (e instanceof EntityDamageByEntityEvent && waiting.contains(((EntityDamageByEntityEvent)e).getDamager().getUniqueId())) e.setCancelled(true);
        if (e instanceof EntityDamageByEntityEvent && ((EntityDamageByEntityEvent)e).getDamager() instanceof Projectile) {
            Object shooter = ((Projectile)((EntityDamageByEntityEvent)e).getDamager()).getShooter();
            if (shooter instanceof Player && waiting((Player)shooter)) e.setCancelled(true);
        }
    }

    @Override public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!sender.hasPermission("qzverdict.admin")) { sender.sendMessage("No permission."); return true; }
        if (guard == null) { sender.sendMessage("QiZhangVerdict unavailable: fix policy/state and restart. Logins remain blocked."); return true; }
        if (args.length >= 2 && args[0].equalsIgnoreCase("rule") && args[1].equalsIgnoreCase("list")) {
            return onCommand(sender, command, label, args.length > 2 ? new String[]{"rules", args[2]} : new String[]{"rules"});
        }
        String action = args.length == 0 ? "status" : args[0].toLowerCase(Locale.ROOT);
        if (action.equals("reload")) {
            try {
                guard.reload();
            } catch (Exception ex) { sender.sendMessage("Reload rejected; previous policy remains active: " + ex.getMessage()); return true; }
            recheckOnline();
            sender.sendMessage("QiZhangVerdict configuration reloaded. " + guard.status());
        } else if (action.equals("integrations")) sender.sendMessage(integrations());
        else if (action.equals("status")) sender.sendMessage(guard.status());
        else if (action.equals("rules") || action.equals("bans")) {
            List<String> rows = action.equals("rules") ? guard.listRules() : guard.listBans();
            int page = 1;
            try { if (args.length > 1) page = Integer.parseInt(args[1]); }
            catch (NumberFormatException ex) { sender.sendMessage("Page must be a number."); return true; }
            int pages = Math.max(1, (rows.size() + 9) / 10);
            if (page < 1 || page > pages) { sender.sendMessage("Page range: 1.." + pages); return true; }
            sender.sendMessage(action + " page " + page + "/" + pages);
            for (int i = (page - 1) * 10; i < Math.min(page * 10, rows.size()); i++) sender.sendMessage(rows.get(i));
        } else if (action.equals("rule")) {
            try {
                if (args.length >= 6 && args[1].equalsIgnoreCase("add")) {
                    String id = guard.addRule(args[2], args[3], args[4], joinArgs(args, 5));
                    recheckOnline(); sender.sendMessage("Added rule and rechecking online players: " + id);
                } else if (args.length == 3 && args[1].equalsIgnoreCase("remove")) {
                    sender.sendMessage(guard.removeRule(args[2]) ? "Removed rule." : "Rule ID not found."); recheckOnline();
                } else sender.sendMessage("/qzverdict rule add <BLACK|WHITE> <MOD|PACK|BRAND|PLAYER|DEVICE> <EXACT|GLOB> <value> ; rule remove <id>");
            } catch (Exception ex) { sender.sendMessage("Rule change rejected: " + ex.getMessage()); }
        } else if (action.equals("ban") && args.length >= 2) {
            try {
                Player target = Bukkit.getPlayerExact(args[1]);
                UUID id = target == null ? UUID.fromString(args[1]) : target.getUniqueId();
                String reason = args.length > 2 ? joinArgs(args, 2) : "Administrator ban";
                guard.ban(id, reason);
                if (target != null) target.kickPlayer("[QiZhangVerdict] " + reason);
                sender.sendMessage("Banned account and known associated device(s): " + id);
            } catch (Exception ex) { sender.sendMessage("Ban rejected (use online name or UUID): " + ex.getMessage()); }
        } else if (action.equals("unban") && args.length == 2) {
            try { sender.sendMessage(guard.unban(args[1]) ? "Unbanned target. Account and device bans are separate; check /qzverdict bans." : "Ban target not found."); }
            catch (Exception ex) { sender.sendMessage("Unban rejected: " + ex.getMessage()); }
        }
        else return false;
        return true;
    }

    private static String joinArgs(String[] args, int start) {
        StringBuilder result = new StringBuilder();
        for (int i = start; i < args.length; i++) { if (i > start) result.append(' '); result.append(args[i]); }
        return result.toString();
    }

    private void recheckOnline() {
        for (Player p : Bukkit.getOnlinePlayers()) {
            UUID id = p.getUniqueId();
            try {
                Decision admission = guard.recheckSession(id, System.currentTimeMillis());
                if (!admission.allowed()) { p.kickPlayer(admission.message()); cleanup(id); continue; }
                String brand = brands.get(id);
                if (brand != null) {
                    Decision d = guard.checkBrand(id, brand);
                    if (!d.allowed()) { p.kickPlayer(d.message()); continue; }
                }
                if (guard.requiresCompanion()) waiting.add(id); else waiting.remove(id);
                byte[] challenge = guard.challenge(id, System.currentTimeMillis());
                challenges.put(id, challenge); messageCounts.remove(id);
                p.sendPluginMessage(this, channel, challenge);
            } catch (RuntimeException ex) { p.kickPlayer("QiZhangVerdict: session recheck failed; reconnect."); cleanup(id); }
        }
    }

    private String integrations() {
        Plugin grim = Bukkit.getPluginManager().getPlugin("GrimAC");
        Plugin xray = Bukkit.getPluginManager().getPlugin("Orebfuscator");
        String serverName = (Bukkit.getName() + " " + Bukkit.getVersion()).toLowerCase(Locale.ROOT);
        boolean paper = serverName.contains("paper") || serverName.contains("purpur");
        return "Integrations: GrimAC=" + (grim != null && grim.isEnabled() ? grim.getDescription().getVersion() + " enabled (check configuration)" : "MISSING; movement/combat prediction unavailable")
            + "; Orebfuscator=" + (xray != null && xray.isEnabled() ? "enabled (check configuration)" : "absent")
            + "; Paper Anti-Xray=" + (paper ? "available; enable and verify per-world config" : "not detected")
            + ". These engines are installed separately.";
    }

    private void saveSafely() {
        if (guard == null || !guard.isDirty() || !saving.compareAndSet(false, true)) return;
        try { guard.save(); } catch (Exception ex) { getLogger().severe("Account history could not be saved: " + ex.getMessage()); }
        finally { saving.set(false); }
    }
    @Override public void onDisable() {
        if (persistence != null) {
            persistence.shutdown();
            try { if (!persistence.awaitTermination(10, TimeUnit.SECONDS)) persistence.shutdownNow(); }
            catch (InterruptedException ex) { persistence.shutdownNow(); Thread.currentThread().interrupt(); }
        }
        if (guard != null) { try { guard.save(); } catch (Exception ex) { getLogger().severe("Final account history save failed: " + ex.getMessage()); } }
        challenges.clear(); waiting.clear(); admittedEvents.clear(); messageCounts.clear(); brands.clear();
    }
}
