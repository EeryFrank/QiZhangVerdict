// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge189;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

/** Preserve greedy rule values and reasons without interpreting colons as separators. */
public final class LegacyCommandParser {
    public static final class Action {
        public final String operation;
        public final List<String> arguments;
        private Action(String operation, String... arguments) {
            this.operation = operation;
            this.arguments = Collections.unmodifiableList(Arrays.asList(arguments));
        }
    }
    private LegacyCommandParser() { }
    public static Action parse(String[] args) {
        if (args.length == 0) return new Action("status");
        String operation = args[0].toLowerCase(Locale.ROOT);
        if (("status".equals(operation) || "reload".equals(operation)) && args.length == 1) return new Action(operation);
        if ("bans".equals(operation) && args.length <= 2) return new Action("bans", page(args.length == 2 ? args[1] : "1"));
        if ("ban".equals(operation) && args.length >= 2) return new Action("ban", args[1], args.length == 2 ? "Administrator ban" : remaining(args, 2));
        if ("unban".equals(operation) && args.length == 2) return new Action("unban", args[1]);
        if ("rule".equals(operation) && args.length >= 2) {
            String sub = args[1].toLowerCase(Locale.ROOT);
            if ("list".equals(sub) && args.length <= 3) return new Action("rules", page(args.length == 3 ? args[2] : "1"));
            if ("remove".equals(sub) && args.length >= 3) return new Action("remove", remaining(args, 2));
            if ("add".equals(sub) && args.length >= 6) return new Action("add", args[2], args[3], args[4], remaining(args, 5));
        }
        throw new IllegalArgumentException("Usage: /qzverdict status|reload|bans [page]|rule list [page]|rule add <black|white> <kind> <exact|glob> <value>|rule remove <id>|ban <UUID|online-name> [reason]|unban <UUID|device:digest>");
    }
    private static String remaining(String[] args, int start) { return String.join(" ", Arrays.copyOfRange(args, start, args.length)).trim(); }
    private static String page(String value) {
        try { if (Integer.parseInt(value) > 0) return value; } catch (NumberFormatException invalid) { }
        throw new IllegalArgumentException("Page must be a positive integer");
    }
}
