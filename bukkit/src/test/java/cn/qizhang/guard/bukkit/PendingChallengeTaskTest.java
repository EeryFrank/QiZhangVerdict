// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.bukkit;

import cn.qizhang.guard.core.ClientReport;
import cn.qizhang.guard.core.Decision;
import cn.qizhang.guard.core.GuardService;
import cn.qizhang.guard.core.Wire;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/** Exercises the production scheduled Runnable without starting Bukkit or Minecraft. */
public final class PendingChallengeTaskTest {
    private static final long NOW = 1000000L;
    private static final String DEVICE = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    private static int passed;

    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Provide an isolated test data directory");
        Path root = Paths.get(args[0]);
        Files.createDirectories(root);
        oldCapturedNonceTimesOut(root.resolve("old-control"));
        sendsCurrentChallengeAfterReload(root.resolve("reload"));
        suppressesRemovedChallenge(root.resolve("completed"));
        suppressesDisconnectedOwner(root.resolve("disconnected"));
        suppressesReplacementOwner(root.resolve("replacement"));
        suppressesOfflineOwner(root.resolve("offline"));
        System.out.println("PASS " + passed + " pending challenge scheduling checks");
    }

    private static void oldCapturedNonceTimesOut(Path path) throws Exception {
        Fixture f = new Fixture(path);
        final byte[] captured = f.pending.get(f.id);
        // Negative-control model of the former joined() lambda, not execution of an old plugin binary.
        Runnable oldTask = () -> { if (f.online.get() && f.pending.containsKey(f.id)) f.sent.add(captured); };
        f.reload(); oldTask.run();
        require("STALE_REPORT".equals(f.answerLast().code()), "Old task did not reproduce a superseded response");
        require(f.guard.expiredReports(NOW + 20000L).contains(f.id), "Old challenge unexpectedly satisfied the current report deadline");
        pass("old-closure model produces stale response and strict timeout");
    }

    private static void sendsCurrentChallengeAfterReload(Path path) throws Exception {
        Fixture f = new Fixture(path);
        f.reload(); f.task.run();
        require(f.sent.size() == 2, "Expected reload send and delayed send");
        require(Wire.decodeChallenge(f.sent.get(0)).equals(Wire.decodeChallenge(f.sent.get(1))), "Delayed send regressed to the initial nonce");
        require(f.answerLast().allowed(), "Newest challenge did not pass real GuardService validation");
        require(f.guard.expiredReports(NOW + 20001L).isEmpty(), "Valid current report later timed out");
        pass("reload before delayed task sends current nonce and satisfies strict validation");
    }

    private static void suppressesRemovedChallenge(Path path) throws Exception {
        Fixture f = new Fixture(path);
        f.pending.remove(f.id); f.task.run();
        require(f.sent.isEmpty(), "Completed or cleared challenge was resent");
        pass("completed or cleared pending challenge is not resent");
    }

    private static void suppressesDisconnectedOwner(Path path) throws Exception {
        Fixture f = new Fixture(path);
        f.currentOwner.set(null); f.task.run();
        require(f.sent.isEmpty(), "Disconnected owner's retained map entry was sent");
        pass("disconnected owner cannot receive retained pending bytes");
    }

    private static void suppressesReplacementOwner(Path path) throws Exception {
        Fixture f = new Fixture(path);
        f.reload(); f.sent.clear(); f.currentOwner.set(new Object()); f.task.run();
        require(f.sent.isEmpty(), "Old Player task sent a replacement session's challenge");
        pass("old Player task cannot send a replacement session challenge");
    }

    private static void suppressesOfflineOwner(Path path) throws Exception {
        Fixture f = new Fixture(path);
        f.online.set(false); f.task.run();
        require(f.sent.isEmpty(), "Offline owner was sent a pending challenge");
        pass("offline owner is not sent a pending challenge");
    }

    private static final class Fixture {
        final UUID id = UUID.randomUUID();
        final Object owner = new Object();
        final AtomicReference<Object> currentOwner = new AtomicReference<Object>(owner);
        final AtomicBoolean online = new AtomicBoolean(true);
        final Map<UUID, byte[]> pending = new HashMap<UUID, byte[]>();
        final List<byte[]> sent = new ArrayList<byte[]>();
        final GuardService guard;
        final PendingChallengeTask task;
        Fixture(Path path) throws Exception {
            if (Files.exists(path)) throw new IllegalArgumentException("Fixture directory already exists: " + path);
            guard = new GuardService(path);
            require(guard.openSession(id, "192.0.2.1", NOW).allowed(), "Fixture admission failed");
            guard.confirmSession(id, NOW);
            pending.put(id, guard.challenge(id, NOW));
            task = new PendingChallengeTask(owner, currentOwner::get, online::get, () -> pending.get(id), sent::add);
        }
        void reload() throws Exception {
            guard.reload();
            byte[] current = guard.challenge(id, NOW + 50L);
            pending.put(id, current); sent.add(current);
        }
        Decision answerLast() throws Exception {
            byte[] last = sent.get(sent.size() - 1);
            ClientReport report = new ClientReport(Collections.singletonList("minecraft"),
                    Collections.<String>emptyList(), Collections.<String>emptyList(), true, DEVICE);
            return guard.acceptReport(id, Wire.encodeReport(Wire.decodeChallenge(last), report), NOW + 100L);
        }
    }

    private static void require(boolean value, String message) { if (!value) throw new AssertionError(message); }
    private static void pass(String name) { passed++; System.out.println("PASS " + passed + " " + name); }
}
