// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge189;

import cn.qizhang.guard.minecraft.MinecraftGuard;
import java.util.function.Supplier;
import net.minecraft.command.CommandBase;
import net.minecraft.command.CommandException;
import net.minecraft.command.ICommandSender;
import net.minecraft.server.MinecraftServer;
import net.minecraft.util.ChatComponentText;

/** Native 1.8 CommandBase signatures; policy and parameter parsing stay shared with the old adapter. */
public final class LegacyGuardCommand extends CommandBase {
    private final Supplier<MinecraftGuard> guard;
    public LegacyGuardCommand(Supplier<MinecraftGuard> guard) { this.guard = guard; }
    @Override public String getCommandName() { return "qzverdict"; }
    @Override public String getCommandUsage(ICommandSender sender) { return "/qzverdict status|reload|rule|ban|unban|bans"; }
    @Override public int getRequiredPermissionLevel() { return 3; }
    @Override public void processCommand(ICommandSender sender, String[] args) throws CommandException {
        final LegacyCommandParser.Action action;
        try { action = LegacyCommandParser.parse(args); }
        catch (IllegalArgumentException invalid) { throw new CommandException(invalid.getMessage()); }
        MinecraftGuard active = guard.get();
        MinecraftServer server = net.minecraftforge.fml.common.FMLCommonHandler.instance().getMinecraftServerInstance();
        if (active == null || server == null) throw new CommandException("QiZhangVerdict is unavailable");
        if ("status".equals(action.operation)) sender.addChatMessage(new ChatComponentText(active.status()));
        else active.admin(server, action.operation, action.arguments, result -> sender.addChatMessage(new ChatComponentText(result)));
    }
}
