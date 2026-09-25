package cn.qizhang.guard.fabric;

import cn.qizhang.guard.client.ClientReporter;
import net.minecraft.network.FriendlyByteBuf;
import io.netty.buffer.Unpooled;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.loader.api.FabricLoader;
import java.util.List;

public final class GuardFabricClient implements ClientModInitializer {
    private final ClientReporter reporter = new ClientReporter();
    @Override public void onInitializeClient() {
        ClientPlayNetworking.registerGlobalReceiver(GuardFabric.CHANNEL, (client, handler, buffer, sender) -> {
            if (buffer.readableBytes() > 30000) return;
            byte[] data = new byte[buffer.readableBytes()]; buffer.readBytes(data);
            client.execute(() -> {
            if (client.getConnection() != handler) return;
            var connection = handler;
            List<String> mods = FabricLoader.getInstance().getAllMods().stream().map(mod -> mod.getMetadata().getId()).sorted().toList();
            List<String> packs = client.getResourcePackRepository().getSelectedPacks().stream().map(pack -> pack.getId()).toList();
            reporter.respond(data, mods, packs, FabricLoader.getInstance().getConfigDir().resolve("qizhangverdict"), client::execute, response -> {
                if (client.getConnection() == connection && connection != null) ClientPlayNetworking.send(GuardFabric.CHANNEL, new FriendlyByteBuf(Unpooled.wrappedBuffer(response)));
            });
            });
        });
    }
}
