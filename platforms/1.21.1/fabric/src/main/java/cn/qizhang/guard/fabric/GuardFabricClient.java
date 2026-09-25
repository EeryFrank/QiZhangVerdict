package cn.qizhang.guard.fabric;

import cn.qizhang.guard.client.ClientReporter;
import cn.qizhang.guard.minecraft.GuardPayload;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.loader.api.FabricLoader;
import java.util.List;

public final class GuardFabricClient implements ClientModInitializer {
    private final ClientReporter reporter = new ClientReporter();
    @Override public void onInitializeClient() {
        ClientPlayNetworking.registerGlobalReceiver(GuardPayload.TYPE, (payload, context) -> {
            var client = context.client(); var connection = client.getConnection();
            if (client.player != context.player()) return;
            List<String> mods = FabricLoader.getInstance().getAllMods().stream().map(mod -> mod.getMetadata().getId()).sorted().toList();
            List<String> packs = client.getResourcePackRepository().getSelectedPacks().stream().map(pack -> pack.getId()).toList();
            reporter.respond(payload.data(), mods, packs, FabricLoader.getInstance().getConfigDir().resolve("qizhangverdict"), client::execute, response -> {
                if (client.getConnection() == connection && connection != null) ClientPlayNetworking.send(new GuardPayload(response));
            });
        });
    }
}
