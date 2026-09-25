package cn.qizhang.guard.client;

import cn.qizhang.guard.core.ClientReport;
import cn.qizhang.guard.core.Wire;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.Collections;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.LinkedBlockingQueue;

/** Standalone privacy/wire smoke: never prints installation IDs or their digests. */
public final class ClientReporterSmoke {
    public static void main(String[] args) throws Exception {
        var directory = Paths.get(args[0]);
        String first = ClientReporter.deviceId("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", directory);
        String repeat = ClientReporter.deviceId("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", directory);
        String other = ClientReporter.deviceId("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", directory);
        if (!first.matches("[0-9a-f]{64}") || !first.equals(repeat) || first.equals(other)) throw new AssertionError("Device scope stability/isolation");
        var accepted = new AtomicReference<byte[]>(); var complete = new CountDownLatch(1);
        String nonce = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc";
        long before = System.nanoTime();
        new ClientReporter().respond(Wire.encodeChallenge(nonce, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
                Arrays.asList("minecraft", "qizhangverdict"), Collections.singletonList("vanilla"), directory, Runnable::run,
                bytes -> { accepted.set(bytes); complete.countDown(); });
        if (TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - before) > 1000) throw new AssertionError("Probe blocked caller");
        if (!complete.await(12, TimeUnit.SECONDS)) throw new AssertionError("Probe exceeded bound");
        var envelope = Wire.decodeReport(accepted.get()); ClientReport report = envelope.report();
        if (!nonce.equals(envelope.nonce()) || !first.equals(report.deviceId()) || !report.complete()) throw new AssertionError("Wire report fields");
        if (report.modIds().size() != 2 || !report.resourcePacks().equals(Collections.singletonList("vanilla"))) throw new AssertionError("Inventory corrupted");
        var reporter = new ClientReporter(); var mainThread = new LinkedBlockingQueue<Runnable>(); var newest = new AtomicReference<byte[]>();
        reporter.respond(Wire.encodeChallenge(nonce, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"), Collections.singletonList("minecraft"), Collections.emptyList(), directory, mainThread::add, newest::set);
        Runnable oldCallback = mainThread.poll(12, TimeUnit.SECONDS);
        if (oldCallback == null) throw new AssertionError("First generation callback missing");
        String latestNonce = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd";
        for (int i = 0; i < 20; i++) reporter.respond(Wire.encodeChallenge(i == 19 ? latestNonce : String.format("%064x", i), "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"), Collections.singletonList("minecraft"), Collections.emptyList(), directory, mainThread::add, newest::set);
        oldCallback.run(); if (newest.get() != null) throw new AssertionError("Superseded callback sent stale report");
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(12);
        while (newest.get() == null && System.nanoTime() < deadline) { Runnable action = mainThread.poll(1, TimeUnit.SECONDS); if (action != null) action.run(); }
        if (newest.get() == null || !latestNonce.equals(Wire.decodeReport(newest.get()).nonce())) throw new AssertionError("Rapid reloads failed to coalesce to latest nonce");
        System.out.println("PASS: stable scoped digest, scope separation, asynchronous probe, wire round trip, stale callback suppression, 20 rapid reloads coalesced; no identifiers printed");
    }
}
