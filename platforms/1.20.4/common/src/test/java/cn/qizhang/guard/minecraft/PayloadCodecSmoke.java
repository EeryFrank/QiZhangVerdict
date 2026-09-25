// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.minecraft;

import io.netty.buffer.Unpooled;
import java.util.Arrays;
import net.minecraft.network.FriendlyByteBuf;

public final class PayloadCodecSmoke {
    public static void main(String[] arguments) {
        for (int length : new int[] {0, 1, 127, 30000}) {
            byte[] raw = new byte[length];
            for (int i = 0; i < raw.length; i++) raw[i] = (byte) (i * 31);
            FriendlyByteBuf buffer = new FriendlyByteBuf(Unpooled.buffer());
            try {
                new GuardPayload(raw).write(buffer);
                if (buffer.readableBytes() != raw.length) throw new AssertionError("Unexpected length prefix");
                byte[] written = new byte[length]; buffer.getBytes(buffer.readerIndex(), written);
                if (!Arrays.equals(raw, written)) throw new AssertionError("Bukkit wire compatibility");
                if (!Arrays.equals(raw, GuardPayload.read(buffer).data()) || buffer.isReadable()) throw new AssertionError("Round trip");
            } finally { buffer.release(); }
        }
        try { new GuardPayload(new byte[30001]); throw new AssertionError("Oversized local payload accepted"); }
        catch (IllegalArgumentException expected) { }
        FriendlyByteBuf oversized = new FriendlyByteBuf(Unpooled.wrappedBuffer(new byte[30001]));
        try {
            int before = oversized.readerIndex();
            try { GuardPayload.read(oversized); throw new AssertionError("Oversized remote payload accepted"); }
            catch (IllegalArgumentException expected) { }
            if (oversized.readerIndex() != before) throw new AssertionError("Read oversized payload before rejecting");
        } finally { oversized.release(); }
        byte[] mutable = {1}; GuardPayload owned = new GuardPayload(mutable); mutable[0] = 2;
        if (owned.data()[0] != 1) throw new AssertionError("Payload retained mutable caller array");
        System.out.println("PASS: raw wire round trips, outbound/inbound bounds and caller-array ownership");
    }
}
