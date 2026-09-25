package cn.qizhang.guard.core;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.Base64;

/** Thread-safe platform-neutral policy. Call confirmSession only after an authenticated successful join. */
public final class GuardService {
    private static final long RESERVATION_MILLIS = 30000L;
    private static final int MAX_SESSIONS = 65536, MAX_TRACKED_IPS = 100000, MAX_ACCOUNT_PAIRS = 1000000;
    private static final int MAX_RATE_IPS = 4096, MAX_RATE_EVENTS = 100000;
    private static final Set<String> VM_EVIDENCE = Collections.unmodifiableSet(new HashSet<String>(Arrays.asList(
            "virtualbox", "vmware", "qemu", "kvm", "xen", "parallels", "hyper-v-guest", "cloud-vm", "bhyve")));
    private final Path directory;
    private final String serverScope;
    private final SecureRandom random = new SecureRandom();
    private final Object saveLock = new Object();
    private final Map<UUID, Session> sessions = new HashMap<UUID, Session>();
    private final Map<String, Map<UUID, Long>> accounts = new HashMap<String, Map<UUID, Long>>();
    private final Map<UUID, Set<String>> devicesByPlayer = new HashMap<UUID, Set<String>>();
    private final Map<String, Set<UUID>> playersByDevice = new HashMap<String, Set<UUID>>();
    private final Map<UUID, String> playerBans = new HashMap<UUID, String>();
    private final Map<String, String> deviceBans = new HashMap<String, String>();
    private final LinkedHashMap<String, ArrayDeque<Long>> rates = new LinkedHashMap<String, ArrayDeque<Long>>(16, .75f, true);
    private GuardConfig config;
    private Blacklist blacklist;
    private RuleRegistry managedRules;
    private long revision, savedRevision, lastMaintenance;
    private int accountPairs, rateEvents;
    private int devicePairs;

    private static final class Session {
        final String ip;
        final long opened;
        boolean confirmed, reportSatisfied, deviceVerified;
        long reportDeadline;
        String nonce;
        String lastIssuedNonce, previousNonce;
        int staleReportCount;
        String deviceId = "";
        Session(String ip, long opened) { this.ip = ip; this.opened = opened; }
    }

    public GuardService(Path directory) throws IOException {
        if (directory == null) throw new IllegalArgumentException("Missing data directory");
        this.directory = directory.toAbsolutePath().normalize();
        Files.createDirectories(this.directory);
        Path scopeFile = this.directory.resolve("server-id.txt");
        createDefault(scopeFile, randomHex(random) + "\n");
        if (Files.size(scopeFile) > 128) throw new IOException("Invalid server-id.txt; preserve server identity and repair the file");
        serverScope = new String(Files.readAllBytes(scopeFile), StandardCharsets.US_ASCII).trim();
        if (!serverScope.matches("[0-9a-f]{64}")) throw new IOException("Invalid server-id.txt; refusing to silently change device identity scope");
        createDefault(this.directory.resolve("guard.properties"), GuardConfig.DEFAULTS);
        createDefault(this.directory.resolve("blacklist.tsv"), Blacklist.DEFAULTS);
        createDefault(this.directory.resolve("rules.tsv"), RuleRegistry.HEADER);
        reload();
        loadState();
    }

    /** Both policy files validate before either becomes live; active sessions and account history survive reload. */
    public synchronized void reload() throws IOException {
        GuardConfig proposedConfig = GuardConfig.read(directory.resolve("guard.properties"));
        Blacklist proposedBlacklist = Blacklist.read(directory.resolve("blacklist.tsv"));
        RuleRegistry proposedRules = RuleRegistry.read(directory.resolve("rules.tsv"));
        config = proposedConfig;
        blacklist = proposedBlacklist;
        managedRules = proposedRules;
    }

