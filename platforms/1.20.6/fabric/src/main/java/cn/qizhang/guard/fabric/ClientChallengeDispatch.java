// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.fabric;

import java.util.concurrent.Executor;
import java.util.function.Supplier;

/** Connection checks shared by the actual receive path and its focused regression test. */
final class ClientChallengeDispatch {
    private ClientChallengeDispatch() {}

    static void enqueue(Executor mainThread, Object originSender, Supplier<?> liveSender, Runnable receive) {
        if (originSender == null) return;
        mainThread.execute(() -> {
            if (liveSender.get() == originSender) receive.run();
        });
    }

    static boolean isCurrentConnection(Object originSender, Object originConnection,
                                       Object currentSender, Object currentConnection, boolean connected) {
        return connected && originSender != null && originConnection != null
            && originSender == currentSender && originConnection == currentConnection;
    }
}
