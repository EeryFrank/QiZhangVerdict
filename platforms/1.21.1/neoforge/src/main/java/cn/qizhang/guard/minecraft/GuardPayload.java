package cn.qizhang.guard.minecraft;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;
public record GuardPayload(byte[] data) implements CustomPacketPayload {
 public static final Type<GuardPayload> TYPE = new Type<>(ResourceLocation.fromNamespaceAndPath("qzguard", "main"));
 public static final StreamCodec<RegistryFriendlyByteBuf, GuardPayload> CODEC = new StreamCodec<>() {
  public GuardPayload decode(RegistryFriendlyByteBuf buffer) { int length=buffer.readableBytes(); if(length > 30000) throw new IllegalArgumentException("QiZhangVerdict payload too large"); byte[] data=new byte[length]; buffer.readBytes(data); return new GuardPayload(data); }
  public void encode(RegistryFriendlyByteBuf buffer, GuardPayload payload) { if(payload.data.length > 30000) throw new IllegalArgumentException("QiZhangVerdict payload too large"); buffer.writeBytes(payload.data); }
 };
 public Type<? extends CustomPacketPayload> type() { return TYPE; }
}