    public synchronized Decision openSession(UUID player, String literalIp, long nowMillis) {
        if (player == null || nowMillis < 0) return Decision.deny("INVALID_SESSION", "Invalid session identity or time");
        if (playerBans.containsKey(player)) return Decision.deny("ACCOUNT_BANNED", "This account is banned by the server");
        Decision playerRule = match("player", player.toString());
        if (!playerRule.allowed()) return sanction(player, playerRule);
        final IpAddress address;
        try { address = IpAddress.parse(literalIp); }
        catch (IllegalArgumentException ex) { return Decision.deny("INVALID_IP", "Expected an IPv4 or IPv6 literal"); }
        maintain(nowMillis);
        if (sessions.containsKey(player)) return Decision.deny("DUPLICATE_SESSION", "This account already has a session");
        String ip = address.toString();
        for (Cidr rule : config.deny) if (rule.contains(address)) return Decision.deny("IP_DENIED", "This IP is denied by server policy");
        if (!config.allow.isEmpty()) {
            boolean found = false;
            for (Cidr rule : config.allow) if (rule.contains(address)) { found = true; break; }
            if (!found) return Decision.deny("IP_NOT_ALLOWED", "This IP is outside the server allowlist");
        }
        if (!recordAttempt(ip, nowMillis)) return Decision.deny("RATE_LIMIT", "Too many connection attempts; try again later");
        if (sessions.size() >= MAX_SESSIONS) return Decision.deny("CAPACITY", "Guard session capacity reached");
        pruneIp(ip, nowMillis);
        Map<UUID, Long> known = accounts.get(ip);
        Set<UUID> reservedAccounts = new HashSet<UUID>();
        if (known != null) reservedAccounts.addAll(known.keySet());
        int online = 0, pendingNewAccounts = 0;
        Set<String> pendingNewIps = new HashSet<String>();
        for (Map.Entry<UUID, Session> item : sessions.entrySet()) {
            Session session = item.getValue();
            if (session.ip.equals(ip)) { online++; reservedAccounts.add(item.getKey()); }
            if (!session.confirmed) {
                Map<UUID, Long> prior = accounts.get(session.ip);
                if (prior == null) pendingNewIps.add(session.ip);
                if (prior == null || !prior.containsKey(item.getKey())) pendingNewAccounts++;
            }
        }
        if (online >= config.maxOnline) return Decision.deny("IP_ONLINE_LIMIT", "Too many simultaneous accounts from this IP");
        if (!reservedAccounts.contains(player) && reservedAccounts.size() >= config.maxAccounts)
            return Decision.deny("IP_ACCOUNT_LIMIT", "This IP has reached the rolling account limit");
        if (known == null && !pendingNewIps.contains(ip) && accounts.size() + pendingNewIps.size() >= MAX_TRACKED_IPS)
            return Decision.deny("CAPACITY", "Guard account storage capacity reached");
        if ((known == null || !known.containsKey(player)) && accountPairs + pendingNewAccounts >= MAX_ACCOUNT_PAIRS)
            return Decision.deny("CAPACITY", "Guard account storage capacity reached");
        sessions.put(player, new Session(ip, nowMillis));
        return Decision.allow();
    }

    /** Commit only successful joins. Attempts/reservations never enter the persisted account database. */
    public synchronized void confirmSession(UUID player, long nowMillis) {
        if (nowMillis < 0) throw new IllegalArgumentException("Invalid time");
        Session session = sessions.get(player);
        if (session == null) throw new IllegalStateException("No reserved session");
        if (session.confirmed) return;
        if (elapsed(nowMillis, session.opened) >= RESERVATION_MILLIS) {
            sessions.remove(player); throw new IllegalStateException("Session reservation expired");
        }
        session.confirmed = true;
        session.reportDeadline = deadline(nowMillis, config.timeout * 1000L);
        Map<UUID, Long> history = accounts.get(session.ip);
        if (history == null) { history = new HashMap<UUID, Long>(); accounts.put(session.ip, history); }
        if (history.put(player, nowMillis) == null) accountPairs++;
        revision++;
    }

    public synchronized void closeSession(UUID player) { sessions.remove(player); }

    public synchronized byte[] challenge(UUID player, long nowMillis) {
        Session session = sessions.get(player);
        if (session == null || !session.confirmed) throw new IllegalStateException("Challenge requires a confirmed session");
        if (nowMillis < 0) throw new IllegalArgumentException("Invalid time");
        session.previousNonce = session.lastIssuedNonce;
        session.nonce = randomHex(random); session.lastIssuedNonce = session.nonce; session.staleReportCount = 0;
        // Reissuing a pending challenge invalidates its nonce without extending its deadline.
        if (session.reportSatisfied) session.reportDeadline = deadline(nowMillis, config.timeout * 1000L);
        session.reportSatisfied = false;
        return Wire.encodeChallenge(session.nonce, serverScope);
    }

