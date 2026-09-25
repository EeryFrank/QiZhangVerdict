// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.bukkit;

import java.util.Objects;
import java.util.function.BooleanSupplier;
import java.util.function.Consumer;
import java.util.function.Supplier;

/** Runs on the server thread and resolves the pending challenge at execution time. */
final class PendingChallengeTask implements Runnable {
    private final Object owner;
    private final Supplier<?> currentOwner;
    private final BooleanSupplier online;
    private final Supplier<byte[]> pending;
    private final Consumer<byte[]> sender;

    PendingChallengeTask(Object owner, Supplier<?> currentOwner, BooleanSupplier online,
                         Supplier<byte[]> pending, Consumer<byte[]> sender) {
        this.owner = Objects.requireNonNull(owner);
        this.currentOwner = Objects.requireNonNull(currentOwner);
        this.online = Objects.requireNonNull(online);
        this.pending = Objects.requireNonNull(pending);
        this.sender = Objects.requireNonNull(sender);
    }

    @Override public void run() {
        if (currentOwner.get() != owner || !online.getAsBoolean()) return;
        byte[] challenge = pending.get();
        if (challenge != null) sender.accept(challenge);
    }
}
