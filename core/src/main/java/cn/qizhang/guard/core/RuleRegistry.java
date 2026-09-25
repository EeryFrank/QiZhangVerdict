package cn.qizhang.guard.core;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;

/** Administrator rules use a bounded wildcard matcher, never regular expressions. */
final class RuleRegistry {
    static final class Budget {
        private int remaining = 1000000;
        void spend(int count) { remaining -= count; if (remaining < 0) throw new BudgetExceeded(); }
    }
    static final class BudgetExceeded extends RuntimeException { private static final long serialVersionUID = 1L; }
    static final String HEADER = "# id\tBLACK|WHITE\tMOD|PACK|BRAND|PLAYER|DEVICE\tEXACT|GLOB\tvalue\n";
    final List<Rule> rules = new ArrayList<Rule>();
    static final class Rule {
        final String id, list, kind, match, value;
        Rule(String id, String list, String kind, String match, String value) throws IOException {
            try { if (!UUID.fromString(id).toString().equals(id)) throw new IllegalArgumentException(); }
            catch (IllegalArgumentException ex) { throw new IOException("Invalid rule ID", ex); }
            this.id = id; this.list = normalizeEnum(list); this.kind = normalizeEnum(kind); this.match = normalizeEnum(match);
            this.value = Blacklist.normalize(value);
            if (!(this.list.equals("BLACK") || this.list.equals("WHITE"))) throw new IOException("Rule list must be BLACK or WHITE");
            if (!(this.kind.equals("MOD") || this.kind.equals("PACK") || this.kind.equals("BRAND") || this.kind.equals("PLAYER") || this.kind.equals("DEVICE"))) throw new IOException("Unsupported rule kind");
            if (!(this.match.equals("EXACT") || this.match.equals("GLOB"))) throw new IOException("Rule match must be EXACT or GLOB");
            if (this.value.isEmpty() || this.value.getBytes(StandardCharsets.UTF_8).length > 256) throw new IOException("Rule value must contain 1..256 UTF-8 bytes");
            for (int i = 0; i < this.value.length(); i++) if (Character.isISOControl(this.value.charAt(i))) throw new IOException("Control character in rule");
            if (this.match.equals("EXACT") && (this.value.indexOf('*') >= 0 || this.value.indexOf('?') >= 0)) throw new IOException("EXACT rules cannot contain wildcards");
            if (this.kind.equals("MOD") && !this.value.matches(this.match.equals("GLOB") ? "[a-z0-9_.?*-]{1,128}" : "[a-z0-9_.-]{1,128}")) throw new IOException("Invalid mod pattern");
            if (this.kind.equals("DEVICE") && !this.value.matches(this.match.equals("GLOB") ? "[0-9a-f?*]{1,64}" : "[0-9a-f]{64}")) throw new IOException("Invalid device pattern");
            if (this.kind.equals("PLAYER")) {
                if (this.match.equals("GLOB")) { if (!this.value.matches("[0-9a-f?*-]{1,36}")) throw new IOException("Invalid UUID pattern"); }
                else try { if (!UUID.fromString(this.value).toString().equals(this.value)) throw new IllegalArgumentException(); }
                catch (IllegalArgumentException ex) { throw new IOException("PLAYER rules require a canonical UUID", ex); }
            }
        }
        String line() { return id + "\t" + list + "\t" + kind + "\t" + match + "\t" + value; }
        boolean matches(String candidate, Budget budget) {
            if (match.equals("EXACT")) { budget.spend(Math.max(value.length(), candidate.length())); return value.equals(candidate); }
            return glob(value, candidate, budget);
        }
    }
    static RuleRegistry read(Path path) throws IOException {
        if (Files.size(path) > 4194304) throw new IOException("rules.tsv exceeds 4 MiB");
        RuleRegistry registry = new RuleRegistry(); Set<String> ids = new HashSet<String>();
        for (String line : Files.readAllLines(path, StandardCharsets.UTF_8)) {
            if (line.trim().isEmpty() || line.trim().startsWith("#")) continue;
            String[] fields = line.split("\t", -1);
            if (fields.length != 5) throw new IOException("Each rules.tsv rule needs five tab-separated fields");
            Rule rule = new Rule(fields[0], fields[1], fields[2], fields[3], fields[4]);
            if (!ids.add(rule.id)) throw new IOException("Duplicate rule ID");
            registry.rules.add(rule); if (registry.rules.size() > 10000) throw new IOException("Too many managed rules");
        }
        return registry;
    }
    RuleRegistry copy() { RuleRegistry copy = new RuleRegistry(); copy.rules.addAll(rules); return copy; }
    boolean matches(String list, String kind, String candidate, Budget budget) {
        String k = normalizeEnum(kind), value = Blacklist.normalize(candidate);
        for (Rule rule : rules) { budget.spend(1); if (rule.list.equals(list) && rule.kind.equals(k) && rule.matches(value, budget)) return true; }
        return false;
    }
    byte[] encode() {
        StringBuilder out = new StringBuilder(HEADER); for (Rule rule : rules) out.append(rule.line()).append('\n');
        return out.toString().getBytes(StandardCharsets.UTF_8);
    }
    private static String normalizeEnum(String value) { return value == null ? "" : value.trim().toUpperCase(Locale.ROOT); }
    static boolean glob(String pattern, String text) {
        return glob(pattern, text, new Budget());
    }
    private static boolean glob(String pattern, String text, Budget budget) {
        // O(pattern length * text length), both bounded to <=256; no recursive backtracking.
        if (text.length() > 256 || pattern.length() > 256) return false;
        boolean[] previous = new boolean[text.length() + 1]; previous[0] = true;
        for (int p = 0; p < pattern.length(); p++) {
            budget.spend(text.length() + 1);
            char c = pattern.charAt(p); boolean[] next = new boolean[text.length() + 1];
            next[0] = c == '*' && previous[0];
            for (int t = 1; t <= text.length(); t++) next[t] = c == '*' ? previous[t] || next[t - 1] : previous[t - 1] && (c == '?' || c == text.charAt(t - 1));
            previous = next;
        }
        return previous[text.length()];
    }
}