    public synchronized Decision acceptReport(UUID player, byte[] payload, long nowMillis) {
        Session session = sessions.get(player);
        if (session == null || !session.confirmed || session.nonce == null)
            return Decision.deny("NO_CHALLENGE", "No outstanding companion challenge");
        String expected = session.nonce;
        session.nonce = null; // Every attempted response consumes the nonce, including malformed or mismatched responses.
        if (playerBans.containsKey(player)) return Decision.deny("ACCOUNT_BANNED", "This account is banned by the server");
        if (nowMillis < 0 || nowMillis >= session.reportDeadline) return Decision.deny("REPORT_EXPIRED", "Companion response timed out");
        final ReportEnvelope envelope;
        try { envelope = Wire.decodeReport(payload); }
        catch (IOException | IllegalArgumentException ex) { return Decision.deny("MALFORMED_REPORT", "Malformed or oversized companion report"); }
        if (!MessageDigest.isEqual(expected.getBytes(StandardCharsets.US_ASCII), envelope.nonce().getBytes(StandardCharsets.US_ASCII))) {
            // A response already in flight during an administrator rechallenge is neither a new pass nor a replay pass.
            if (envelope.nonce().equals(session.previousNonce) && session.staleReportCount++ < 2) {
                session.nonce = expected;
                return Decision.deny("STALE_REPORT", "Previous challenge response ignored; current challenge still required");
            }
            return Decision.deny("NONCE_MISMATCH", "Companion challenge does not match");
        }
        ClientReport report = envelope.report();
        RuleRegistry.Budget policyBudget = new RuleRegistry.Budget();
        if (!report.complete()) return Decision.deny("REPORT_INCOMPLETE", "Companion inventory is incomplete");
        if (config.deviceRequired && report.deviceId().isEmpty()) return Decision.deny("DEVICE_REQUIRED", "This server requires a scoped device identifier");
        if (!report.deviceId().isEmpty()) {
            if (!bindDevice(player, report.deviceId())) return Decision.deny("DEVICE_CAPACITY", "Device association capacity reached");
            if (deviceBans.containsKey(report.deviceId())) return sanction(player, Decision.deny("DEVICE_BANNED", "This reported device identifier is banned"));
            Decision deviceRule = match("device", report.deviceId(), policyBudget);
            if (!deviceRule.allowed()) return sanction(player, deviceRule);
            int peers = 0;
            for (Map.Entry<UUID, Session> entry : sessions.entrySet()) {
                Session other = entry.getValue();
                if (!entry.getKey().equals(player) && other.deviceVerified && other.ip.equals(session.ip) && other.deviceId.equals(report.deviceId())) peers++;
            }
            if (peers >= config.maxIpDevice) return Decision.deny("IP_DEVICE_ONLINE_LIMIT", "Only the configured number of accounts may use the same IP and device concurrently");
        }
        Decision playerRule = match("player", player.toString(), policyBudget);
        if (!playerRule.allowed()) return sanction(player, playerRule);
        Decision alert = null;
        for (String mod : report.modIds()) {
            if (!Blacklist.normalize(mod).matches("[a-z0-9_.-]{1,128}")) return Decision.deny("MALFORMED_REPORT", "Invalid mod identifier");
            Decision result = match("mod", mod, policyBudget);
            if (!result.allowed()) return sanction(player, result);
            if (!result.code().equals("OK")) alert = result;
        }
        for (String pack : report.resourcePacks()) {
            Decision result = match("pack", pack, policyBudget);
            if (!result.allowed()) return sanction(player, result);
            if (!result.code().equals("OK")) alert = result;
        }
        if (config.vmAction != GuardConfig.Action.OFF && !report.vmSignals().isEmpty()) {
            boolean evidence = false;
            for (String signal : report.vmSignals()) if (VM_EVIDENCE.contains(Blacklist.normalize(signal))) evidence = true;
            if (evidence && config.vmAction == GuardConfig.Action.DENY)
                return sanction(player, Decision.deny("VM_DENIED", "Companion reported a virtual machine indicator"));
            alert = Decision.alert(evidence ? "VM_ALERT" : "VM_UNKNOWN", evidence
                    ? "Companion reported a virtual machine indicator" : "VM status is unknown or has only inconclusive indicators");
        }
        session.reportSatisfied = true;
        session.deviceId = report.deviceId(); session.deviceVerified = !report.deviceId().isEmpty();
        return alert == null ? Decision.allow() : alert;
    }

