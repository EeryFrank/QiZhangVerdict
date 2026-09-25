// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.minecraft;

import java.util.Objects;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;

/** The Bukkit-compatible wire bytes, without a second length prefix. */
public record GuardPayload(byte[] data) implements CustomPacketPayload {
    private static final int MAX_BYTES = 30000;
    public static final Type<GuardPayload> TYPE = new Type<>(Identifier.fromNamespaceAndPath("qzguard", "main"));
    public static final StreamCodec<RegistryFriendlyByteBuf, GuardPayload> CODEC = new StreamCodec<>() {
        @Override
        public GuardPayload decode(RegistryFriendlyByteBuf buffer) {
            int size = buffer.readableBytes();
            if (size > MAX_BYTES) throw new IllegalArgumentException("QiZhangVerdict payload exceeds 30000 bytes");
            byte[] bytes = new byte[size];
            buffer.readBytes(bytes);
            return new GuardPayload(bytes);
        }

        @Override
        public void encode(RegistryFriendlyByteBuf buffer, GuardPayload value) {
            buffer.writeBytes(value.data);
        }
    };

    public GuardPayload {
        Objects.requireNonNull(data, "data");
        if (data.length > MAX_BYTES) throw new IllegalArgumentException("QiZhangVerdict payload exceeds 30000 bytes");
        data = data.clone();
    }

    @Override
    public byte[] data() { return data.clone(); }

    @Override
    public Type<GuardPayload> type() { return TYPE; }
}
