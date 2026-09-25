// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.neoforge;

import java.util.concurrent.Executor;
import java.util.function.Supplier;

/** Compare connection identity after the queued login work has run. */
final class ClientChallengeDispatch {
    private ClientChallengeDispatch() { }
    static void enqueue(Executor mainThread, Object originConnection, Supplier<?> currentConnection, Runnable receive) {
        if (originConnection == null) return;
        mainThread.execute(() -> {
            if (currentConnection.get() == originConnection) receive.run();
        });
    }
}