    /** Required timeouts remove the reservation once; optional report timeouts never disconnect. */
    public synchronized List<UUID> expiredReports(long nowMillis) {
        if (nowMillis < 0) throw new IllegalArgumentException("Invalid time");
        maintain(nowMillis);
        List<UUID> expired = new ArrayList<UUID>();
        Iterator<Map.Entry<UUID, Session>> iterator = sessions.entrySet().iterator();
        while (iterator.hasNext()) {
            Map.Entry<UUID, Session> item = iterator.next();
            Session session = item.getValue();
            if (session.confirmed && !session.reportSatisfied && nowMillis >= session.reportDeadline) {
                session.nonce = null;
                if (config.companion) { expired.add(item.getKey()); iterator.remove(); }
            }
        }
        return expired;
    }

    public synchronized Decision checkBrand(String brand) {
        if (brand == null || brand.getBytes(StandardCharsets.UTF_8).length > 256)
            return Decision.deny("INVALID_BRAND", "Invalid client brand");
        return match("brand", brand);
    }
    public synchronized Decision checkBrand(UUID player, String brand) {
        if (player == null) return Decision.deny("INVALID_SESSION", "Missing player identity");
        if (playerBans.containsKey(player)) return Decision.deny("ACCOUNT_BANNED", "This account is banned by the server");
        Decision result = checkBrand(brand);
        return !result.allowed() && result.code().equals("BLACKLIST_DENIED") ? sanction(player, result) : result;
    }
    public synchronized String status() {
        return "QiZhangVerdict sessions=" + sessions.size() + ", trackedIPs=" + accounts.size() + ", accountPairs=" + accountPairs
                + ", rules=" + (blacklist.size() + managedRules.rules.size()) + ", companion=" + (config.companion ? "required" : "optional")
                + ", vm=" + config.vmAction + ", blacklist=" + config.blacklistAction + ", rateBuckets=" + rates.size()
                + ", accountBans=" + playerBans.size() + ", deviceBans=" + deviceBans.size() + ", deviceRequired=" + config.deviceRequired;
    }
    public synchronized boolean requiresCompanion() { return config.companion; }
    public synchronized int reportTimeoutSeconds() { return config.timeout; }
    public synchronized boolean isDirty() { return revision != savedRevision; }

