// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge189;

import java.util.Arrays;

public final class LegacyCommandSmoke {
    public static void main(String[] args) {
        LegacyGuardCommand command = new LegacyGuardCommand(() -> null);
        require(!command.canCommandSenderUseCommand(sender(2)), "non-administrator may manage guard");
        require(command.canCommandSenderUseCommand(sender(3)), "administrator rejected");
        String digest = String.join("", java.util.Collections.nCopies(64, "a"));
        equal("unban", new String[]{"device:" + digest}, "unban", "device:" + digest);
        equal("remove", new String[]{"legacy:mod:meteor-client"}, "rule", "remove", "legacy:mod:meteor-client");
        equal("add", new String[]{"black", "pack", "glob", "*ore vision*"}, "rule", "add", "black", "pack", "glob", "*ore", "vision*");
        equal("ban", new String[]{"Player", "reason with spaces"}, "ban", "Player", "reason", "with", "spaces");
        equal("rules", new String[]{"2"}, "rule", "list", "2");
        for (String[] rejected : new String[][]{{"bans", "0"}, {"bans", "-1"}, {"rule", "list", "2147483648"}, {"reload", "extra"}, {"rule", "add", "black"}, {"unknown"}}) {
            try { LegacyCommandParser.parse(rejected); throw new AssertionError("Accepted invalid command"); }
            catch (IllegalArgumentException expected) { }
        }
        System.out.println("PASS: 13 legacy command permission/argument checks (non-admin denial, admin access, colon IDs, greedy spaces, positive pages, invalid commands)");
    }
    private static void equal(String operation, String[] expected, String... input) {
        LegacyCommandParser.Action action = LegacyCommandParser.parse(input);
        require(operation.equals(action.operation) && Arrays.asList(expected).equals(action.arguments), "command mismatch");
    }
    private static void require(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
    private static net.minecraft.command.ICommandSender sender(final int level) {
        return (net.minecraft.command.ICommandSender) java.lang.reflect.Proxy.newProxyInstance(
                LegacyCommandSmoke.class.getClassLoader(), new Class<?>[]{net.minecraft.command.ICommandSender.class},
                (proxy, method, values) -> {
                    if ("canCommandSenderUseCommand".equals(method.getName())) return ((Integer) values[0]) <= level;
                    throw new AssertionError("Unexpected permission dependency: " + method.getName());
                });
    }
}
