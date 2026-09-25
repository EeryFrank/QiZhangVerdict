package cn.qizhang.guard.core;

import java.io.IOException;
import java.net.URI;
import java.net.URISyntaxException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.ArrayList;
import java.util.Collections;

final class Blacklist {
    static final String DEFAULTS = "# kind<TAB>exact normalized value<TAB>OFF|ALERT|DENY<TAB>source URL\n"
            + "# Exact identifiers only; this is not an exhaustive cheat database or proof of detection.\n"
            + "mod\tmeteor-client\tDENY\thttps://github.com/MeteorDevelopment/meteor-client/blob/master/src/main/resources/fabric.mod.json\n"
            + "mod\twurst\tDENY\thttps://raw.githubusercontent.com/Wurst-Imperium/Wurst7/master/src/main/resources/fabric.mod.json\n"
            + "mod\tliquidbounce\tDENY\thttps://raw.githubusercontent.com/CCBlueX/LiquidBounce/nextgen/src/main/resources/fabric.mod.json\n"
            + "mod\tbleachhack\tDENY\thttps://raw.githubusercontent.com/BleachDev/BleachHack/master/src/main/resources/fabric.mod.json\n"
            + "mod\tadvanced-xray-fabric\tDENY\thttps://raw.githubusercontent.com/AdvancedXRay/XRay-Fabric/main/src/main/resources/fabric.mod.json\n"
            + "mod\tthunderhack\tDENY\thttps://raw.githubusercontent.com/Pan4ur/ThunderHack-Recode/main/src/main/resources/fabric.mod.json\n"
            + "mod\tearthhack\tDENY\thttps://raw.githubusercontent.com/3arthqu4ke/3arthh4ck/master/src/main/resources/mcmod.info\n"
            + "mod\tkamiblue\tDENY\thttps://raw.githubusercontent.com/kami-blue/client/master/src/main/resources/mcmod.info\n"
            + "mod\tsalhack\tDENY\thttps://raw.githubusercontent.com/ionar2/salhack/master/src/main/resources/mcmod.info\n"
            + "mod\txray\tDENY\thttps://raw.githubusercontent.com/AdvancedXRay/XRay-Mod/main/gradle.properties\n"
            + "automation\tbaritone\tALERT\thttps://raw.githubusercontent.com/cabaletta/baritone/1.21.4/fabric/src/main/resources/fabric.mod.json\n";
    private final Map<String, Rule> rules = new HashMap<String, Rule>();
    static final class Rule {
        final GuardConfig.Action action;
        final String kind;
        Rule(GuardConfig.Action action, String kind) { this.action = action; this.kind = kind; }
    }
    static Blacklist read(Path path) throws IOException {
        if (Files.size(path) > 4194304) throw new IOException("Blacklist exceeds 4 MiB");
        Blacklist result = new Blacklist();
        List<String> lines = Files.readAllLines(path, StandardCharsets.UTF_8);
        int lineNo = 0;
        for (String line : lines) {
            lineNo++;
            if (line.trim().isEmpty() || line.trim().startsWith("#")) continue;
            String[] parts = line.split("\t", -1);
            if (parts.length != 4) throw new IOException("blacklist.tsv line " + lineNo + " must have four tab-separated fields");
            String kind = normalize(parts[0]), value = normalize(parts[1]);
            if (!(kind.equals("mod") || kind.equals("automation") || kind.equals("pack") || kind.equals("brand")))
                throw new IOException("Unknown blacklist kind at line " + lineNo);
            if (value.isEmpty() || value.getBytes(StandardCharsets.UTF_8).length > 256 || hasControls(value))
                throw new IOException("Invalid blacklist value at line " + lineNo);
            if ((kind.equals("mod") || kind.equals("automation")) && !value.matches("[a-z0-9_.-]{1,128}"))
                throw new IOException("Invalid mod identifier at line " + lineNo);
            try {
                URI source = new URI(parts[3]);
                if (!("https".equals(source.getScheme()) || "http".equals(source.getScheme())) || source.getHost() == null)
                    throw new URISyntaxException(parts[3], "Expected public source URL");
            } catch (URISyntaxException ex) { throw new IOException("Invalid source URL at blacklist line " + lineNo, ex); }
            String key = (kind.equals("automation") ? "mod" : kind) + "\t" + value;
            if (result.rules.put(key, new Rule(GuardConfig.action(parts[2], "blacklist line " + lineNo), kind)) != null)
                throw new IOException("Duplicate blacklist identifier at line " + lineNo);
            if (result.rules.size() > 10000) throw new IOException("Too many blacklist entries");
        }
        return result;
    }
    Rule lookup(String kind, String value) { return rules.get(kind + "\t" + normalize(value)); }
    int size() { return rules.size(); }
    List<String> listRules() {
        List<String> result = new ArrayList<String>();
        for (Map.Entry<String, Rule> entry : rules.entrySet()) {
            String[] key = entry.getKey().split("\t", 2); Rule rule = entry.getValue();
            result.add("legacy:" + rule.kind + ":" + key[1] + "\tBLACK\t" + key[0].toUpperCase(Locale.ROOT) + "\tEXACT\t" + key[1] + "\t" + rule.action);
        }
        Collections.sort(result); return result;
    }
    static String normalize(String value) { return value == null ? "" : value.trim().toLowerCase(Locale.ROOT); }
    private static boolean hasControls(String value) {
        for (int i = 0; i < value.length(); i++) if (Character.isISOControl(value.charAt(i))) return true;
        return false;
    }
}