    public synchronized List<String> listRules() {
        List<String> lines = new ArrayList<String>(blacklist.listRules());
        for (RuleRegistry.Rule rule : managedRules.rules) lines.add(rule.line());
        return Collections.unmodifiableList(lines);
    }
    public synchronized String addRule(String list, String kind, String match, String value) throws IOException {
        if (managedRules.rules.size() >= 10000) throw new IOException("Too many managed rules");
        RuleRegistry.Rule added = new RuleRegistry.Rule(UUID.randomUUID().toString(), list, kind, match, value);
        for (RuleRegistry.Rule existing : managedRules.rules) if (existing.list.equals(added.list) && existing.kind.equals(added.kind)
                && existing.match.equals(added.match) && existing.value.equals(added.value)) return existing.id;
        RuleRegistry proposed = managedRules.copy(); proposed.rules.add(added);
        atomicWrite(directory.resolve("rules.tsv"), proposed.encode()); managedRules = proposed; return added.id;
    }
    public synchronized boolean removeRule(String id) throws IOException {
        if (id == null) return false;
        if (id.startsWith("legacy:")) {
            String[] target = id.split(":", 3); if (target.length != 3) return false;
            Path path = directory.resolve("blacklist.tsv"); StringBuilder out = new StringBuilder(); boolean removed = false;
            // Validate the file before an admin operation so unrelated malformed edits are never silently lost.
            Blacklist.read(path);
            for (String line : Files.readAllLines(path, StandardCharsets.UTF_8)) {
                String[] fields = line.split("\t", -1);
                if (fields.length == 4 && Blacklist.normalize(fields[0]).equals(target[1]) && Blacklist.normalize(fields[1]).equals(target[2])) removed = true;
                else out.append(line).append('\n');
            }
            if (!removed) return false;
            atomicWrite(path, out.toString().getBytes(StandardCharsets.UTF_8)); blacklist = Blacklist.read(path); return true;
        }
        RuleRegistry proposed = managedRules.copy(); boolean removed = false;
        Iterator<RuleRegistry.Rule> iterator = proposed.rules.iterator();
        while (iterator.hasNext()) if (iterator.next().id.equals(id)) { iterator.remove(); removed = true; }
        if (!removed) return false;
        atomicWrite(directory.resolve("rules.tsv"), proposed.encode()); managedRules = proposed; return true;
    }
    public synchronized List<String> listBans() {
        List<String> lines = new ArrayList<String>();
        for (Map.Entry<UUID, String> entry : playerBans.entrySet()) lines.add(entry.getKey() + "\t" + entry.getValue());
        for (Map.Entry<String, String> entry : deviceBans.entrySet()) lines.add("device:" + entry.getKey() + "\t" + entry.getValue());
        Collections.sort(lines); return Collections.unmodifiableList(lines);
    }
    /** Adapters must disconnect these players; querying never mutates a live session. */
    public synchronized List<UUID> bannedSessions() {
        List<UUID> result = new ArrayList<UUID>();
        for (Map.Entry<UUID, Session> entry : sessions.entrySet())
            if (playerBans.containsKey(entry.getKey()) || (!entry.getValue().deviceId.isEmpty() && deviceBans.containsKey(entry.getValue().deviceId))) result.add(entry.getKey());
        return result;
    }
    /** Revalidate online policy after reload without closing/reopening or changing rolling history. */
    public synchronized Decision recheckSession(UUID player, long nowMillis) {
        if (nowMillis < 0) return Decision.deny("INVALID_SESSION", "Invalid session time");
        Session session = sessions.get(player);
        if (session == null) return Decision.deny("NO_SESSION", "No active guard session");
        if (playerBans.containsKey(player)) return Decision.deny("ACCOUNT_BANNED", "This account is banned by the server");
        if (!session.deviceId.isEmpty() && deviceBans.containsKey(session.deviceId)) return Decision.deny("DEVICE_BANNED", "This reported device identifier is banned");
        IpAddress address = IpAddress.parse(session.ip);
        for (Cidr rule : config.deny) if (rule.contains(address)) return Decision.deny("IP_DENIED", "This IP is denied by server policy");
        if (!config.allow.isEmpty()) {
            boolean found = false; for (Cidr rule : config.allow) if (rule.contains(address)) { found = true; break; }
            if (!found) return Decision.deny("IP_NOT_ALLOWED", "This IP is outside the server allowlist");
        }
        Decision playerRule = match("player", player.toString());
        return playerRule.allowed() ? playerRule : sanction(player, playerRule);
    }
    public void ban(UUID player, String reason) throws IOException {
        if (player == null) throw new IllegalArgumentException("Missing player UUID");
        synchronized (this) { if (!banAssociated(player, safeReason(reason))) throw new IOException("Ban storage capacity reached; no ban records changed"); }
        save();
    }
    public boolean unban(String target) throws IOException {
        boolean removed;
        synchronized (this) {
            if (target != null && target.startsWith("device:")) {
                String device = target.substring(7);
                if (!device.matches("[0-9a-f]{64}")) throw new IllegalArgumentException("Invalid device digest");
                removed = deviceBans.remove(device) != null;
            } else {
                UUID player = UUID.fromString(target == null ? "" : target);
                if (!player.toString().equals(target)) throw new IllegalArgumentException("Expected canonical UUID");
                removed = playerBans.remove(player) != null;
            }
            if (removed) revision++;
        }
        if (removed) save(); return removed;
    }

    /** Snapshot under the service lock, serialize writes, fsync the temporary file, then atomically replace. */
    public void save() throws IOException {
        synchronized (saveLock) {
            final byte[] snapshot;
            final long snapshotRevision;
            synchronized (this) {
                snapshotRevision = revision;
                StringBuilder out = new StringBuilder("QZG-STATE\t2\n");
                List<String> ips = new ArrayList<String>(accounts.keySet()); Collections.sort(ips);
                for (String ip : ips) {
                    List<UUID> ids = new ArrayList<UUID>(accounts.get(ip).keySet()); Collections.sort(ids);
                    for (UUID id : ids) out.append("A\t").append(ip).append('\t').append(id).append('\t').append(accounts.get(ip).get(id)).append('\n');
                }
                List<UUID> players = new ArrayList<UUID>(devicesByPlayer.keySet()); Collections.sort(players);
                for (UUID player : players) {
                    List<String> devices = new ArrayList<String>(devicesByPlayer.get(player)); Collections.sort(devices);
                    for (String device : devices) out.append("D\t").append(player).append('\t').append(device).append('\n');
                }
                for (String line : listBans()) {
                    int tab = line.indexOf('\t'); String target = line.substring(0, tab), reason = line.substring(tab + 1);
                    out.append(target.startsWith("device:") ? "V\t" : "B\t").append(target.startsWith("device:") ? target.substring(7) : target)
                            .append('\t').append(Base64.getEncoder().encodeToString(reason.getBytes(StandardCharsets.UTF_8))).append('\n');
                }
                snapshot = out.toString().getBytes(StandardCharsets.UTF_8);
                if (snapshot.length > 134217728) throw new IOException("Account state exceeds the 128 MiB safe reload limit; existing state retained");
            }
            atomicWrite(directory.resolve("accounts.state"), snapshot);
            synchronized (this) { if (revision == snapshotRevision) savedRevision = snapshotRevision; }
        }
    }

