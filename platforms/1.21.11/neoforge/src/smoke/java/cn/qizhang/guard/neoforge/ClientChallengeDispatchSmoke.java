// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.neoforge;

import java.util.ArrayDeque;
import java.util.Queue;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/** Tests the production dispatcher with a controlled game-thread queue, not a real client. */
public final class ClientChallengeDispatchSmoke {
    private static int checks;
    private static void check(String name, boolean value) {
        if (!value) throw new AssertionError(name);
        System.out.println("PASS client-dispatch " + (++checks) + ": " + name);
    }
    private static void drain(Queue<Runnable> queue) { while (!queue.isEmpty()) queue.remove().run(); }

    public static void main(String[] args) {
        Queue<Runnable> main = new ArrayDeque<>();
        Object original = new Object();
        AtomicReference<Object> connection = new AtomicReference<>();
        AtomicReference<Object> player = new AtomicReference<>();
        AtomicInteger received = new AtomicInteger();

        main.add(() -> { connection.set(original); player.set(new Object()); });
        ClientChallengeDispatch.enqueue(main::add, original, () -> {
            if (player.get() == null) throw new AssertionError("connection inspected before queued login");
            return connection.get();
        }, received::incrementAndGet);
        check("queues without inspecting pre-login state", received.get() == 0 && player.get() == null);
        drain(main);
        check("receives challenge after queued login on original connection", received.get() == 1);

        ClientChallengeDispatch.enqueue(main::add, original, connection::get, received::incrementAndGet);
        connection.set(new Object()); drain(main);
        check("switched connection discards old challenge", received.get() == 1);

        connection.set(original);
        ClientChallengeDispatch.enqueue(main::add, original, connection::get, received::incrementAndGet);
        connection.set(null); drain(main);
        check("disconnected listener discards queued challenge", received.get() == 1);

        connection.set(original);
        AtomicBoolean connected = new AtomicBoolean(true);
        ClientChallengeDispatch.enqueue(main::add, original,
            () -> connected.get() ? connection.get() : null, received::incrementAndGet);
        connected.set(false); drain(main);
        check("supplier excludes closed connection while object remains", received.get() == 1 && connection.get() == original);

        ClientChallengeDispatch.enqueue(main::add, null, connection::get, received::incrementAndGet);
        check("null origin cannot match a missing current connection", main.isEmpty() && received.get() == 1);

        Object equalButDistinct = new Object() { @Override public boolean equals(Object other) { return true; } };
        ClientChallengeDispatch.enqueue(main::add, equalButDistinct, () -> original, received::incrementAndGet);
        drain(main);
        check("comparison uses identity rather than equals", received.get() == 1);

        connection.set(original);
        ClientChallengeDispatch.enqueue(main::add, original, connection::get, received::incrementAndGet);
        drain(main);
        check("next challenge on same live connection remains supported", received.get() == 2);

        Object replacement = new Object();
        AtomicInteger oldDelivered = new AtomicInteger();
        AtomicInteger newDelivered = new AtomicInteger();
        ClientChallengeDispatch.enqueue(main::add, original, connection::get, oldDelivered::incrementAndGet);
        main.add(() -> connection.set(replacement));
        ClientChallengeDispatch.enqueue(main::add, replacement, connection::get, newDelivered::incrementAndGet);
        connection.set(replacement);
        drain(main);
        check("reconnect drops obsolete queued work and accepts new origin", oldDelivered.get() == 0 && newDelivered.get() == 1);
        System.out.println("PASS client-dispatch total=" + checks);
    }
}
