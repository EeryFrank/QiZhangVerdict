// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge;

import io.netty.buffer.Unpooled;
import java.util.Objects;
import net.minecraft.network.FriendlyByteBuf;

/** Raw EventNetworkChannel body. No discriminator or extra length prefix. */
final class ForgeWire {
    static final int MAX_BYTES = 30_000;
    private ForgeWire() { }

    /** Copy the readable slice while Forge still owns the incoming network buffer. */
    static byte[] capture(FriendlyByteBuf source) {
        Objects.requireNonNull(source, "source");
        int size = source.readableBytes();
        if (size > MAX_BYTES) throw new IllegalArgumentException("QiZhangVerdict payload too large");
        byte[] result = new byte[size];
        source.getBytes(source.readerIndex(), result);
        return result;
    }

    /** The packet may encode later on Netty's thread; do not retain the caller's mutable array. */
    static FriendlyByteBuf outbound(byte[] source) {
        Objects.requireNonNull(source, "source");
        if (source.length > MAX_BYTES) throw new IllegalArgumentException("QiZhangVerdict payload too large");
        return new FriendlyByteBuf(Unpooled.wrappedBuffer(source.clone()));
    }
}