    private Decision match(String kind, String value) {
        return match(kind, value, new RuleRegistry.Budget());
    }
    private Decision match(String kind, String value, RuleRegistry.Budget budget) {
        if (config.blacklistAction == GuardConfig.Action.OFF) return Decision.allow();
        try {
            if (managedRules.matches("WHITE", kind, value, budget)) return Decision.allow();
            if (managedRules.matches("BLACK", kind, value, budget)) return config.blacklistAction == GuardConfig.Action.DENY
                    ? Decision.deny("BLACKLIST_DENIED", "Reported " + kind + " matches a server blacklist rule")
                    : Decision.alert("BLACKLIST_ALERT", "Reported " + kind + " matches a server blacklist rule");
        } catch (RuleRegistry.BudgetExceeded ex) { return Decision.deny("RULE_EVALUATION_LIMIT", "Server rule complexity exceeds the bounded evaluation budget"); }
        Blacklist.Rule rule = blacklist.lookup(kind, value);
        if (rule == null || rule.action == GuardConfig.Action.OFF || config.blacklistAction == GuardConfig.Action.OFF) return Decision.allow();
        String code = rule.kind.equals("automation") ? "AUTOMATION" : "BLACKLIST";
        if (rule.action == GuardConfig.Action.DENY && config.blacklistAction == GuardConfig.Action.DENY)
            return Decision.deny(code + "_DENIED", "Reported " + kind + " matches an exact server blacklist rule");
        return Decision.alert(code + "_ALERT", "Reported " + kind + " matches an exact server blacklist rule");
    }

