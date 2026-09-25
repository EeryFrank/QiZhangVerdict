// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.minecraft.mixin;

import cn.qizhang.guard.minecraft.MinecraftGuard;
import com.mojang.brigadier.ParseResults;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.server.level.ServerPlayer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** 1.19.2 command dispatch, after network signature validation and before execution. */
@Mixin(Commands.class)
public abstract class CommandGate119Mixin {
    @Inject(method = "performCommand(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)I", at = @At("HEAD"), cancellable = true, require = 1)
    private void qizhangverdict$denyPendingCommand(ParseResults<CommandSourceStack> parsed, String command, CallbackInfoReturnable<Integer> callback) {
        if (parsed.getContext().getSource().getEntity() instanceof ServerPlayer player && MinecraftGuard.isWaiting(player))
            callback.setReturnValue(0);
    }
}
