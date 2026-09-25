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
            + "# Fresh-install snapshot of catalog/blacklist-extension.tsv; existing administrator files are preserved.\n"
            + "automation\tbaritoe\tALERT\thttps://raw.githubusercontent.com/cabaletta/baritone/3d3da10b0cb0fb71a80ffb2fe673fac6927924d2/forge/src/main/resources/META-INF/mods.toml\n"
            + "automation\tbaritone\tALERT\thttps://raw.githubusercontent.com/cabaletta/baritone/3d3da10b0cb0fb71a80ffb2fe673fac6927924d2/fabric/src/main/resources/fabric.mod.json\n"
            + "mod\tadvanced-xray-fabric\tDENY\thttps://raw.githubusercontent.com/AdvancedXRay/XRay-Fabric/1351f0776f6cb634ff0d502435f220ea501ad576/src/main/resources/fabric.mod.json\n"
            + "mod\taegis\tDENY\thttps://raw.githubusercontent.com/aegisclient/client/8d20597359f49e9028c3dfc43888bab3c760bce9/src/main/resources/fabric.mod.json\n"
            + "mod\talien\tDENY\thttps://raw.githubusercontent.com/iM4dCat/Alien/8a4348bce4d9a2cefe020da71d988a48a1a54a21/src/main/resources/fabric.mod.json\n"
            + "mod\taoba\tDENY\thttps://raw.githubusercontent.com/Cocolots/Aoba-Client/c698b09d4f4e76db4b1dee0a0d6b2051324b9ce0/src/main/resources/fabric.mod.json\n"
            + "mod\tares\tDENY\thttps://raw.githubusercontent.com/AresClient/ares/c60af6fddc11c9dee0676a8c4a21fc9b2f0aafcb/ares-fabric-1.16/src/main/resources/fabric.mod.json\n"
            + "mod\tatianxray\tALERT\thttps://raw.githubusercontent.com/ate47/Xray/74367d98ec04d1aa7029e70f0ab083033e5c91f5/src/main/resources/META-INF/mods.toml\n"
            + "mod\tblackout\tDENY\thttps://raw.githubusercontent.com/KassuK1/BlackOut/4c18af3f58040e4ff4337b81cf627daacbdfba14/src/main/resources/fabric.mod.json\n"
            + "mod\tbleachhack\tDENY\thttps://raw.githubusercontent.com/BleachDev/BleachHack/2a30d34be73aa62484bb1ede97a7f657044fe333/src/main/resources/fabric.mod.json\n"
            + "mod\tcheatutils\tDENY\thttps://raw.githubusercontent.com/Zergatul/cheatutils/08c1a79e27724fce4460c3f61bcfa991b8a64199/fabric/src/main/resources/fabric.mod.json\n"
            + "mod\tcigarette\tDENY\thttps://raw.githubusercontent.com/cigaretteclient/cigarette/452a33333c985358ab56ac82258a8b82b35a0d3f/src/main/resources/fabric.mod.json\n"
            + "mod\tearthhack\tDENY\thttps://raw.githubusercontent.com/3arthqu4ke/3arthh4ck/211660641696fbd43edadc37471cdcb21dfa392d/src/main/resources/mcmod.info\n"
            + "mod\tfdpclient\tDENY\thttps://raw.githubusercontent.com/SkidderMC/FDPClient/07d03078b3fe12ac7278c678f56d0e7f607fbec2/src/main/resources/mcmod.info\n"
            + "mod\tferox\tDENY\thttps://raw.githubusercontent.com/olliem5/ferox/627205bf13f3a8ff65780a60b319defdcab73eb4/src/main/resources/mcmod.info\n"
            + "mod\tforgehax\tDENY\thttps://raw.githubusercontent.com/fr1kin/ForgeHax/7c954394b1e9a341526e34d7884222ceaa508640/src/main/resources/META-INF/mods.toml\n"
            + "mod\tgamesense\tDENY\thttps://raw.githubusercontent.com/IUDevman/gamesense-client/62061a43fea311f42c64ea2b1dbbb56599c32295/src/main/resources/mcmod.info\n"
            + "mod\thypnotic\tDENY\thttps://raw.githubusercontent.com/Hypnotic-Development/Hypnotic-Client/ec9daf0586d37af0f4f9bac2817636c34c1270ac/src/main/resources/fabric.mod.json\n"
            + "mod\tjex\tDENY\thttps://raw.githubusercontent.com/DustinRepo/JexClient/017ce1229fc446f66eee5c564ce28af142368f3d/src/main/resources/fabric.mod.json\n"
            + "mod\tkami\tDENY\thttps://raw.githubusercontent.com/zeroeightysix/KAMI/7195851c1c319cdd0b79ff5618fde7e2f1b7ab5a/src/main/resources/fabric.mod.json\n"
            + "mod\tkamiblue\tDENY\thttps://raw.githubusercontent.com/kami-blue/client/5a9e51a124cf18ec2e73b63a8dc2e2fbb0d3a43a/src/main/resources/mcmod.info\n"
            + "mod\tkeystrokesmod\tALERT\thttps://raw.githubusercontent.com/K-ov/Raven/5f18282e78418a99ac4167fde3e90c49fa2487b5/src/main/resources/mcmod.info\n"
            + "mod\tkrs\tDENY\thttps://raw.githubusercontent.com/Aspw-w/Krs/9b7df86029b68d5906d68f2aaecaba5a05a5bf61/src/client/resources/fabric.mod.json\n"
            + "mod\tlambda\tDENY\thttps://raw.githubusercontent.com/lambda-client/lambda/92da438fc39c27009f90b7b69196555454c9c096/src/main/resources/fabric.mod.json\n"
            + "mod\tliquidbounce\tDENY\thttps://raw.githubusercontent.com/CCBlueX/LiquidBounce/1ed823acf30b0fb2ee0c1a816fcd04b7c012c16d/src/main/resources/fabric.mod.json\n"
            + "mod\tmastermind\tDENY\thttps://raw.githubusercontent.com/Snowiiii/MasterMind-Fabric/1435f12071a75140db988c24dae082b9be4ec951/src/main/resources/fabric.mod.json\n"
            + "mod\tmeteor-client\tDENY\thttps://raw.githubusercontent.com/MeteorDevelopment/meteor-client/5f274f542342d2525bd2c32b9ce677b4ccddc527/src/main/resources/fabric.mod.json\n"
            + "mod\tmeteor-rejects\tDENY\thttps://raw.githubusercontent.com/AntiCope/meteor-rejects/6a56030ca7481daf9655ca67d3c0750b9fdf1f8b/src/main/resources/fabric.mod.json\n"
            + "mod\tmeteorplus\tDENY\thttps://raw.githubusercontent.com/MeteorClientPlus/MeteorPlus/657959e9b46faa0c1228c5978d3afe844351c911/src/main/resources/fabric.mod.json\n"
            + "mod\tnightx\tDENY\thttps://raw.githubusercontent.com/Aspw-w/NightX-Client/1c771444a9120d8c06fe7d88a3f5849402849bb4/src/main/resources/mcmod.info\n"
            + "mod\tsalhack\tDENY\thttps://raw.githubusercontent.com/ionar2/spidermod/71540547486c11985d6533df45c71a6ad5b22841/src/main/resources/mcmod.info\n"
            + "mod\tseppukumod\tDENY\thttps://raw.githubusercontent.com/seppukudevelopment/seppuku/7956c5d6f74fac43e04e3f6466c4e7d236096e78/src/main/resources/mcmod.info\n"
            + "mod\tstreak-addon\tDENY\thttps://raw.githubusercontent.com/etianl/Trouser-Streak/d4f535813ff6df3bbb998e71e15f148dab4c672f/src/main/resources/fabric.mod.json\n"
            + "mod\tthunderhack\tDENY\thttps://raw.githubusercontent.com/Pan4ur/ThunderHack-Recode/49c76bcc5a5e4fbd12b06305c09f0c8fb76c510b/src/main/resources/fabric.mod.json\n"
            + "mod\ttrollhack\tDENY\thttps://raw.githubusercontent.com/Luna5ama/TrollHack/fbd6a8d74426f653de61ca8bd09e80a488af4398/fabric/src/main/resources/fabric.mod.json\n"
            + "mod\twurst\tDENY\thttps://raw.githubusercontent.com/Wurst-Imperium/Wurst7/15969f6394c9e263624d696108f7075939d4d7f7/src/main/resources/fabric.mod.json\n"
            + "mod\twurstplus\tDENY\thttps://raw.githubusercontent.com/TrvsF/wurstplus-two/b6cbe48605e090186a2c507e0c046cfd8825c59c/src/main/resources/mcmod.info\n"
            + "mod\twurstplusthree\tDENY\thttps://raw.githubusercontent.com/WurstPlus/wurst-plus-three/4eca774c0998dfc06d2f378bf0d939b8ad59318c/src/main/resources/mcmod.info\n"
            + "mod\txray\tDENY\thttps://raw.githubusercontent.com/AdvancedXRay/XRay-Mod/63c6e61754040f57308b7207c688364f686a2079/fabric/src/main/resources/fabric.mod.json\n";
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
