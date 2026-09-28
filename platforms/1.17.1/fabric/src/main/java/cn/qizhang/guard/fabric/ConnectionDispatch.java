// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.fabric;

import java.util.concurrent.Executor;
import java.util.function.BooleanSupplier;
import java.util.function.Supplier;

/** Identity checks used by the real network receive path and asynchronous client response. */
final class ConnectionDispatch {
    private ConnectionDispatch() { }

    static boolean current(Object originConnection, Object originListener,
                           Object currentConnection, Object currentListener, Object transportListener,
                           boolean connected, boolean play) {
        return connected && play && originConnection != null && originListener != null
            && originConnection == currentConnection && originListener == currentListener
            && originListener == transportListener;
    }

    static void enqueue(Executor mainThread, Object originConnection, Object originListener,
                        Supplier<?> currentConnection, Supplier<?> currentListener, Supplier<?> transportListener,
                        BooleanSupplier connected, BooleanSupplier play, Runnable receive) {
        if (originConnection == null || originListener == null) return;
        mainThread.execute(() -> {
            if (current(originConnection, originListener, currentConnection.get(), currentListener.get(), transportListener.get(),
                    connected.getAsBoolean(), play.getAsBoolean())) receive.run();
        });
    }
}
