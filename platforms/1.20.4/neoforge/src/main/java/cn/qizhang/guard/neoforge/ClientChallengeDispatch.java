// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.neoforge;

import java.util.concurrent.Executor;
import java.util.function.Supplier;

/** Schedules a challenge after earlier login work, preserving its connection identity. */
final class ClientChallengeDispatch {
    private ClientChallengeDispatch() {}

    static void enqueue(Executor mainThread, Object originChannel, Supplier<?> currentChannel, Runnable receive) {
        if (originChannel == null) return;
        mainThread.execute(() -> {
            if (currentChannel.get() == originChannel) receive.run();
        });
    }
}
