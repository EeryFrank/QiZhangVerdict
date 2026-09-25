// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.minecraft;

import java.util.Objects;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;

/** Raw qzguard:main bytes; no inner length prefix, matching the Bukkit transport. */
public record GuardPayload(byte[] data) implements CustomPacketPayload {
    public static final int MAX_BYTES = 30_000;
    public static final Type<GuardPayload> TYPE = new Type<>(Identifier.fromNamespaceAndPath("qzguard", "main"));

    public GuardPayload {
        Objects.requireNonNull(data, "data");
        if (data.length > MAX_BYTES) throw new IllegalArgumentException("QiZhangVerdict payload too large");
        data = data.clone();
    }

    @Override public byte[] data() { return data.clone(); }

    public static final StreamCodec<RegistryFriendlyByteBuf, GuardPayload> CODEC = new StreamCodec<>() {
        @Override public GuardPayload decode(RegistryFriendlyByteBuf buffer) {
            int length = buffer.readableBytes();
            if (length > MAX_BYTES) throw new IllegalArgumentException("QiZhangVerdict payload too large");
            byte[] data = new byte[length];
            buffer.readBytes(data);
            return new GuardPayload(data);
        }

        @Override public void encode(RegistryFriendlyByteBuf buffer, GuardPayload payload) {
            buffer.writeBytes(payload.data);
        }
    };

    @Override public Type<? extends CustomPacketPayload> type() { return TYPE; }
}
