package cn.qizhang.guard.minecraft;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.CommandSource;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;
import net.minecraft.world.phys.Vec2;
import net.minecraft.world.phys.Vec3;

/** Parses the actual registered command tree with the actual Brigadier implementation. */
public final class CommandParserSmoke {
    public static void main(String[] args) {
        var dispatcher = new CommandDispatcher<CommandSourceStack>();
        GuardCommands.register(dispatcher, () -> null);
        var admin = source(4);
        String device = "device:" + "a".repeat(64);
        parse(dispatcher, admin, "qzverdict unban " + device, "uuid-or-device", device);
        parse(dispatcher, admin, "qzverdict rule remove legacy:mod:baritone", "id", "legacy:mod:baritone");
        parse(dispatcher, admin, "qzverdict rule add BLACK PACK GLOB *X Ray*.zip", "value", "*X Ray*.zip");
        parse(dispatcher, admin, "qzverdict ban VerdictClient Grim reach violation", "reason", "Grim reach violation");
        parse(dispatcher, admin, "qzverdict ban 86f10d93-6a7a-3707-bf5f-b5decc1e46a7", "uuid", "86f10d93-6a7a-3707-bf5f-b5decc1e46a7");
        if (!dispatcher.parse("qzverdict status", source(0)).getReader().canRead()) throw new AssertionError("Non-admin unexpectedly parsed admin command");
        if (!dispatcher.parse("qzverdict rule list 0", admin).getReader().canRead()) throw new AssertionError("Zero page accepted");
        System.out.println("PASS: production command tree accepts unquoted device digests and legacy rule IDs, glob spaces and ban reasons; rejects non-admin access and invalid pages");
    }
    private static CommandSourceStack source(int permission) {
        return new CommandSourceStack(CommandSource.NULL, Vec3.ZERO, Vec2.ZERO, null, permission, "ParserSmoke", Component.literal("ParserSmoke"), null, null);
    }
    private static void parse(CommandDispatcher<CommandSourceStack> dispatcher, CommandSourceStack source, String text, String key, String expected) {
        var parsed = dispatcher.parse(text, source);
        if (parsed.getReader().canRead() || !parsed.getExceptions().isEmpty()) throw new AssertionError("Parse failed: " + text);
        String actual = StringArgumentType.getString(parsed.getContext().build(text), key);
        if (!expected.equals(actual)) throw new AssertionError("Wrong argument for " + key);
    }
}
