// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.fabric;

import java.util.ArrayDeque;
import java.util.concurrent.atomic.AtomicInteger;

/** Calls the exact helper used by network callbacks and delayed reporter replies. */
public final class ConnectionDispatchSmoke {
    private static int count;
    private static void check(boolean condition, String name) {
        if (!condition) throw new AssertionError(name);
        System.out.println("PASS fabric-connection-dispatch " + (++count) + ": " + name);
    }
    public static void main(String[] args) {
        Object connection = new Object(), listener = new Object();
        Object[] current = {null, null, null}; boolean[] state = {true, true};
        var queue = new ArrayDeque<Runnable>(); var calls = new AtomicInteger();
        Runnable enqueue = () -> ConnectionDispatch.enqueue(queue::add, connection, listener,
            () -> current[0], () -> current[1], () -> current[2], () -> state[0], () -> state[1], calls::incrementAndGet);
        enqueue.run(); check(calls.get() == 0 && queue.size() == 1, "queues before inspecting current login state");
        current[0] = connection; current[1] = listener; current[2] = listener; queue.remove().run();
        check(calls.get() == 1, "queued login accepts original live PLAY listener");
        enqueue.run(); current[0] = new Object(); queue.remove().run();
        check(calls.get() == 1, "server switch rejects old transport");
        current[0] = connection; enqueue.run(); current[1] = new Object(); queue.remove().run();
        check(calls.get() == 1, "same transport with replaced listener is rejected");
        current[1] = listener; enqueue.run(); current[2] = new Object(); queue.remove().run();
        check(calls.get() == 1, "retained local listener cannot hide replacement on the transport");
        current[2] = listener;
        current[1] = listener; enqueue.run(); state[0] = false; queue.remove().run();
        check(calls.get() == 1, "closed transport is rejected even when objects remain");
        state[0] = true; enqueue.run(); state[1] = false; queue.remove().run();
        check(calls.get() == 1, "non-PLAY listener rejects queued PLAY payload");
        state[1] = true; enqueue.run(); current[1] = null; queue.remove().run();
        check(calls.get() == 1, "disconnected listener cannot receive queued payload");
        current[1] = listener; enqueue.run(); queue.remove().run();
        check(calls.get() == 2, "new challenge on same valid connection still works");
        ConnectionDispatch.enqueue(queue::add, null, listener, () -> connection, () -> listener, () -> listener, () -> true, () -> true, calls::incrementAndGet);
        ConnectionDispatch.enqueue(queue::add, connection, null, () -> connection, () -> listener, () -> listener, () -> true, () -> true, calls::incrementAndGet);
        check(queue.isEmpty(), "null origins are never queued");
        Object left = new String("equal"), right = new String("equal");
        check(!ConnectionDispatch.current(left, listener, right, listener, listener, true, true), "connection comparison uses identity not equals");
        check(!ConnectionDispatch.current(connection, left, connection, right, left, true, true), "listener comparison uses identity not equals");
        check(!ConnectionDispatch.current(connection, listener, connection, listener, listener, false, true), "delayed response cannot use closed connection");
        check(!ConnectionDispatch.current(connection, listener, connection, listener, listener, true, false), "delayed response cannot use non-PLAY phase");
        check(ConnectionDispatch.current(connection, listener, connection, listener, listener, true, true), "delayed response may use exact live PLAY origin");
        System.out.println("PASS fabric-connection-dispatch total=" + count);
    }
}
