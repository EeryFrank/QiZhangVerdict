package cn.qizhang.guard.core;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/** Exercises the production parser, fresh defaults and preservation of existing administrator files. */
public final class CatalogCompatibilityTest {
    private static final long NOW = 1800000000000L;
    private static final String DEVICE = String.join("", Collections.nCopies(64, "a"));
    private static Path testRoot;

    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Expected catalog TSV path");
        Path input = Paths.get(args[0]);
        testRoot = Paths.get(System.getProperty("qzguard.testDir", "E:/CodexTemp/QiZhangVerdict/catalog-tests"));
        Files.createDirectories(testRoot);
        Blacklist loaded = Blacklist.read(input);
        Map<String, String> catalog = rows(input);
        Path freshDirectory = fresh();
        new GuardService(freshDirectory);
        Path generatedFile = freshDirectory.resolve("blacklist.tsv");
        require(catalog.equals(rows(generatedFile)), "Fresh defaults must preserve every catalog kind, ID, action and pinned source without extra entries");
        Blacklist generated = Blacklist.read(generatedFile);
        int count = 0, denies = 0, alerts = 0;
        for (String line : catalog.values()) {
            String[] fields = line.split("\t", -1);
            require(fields[3].matches("https://raw\\.githubusercontent\\.com/[^/]+/[^/]+/[0-9a-f]{40}/.+"), "Catalog source is not pinned to an exact commit: " + fields[1]);
            String kind = fields[0].equals("automation") ? "mod" : fields[0];
            for (Blacklist parser : new Blacklist[]{loaded, generated}) {
                Blacklist.Rule rule = parser.lookup(kind, fields[1]);
                require(rule != null && rule.kind.equals(fields[0]) && rule.action.name().equals(fields[2]),
                        "Production parser changed catalog kind or action: " + fields[1]);
            }
            require(kind.equals("mod"), "Report exercise requires an exact mod/automation catalog entry");
            GuardService guard = new GuardService(fresh());
            Decision result = report(guard, fields[1]);
            if (fields[2].equals("DENY")) {
                denies++;
                require(!result.allowed() && result.code().equals(fields[0].equals("automation") ? "AUTOMATION_DENIED" : "BLACKLIST_DENIED"),
                        "Fresh default failed to deny catalog identifier: " + fields[1]);
                require(guard.listBans().size() == 2, "Catalog DENY did not create account and device ban records: " + fields[1]);
            } else {
                require(fields[2].equals("ALERT"), "Unexpected default catalog action");
                alerts++;
                require(result.allowed() && result.code().equals(fields[0].equals("automation") ? "AUTOMATION_ALERT" : "BLACKLIST_ALERT"),
                        "Alert-only catalog identifier was denied or lost its alert: " + fields[1]);
                require(guard.listBans().isEmpty(), "Alert-only default created a permanent ban: " + fields[1]);
            }
            count++;
            System.out.println("PASS rule " + count + ": " + fields[0] + " " + fields[1] + " " + fields[2] + "; parser, fresh defaults, source and report");
        }
        require(count > 0 && count == loaded.size() && count == generated.size(), "Missing or duplicate catalog identities");
        require(count == 39 && denies == 35, "Reviewed development catalog must contain 39 identities, including 35 DENY rules");
        for (String alertOnly : new String[]{"baritone", "baritoe", "keystrokesmod", "atianxray"}) {
            Blacklist.Rule rule = loaded.lookup("mod", alertOnly);
            require(rule != null && rule.action == GuardConfig.Action.ALERT, "Ambiguous/automation identifier must remain ALERT: " + alertOnly);
        }
        require(alerts == 4, "The four reviewed alert-only exceptions must remain unchanged");
        ordinaryIdentifiers(loaded);
        preserveAdministratorChanges();
        preserveSparseExistingFile();
        System.out.println("PASS: production Blacklist parser and fresh GuardService enforce " + count + " exact catalog rules (" + denies + " DENY, " + alerts + " ALERT); 3 preservation and ordinary-ID controls passed");
    }

    private static void ordinaryIdentifiers(Blacklist loaded) throws Exception {
        String[] ordinary = {"bigrat", "template", "antixray", "sodium", "iris", "jei", "fabricloader", "meteor-client-helper",
                "eclient", "xulu", "coffee", "atomic", "ferox-helper", "wurstplusthree-helper"};
        for (String id : ordinary) require(loaded.lookup("mod", id) == null, "Ordinary or ambiguous identifier unexpectedly listed: " + id);
        GuardService guard = new GuardService(fresh());
        Decision result = report(guard, ordinary);
        require(result.allowed() && result.code().equals("OK") && guard.listBans().isEmpty(), "Ordinary identifiers must not cause a default denial or ban");
        System.out.println("PASS control 1: ordinary and ambiguous identifiers remain allowed without bans");
    }

    private static void preserveAdministratorChanges() throws Exception {
        Path directory = fresh(); GuardService guard = new GuardService(directory);
        Path path = directory.resolve("blacklist.tsv");
        String text = new String(Files.readAllBytes(path), StandardCharsets.UTF_8);
        String changed = text.replace("mod\tmeteor-client\tDENY\t", "mod\tmeteor-client\tOFF\t");
        changed = changed.replace("mod\tferox\tDENY\t", "mod\tferox\tOFF\t");
        require(!changed.equals(text), "Expected an editable default meteor-client rule");
        Files.write(path, changed.getBytes(StandardCharsets.UTF_8)); guard.reload();
        require(guard.removeRule("legacy:mod:xray"), "Administrator could not delete the default xray rule");
        require(guard.removeRule("legacy:mod:wurstplusthree"), "Administrator could not delete the new wurstplusthree rule");
        byte[] administratorBytes = Files.readAllBytes(path);
        guard.reload();
        require(Arrays.equals(administratorBytes, Files.readAllBytes(path)), "Reload rewrote administrator rules");
        GuardService restarted = new GuardService(directory); restarted.reload();
        require(Arrays.equals(administratorBytes, Files.readAllBytes(path)), "Constructor or reload restored administrator-deleted/OFF rules");
        Blacklist parsed = Blacklist.read(path);
        require(parsed.lookup("mod", "meteor-client").action == GuardConfig.Action.OFF && parsed.lookup("mod", "xray") == null,
                "Administrator actions were not preserved");
        require(parsed.lookup("mod", "ferox").action == GuardConfig.Action.OFF && parsed.lookup("mod", "wurstplusthree") == null,
                "Administrator OFF/deletion of new catalog rules was not preserved");
        Decision result = report(restarted, "meteor-client", "xray", "ferox", "wurstplusthree");
        require(result.allowed() && result.code().equals("OK") && restarted.listBans().isEmpty(), "Existing OFF/deleted rules still denied or banned");
        System.out.println("PASS control 2: administrator OFF and API deletion survive reload and a new GuardService byte-for-byte");
    }

    private static void preserveSparseExistingFile() throws Exception {
        Path directory = fresh(); Path path = directory.resolve("blacklist.tsv");
        byte[] administratorBytes = ("# Existing administrator list; intentionally omits default entries.\r\n"
                + "mod\tmeteor-client\tOFF\thttps://example.org/admin-policy\r\n").getBytes(StandardCharsets.UTF_8);
        Files.write(path, administratorBytes);
        GuardService guard = new GuardService(directory); guard.reload();
        require(Arrays.equals(administratorBytes, Files.readAllBytes(path)), "First updated constructor merged defaults into an existing sparse administrator file");
        require(guard.listRules().size() == 1, "Existing sparse policy gained default rules");
        require(report(guard, "meteor-client", "xray", "ferox", "wurstplusthree").allowed() && guard.listBans().isEmpty(), "Existing sparse administrator policy was ignored");
        System.out.println("PASS control 3: pre-existing sparse CRLF policy is never auto-expanded or normalized");
    }

    private static Map<String, String> rows(Path path) throws Exception {
        Map<String, String> result = new LinkedHashMap<String, String>();
        for (String line : Files.readAllLines(path, StandardCharsets.UTF_8)) {
            if (line.trim().isEmpty() || line.trim().startsWith("#")) continue;
            String[] fields = line.split("\t", -1);
            require(fields.length == 4, "Catalog row must contain four fields");
            require(result.put(fields[0] + "\t" + fields[1], line) == null, "Duplicate exact catalog row");
        }
        return result;
    }

    private static Decision report(GuardService guard, String... mods) throws Exception {
        UUID player = UUID.randomUUID();
        require(guard.openSession(player, "192.0.2.1", NOW).allowed(), "Fresh test session denied before report");
        guard.confirmSession(player, NOW);
        String nonce = Wire.decodeChallenge(guard.challenge(player, NOW));
        ClientReport report = new ClientReport(Arrays.asList(mods), Collections.<String>emptyList(), Collections.<String>emptyList(), true, DEVICE);
        Decision result = guard.acceptReport(player, Wire.encodeReport(nonce, report), NOW + 1);
        guard.closeSession(player);
        return result;
    }

    private static Path fresh() throws Exception { return Files.createTempDirectory(testRoot, "case-"); }
    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
