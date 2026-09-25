package cn.qizhang.guard.core;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicInteger;

/** Dependency-free integration/security regression runner: Gradle :core:securityTest. */
public final class SecurityRegressionTest {
    private static final long NOW = 1800000000000L;
    private static int passed;
    private static Path testRoot;
    private static final String DEVICE_A = String.join("", Collections.nCopies(64, "a"));
    private static final String DEVICE_B = String.join("", Collections.nCopies(64, "b"));
    private static final String DEVICE_C = String.join("", Collections.nCopies(64, "c"));
    private interface Check { void run() throws Exception; }
    public static void main(String[] args) throws Exception {
        testRoot = Paths.get(System.getProperty("qzguard.testDir", "E:/CodexTemp/QiZhangGuard/core-tests"));
        Files.createDirectories(testRoot);
        run("literal parser rejects DNS and ambiguous representations", SecurityRegressionTest::literalValidation);
        run("IPv4-mapped IPv6 shares limits with IPv4", SecurityRegressionTest::mappedIdentity);
        run("IPv6 canonical forms share limits", SecurityRegressionTest::ipv6Identity);
        run("CIDR allow and deny precedence", SecurityRegressionTest::cidrPolicy);
        run("mapped CIDR semantics", SecurityRegressionTest::mappedCidr);
        run("failed attempts do not consume persisted accounts", SecurityRegressionTest::unconfirmedNotPersisted);
        run("rolling history survives restart and expires", SecurityRegressionTest::rollingHistory);
        run("concurrent pending accounts cannot bypass account limit", SecurityRegressionTest::concurrentAccounts);
        run("concurrent joins cannot bypass online limit", SecurityRegressionTest::concurrentOnline);
        run("duplicate UUID cannot overwrite a session", SecurityRegressionTest::duplicateSession);
        run("pending reservations expire", SecurityRegressionTest::reservationExpiry);
        run("join rate limit resets after rolling minute", SecurityRegressionTest::rateLimit);
        run("attacker IP buckets are bounded", SecurityRegressionTest::boundedRateBuckets);
        run("configuration reload is transactional", SecurityRegressionTest::transactionalReload);
        run("invalid blacklist prevents configuration reload", SecurityRegressionTest::blacklistTransaction);
        run("corrupt persisted history fails closed", SecurityRegressionTest::corruptState);
        run("state replacement preserves coherent latest history", SecurityRegressionTest::saveConcurrency);
        run("fresh nonce and replay rejection", SecurityRegressionTest::nonceReplay);
        run("mismatched nonce consumes challenge", SecurityRegressionTest::nonceMismatch);
        run("reissued challenge invalidates old nonce", SecurityRegressionTest::nonceReplacement);
        run("required report timeout kicks exactly once", SecurityRegressionTest::requiredTimeout);
        run("optional report timeout does not kick", SecurityRegressionTest::optionalTimeout);
        run("retry cannot extend report deadline", SecurityRegressionTest::challengeDeadline);
        run("malformed oversized incomplete and trailing reports rejected", SecurityRegressionTest::wireBounds);
        run("wire rejects invalid UTF-8 and protocol versions", SecurityRegressionTest::wireEncoding);
        run("client report owns immutable copied lists", SecurityRegressionTest::defensiveCopies);
        run("blacklist uses exact normalized identifiers", SecurityRegressionTest::exactBlacklist);
        run("automation default only alerts", SecurityRegressionTest::automationAlert);
        run("VM DENY requires companion", SecurityRegressionTest::vmRequiresCompanion);
        run("VM evidence and unknown are distinguished", SecurityRegressionTest::vmEvidence);
        run("global blacklist OFF and ALERT are honored", SecurityRegressionTest::blacklistActions);
        run("managed glob rules and matching whitelist", SecurityRegressionTest::managedRules);
        run("rule mutations persist and invalid changes are transactional", SecurityRegressionTest::managedPersistence);
        run("legacy blacklist rules support list and removal", SecurityRegressionTest::legacyRuleRemoval);
        run("account and device bans propagate and survive restart", SecurityRegressionTest::linkedBans);
        run("whitelist never bypasses a persistent ban", SecurityRegressionTest::whiteCannotBypassBan);
        run("account and device unban are independent", SecurityRegressionTest::independentUnban);
        run("KICK sanctions never persist a blacklist ban", SecurityRegressionTest::kickOnly);
        run("missing devices and invalid reports do not permanently ban", SecurityRegressionTest::missingDevice);
        run("same IP and device allows one concurrent account", SecurityRegressionTest::sameIpDevice);
        run("same IP different devices allow three accounts", SecurityRegressionTest::differentDevices);
        run("different IP same device is allowed until banned", SecurityRegressionTest::differentIps);
        run("concurrent device reports cannot bypass the device limit", SecurityRegressionTest::concurrentDevice);
        run("IP and device limit respects configuration two", SecurityRegressionTest::twoPerDevice);
        run("brand sanctions bind known device only", SecurityRegressionTest::brandSanctions);
        run("device protocol round trip and legacy rejection", SecurityRegressionTest::deviceWire);
        run("online associated bans are discoverable without losing sessions", SecurityRegressionTest::onlineBans);
        run("rechallenge applies new player rules", SecurityRegressionTest::playerRuleRefresh);
        run("admin bans and background saves do not deadlock", SecurityRegressionTest::banSaveConcurrency);
        run("online IP policy reload does not rewrite account history", SecurityRegressionTest::onlineIpReload);
        run("server scope persists across restarts and differs across instances", SecurityRegressionTest::stableScope);
        run("corrupt server scope is rejected rather than regenerated", SecurityRegressionTest::corruptScope);
        run("pathological managed rules have a report-wide budget", SecurityRegressionTest::ruleBudget);
        run("in-flight old report cannot consume or satisfy the new challenge", SecurityRegressionTest::staleReport);
        run("only two previous-nonce reports are tolerated", SecurityRegressionTest::staleReportLimit);
        System.out.println("PASS: " + passed + " security regression tests");
    }
    private static void run(String name, Check check) throws Exception {
        check.run(); passed++; System.out.println("PASS " + passed + ": " + name);
    }
    private static Path fresh() throws IOException { return Files.createTempDirectory(testRoot, "case-"); }
    private static GuardService guard(Path directory, String... pairs) throws IOException {
        GuardService guard = new GuardService(directory); configure(directory, pairs); guard.reload(); return guard;
    }
    private static void configure(Path directory, String... pairs) throws IOException {
        String text = GuardConfig.DEFAULTS;
        for (int i = 0; i < pairs.length; i += 2) {
            String prefix = pairs[i] + "=";
            StringBuilder edited = new StringBuilder();
            for (String line : text.split("\n")) edited.append(line.startsWith(prefix) ? prefix + pairs[i + 1] : line).append('\n');
            text = edited.toString();
        }
        Files.write(directory.resolve("guard.properties"), text.getBytes(StandardCharsets.UTF_8));
    }
    private static void require(boolean value, String reason) { if (!value) throw new AssertionError(reason); }
    private static void code(Decision value, String expected) { require(value.code().equals(expected), "Expected " + expected + ", got " + value); }
    private static UUID join(GuardService service, String ip, long time) {
        UUID id = UUID.randomUUID(); require(service.openSession(id, ip, time).allowed(), "Open failed"); service.confirmSession(id, time); return id;
    }
    private static ClientReport report(String... mods) { return deviceReport(DEVICE_A, mods); }
    private static ClientReport deviceReport(String device, String... mods) { return new ClientReport(Arrays.asList(mods), Collections.<String>emptyList(), Collections.<String>emptyList(), true, device); }
    private static Decision send(GuardService service, UUID id, ClientReport report) throws IOException {
        String nonce = Wire.decodeChallenge(service.challenge(id, NOW)); return service.acceptReport(id, Wire.encodeReport(nonce, report), NOW + 1);
    }
    private static void expectFailure(Check operation) throws Exception {
        boolean failed = false;
        try { operation.run(); } catch (IOException | IllegalArgumentException | IllegalStateException expected) { failed = true; }
        require(failed, "Expected validation failure");
    }
    private static void literalValidation() throws Exception {
        String[] bad = {"localhost", "example.com", "127.1", "0177.0.0.1", "0x7f000001", "2130706433", " 127.0.0.1", "[::1]", "fe80::1%2", "1::2::3", "1:2:3:4:5:6:7", "1:2:3:4:5:6:7:8:9", "1.2.3.256", "1.2.3.-1", "::ffff:192.168.001.1"};
        GuardService guard = new GuardService(fresh());
        for (String value : bad) code(guard.openSession(UUID.randomUUID(), value, NOW), "INVALID_IP");
        for (String good : Arrays.asList("::", "::1", "2001:db8::1", "1:2:3:4:5:6:7:8", "::ffff:192.0.2.1", "2001:db8::192.0.2.1")) IpAddress.parse(good);
    }
    private static void mappedIdentity() throws Exception {
        GuardService guard = guard(fresh(), "limits.max-online-per-ip", "1"); join(guard, "192.0.2.8", NOW);
        code(guard.openSession(UUID.randomUUID(), "::ffff:c000:208", NOW), "IP_ONLINE_LIMIT");
        code(guard.openSession(UUID.randomUUID(), "::ffff:192.0.2.8", NOW), "IP_ONLINE_LIMIT");
    }
    private static void ipv6Identity() throws Exception {
        GuardService guard = guard(fresh(), "limits.max-online-per-ip", "1"); join(guard, "2001:db8::a", NOW);
        code(guard.openSession(UUID.randomUUID(), "2001:0DB8:0:0:0:0:0:000A", NOW), "IP_ONLINE_LIMIT");
    }
    private static void cidrPolicy() throws Exception {
        GuardService guard = guard(fresh(), "ip.allow", "192.0.2.0/24,2001:db8::/32", "ip.deny", "192.0.2.128/25,2001:db8:bad::/48");
        require(guard.openSession(UUID.randomUUID(), "192.0.2.127", NOW).allowed(), "IPv4 allow failed");
        code(guard.openSession(UUID.randomUUID(), "192.0.2.128", NOW), "IP_DENIED");
        code(guard.openSession(UUID.randomUUID(), "198.51.100.1", NOW), "IP_NOT_ALLOWED");
        require(guard.openSession(UUID.randomUUID(), "2001:db8:ace::1", NOW).allowed(), "IPv6 allow failed");
        code(guard.openSession(UUID.randomUUID(), "2001:db8:bad::1", NOW), "IP_DENIED");
    }
    private static void mappedCidr() throws Exception {
        GuardService guard = guard(fresh(), "ip.deny", "::ffff:192.0.2.0/120");
        code(guard.openSession(UUID.randomUUID(), "192.0.2.255", NOW), "IP_DENIED");
        expectFailure(() -> Cidr.parse("::ffff:192.0.2.0/95"));
    }
    private static void unconfirmedNotPersisted() throws Exception {
        Path directory = fresh(); GuardService guard = guard(directory, "limits.max-accounts-per-ip", "1");
        UUID failed = UUID.randomUUID(); require(guard.openSession(failed, "192.0.2.1", NOW).allowed(), "Reservation failed"); guard.closeSession(failed);
        require(!guard.isDirty(), "Reservation modified persistence"); guard.save();
        guard = new GuardService(directory); UUID good = join(guard, "192.0.2.1", NOW); guard.closeSession(good);
        code(guard.openSession(failed, "192.0.2.1", NOW), "IP_ACCOUNT_LIMIT");
    }
    private static void rollingHistory() throws Exception {
        Path directory = fresh(); GuardService guard = guard(directory, "limits.max-accounts-per-ip", "1", "limits.account-window-hours", "1");
        UUID id = join(guard, "192.0.2.1", NOW); guard.closeSession(id); guard.save(); require(!guard.isDirty(), "Save remained dirty");
        guard = new GuardService(directory); code(guard.openSession(UUID.randomUUID(), "192.0.2.1", NOW + 3599999), "IP_ACCOUNT_LIMIT");
        require(guard.openSession(UUID.randomUUID(), "192.0.2.1", NOW + 3600000).allowed(), "History did not expire");
    }
    private static void concurrentAccounts() throws Exception { concurrentLimit(2, 100, 2); }
    private static void concurrentOnline() throws Exception { concurrentLimit(100, 3, 3); }
    private static void concurrentLimit(int accounts, int online, int expected) throws Exception {
        final GuardService guard = guard(fresh(), "limits.max-accounts-per-ip", "" + accounts, "limits.max-online-per-ip", "" + online, "limits.attempts-per-minute", "1000");
        ExecutorService pool = Executors.newFixedThreadPool(16); CountDownLatch start = new CountDownLatch(1); AtomicInteger accepted = new AtomicInteger();
        List<Future<?>> tasks = new ArrayList<Future<?>>();
        try {
            for (int i = 0; i < 64; i++) tasks.add(pool.submit(() -> { try { start.await(); if (guard.openSession(UUID.randomUUID(), "192.0.2.2", NOW).allowed()) accepted.incrementAndGet(); } catch (InterruptedException ex) { Thread.currentThread().interrupt(); throw new RuntimeException(ex); } }));
            start.countDown(); for (Future<?> task : tasks) task.get(); require(accepted.get() == expected, "Concurrent limit bypass: " + accepted.get());
        } finally { pool.shutdownNow(); }
    }
    private static void duplicateSession() throws Exception {
        GuardService guard = guard(fresh(), "limits.max-online-per-ip", "1"); UUID id = join(guard, "192.0.2.1", NOW);
        code(guard.openSession(id, "192.0.2.2", NOW), "DUPLICATE_SESSION"); code(guard.openSession(UUID.randomUUID(), "192.0.2.1", NOW), "IP_ONLINE_LIMIT");
    }
    private static void reservationExpiry() throws Exception {
        GuardService guard = guard(fresh(), "limits.max-accounts-per-ip", "1"); UUID id = UUID.randomUUID(); guard.openSession(id, "192.0.2.1", NOW);
        require(guard.openSession(id, "192.0.2.1", NOW + 30000).allowed(), "Expired duplicate reservation remains"); guard.closeSession(id);
        guard.openSession(id, "192.0.2.1", NOW); expectFailure(() -> guard.confirmSession(id, NOW + 30000));
        require(!guard.isDirty(), "Expired confirmation persisted history");
    }
    private static void rateLimit() throws Exception {
        GuardService guard = guard(fresh(), "limits.attempts-per-minute", "2");
        for (int i = 0; i < 2; i++) { UUID id = UUID.randomUUID(); require(guard.openSession(id, "192.0.2.1", NOW).allowed(), "Attempt too early blocked"); guard.closeSession(id); }
        code(guard.openSession(UUID.randomUUID(), "192.0.2.1", NOW + 59999), "RATE_LIMIT");
        require(guard.openSession(UUID.randomUUID(), "192.0.2.1", NOW + 60000).allowed(), "Rate window did not reset");
    }
    private static void boundedRateBuckets() throws Exception {
        GuardService guard = new GuardService(fresh());
        for (int i = 0; i < 5000; i++) { UUID id = UUID.randomUUID(); guard.openSession(id, "10.0." + (i / 256) + "." + (i % 256), NOW); guard.closeSession(id); }
        require(guard.status().contains("rateBuckets=4096"), "Rate bucket memory is not bounded");
        require(guard.status().contains("accountPairs=0"), "Unauthenticated attempts consumed history");
    }
    private static void transactionalReload() throws Exception {
        Path directory = fresh(); GuardService guard = guard(directory, "ip.deny", "192.0.2.0/24");
        configure(directory, "ip.deny", "", "limits.max-online-per-ip", "0"); expectFailure(guard::reload);
        code(guard.openSession(UUID.randomUUID(), "192.0.2.1", NOW), "IP_DENIED");
        configure(directory, "companion.required", "maybe"); expectFailure(guard::reload);
    }
    private static void blacklistTransaction() throws Exception {
        Path directory = fresh(); GuardService guard = guard(directory, "ip.deny", "192.0.2.0/24"); configure(directory, "ip.deny", "");
        Files.write(directory.resolve("blacklist.tsv"), "mod\t*\tDENY\thttps://example.com\n".getBytes(StandardCharsets.UTF_8)); expectFailure(guard::reload);
        code(guard.openSession(UUID.randomUUID(), "192.0.2.1", NOW), "IP_DENIED");
    }
    private static void corruptState() throws Exception {
        Path directory = fresh(); new GuardService(directory);
        for (String broken : Arrays.asList("garbage\n", "QZG-STATE\t1\nnot-a-record\n", "QZG-STATE\t1\nexample.com\t" + UUID.randomUUID() + "\t1\n")) {
            Files.write(directory.resolve("accounts.state"), broken.getBytes(StandardCharsets.UTF_8)); expectFailure(() -> new GuardService(directory));
            require(new String(Files.readAllBytes(directory.resolve("accounts.state")), StandardCharsets.UTF_8).equals(broken), "Corrupt state was overwritten");
        }
    }
    private static void saveConcurrency() throws Exception {
        Path directory = fresh(); GuardService guard = new GuardService(directory); ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            Future<?> writer = pool.submit(() -> { try { for (int i = 0; i < 20; i++) guard.save(); } catch (IOException ex) { throw new RuntimeException(ex); } });
            for (int i = 0; i < 100; i++) { UUID id = join(guard, "10.1.0." + i, NOW); guard.closeSession(id); }
            writer.get(); guard.save(); GuardService restored = new GuardService(directory);
            require(restored.status().contains("accountPairs=100"), "Concurrent save lost history"); require(!guard.isDirty(), "Last save remained dirty");
            try (java.util.stream.Stream<Path> files = Files.list(directory)) { require(files.noneMatch(p -> p.getFileName().toString().endsWith(".tmp")), "Temporary state file leaked"); }
        } finally { pool.shutdownNow(); }
    }
    private static void nonceReplay() throws Exception {
        GuardService guard = new GuardService(fresh()); UUID id = join(guard, "192.0.2.1", NOW); String nonce = Wire.decodeChallenge(guard.challenge(id, NOW));
        byte[] payload = Wire.encodeReport(nonce, report("fabricloader")); require(guard.acceptReport(id, payload, NOW + 1).allowed(), "Clean report rejected");
        code(guard.acceptReport(id, payload, NOW + 2), "NO_CHALLENGE");
    }
    private static void nonceMismatch() throws Exception {
        GuardService guard = new GuardService(fresh()); UUID id = join(guard, "192.0.2.1", NOW); String actual = Wire.decodeChallenge(guard.challenge(id, NOW));
        String fake = (actual.charAt(0) == '0' ? "1" : "0") + actual.substring(1);
        code(guard.acceptReport(id, Wire.encodeReport(fake, report()), NOW), "NONCE_MISMATCH");
        code(guard.acceptReport(id, Wire.encodeReport(actual, report()), NOW), "NO_CHALLENGE");
    }
    private static void nonceReplacement() throws Exception {
        GuardService guard = new GuardService(fresh()); UUID id = join(guard, "192.0.2.1", NOW);
        String old = Wire.decodeChallenge(guard.challenge(id, NOW)), fresh = Wire.decodeChallenge(guard.challenge(id, NOW)); require(!old.equals(fresh), "Nonce reused");
        code(guard.acceptReport(id, Wire.encodeReport(old, report()), NOW), "STALE_REPORT");
    }
    private static void requiredTimeout() throws Exception {
        GuardService guard = guard(fresh(), "companion.required", "true", "companion.timeout-seconds", "1"); UUID id = join(guard, "192.0.2.1", NOW);
        require(guard.expiredReports(NOW + 999).isEmpty(), "Premature timeout"); require(guard.expiredReports(NOW + 1000).equals(Collections.singletonList(id)), "Required timeout missing");
        require(guard.expiredReports(NOW + 1001).isEmpty(), "Timeout emitted twice");
    }
    private static void optionalTimeout() throws Exception {
        GuardService guard = guard(fresh(), "companion.timeout-seconds", "1", "companion.required", "false", "device.required", "false", "vm.action", "OFF"); UUID id = join(guard, "192.0.2.1", NOW); guard.challenge(id, NOW);
        require(guard.expiredReports(NOW + 1000).isEmpty(), "Optional client kicked"); require(guard.status().contains("sessions=1"), "Optional session removed");
    }
    private static void challengeDeadline() throws Exception {
        GuardService guard = guard(fresh(), "companion.required", "true", "companion.timeout-seconds", "1"); UUID id = join(guard, "192.0.2.1", NOW);
        guard.challenge(id, NOW); String nonce = Wire.decodeChallenge(guard.challenge(id, NOW + 999));
        code(guard.acceptReport(id, Wire.encodeReport(nonce, report()), NOW + 1000), "REPORT_EXPIRED");
    }
    private static void wireBounds() throws Exception {
        GuardService guard = new GuardService(fresh()); UUID id = join(guard, "192.0.2.1", NOW);
        String nonce = Wire.decodeChallenge(guard.challenge(id, NOW)); byte[] good = Wire.encodeReport(nonce, report());
        expectFailure(() -> Wire.decodeReport(Arrays.copyOf(good, good.length + 1)));
        expectFailure(() -> Wire.decodeReport(new byte[30001]));
        code(guard.acceptReport(id, new byte[30001], NOW), "MALFORMED_REPORT");
        nonce = Wire.decodeChallenge(guard.challenge(id, NOW));
        code(guard.acceptReport(id, Wire.encodeReport(nonce, new ClientReport(Collections.<String>emptyList(), Collections.<String>emptyList(), Collections.<String>emptyList(), false)), NOW), "REPORT_INCOMPLETE");
        final String nonceAgain = Wire.decodeChallenge(guard.challenge(id, NOW));
        expectFailure(() -> Wire.encodeReport(nonceAgain, new ClientReport(Collections.nCopies(1025, "a"), Collections.<String>emptyList(), Collections.<String>emptyList(), true)));
        expectFailure(() -> Wire.encodeReport(nonceAgain, report("bad\nmod")));
    }
    private static void wireEncoding() throws Exception {
        String nonce = String.join("", Collections.nCopies(64, "a")); byte[] payload = Wire.encodeReport(nonce, report("ab"));
        byte[] badVersion = payload.clone(); badVersion[4] = 1; expectFailure(() -> Wire.decodeReport(badVersion));
        byte[] badUtf8 = payload.clone(); badUtf8[77] = (byte) 0xc0; badUtf8[78] = (byte) 0xaf; expectFailure(() -> Wire.decodeReport(badUtf8));
        byte[] badCount = payload.clone(); badCount[73] = 0x7f; badCount[74] = (byte) 0xff; expectFailure(() -> Wire.decodeReport(badCount));
        expectFailure(() -> Wire.encodeReport(nonce, report("\ud800")));
    }
    private static void defensiveCopies() throws Exception {
        List<String> items = new ArrayList<String>(); items.add("fabricloader"); ClientReport report = new ClientReport(items, items, items, true); items.add("meteor-client");
        require(report.modIds().size() == 1, "Input mutation leaked into report"); boolean failed = false;
        try { report.modIds().add("bad"); } catch (UnsupportedOperationException expected) { failed = true; } require(failed, "Report list is mutable");
    }
    private static void exactBlacklist() throws Exception {
        GuardService guard = guard(fresh(), "sanctions.on-deny", "KICK"); UUID id = join(guard, "192.0.2.1", NOW);
        code(send(guard, id, report("Meteor-Client")), "BLACKLIST_DENIED");
        code(send(guard, id, report("xray")), "BLACKLIST_DENIED");
        require(send(guard, id, report("antixray", "meteor-client-helper", "fabricloader", "schematica", "lunatriuscore")).allowed(), "Substring or bundled metadata caused false positive");
        Path directory = fresh(); GuardService brand = new GuardService(directory);
        Files.write(directory.resolve("blacklist.tsv"), "brand\twurst\tDENY\thttps://github.com/Wurst-Imperium/Wurst7\n".getBytes(StandardCharsets.UTF_8), StandardOpenOption.APPEND); brand.reload();
        code(brand.checkBrand(" WURST "), "BLACKLIST_DENIED"); require(brand.checkBrand("wurst-helper").allowed(), "Brand substring matched");
    }
    private static void automationAlert() throws Exception {
        GuardService guard = new GuardService(fresh()); UUID id = join(guard, "192.0.2.1", NOW); Decision result = send(guard, id, report("baritone"));
        require(result.allowed(), "Automation banned by default"); code(result, "AUTOMATION_ALERT");
    }
    private static void vmRequiresCompanion() throws Exception { Path directory = fresh(); GuardService guard = new GuardService(directory); configure(directory, "vm.action", "DENY", "companion.required", "false", "device.required", "false"); expectFailure(guard::reload); }
    private static void vmEvidence() throws Exception {
        GuardService guard = guard(fresh(), "companion.required", "true", "vm.action", "DENY"); UUID id = join(guard, "192.0.2.1", NOW);
        code(send(guard, id, new ClientReport(Collections.<String>emptyList(), Collections.<String>emptyList(), Arrays.asList("hypervisor-present", "unknown"), true, DEVICE_A)), "VM_UNKNOWN");
        code(send(guard, id, new ClientReport(Collections.<String>emptyList(), Collections.<String>emptyList(), Collections.singletonList("vmware"), true, DEVICE_A)), "VM_DENIED");
    }
    private static void blacklistActions() throws Exception {
        for (String action : Arrays.asList("OFF", "ALERT")) {
            GuardService guard = guard(fresh(), "blacklist.action", action); UUID id = join(guard, "192.0.2.1", NOW);
            Decision result = send(guard, id, report("meteor-client")); require(result.allowed(), "Global action ignored"); code(result, action.equals("OFF") ? "OK" : "BLACKLIST_ALERT");
        }
    }
    private static void managedRules() throws Exception {
        GuardService guard = guard(fresh(), "sanctions.on-deny", "KICK"); guard.addRule("BLACK", "MOD", "GLOB", "*xray*");
        guard.addRule("WHITE", "MOD", "EXACT", "antixray"); UUID id = join(guard, "192.0.2.1", NOW);
        code(send(guard, id, report("some-xray-mod")), "BLACKLIST_DENIED"); require(send(guard, id, report("antixray")).allowed(), "Matching white rule ignored");
        code(send(guard, id, report("antixray", "meteor-client")), "BLACKLIST_DENIED");
        require(RuleRegistry.glob("a?c*", "abc123") && !RuleRegistry.glob("a?c", "ac"), "Wildcard semantics incorrect");
        require(!RuleRegistry.glob(String.join("", Collections.nCopies(100, "*a")), String.join("", Collections.nCopies(100, "a")) + "b"), "Bounded worst-case matcher failed");
    }
    private static void managedPersistence() throws Exception {
        Path directory = fresh(); GuardService guard = new GuardService(directory); String id = guard.addRule("BLACK", "BRAND", "GLOB", "cheat-*");
        guard.reload(); require(guard.listRules().stream().anyMatch(line -> line.startsWith(id + "\t")), "Reload lost added rule");
        GuardService restored = new GuardService(directory); code(restored.checkBrand("cheat-test"), "BLACKLIST_DENIED");
        int count = restored.listRules().size(); expectFailure(() -> restored.addRule("BLACK", "DEVICE", "EXACT", "bad")); require(restored.listRules().size() == count, "Invalid rule mutated memory");
        require(restored.removeRule(id), "Rule removal failed"); restored.reload(); require(restored.checkBrand("cheat-test").allowed(), "Removed rule remains");
        restored.addRule("BLACK", "BRAND", "EXACT", "blocked");
        Files.write(directory.resolve("rules.tsv"), "invalid\n".getBytes(StandardCharsets.UTF_8)); expectFailure(restored::reload); code(restored.checkBrand("blocked"), "BLACKLIST_DENIED");
    }
    private static void legacyRuleRemoval() throws Exception {
        GuardService guard = new GuardService(fresh()); require(guard.listRules().stream().anyMatch(line -> line.startsWith("legacy:mod:meteor-client\t")), "Legacy rule omitted");
        require(guard.removeRule("legacy:mod:meteor-client"), "Cannot remove legacy entry"); guard.reload(); UUID id = join(guard, "192.0.2.1", NOW);
        require(send(guard, id, report("meteor-client")).allowed(), "Removed default still matched");
    }
    private static void linkedBans() throws Exception {
        Path directory = fresh(); GuardService guard = new GuardService(directory); UUID first = join(guard, "192.0.2.1", NOW); require(send(guard, first, report()).allowed(), "First device association failed"); guard.closeSession(first);
        UUID second = join(guard, "192.0.2.1", NOW); code(send(guard, second, report("meteor-client")), "BLACKLIST_DENIED"); guard.closeSession(second);
        code(guard.openSession(first, "198.51.100.1", NOW), "ACCOUNT_BANNED"); guard.save(); GuardService restored = new GuardService(directory);
        code(restored.openSession(second, "198.51.100.1", NOW), "ACCOUNT_BANNED");
        UUID third = join(restored, "203.0.113.1", NOW); code(send(restored, third, report()), "DEVICE_BANNED"); restored.closeSession(third);
        code(restored.openSession(third, "203.0.113.2", NOW), "ACCOUNT_BANNED");
        require(restored.listBans().size() == 4, "Linked accounts/device not all banned");
    }
    private static void whiteCannotBypassBan() throws Exception {
        GuardService guard = new GuardService(fresh()); UUID id = join(guard, "192.0.2.1", NOW); send(guard, id, report()); guard.ban(id, "test"); guard.closeSession(id);
        guard.addRule("WHITE", "PLAYER", "EXACT", id.toString()); guard.addRule("WHITE", "DEVICE", "EXACT", DEVICE_A);
        code(guard.openSession(id, "192.0.2.1", NOW), "ACCOUNT_BANNED"); UUID other = join(guard, "192.0.2.2", NOW); code(send(guard, other, report()), "DEVICE_BANNED");
    }
    private static void independentUnban() throws Exception {
        GuardService guard = new GuardService(fresh()); UUID id = join(guard, "192.0.2.1", NOW); send(guard, id, report()); guard.ban(id, "test"); guard.closeSession(id);
        require(guard.unban(id.toString()), "Account unban failed"); require(guard.listBans().size() == 1, "Account unban also removed device");
        require(guard.unban("device:" + DEVICE_A), "Device unban failed"); require(guard.listBans().isEmpty(), "Unban left records"); require(guard.openSession(id, "192.0.2.1", NOW).allowed(), "Unbanned account denied");
    }
    private static void kickOnly() throws Exception {
        GuardService guard = guard(fresh(), "sanctions.on-deny", "KICK"); UUID id = join(guard, "192.0.2.1", NOW); code(send(guard, id, report("meteor-client")), "BLACKLIST_DENIED");
        require(guard.listBans().isEmpty(), "KICK created bans"); guard.closeSession(id); require(guard.openSession(id, "192.0.2.1", NOW).allowed(), "Kicked account permanently banned");
    }
    private static void missingDevice() throws Exception {
        GuardService guard = new GuardService(fresh()); UUID id = join(guard, "192.0.2.1", NOW); code(send(guard, id, deviceReport("")), "DEVICE_REQUIRED");
        guard.challenge(id, NOW); code(guard.acceptReport(id, new byte[]{1}, NOW), "MALFORMED_REPORT"); require(guard.listBans().isEmpty(), "Missing or malformed report permanently banned");
    }
    private static void sameIpDevice() throws Exception {
        GuardService guard = new GuardService(fresh()); UUID first = join(guard, "192.0.2.1", NOW); require(send(guard, first, report()).allowed(), "First rejected");
        UUID second = join(guard, "192.0.2.1", NOW); code(send(guard, second, report()), "IP_DEVICE_ONLINE_LIMIT"); require(guard.listBans().isEmpty(), "Quota caused permanent ban");
        guard.challenge(first, NOW); code(send(guard, second, report()), "IP_DEVICE_ONLINE_LIMIT"); guard.closeSession(first);
        require(send(guard, second, report()).allowed(), "Disconnect did not release device slot");
    }
    private static void differentDevices() throws Exception {
        GuardService guard = new GuardService(fresh());
        for (String device : Arrays.asList(DEVICE_A, DEVICE_B, DEVICE_C)) { UUID id = join(guard, "192.0.2.1", NOW); require(send(guard, id, deviceReport(device)).allowed(), "Different device denied"); }
        code(guard.openSession(UUID.randomUUID(), "192.0.2.1", NOW), "IP_ONLINE_LIMIT"); require(guard.listBans().isEmpty(), "IP quota caused ban");
    }
    private static void differentIps() throws Exception {
        GuardService guard = new GuardService(fresh()); UUID first = join(guard, "192.0.2.1", NOW), second = join(guard, "192.0.2.2", NOW);
        require(send(guard, first, report()).allowed() && send(guard, second, report()).allowed(), "Device quota incorrectly spans different IPs"); guard.ban(first, "test");
        code(send(guard, second, report()), "ACCOUNT_BANNED");
    }
    private static void concurrentDevice() throws Exception {
        GuardService guard = new GuardService(fresh()); UUID first = join(guard, "192.0.2.1", NOW), second = join(guard, "192.0.2.1", NOW);
        String a = Wire.decodeChallenge(guard.challenge(first, NOW)), b = Wire.decodeChallenge(guard.challenge(second, NOW)); ExecutorService pool = Executors.newFixedThreadPool(2);
        CountDownLatch start = new CountDownLatch(1);
        try {
            Future<Decision> one = pool.submit(() -> { start.await(); return guard.acceptReport(first, Wire.encodeReport(a, report()), NOW); });
            Future<Decision> two = pool.submit(() -> { start.await(); return guard.acceptReport(second, Wire.encodeReport(b, report()), NOW); }); start.countDown();
            require(one.get().allowed() != two.get().allowed(), "Concurrent reports both accepted or both denied");
        } finally { pool.shutdownNow(); }
    }
    private static void twoPerDevice() throws Exception {
        GuardService guard = guard(fresh(), "limits.max-online-per-ip-device", "2");
        for (int i = 0; i < 2; i++) require(send(guard, join(guard, "192.0.2.1", NOW), report()).allowed(), "Configured second account rejected");
        code(send(guard, join(guard, "192.0.2.1", NOW), report()), "IP_DEVICE_ONLINE_LIMIT");
    }
    private static void brandSanctions() throws Exception {
        GuardService guard = new GuardService(fresh()); guard.addRule("BLACK", "BRAND", "EXACT", "cheat"); UUID id = join(guard, "192.0.2.1", NOW); send(guard, id, report());
        code(guard.checkBrand(id, "cheat"), "BLACKLIST_DENIED"); require(guard.listBans().size() == 2, "Known brand device not linked");
        GuardService unknown = new GuardService(fresh()); unknown.addRule("BLACK", "BRAND", "EXACT", "cheat"); UUID fresh = join(unknown, "192.0.2.1", NOW);
        code(unknown.checkBrand(fresh, "cheat"), "BLACKLIST_DENIED"); require(unknown.listBans().size() == 1, "Unknown device was fabricated");
    }
    private static void deviceWire() throws Exception {
        String nonce = DEVICE_A; byte[] payload = Wire.encodeReport(nonce, deviceReport(DEVICE_B)); require(Wire.decodeReport(payload).report().deviceId().equals(DEVICE_B), "Device digest lost");
        expectFailure(() -> deviceReport("raw-machine-guid")); payload[4] = 1; expectFailure(() -> Wire.decodeReport(payload));
    }
    private static void onlineBans() throws Exception {
        GuardService guard = new GuardService(fresh()); UUID first = join(guard, "192.0.2.1", NOW), second = join(guard, "192.0.2.2", NOW);
        send(guard, first, report()); send(guard, second, report()); code(send(guard, first, report("meteor-client")), "BLACKLIST_DENIED");
        require(guard.bannedSessions().containsAll(Arrays.asList(first, second)), "Associated online account absent");
        require(guard.bannedSessions().size() == 2 && guard.status().contains("sessions=2"), "Ban query consumed sessions");
        guard.closeSession(second); require(!guard.bannedSessions().contains(second), "Closed banned session remained");
    }
    private static void playerRuleRefresh() throws Exception {
        GuardService guard = new GuardService(fresh()); UUID id = join(guard, "192.0.2.1", NOW); send(guard, id, report());
        guard.addRule("BLACK", "PLAYER", "EXACT", id.toString()); code(send(guard, id, report()), "BLACKLIST_DENIED");
    }
    private static void banSaveConcurrency() throws Exception {
        GuardService guard = new GuardService(fresh()); UUID id = join(guard, "192.0.2.1", NOW); send(guard, id, report());
        ExecutorService pool = Executors.newFixedThreadPool(2); CountDownLatch start = new CountDownLatch(1);
        try {
            Future<?> saver = pool.submit(() -> { try { start.await(); for (int i = 0; i < 30; i++) guard.save(); } catch (Exception ex) { throw new RuntimeException(ex); } });
            Future<?> admin = pool.submit(() -> { try { start.await(); for (int i = 0; i < 15; i++) { guard.ban(id, "test" + i); guard.unban(id.toString()); } } catch (Exception ex) { throw new RuntimeException(ex); } });
            start.countDown(); saver.get(20, java.util.concurrent.TimeUnit.SECONDS); admin.get(20, java.util.concurrent.TimeUnit.SECONDS);
        } finally { pool.shutdownNow(); }
    }
    private static void onlineIpReload() throws Exception {
        Path directory = fresh(); GuardService guard = new GuardService(directory); UUID id = join(guard, "192.0.2.1", NOW); send(guard, id, report()); guard.save();
        configure(directory, "ip.deny", "192.0.2.0/24"); guard.reload(); code(guard.recheckSession(id, NOW + 10), "IP_DENIED");
        require(!guard.isDirty(), "Online IP check rewrote history"); require(guard.listBans().isEmpty(), "IP deny permanently banned account");
    }
    private static void stableScope() throws Exception {
        Path directory = fresh(); GuardService guard = new GuardService(directory); UUID id = join(guard, "192.0.2.1", NOW);
        byte[] one = guard.challenge(id, NOW), two = guard.challenge(id, NOW + 1);
        String scope = Wire.decodeServerScope(one); require(scope.equals(Wire.decodeServerScope(two)), "Nonce rotation changed server scope");
        require(!Wire.decodeChallenge(one).equals(Wire.decodeChallenge(two)), "Nonce did not rotate");
        GuardService restored = new GuardService(directory); require(scope.equals(Wire.decodeServerScope(restored.challenge(join(restored, "192.0.2.1", NOW), NOW))), "Restart changed server scope");
        GuardService other = new GuardService(fresh()); require(!scope.equals(Wire.decodeServerScope(other.challenge(join(other, "192.0.2.1", NOW), NOW))), "Separate instances share device scope");
        require(Wire.decodeServerScope(Wire.encodeChallenge(DEVICE_A)).equals(String.join("", Collections.nCopies(64, "0"))), "Compatibility challenge default scope changed");
    }
    private static void corruptScope() throws Exception {
        Path directory = fresh(); new GuardService(directory); Files.write(directory.resolve("server-id.txt"), "bad\n".getBytes(StandardCharsets.US_ASCII));
        expectFailure(() -> new GuardService(directory)); require(new String(Files.readAllBytes(directory.resolve("server-id.txt")), StandardCharsets.US_ASCII).equals("bad\n"), "Bad server identity was overwritten");
    }
    private static void ruleBudget() throws Exception {
        Path directory = fresh(); GuardService guard = new GuardService(directory); StringBuilder rules = new StringBuilder(RuleRegistry.HEADER);
        String prefix = String.join("", Collections.nCopies(120, "a"));
        for (int i = 0; i < 100; i++) rules.append(UUID.randomUUID()).append("\tBLACK\tMOD\tGLOB\t*").append(prefix).append("z\n");
        Files.write(directory.resolve("rules.tsv"), rules.toString().getBytes(StandardCharsets.UTF_8)); guard.reload();
        UUID id = join(guard, "192.0.2.1", NOW); code(send(guard, id, report(prefix + "aaaa")), "RULE_EVALUATION_LIMIT"); require(guard.listBans().isEmpty(), "Policy complexity failure caused a permanent ban");
    }
    private static void staleReport() throws Exception {
        GuardService guard = guard(fresh(), "companion.timeout-seconds", "1"); UUID id = join(guard, "192.0.2.1", NOW);
        String old = Wire.decodeChallenge(guard.challenge(id, NOW)), current = Wire.decodeChallenge(guard.challenge(id, NOW + 10));
        Decision stale = guard.acceptReport(id, Wire.encodeReport(old, report("meteor-client")), NOW + 20);
        code(stale, "STALE_REPORT"); require(!stale.allowed() && guard.listBans().isEmpty(), "Stale report passed validation or caused a ban");
        require(guard.acceptReport(id, Wire.encodeReport(current, report()), NOW + 30).allowed(), "Old packet consumed current nonce");
        code(guard.acceptReport(id, Wire.encodeReport(old, report()), NOW + 40), "NO_CHALLENGE");
        GuardService timeout = guard(fresh(), "companion.timeout-seconds", "1"); UUID other = join(timeout, "192.0.2.1", NOW);
        String initial = Wire.decodeChallenge(timeout.challenge(other, NOW)); timeout.challenge(other, NOW + 900);
        code(timeout.acceptReport(other, Wire.encodeReport(initial, report()), NOW + 999), "STALE_REPORT");
        require(timeout.expiredReports(NOW + 1000).contains(other), "Old response extended deadline or satisfied challenge");
    }
    private static void staleReportLimit() throws Exception {
        GuardService guard = new GuardService(fresh()); UUID id = join(guard, "192.0.2.1", NOW);
        String old = Wire.decodeChallenge(guard.challenge(id, NOW)), current = Wire.decodeChallenge(guard.challenge(id, NOW));
        for (int i = 0; i < 2; i++) code(guard.acceptReport(id, Wire.encodeReport(old, report()), NOW), "STALE_REPORT");
        code(guard.acceptReport(id, Wire.encodeReport(old, report()), NOW), "NONCE_MISMATCH");
        code(guard.acceptReport(id, Wire.encodeReport(current, report()), NOW), "NO_CHALLENGE");
    }
}
