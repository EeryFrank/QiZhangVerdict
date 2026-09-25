package cn.qizhang.guard.forge112;

import cn.qizhang.guard.minecraft.MinecraftGuard;
import java.util.function.Supplier;
import net.minecraft.command.CommandBase;
import net.minecraft.command.CommandException;
import net.minecraft.command.ICommandSender;
import net.minecraft.server.MinecraftServer;
import net.minecraft.util.text.TextComponentString;

public final class LegacyGuardCommand extends CommandBase {
    private final Supplier<MinecraftGuard> guard;
    public LegacyGuardCommand(Supplier<MinecraftGuard> guard) { this.guard = guard; }
    @Override public String getName() { return "qzverdict"; }
    @Override public String getUsage(ICommandSender sender) { return "/qzverdict status|reload|rule|ban|unban|bans"; }
    @Override public int getRequiredPermissionLevel() { return 3; }
    @Override public void execute(MinecraftServer server, ICommandSender sender, String[] args) throws CommandException {
        final LegacyCommandParser.Action action;
        try { action = LegacyCommandParser.parse(args); }
        catch (IllegalArgumentException invalid) { throw new CommandException(invalid.getMessage()); }
        MinecraftGuard active = guard.get();
        if (active == null) throw new CommandException("QiZhangVerdict is unavailable");
        if ("status".equals(action.operation)) sender.sendMessage(new TextComponentString(active.status()));
        else active.admin(server, action.operation, action.arguments, result -> sender.sendMessage(new TextComponentString(result)));
    }
}
