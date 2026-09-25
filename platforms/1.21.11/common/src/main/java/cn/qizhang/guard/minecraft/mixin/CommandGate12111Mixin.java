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
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** 1.21.11 player command dispatch remains blocked during companion isolation, including operators. */
@Mixin(Commands.class)
public abstract class CommandGate12111Mixin {
    @Inject(method = "performCommand(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)V",
            at = @At("HEAD"), cancellable = true, require = 1)
    private void qizhangverdict$denyPendingCommand(ParseResults<CommandSourceStack> parsed,
            String command, CallbackInfo callback) {
        if (parsed.getContext().getSource().getEntity() instanceof ServerPlayer player
                && MinecraftGuard.isWaiting(player)) callback.cancel();
    }
}
