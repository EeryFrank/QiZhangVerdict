package cn.qizhang.guard.client;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.util.Arrays;

/** GPL-3.0-only. Proves the legacy bridge cannot read beyond the original probe limits. */
public final class LegacyJava8Smoke {
    public static void main(String[] args) throws Exception {
        for (int limit : new int[]{0, 128, 256, 1024, 4096, 8192}) {
            byte[] bytes = new byte[limit + 3]; Arrays.fill(bytes, (byte) 7);
            ByteArrayInputStream input = new ByteArrayInputStream(bytes);
            byte[] read = LegacyJava8.readBounded(input, limit);
            if (read.length != limit || input.available() != 3) throw new AssertionError("Read exceeded bound " + limit);
        }
        if (LegacyJava8.readBounded(new ByteArrayInputStream(new byte[]{1, 2}), 128).length != 2)
            throw new AssertionError("Short stream corrupted");
        InputStream zeroOnce = new InputStream() {
            int state;
            @Override public int read(byte[] b, int off, int len) { return state++ == 0 ? 0 : -1; }
            @Override public int read() { return 42; }
        };
        if (!Arrays.equals(new byte[]{42}, LegacyJava8.readBounded(zeroOnce, 128)))
            throw new AssertionError("Zero-byte read did not make progress");
        try { LegacyJava8.readBounded(new ByteArrayInputStream(new byte[0]), 8193); throw new AssertionError("Unbounded limit accepted"); }
        catch (IllegalArgumentException expected) { }
        System.out.println("PASS: Java 8 probe bridge preserves bounded, short, empty and zero-progress reads");
    }
}
