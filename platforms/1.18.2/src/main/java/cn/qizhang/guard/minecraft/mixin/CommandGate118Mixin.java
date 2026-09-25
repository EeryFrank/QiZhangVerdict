package cn.qizhang.guard.minecraft.mixin;

import cn.qizhang.guard.minecraft.MinecraftGuard;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.server.level.ServerPlayer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** 1.18.2 dispatch takes the source before parsing. Gate every pending player's command, including OPs. */
@Mixin(Commands.class)
public abstract class CommandGate118Mixin {
    @Inject(method = "performCommand(Lnet/minecraft/commands/CommandSourceStack;Ljava/lang/String;)I",
            at = @At("HEAD"), cancellable = true, require = 1)
    private void qizhangverdict$denyPendingCommand(CommandSourceStack source, String command,
                                                   CallbackInfoReturnable<Integer> callback) {
        if (source.getEntity() instanceof ServerPlayer player && MinecraftGuard.isWaiting(player))
            callback.setReturnValue(0);
    }
}
