package cn.qizhang.guard.client;

import cn.qizhang.guard.core.ClientReport;
import cn.qizhang.guard.core.Wire;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.UUID;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

/** Privacy-limited self report. This is not attestation and can be forged by modified clients. */
public final class ClientReporter {
    private final ThreadPoolExecutor probeWorker = new ThreadPoolExecutor(1, 1, 10, TimeUnit.SECONDS,
            new ArrayBlockingQueue<Runnable>(1), task -> { Thread t = new Thread(task, "QiZhangVerdict-client-probe"); t.setDaemon(true); return t; });
    private long generation;
    private String lastNonce = "", lastScope = "";
    private Request latest;
    private boolean running;

    public ClientReporter() { probeWorker.allowCoreThreadTimeOut(true); }

    /** Coalesces rapid reloads: at most one active probe and one latest request per client. */
    public synchronized void respond(byte[] challenge, List<String> mods, List<String> packs, Path clientConfig, Consumer<Runnable> clientThread, Consumer<byte[]> sender) {
        final String nonce;
        final String serverScope;
        try { nonce = Wire.decodeChallenge(challenge); serverScope = Wire.decodeServerScope(challenge); } catch (Exception invalid) { return; }
        if (lastNonce.equals(nonce) && lastScope.equals(serverScope)) return;
        lastNonce = nonce; lastScope = serverScope;
        latest = new Request(++generation, nonce, serverScope, new ArrayList<>(mods), new ArrayList<>(packs), clientConfig, clientThread, sender);
        if (!running) { running = true; probeWorker.execute(this::drain); }
    }

    private void drain() {
        while (true) {
            final Request request;
            synchronized (this) {
                request = latest; latest = null;
                if (request == null) { running = false; return; }
            }
            byte[] encoded;
            try { encoded = Wire.encodeReport(request.nonce, new ClientReport(request.mods, request.packs, probe(), true, deviceId(request.scope, request.config))); }
            catch (Exception invalidInventory) {
                encoded = Wire.encodeReport(request.nonce, new ClientReport(Collections.emptyList(), Collections.emptyList(), Collections.singletonList("unknown"), false));
            }
            final byte[] response = encoded;
            try {
                request.clientThread.accept(() -> {
                    synchronized (ClientReporter.this) {
                        if (generation != request.generation) return;
                        request.sender.accept(response);
                    }
                });
            } catch (RuntimeException connectionClosed) { /* A later connection still gets its latest request. */ }
        }
    }

    private static final class Request {
        final long generation; final String nonce, scope; final List<String> mods, packs; final Path config;
        final Consumer<Runnable> clientThread; final Consumer<byte[]> sender;
        Request(long generation, String nonce, String scope, List<String> mods, List<String> packs, Path config, Consumer<Runnable> clientThread, Consumer<byte[]> sender) {
            this.generation = generation; this.nonce = nonce; this.scope = scope; this.mods = mods; this.packs = packs;
            this.config = config; this.clientThread = clientThread; this.sender = sender;
        }
    }

