// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge;

import io.netty.buffer.Unpooled;
import java.util.Arrays;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.network.ChannelBuilder;

/** Real EventNetworkChannel.encode plus the exact production raw-body helpers. */
public final class ForgePayloadSmoke {
    public static void main(String[] args) {
        var channel = ChannelBuilder.named(new ResourceLocation("qzguard", "payload_contract"))
            .networkProtocolVersion(2).optional().eventNetworkChannel();
        for (int length : new int[] {0, 1, 127, 30000}) {
            byte[] raw = new byte[length];
            for (int i = 0; i < length; i++) raw[i] = (byte) (i * 31);
            var outgoing = ForgeWire.outbound(raw);
            var encoded = new FriendlyByteBuf(Unpooled.buffer());
            try {
                channel.encode(encoded, outgoing);
                if (encoded.readableBytes() != length || !Arrays.equals(raw, ForgeWire.capture(encoded)))
                    throw new AssertionError("Forge channel changed raw wire bytes or added a prefix");
                if (encoded.readerIndex() != 0 || outgoing.readerIndex() != 0)
                    throw new AssertionError("Codec consumed a caller-owned buffer");
                byte[] captured = ForgeWire.capture(encoded);
                if (length != 0) { encoded.setByte(0, 99); if (captured[0] != raw[0]) throw new AssertionError("Input buffer ownership leaked"); }
            } finally { outgoing.release(); encoded.release(); }
        }
        var slice = new FriendlyByteBuf(Unpooled.wrappedBuffer(new byte[] {42, 1, 2}));
        try { slice.readerIndex(1); if (!Arrays.equals(ForgeWire.capture(slice), new byte[] {1, 2}) || slice.readerIndex() != 1) throw new AssertionError("Readable slice mismatch"); }
        finally { slice.release(); }
        byte[] mutable = {1}; var owned = ForgeWire.outbound(mutable); mutable[0] = 2;
        try { if (owned.getByte(0) != 1) throw new AssertionError("Outbound caller array retained"); }
        finally { owned.release(); }
        var oversized = new FriendlyByteBuf(Unpooled.wrappedBuffer(new byte[30001]));
        try {
            try { ForgeWire.capture(oversized); throw new AssertionError("Oversized input accepted"); }
            catch (IllegalArgumentException expected) { }
            if (oversized.readerIndex() != 0) throw new AssertionError("Oversized input consumed before rejection");
        } finally { oversized.release(); }
        try { ForgeWire.outbound(new byte[30001]); throw new AssertionError("Oversized output accepted"); }
        catch (IllegalArgumentException expected) { }
        try { ForgeWire.outbound(null); throw new AssertionError("Null output accepted"); }
        catch (NullPointerException expected) { }
        try { ForgeWire.capture(null); throw new AssertionError("Null input accepted"); }
        catch (NullPointerException expected) { }
        System.out.println("PASS: actual EventNetworkChannel raw round trips, 30000-byte bounds, readable slice and defensive buffer ownership");
    }
}
