package cn.qizhang.guard.core;

import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Properties;

final class GuardConfig {
    static final String DEFAULTS = "# QiZhangVerdict: restart/reload after editing; IPs are literals or CIDRs, comma separated.\n"
            + "limits.max-online-per-ip=3\nlimits.max-online-per-ip-device=1\nlimits.max-accounts-per-ip=5\nlimits.account-window-hours=720\n"
            + "limits.attempts-per-minute=20\nip.allow=\nip.deny=\ncompanion.required=true\ncompanion.timeout-seconds=20\n"
            + "vm.action=DENY\nblacklist.action=DENY\nsanctions.on-deny=BAN\ndevice.required=true\n";
    enum Action { OFF, ALERT, DENY }
    final int maxOnline, maxAccounts, attempts, timeout, maxIpDevice;
    final long windowMillis;
    final boolean companion;
    final boolean deviceRequired, banOnDeny;
    final Action vmAction, blacklistAction;
    final List<Cidr> allow, deny;
    private GuardConfig(Properties p) throws IOException {
        maxOnline = integer(p, "limits.max-online-per-ip", 3, 1, 10000);
        maxIpDevice = integer(p, "limits.max-online-per-ip-device", 1, 1, 10000);
        maxAccounts = integer(p, "limits.max-accounts-per-ip", 5, 1, 100000);
        attempts = integer(p, "limits.attempts-per-minute", 20, 1, 100000);
        timeout = integer(p, "companion.timeout-seconds", 20, 1, 300);
        windowMillis = integer(p, "limits.account-window-hours", 720, 1, 87600) * 3600000L;
        String required = p.getProperty("companion.required", "true").trim();
        if (!required.equals("true") && !required.equals("false")) throw new IOException("companion.required must be true or false");
        companion = Boolean.parseBoolean(required);
        String device = p.getProperty("device.required", "true").trim();
        if (!device.equals("true") && !device.equals("false")) throw new IOException("device.required must be true or false");
        deviceRequired = Boolean.parseBoolean(device);
        if (deviceRequired && !companion) throw new IOException("device.required=true requires companion.required=true");
        String sanctions = p.getProperty("sanctions.on-deny", "BAN").trim();
        if (!sanctions.equals("BAN") && !sanctions.equals("KICK")) throw new IOException("sanctions.on-deny must be BAN or KICK");
        banOnDeny = sanctions.equals("BAN");
        vmAction = action(p.getProperty("vm.action", "DENY"), "vm.action");
        blacklistAction = action(p.getProperty("blacklist.action", "DENY"), "blacklist.action");
        if (vmAction == Action.DENY && !companion) throw new IOException("vm.action=DENY requires companion.required=true");
        allow = networks(p.getProperty("ip.allow", "")); deny = networks(p.getProperty("ip.deny", ""));
        for (String name : p.stringPropertyNames()) {
            if (!(name.equals("limits.max-online-per-ip") || name.equals("limits.max-online-per-ip-device") || name.equals("limits.max-accounts-per-ip")
                    || name.equals("limits.account-window-hours") || name.equals("limits.attempts-per-minute")
                    || name.equals("companion.timeout-seconds") || name.equals("companion.required")
                    || name.equals("vm.action") || name.equals("blacklist.action") || name.equals("ip.allow") || name.equals("ip.deny")
                    || name.equals("device.required") || name.equals("sanctions.on-deny")))
                throw new IOException("Unknown configuration key: " + name);
        }
    }
    static GuardConfig read(Path path) throws IOException {
        if (Files.size(path) > 65536) throw new IOException("Configuration exceeds 64 KiB");
        Properties properties = new Properties();
        try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) { properties.load(reader); }
        catch (IllegalArgumentException ex) { throw new IOException("Malformed properties file", ex); }
        return new GuardConfig(properties);
    }
    static Action action(String text, String field) throws IOException {
        try { return Action.valueOf(text.trim().toUpperCase(Locale.ROOT)); }
        catch (IllegalArgumentException ex) { throw new IOException("Invalid action for " + field, ex); }
    }
    private static int integer(Properties p, String name, int defaultValue, int min, int max) throws IOException {
        String text = p.getProperty(name, Integer.toString(defaultValue)).trim();
        try {
            int value = Integer.parseInt(text);
            if (value < min || value > max) throw new NumberFormatException();
            return value;
        } catch (NumberFormatException ex) { throw new IOException(name + " must be in range " + min + ".." + max); }
    }
    private static List<Cidr> networks(String text) throws IOException {
        ArrayList<Cidr> result = new ArrayList<Cidr>();
        if (text.trim().isEmpty()) return result;
        String[] parts = text.split(",", -1);
        if (parts.length > 1024) throw new IOException("Too many IP rules");
        try { for (String part : parts) result.add(Cidr.parse(part.trim())); }
        catch (IllegalArgumentException ex) { throw new IOException("Invalid IP/CIDR rule: " + ex.getMessage(), ex); }
        return result;
    }
}
