package cn.qizhang.guard.fabric;

import cn.qizhang.guard.client.ClientReporter;
import io.netty.buffer.Unpooled;
import java.util.List;
import java.util.stream.Collectors;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.network.FriendlyByteBuf;

/** GPL-3.0-only. Snapshot inventory on the client thread and retain connection ownership. */
public final class GuardFabricClient implements ClientModInitializer {
    private final ClientReporter reporter = new ClientReporter();
    @Override public void onInitializeClient() {
        ClientPlayNetworking.registerGlobalReceiver(GuardFabric.CHANNEL, (client, handler, buffer, sender) -> {
            if (buffer.readableBytes() > 30000) return;
            byte[] bytes = new byte[buffer.readableBytes()]; buffer.readBytes(bytes);
            client.execute(() -> {
                if (client.getConnection() != handler) return;
                final ClientPacketListener connection = handler;
                List<String> mods = FabricLoader.getInstance().getAllMods().stream()
                        .map(mod -> mod.getMetadata().getId()).sorted().collect(Collectors.toList());
                List<String> packs = client.getResourcePackRepository().getSelectedPacks().stream()
                        .map(pack -> pack.getId()).collect(Collectors.toList());
                reporter.respond(bytes, mods, packs, FabricLoader.getInstance().getConfigDir().resolve("qizhangverdict"),
                        client::execute, response -> {
                    if (client.getConnection() == connection && connection != null)
                        ClientPlayNetworking.send(GuardFabric.CHANNEL, new FriendlyByteBuf(Unpooled.wrappedBuffer(response)));
                });
            });
        });
    }
}