    private Decision sanction(UUID player, Decision result) {
        if (!result.allowed() && config.banOnDeny && (result.code().equals("BLACKLIST_DENIED") || result.code().equals("AUTOMATION_DENIED") || result.code().equals("VM_DENIED") || result.code().equals("DEVICE_BANNED")))
            if (!banAssociated(player, safeReason(result.code()))) return Decision.deny("SANCTION_CAPACITY", "Ban capacity reached; connection denied without new permanent records");
        return result;
    }
    private boolean bindDevice(UUID player, String device) {
        Set<String> devices = devicesByPlayer.get(player);
        if (devices != null && devices.contains(device)) return true;
        if (devicePairs >= MAX_ACCOUNT_PAIRS || (devices != null && devices.size() >= 8)) return false;
        if (devices == null) { devices = new HashSet<String>(); devicesByPlayer.put(player, devices); }
        devices.add(device);
        Set<UUID> players = playersByDevice.get(device);
        if (players == null) { players = new HashSet<UUID>(); playersByDevice.put(device, players); }
        players.add(player); devicePairs++; revision++; return true;
    }
    private boolean banAssociated(UUID initial, String reason) {
        ArrayDeque<UUID> pending = new ArrayDeque<UUID>(); Set<UUID> visitedPlayers = new HashSet<UUID>(); Set<String> visitedDevices = new HashSet<String>();
        pending.add(initial);
        while (!pending.isEmpty()) {
            UUID player = pending.removeFirst(); if (!visitedPlayers.add(player)) continue;
            Set<String> devices = devicesByPlayer.get(player);
            if (devices == null) continue;
            for (String device : devices) if (visitedDevices.add(device)) {
                Set<UUID> linked = playersByDevice.get(device); if (linked != null) pending.addAll(linked);
            }
        }
        int newPlayers = 0, newDevices = 0;
        for (UUID player : visitedPlayers) if (!playerBans.containsKey(player)) newPlayers++;
        for (String device : visitedDevices) if (!deviceBans.containsKey(device)) newDevices++;
        if ((long) playerBans.size() + newPlayers > MAX_ACCOUNT_PAIRS || (long) deviceBans.size() + newDevices > MAX_ACCOUNT_PAIRS) return false;
        for (UUID player : visitedPlayers) if (!reason.equals(playerBans.put(player, reason))) revision++;
        for (String device : visitedDevices) if (!reason.equals(deviceBans.put(device, reason))) revision++;
        return true;
    }
    private static String safeReason(String reason) {
        if (reason == null || reason.trim().isEmpty()) return "Administrator ban";
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < reason.length() && out.length() < 160; i++) if (!Character.isISOControl(reason.charAt(i))) out.append(reason.charAt(i));
        return out.toString().isEmpty() ? "Administrator ban" : out.toString();
    }

    private void maintain(long now) {
        Iterator<Session> iterator = sessions.values().iterator();
        while (iterator.hasNext()) {
            Session session = iterator.next();
            if (!session.confirmed && elapsed(now, session.opened) >= RESERVATION_MILLIS) iterator.remove();
        }
        if (lastMaintenance == 0 || elapsed(now, lastMaintenance) >= 60000L) {
            for (String ip : new ArrayList<String>(accounts.keySet())) pruneIp(ip, now);
            Iterator<ArrayDeque<Long>> ratesIterator = rates.values().iterator();
            while (ratesIterator.hasNext()) {
                ArrayDeque<Long> queue = ratesIterator.next(); trimRate(queue, now);
                if (queue.isEmpty()) ratesIterator.remove();
            }
            lastMaintenance = now;
        }
    }
    private void pruneIp(String ip, long now) {
        Map<UUID, Long> history = accounts.get(ip);
        if (history == null) return;
        Iterator<Long> iterator = history.values().iterator();
        while (iterator.hasNext()) if (elapsed(now, iterator.next()) >= config.windowMillis) { iterator.remove(); accountPairs--; revision++; }
        if (history.isEmpty()) accounts.remove(ip);
    }
    private boolean recordAttempt(String ip, long now) {
        ArrayDeque<Long> queue = rates.get(ip);
        if (queue == null) {
            while (rates.size() >= MAX_RATE_IPS || rateEvents >= MAX_RATE_EVENTS) evictOldestRate();
            queue = new ArrayDeque<Long>(); rates.put(ip, queue);
        }
        trimRate(queue, now);
        if (queue.size() >= config.attempts) return false;
        if (rateEvents >= MAX_RATE_EVENTS) return false;
        queue.addLast(now); rateEvents++; return true;
    }
    private void trimRate(ArrayDeque<Long> queue, long now) {
        while (!queue.isEmpty() && elapsed(now, queue.peekFirst()) >= 60000L) { queue.removeFirst(); rateEvents--; }
    }
    private void evictOldestRate() {
        Iterator<ArrayDeque<Long>> iterator = rates.values().iterator();
        if (iterator.hasNext()) { rateEvents -= iterator.next().size(); iterator.remove(); }
    }
    private void loadState() throws IOException {
        Path state = directory.resolve("accounts.state");
        if (!Files.exists(state)) return;
        if (Files.size(state) > 134217728L) throw new IOException("Account state exceeds 128 MiB; refusing to discard it");
        try (BufferedReader reader = Files.newBufferedReader(state, StandardCharsets.UTF_8)) {
            String header = reader.readLine(); boolean legacy = "QZG-STATE\t1".equals(header);
            if (!legacy && !"QZG-STATE\t2".equals(header)) throw new IOException("Invalid account state header; refusing to reset history");
            String line; int lineNo = 1;
            while ((line = reader.readLine()) != null) {
                lineNo++;
                if (line.length() > 2048) throw new IOException("Account state line is too long: " + lineNo);
                String[] fields = line.split("\t", -1);
                try {
                    if (legacy || (fields.length == 4 && fields[0].equals("A"))) {
                        int offset = legacy ? 0 : 1;
                        if (fields.length != offset + 3) throw new IllegalArgumentException("Invalid account row");
                        String ip = IpAddress.parse(fields[offset]).toString(); UUID id = canonicalUuid(fields[offset + 1]);
                        long seen = Long.parseLong(fields[offset + 2]); if (seen < 0) throw new IllegalArgumentException("Negative timestamp");
                        Map<UUID, Long> history = accounts.get(ip);
                        if (history == null) { history = new HashMap<UUID, Long>(); accounts.put(ip, history); }
                        if (history.put(id, seen) != null) throw new IllegalArgumentException("Duplicate account record");
                        if (++accountPairs > MAX_ACCOUNT_PAIRS || accounts.size() > MAX_TRACKED_IPS) throw new IOException("Account state exceeds capacity");
                    } else if (fields.length == 3 && fields[0].equals("D")) {
                        UUID player = canonicalUuid(fields[1]); String device = fields[2];
                        if (!device.matches("[0-9a-f]{64}")) throw new IllegalArgumentException("Invalid device digest");
                        if (devicesByPlayer.containsKey(player) && devicesByPlayer.get(player).contains(device)) throw new IllegalArgumentException("Duplicate device record");
                        if (!bindDevice(player, device)) throw new IllegalArgumentException("Device association capacity exceeded");
                    } else if (fields.length == 3 && (fields[0].equals("B") || fields[0].equals("V"))) {
                        byte[] reasonBytes = Base64.getDecoder().decode(fields[2]);
                        String reason = StandardCharsets.UTF_8.newDecoder().onMalformedInput(java.nio.charset.CodingErrorAction.REPORT)
                                .onUnmappableCharacter(java.nio.charset.CodingErrorAction.REPORT).decode(ByteBuffer.wrap(reasonBytes)).toString();
                        if (!safeReason(reason).equals(reason)) throw new IllegalArgumentException("Invalid ban reason");
                        if (fields[0].equals("B")) {
                            if (playerBans.put(canonicalUuid(fields[1]), reason) != null) throw new IllegalArgumentException("Duplicate player ban");
                        } else {
                            if (!fields[1].matches("[0-9a-f]{64}")) throw new IllegalArgumentException("Invalid device digest");
                            if (deviceBans.put(fields[1], reason) != null) throw new IllegalArgumentException("Duplicate device ban");
                        }
                        if (playerBans.size() > MAX_ACCOUNT_PAIRS || deviceBans.size() > MAX_ACCOUNT_PAIRS) throw new IllegalArgumentException("Ban capacity exceeded");
                    } else throw new IllegalArgumentException("Unrecognized state row");
                } catch (IllegalArgumentException ex) { throw new IOException("Invalid account state at line " + lineNo + "; refusing to reset history", ex); }
            }
            revision = 0; savedRevision = 0;
        }
    }
    private static UUID canonicalUuid(String value) {
        UUID uuid = UUID.fromString(value); if (!uuid.toString().equals(value)) throw new IllegalArgumentException("Noncanonical UUID"); return uuid;
    }
    private static void createDefault(Path path, String contents) throws IOException {
        if (!Files.exists(path)) {
            try { Files.write(path, contents.getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE); }
            catch (java.nio.file.FileAlreadyExistsException ignored) { /* Another creator won; validate its file. */ }
        }
    }
    private static void atomicWrite(Path destination, byte[] bytes) throws IOException {
        Path temp = Files.createTempFile(destination.getParent(), ".qzg-state-", ".tmp");
        try {
            try (FileChannel channel = FileChannel.open(temp, StandardOpenOption.WRITE, StandardOpenOption.TRUNCATE_EXISTING)) {
                ByteBuffer data = ByteBuffer.wrap(bytes);
                while (data.hasRemaining()) channel.write(data);
                channel.force(true);
            }
            try { Files.move(temp, destination, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING); }
            catch (AtomicMoveNotSupportedException ex) { throw new IOException("Filesystem does not support atomic state replacement; existing history retained", ex); }
        } finally { Files.deleteIfExists(temp); }
    }
    private static long elapsed(long now, long before) { return now >= before ? now - before : 0L; }
    private static long deadline(long now, long delta) { return now > Long.MAX_VALUE - delta ? Long.MAX_VALUE : now + delta; }
    private static String randomHex(SecureRandom random) {
        byte[] bytes = new byte[32]; random.nextBytes(bytes); StringBuilder out = new StringBuilder(64);
        for (byte value : bytes) out.append(Character.forDigit((value >>> 4) & 15, 16)).append(Character.forDigit(value & 15, 16));
        return out.toString();
    }
}
