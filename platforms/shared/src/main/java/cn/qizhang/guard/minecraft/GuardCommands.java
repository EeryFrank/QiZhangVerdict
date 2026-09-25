package cn.qizhang.guard.minecraft;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import java.util.Arrays;
import com.mojang.brigadier.context.CommandContext;
import java.util.function.Supplier;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;

public final class GuardCommands {
    private GuardCommands() { }
    public static void register(CommandDispatcher<CommandSourceStack> dispatcher, Supplier<MinecraftGuard> guard) {
        dispatcher.register(Commands.literal("qzverdict").requires(source -> source.hasPermission(3))
                .then(Commands.literal("status").executes(context -> { context.getSource().sendSuccess(() -> Component.literal(guard.get().status()), false); return 1; }))
                .then(Commands.literal("reload").executes(context -> run(context, guard, "reload")))
                .then(Commands.literal("bans").executes(context -> run(context, guard, "bans", "1"))
                        .then(Commands.argument("page", IntegerArgumentType.integer(1)).executes(context -> run(context, guard, "bans", Integer.toString(IntegerArgumentType.getInteger(context, "page"))))))
                .then(Commands.literal("rule")
                        .then(Commands.literal("list").executes(context -> run(context, guard, "rules", "1"))
                                .then(Commands.argument("page", IntegerArgumentType.integer(1)).executes(context -> run(context, guard, "rules", Integer.toString(IntegerArgumentType.getInteger(context, "page"))))))
                        .then(Commands.literal("remove").then(Commands.argument("id", StringArgumentType.greedyString()).executes(context -> run(context, guard, "remove", arg(context, "id").trim()))))
                        .then(Commands.literal("add").then(Commands.argument("list", StringArgumentType.word())
                                .then(Commands.argument("kind", StringArgumentType.word())
                                        .then(Commands.argument("match", StringArgumentType.word())
                                                .then(Commands.argument("value", StringArgumentType.greedyString()).executes(context -> run(context, guard, "add", arg(context, "list"), arg(context, "kind"), arg(context, "match"), arg(context, "value")))))))))
                .then(Commands.literal("ban").then(Commands.argument("uuid", StringArgumentType.word())
                        .executes(context -> run(context, guard, "ban", arg(context, "uuid"), "Administrator ban"))
                        .then(Commands.argument("reason", StringArgumentType.greedyString()).executes(context -> run(context, guard, "ban", arg(context, "uuid"), arg(context, "reason"))))))
                .then(Commands.literal("unban").then(Commands.argument("uuid-or-device", StringArgumentType.greedyString()).executes(context -> run(context, guard, "unban", arg(context, "uuid-or-device").trim())))));
    }
    private static String arg(CommandContext<CommandSourceStack> context, String name) { return StringArgumentType.getString(context, name); }
    private static int run(CommandContext<CommandSourceStack> context, Supplier<MinecraftGuard> guard, String action, String... args) {
        var source = context.getSource();
        guard.get().admin(source.getServer(), action, Arrays.asList(args), result -> source.sendSuccess(() -> Component.literal(result), false));
        return 1;
    }
}
