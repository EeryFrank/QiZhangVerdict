package cn.qizhang.guard.core;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/** Untrusted client claims, never remote attestation or proof of a clean client. */
public final class ClientReport {
    private final List<String> modIds;
    private final List<String> resourcePacks;
    private final List<String> vmSignals;
    private final boolean complete;
    private final String deviceId;
    public ClientReport(List<String> modIds, List<String> resourcePacks, List<String> vmSignals, boolean complete) {
        this(modIds, resourcePacks, vmSignals, complete, "");
    }
    public ClientReport(List<String> modIds, List<String> resourcePacks, List<String> vmSignals, boolean complete, String deviceId) {
        this.modIds = copy(modIds); this.resourcePacks = copy(resourcePacks);
        this.vmSignals = copy(vmSignals); this.complete = complete;
        if (deviceId == null || !(deviceId.isEmpty() || deviceId.matches("[0-9a-f]{64}")))
            throw new IllegalArgumentException("Device ID must be empty or a lowercase SHA-256 digest");
        this.deviceId = deviceId;
    }
    private static List<String> copy(List<String> input) {
        Objects.requireNonNull(input, "report list");
        if (input.size() > Wire.MAX_MODS) throw new IllegalArgumentException("Too many report entries");
        ArrayList<String> out = new ArrayList<String>(input.size());
        for (String item : input) out.add(Objects.requireNonNull(item, "report entry"));
        return Collections.unmodifiableList(out);
    }
    public List<String> modIds() { return modIds; }
    public List<String> resourcePacks() { return resourcePacks; }
    public List<String> vmSignals() { return vmSignals; }
    public boolean complete() { return complete; }
    public String deviceId() { return deviceId; }
}
