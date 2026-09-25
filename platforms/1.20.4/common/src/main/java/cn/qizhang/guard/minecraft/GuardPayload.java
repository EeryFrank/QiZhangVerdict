// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.minecraft;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;

/** Raw payload body remains compatible with the Bukkit qzguard:main channel. */
public record GuardPayload(byte[] data) implements CustomPacketPayload {
    public static final ResourceLocation ID = new ResourceLocation("qzguard", "main");
    public GuardPayload {
        if (data == null || data.length > 30000) throw new IllegalArgumentException("QiZhangVerdict payload too large or null");
        data = data.clone();
    }
    public static GuardPayload read(FriendlyByteBuf buffer) {
        int length = buffer.readableBytes();
        if (length > 30000) throw new IllegalArgumentException("QiZhangVerdict payload too large");
        byte[] data = new byte[length]; buffer.readBytes(data);
        return new GuardPayload(data);
    }
    @Override public ResourceLocation id() { return ID; }
    @Override public void write(FriendlyByteBuf buffer) { buffer.writeBytes(data); }
}