    /** Hashes an installation identifier separately for each server. Raw IDs never leave this method. */
    static String deviceId(String serverScope, Path config) {
        String raw = "";
        String os = System.getProperty("os.name", "").toLowerCase(Locale.ROOT);
        try {
            if (os.contains("windows")) {
                String systemRoot = System.getenv("SystemRoot");
                Process process = new ProcessBuilder(systemRoot + "\\System32\\reg.exe", "query",
                        "HKLM\\SOFTWARE\\Microsoft\\Cryptography", "/v", "MachineGuid")
                        .redirectError(ProcessBuilder.Redirect.DISCARD).start();
                try {
                    if (process.waitFor(1500, TimeUnit.MILLISECONDS) && process.exitValue() == 0) {
                        try (InputStream stream = process.getInputStream()) {
                            String output = new String(stream.readNBytes(4096), StandardCharsets.UTF_8);
                            java.util.regex.Matcher matcher = java.util.regex.Pattern.compile("(?i)MachineGuid\\s+REG_SZ\\s+([a-f0-9-]{16,64})").matcher(output);
                            if (matcher.find()) raw = matcher.group(1);
                        }
                    }
                } finally { if (process.isAlive()) process.destroyForcibly(); }
            } else if (os.contains("linux")) {
                try (InputStream stream = Files.newInputStream(Paths.get("/etc/machine-id"))) {
                    String value = new String(stream.readNBytes(256), StandardCharsets.UTF_8).trim();
                    if (value.matches("[a-fA-F0-9]{32}")) raw = value;
                }
            }
        } catch (Exception unavailable) { }
        if (raw.isEmpty()) {
            try {
                Files.createDirectories(config);
                Path file = config.resolve("installation-id.txt");
                if (!Files.exists(file)) Files.writeString(file, UUID.randomUUID().toString(), StandardCharsets.UTF_8, StandardOpenOption.CREATE_NEW);
                try (InputStream stream = Files.newInputStream(file)) { raw = new String(stream.readNBytes(128), StandardCharsets.UTF_8).trim(); }
                if (!raw.matches("[a-fA-F0-9-]{36}")) return "";
                System.out.println("[QiZhangVerdict] Device report uses a local random installation ID fallback; it is not hardware attestation.");
            } catch (Exception unavailable) { return ""; }
        }
        try {
            String scoped = "QiZhangVerdict|" + serverScope.trim().toLowerCase(Locale.ROOT) + "|" + raw.trim().toLowerCase(Locale.ROOT);
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(scoped.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(); for (byte value : digest) hex.append(String.format(Locale.ROOT, "%02x", value & 255)); return hex.toString();
        } catch (Exception unavailable) { return ""; }
    }

    static List<String> probe() {
        String os = System.getProperty("os.name", "").toLowerCase(Locale.ROOT);
        String raw;
        try {
            if (os.contains("windows")) {
                String systemRoot = System.getenv("SystemRoot");
                if (systemRoot == null) return Collections.singletonList("unknown");
                Process process = new ProcessBuilder(systemRoot + "\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                        "-NoLogo", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command",
                        "$c=Get-CimInstance Win32_ComputerSystem; $b=Get-CimInstance Win32_BIOS; $c.Manufacturer; $c.Model; $b.Manufacturer")
                        .redirectError(ProcessBuilder.Redirect.DISCARD).start();
                try {
                    if (!process.waitFor(1800, TimeUnit.MILLISECONDS)) { process.destroyForcibly(); return Collections.singletonList("unknown"); }
                    if (process.exitValue() != 0) return Collections.singletonList("unknown");
                    try (InputStream input = process.getInputStream()) { raw = new String(input.readNBytes(8192), StandardCharsets.UTF_8); }
                } finally { if (process.isAlive()) process.destroyForcibly(); }
            } else if (os.contains("linux")) {
                StringBuilder text = new StringBuilder();
                for (String field : new String[]{"sys_vendor", "product_name", "board_vendor", "bios_vendor"}) {
                    try (InputStream input = Files.newInputStream(Paths.get("/sys/class/dmi/id", field))) {
                        text.append(new String(input.readNBytes(1024), StandardCharsets.UTF_8)).append('\n');
                    } catch (Exception unavailable) { }
                }
                raw = text.toString();
            } else return Collections.singletonList("unknown");
        } catch (Exception unavailable) { return Collections.singletonList("unknown"); }
        raw = raw.toLowerCase(Locale.ROOT);
        if (raw.trim().isEmpty()) return Collections.singletonList("unknown");
        List<String> signals = new ArrayList<>();
        for (String[] marker : new String[][]{{"vmware", "vmware"}, {"virtualbox", "virtualbox"}, {"innotek", "virtualbox"},
                {"qemu", "qemu"}, {"kvm", "kvm"}, {"xen", "xen"}, {"parallels", "parallels"}, {"bhyve", "bhyve"}}) {
            if (raw.contains(marker[0]) && !signals.contains(marker[1])) signals.add(marker[1]);
        }
        // VBS/HypervisorPresent on a physical Windows host is deliberately not considered VM evidence.
        if (raw.contains("microsoft corporation") && raw.contains("virtual machine")) signals.add("hyper-v-guest");
        return signals;
    }
}
