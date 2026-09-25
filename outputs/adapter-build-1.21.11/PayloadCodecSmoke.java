// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.minecraft;

import io.netty.buffer.Unpooled;
import java.util.Arrays;
import net.minecraft.core.RegistryAccess;
import net.minecraft.network.RegistryFriendlyByteBuf;

/** Exercises the production stream codec, including Bukkit's unprefixed wire representation. */
public final class PayloadCodecSmoke {
    public static void main(String[] arguments) {
        for (int length : new int[] {0, 1, 127, 30000}) {
            byte[] raw = new byte[length];
            for (int i = 0; i < raw.length; i++) raw[i] = (byte) (i * 31);
            var buffer = new RegistryFriendlyByteBuf(Unpooled.buffer(), RegistryAccess.EMPTY);
            try {
                GuardPayload.CODEC.encode(buffer, new GuardPayload(raw));
                if (buffer.readableBytes() != raw.length) throw new AssertionError("Unexpected wire length prefix");
                byte[] written = new byte[length]; buffer.getBytes(buffer.readerIndex(), written);
                if (!Arrays.equals(raw, written)) throw new AssertionError("Bukkit wire bytes changed");
                if (!Arrays.equals(raw, GuardPayload.CODEC.decode(buffer).data()) || buffer.isReadable())
                    throw new AssertionError("Round trip failed");
            } finally { buffer.release(); }
        }
        try { new GuardPayload(new byte[30001]); throw new AssertionError("Oversized local payload accepted"); }
        catch (IllegalArgumentException expected) { }
        var oversized = new RegistryFriendlyByteBuf(Unpooled.wrappedBuffer(new byte[30001]), RegistryAccess.EMPTY);
        try {
            int before = oversized.readerIndex();
            try { GuardPayload.CODEC.decode(oversized); throw new AssertionError("Oversized remote payload accepted"); }
            catch (IllegalArgumentException expected) { }
            if (oversized.readerIndex() != before) throw new AssertionError("Read remote payload before rejecting size");
        } finally { oversized.release(); }
        byte[] mutable = {1}; GuardPayload owned = new GuardPayload(mutable); mutable[0] = 2;
        if (owned.data()[0] != 1) throw new AssertionError("Caller array retained");
        byte[] exposed = owned.data(); exposed[0] = 3;
        if (owned.data()[0] != 1) throw new AssertionError("Accessor exposes internal array");
        System.out.println("PASS: four raw wire round trips, inbound/outbound bounds and defensive array ownership");
    }
}
