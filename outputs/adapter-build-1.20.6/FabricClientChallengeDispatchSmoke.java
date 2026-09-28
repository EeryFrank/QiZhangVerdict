// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.fabric;

import java.util.ArrayDeque;
import java.util.Queue;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/** Pure callback-ownership checks; this does not claim an actual Fabric connection test. */
public final class ClientChallengeDispatchSmoke {
    private static int checks;
    private static void check(String name, boolean value) {
        if (!value) throw new AssertionError(name);
        System.out.println("PASS fabric-client-dispatch " + (++checks) + ": " + name);
    }
    private static void drain(Queue<Runnable> queue) { while (!queue.isEmpty()) queue.remove().run(); }

    public static void main(String[] args) {
        Queue<Runnable> main = new ArrayDeque<>();
        Object original = new Object();
        AtomicReference<Object> sender = new AtomicReference<>();
        AtomicInteger received = new AtomicInteger();
        main.add(() -> sender.set(original));
        ClientChallengeDispatch.enqueue(main::add, original, sender::get, received::incrementAndGet);
        check("receive defers inspection until queued login work", received.get() == 0 && sender.get() == null);
        drain(main);
        check("original sender receives after login", received.get() == 1);

        ClientChallengeDispatch.enqueue(main::add, original, sender::get, received::incrementAndGet);
        sender.set(new Object()); drain(main);
        check("switching servers discards old challenge", received.get() == 1);
        sender.set(original);
        ClientChallengeDispatch.enqueue(main::add, original, sender::get, received::incrementAndGet);
        sender.set(null); drain(main);
        check("disconnect discards queued challenge", received.get() == 1);

        sender.set(original);
        AtomicBoolean open = new AtomicBoolean(true);
        ClientChallengeDispatch.enqueue(main::add, original, () -> open.get() ? sender.get() : null, received::incrementAndGet);
        open.set(false); drain(main);
        check("closed transport is excluded even with retained sender", received.get() == 1 && sender.get() == original);
        ClientChallengeDispatch.enqueue(main::add, null, sender::get, received::incrementAndGet);
        check("null origin never queues a receive", main.isEmpty());
        Object equalButDifferent = new Object() { @Override public boolean equals(Object other) { return true; } };
        ClientChallengeDispatch.enqueue(main::add, equalButDifferent, sender::get, received::incrementAndGet);
        drain(main);
        check("origin comparison uses identity", received.get() == 1);

        Object connection = new Object();
        check("response allowed only for original live listener and sender",
            ClientChallengeDispatch.isCurrentConnection(original, connection, original, connection, true));
        check("changed response sender rejected",
            !ClientChallengeDispatch.isCurrentConnection(original, connection, new Object(), connection, true));
        check("changed response listener rejected",
            !ClientChallengeDispatch.isCurrentConnection(original, connection, original, new Object(), true));
        check("closed response transport rejected",
            !ClientChallengeDispatch.isCurrentConnection(original, connection, original, connection, false));
        check("null origin listener cannot match disconnected client",
            !ClientChallengeDispatch.isCurrentConnection(original, null, original, null, true));
        System.out.println("PASS fabric-client-dispatch total=" + checks);
    }
}
