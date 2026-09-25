package cn.qizhang.guard.core;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/** Loads the shipped extension with the actual production parser, without changing server files. */
public final class CatalogCompatibilityTest {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Expected catalog TSV path");
        Path input = Paths.get(args[0]);
        Blacklist loaded = Blacklist.read(input);
        int count = 0;
        for (String line : Files.readAllLines(input, StandardCharsets.UTF_8)) {
            if (line.trim().isEmpty() || line.trim().startsWith("#")) continue;
            String[] fields = line.split("\t", -1);
            String kind = fields[0].equals("automation") ? "mod" : fields[0];
            Blacklist.Rule rule = loaded.lookup(kind, fields[1]);
            if (rule == null || !rule.action.name().equals(fields[2]))
                throw new AssertionError("Production parser changed catalog rule: " + fields[1]);
            count++;
        }
        if (count == 0 || count != loaded.size()) throw new AssertionError("Missing or duplicate catalog identities");
        for (String allowed : new String[]{"antixray", "sodium", "iris", "jei"})
            if (loaded.lookup("mod", allowed) != null) throw new AssertionError("Unexpected ordinary mod denial: " + allowed);
        for (String alertOnly : new String[]{"baritone", "baritoe", "keystrokesmod"}) {
            Blacklist.Rule rule = loaded.lookup("mod", alertOnly);
            if (rule == null || rule.action != GuardConfig.Action.ALERT)
                throw new AssertionError("Ambiguous/automation identifier must remain ALERT: " + alertOnly);
        }
        System.out.println("PASS: production Blacklist parser accepts " + count + " exact extension rules; alert-only and ordinary IDs preserved");
    }
}
