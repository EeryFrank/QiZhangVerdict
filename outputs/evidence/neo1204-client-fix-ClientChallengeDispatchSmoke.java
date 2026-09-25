// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.neoforge;

import java.util.ArrayDeque;
import java.util.Optional;
import java.util.Queue;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.atomic.AtomicBoolean;

/** Exercises the production dispatcher called by GuardNeoForgeClient.receive. */
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

        // Negative control: NeoForge's player Optional is a network-time snapshot.
        Optional<Object> networkTimePlayer = Optional.ofNullable(player.get());
        main.add(() -> { connection.set(original); player.set(new Object()); });
        main.add(() -> networkTimePlayer.ifPresent(ignored -> received.incrementAndGet()));
        drain(main);
        check("old snapshot drops initial challenge despite completed queued login", received.get() == 0 && player.get() != null);

        connection.set(null); player.set(null);
        main.add(() -> { connection.set(original); player.set(new Object()); });
        ClientChallengeDispatch.enqueue(main::add, original, () -> {
            if (player.get() == null) throw new AssertionError("connection inspected before queued login");
            return connection.get();
        }, received::incrementAndGet);
        check("production entry queues without reading network-time player or connection", received.get() == 0 && player.get() == null);
        drain(main);
        check("production entry receives challenge after login on its original connection", received.get() == 1);

        ClientChallengeDispatch.enqueue(main::add, original, connection::get, received::incrementAndGet);
        connection.set(new Object()); drain(main);
        check("connection switched before queued work discards previous challenge", received.get() == 1);

        connection.set(original);
        ClientChallengeDispatch.enqueue(main::add, original, connection::get, received::incrementAndGet);
        connection.set(null); drain(main);
        check("disconnected client discards queued challenge", received.get() == 1);

        // Model the production supplier's isConnected gate: a closed connection
        // can retain its listener/channel object until a later client tick.
        connection.set(original);
        AtomicBoolean connected = new AtomicBoolean(true);
        ClientChallengeDispatch.enqueue(main::add, original,
            () -> connected.get() ? connection.get() : null, received::incrementAndGet);
        connected.set(false); drain(main);
        check("supplier excludes closed connection even while original object remains", received.get() == 1 && connection.get() == original);

        ClientChallengeDispatch.enqueue(main::add, null, connection::get, received::incrementAndGet);
        check("null origin cannot match a missing current connection", main.isEmpty() && received.get() == 1);

        Object equalButDistinct = new Object() { @Override public boolean equals(Object other) { return true; } };
        ClientChallengeDispatch.enqueue(main::add, equalButDistinct, () -> original, received::incrementAndGet);
        drain(main);
        check("connection comparison uses identity, not equals", received.get() == 1);

        connection.set(original);
        ClientChallengeDispatch.enqueue(main::add, original, connection::get, received::incrementAndGet);
        drain(main);
        check("subsequent same-connection challenge remains supported", received.get() == 2);
        System.out.println("PASS client-dispatch total=" + checks);
    }
}
