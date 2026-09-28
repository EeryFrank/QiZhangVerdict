// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge;

import io.netty.buffer.Unpooled;
import java.util.Arrays;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.protocol.game.ClientboundCustomPayloadPacket;
import net.minecraft.network.protocol.game.ServerboundCustomPayloadPacket;
import net.minecraft.resources.ResourceLocation;

/** Actual vanilla packet writers used by the Forge 37 event-channel transport. */
public final class LegacyPayloadSmoke {
    public static void main(String[] args) {
        var channel = new ResourceLocation("qzguard", "main");
        for (int length : new int[] {0, 1, 127, 30000}) {
            byte[] raw = new byte[length];
            for (int i = 0; i < length; i++) raw[i] = (byte) (i * 31);
            for (boolean serverbound : new boolean[] {false, true}) {
                var outgoing = ForgeWire.outbound(raw);
                var encoded = new FriendlyByteBuf(Unpooled.buffer());
                try {
                    if (serverbound) new ServerboundCustomPayloadPacket(channel, outgoing).write(encoded);
                    else new ClientboundCustomPayloadPacket(channel, outgoing).write(encoded);
                    if (!channel.equals(encoded.readResourceLocation()) || encoded.readableBytes() != length
                            || !Arrays.equals(raw, ForgeWire.capture(encoded)))
                        throw new AssertionError("Vanilla custom payload added a raw-body prefix or changed bytes");
                    int position = encoded.readerIndex();
                    byte[] captured = ForgeWire.capture(encoded);
                    if (encoded.readerIndex() != position) throw new AssertionError("Capture consumed network buffer");
                    if (length != 0) {
                        encoded.setByte(position, 99);
                        if (captured[0] != raw[0]) throw new AssertionError("Input ownership leaked");
                    }
                } finally { outgoing.release(); encoded.release(); }
            }
        }
        var slice = new FriendlyByteBuf(Unpooled.wrappedBuffer(new byte[] {42, 1, 2}));
        try {
            slice.readerIndex(1);
            if (!Arrays.equals(ForgeWire.capture(slice), new byte[] {1, 2}) || slice.readerIndex() != 1)
                throw new AssertionError("Readable slice mismatch");
        } finally { slice.release(); }
        byte[] mutable = {1}; var owned = ForgeWire.outbound(mutable); mutable[0] = 2;
        try { if (owned.getByte(0) != 1) throw new AssertionError("Outbound caller array retained"); }
        finally { owned.release(); }
        var oversized = new FriendlyByteBuf(Unpooled.wrappedBuffer(new byte[30001]));
        try {
            try { ForgeWire.capture(oversized); throw new AssertionError("Oversized input accepted"); }
            catch (IllegalArgumentException expected) { }
            if (oversized.readerIndex() != 0) throw new AssertionError("Oversized input consumed");
        } finally { oversized.release(); }
        try { ForgeWire.outbound(new byte[30001]); throw new AssertionError("Oversized output accepted"); }
        catch (IllegalArgumentException expected) { }
        try { ForgeWire.outbound(null); throw new AssertionError("Null output accepted"); }
        catch (NullPointerException expected) { }
        try { ForgeWire.capture(null); throw new AssertionError("Null input accepted"); }
        catch (NullPointerException expected) { }
        System.out.println("PASS: eight actual legacy custom-payload writes, 30000-byte bounds, readable slice and defensive ownership");
    }
}
