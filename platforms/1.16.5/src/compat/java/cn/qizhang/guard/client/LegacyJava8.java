package cn.qizhang.guard.client;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.Locale;

/** GPL-3.0-only. Java 8 replacements only; no policy or reporting changes. */
final class LegacyJava8 {
    private LegacyJava8() { }

    static byte[] readBounded(InputStream input, int limit) throws IOException {
        if (limit < 0 || limit > 8192) throw new IllegalArgumentException("Invalid probe read limit");
        ByteArrayOutputStream output = new ByteArrayOutputStream(Math.min(limit, 1024));
        byte[] buffer = new byte[Math.min(limit, 1024)];
        int remaining = limit;
        while (remaining > 0) {
            int count = input.read(buffer, 0, Math.min(buffer.length, remaining));
            if (count < 0) break;
            if (count == 0) {
                int value = input.read();
                if (value < 0) break;
                output.write(value);
                remaining--;
            } else {
                output.write(buffer, 0, count);
                remaining -= count;
            }
        }
        return output.toByteArray();
    }

    static ProcessBuilder.Redirect discardError() {
        boolean windows = System.getProperty("os.name", "").toLowerCase(Locale.ROOT).contains("windows");
        return ProcessBuilder.Redirect.to(new File(windows ? "NUL" : "/dev/null"));
    }
}
