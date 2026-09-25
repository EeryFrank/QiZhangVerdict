package cn.qizhang.guard.core;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Literal-only parser. Deliberately never calls InetAddress or a name resolver. */
final class IpAddress {
    final byte[] bytes;
    private IpAddress(byte[] bytes) { this.bytes = bytes; }
    static IpAddress parse(String literal) {
        byte[] raw = raw(literal);
        if (mapped(raw)) raw = Arrays.copyOfRange(raw, 12, 16);
        return new IpAddress(raw);
    }
    static byte[] raw(String value) {
        if (value == null || value.isEmpty() || value.length() > 45 || !value.equals(value.trim()) || value.indexOf('%') >= 0)
            throw new IllegalArgumentException("Expected an IP literal");
        if (value.indexOf(':') < 0) return ipv4(value);
        if (value.indexOf('.') >= 0) {
            int last = value.lastIndexOf(':');
            byte[] four = ipv4(value.substring(last + 1));
            value = value.substring(0, last + 1) + Integer.toHexString(((four[0] & 255) << 8) | (four[1] & 255))
                    + ":" + Integer.toHexString(((four[2] & 255) << 8) | (four[3] & 255));
        }
        int gap = value.indexOf("::");
        if (gap >= 0 && value.indexOf("::", gap + 2) >= 0) throw new IllegalArgumentException("Multiple IPv6 compression markers");
        List<Integer> left = words(gap < 0 ? value : value.substring(0, gap));
        List<Integer> right = gap < 0 ? new ArrayList<Integer>() : words(value.substring(gap + 2));
        int total = left.size() + right.size();
        if ((gap < 0 && total != 8) || (gap >= 0 && total >= 8)) throw new IllegalArgumentException("Invalid IPv6 length");
        byte[] result = new byte[16];
        int at = 0;
        for (int word : left) { result[at++] = (byte) (word >>> 8); result[at++] = (byte) word; }
        at = 16 - right.size() * 2;
        for (int word : right) { result[at++] = (byte) (word >>> 8); result[at++] = (byte) word; }
        return result;
    }
    private static List<Integer> words(String value) {
        ArrayList<Integer> result = new ArrayList<Integer>();
        if (value.isEmpty()) return result;
        for (String part : value.split(":", -1)) {
            if (!part.matches("[0-9a-fA-F]{1,4}")) throw new IllegalArgumentException("Invalid IPv6 group");
            result.add(Integer.parseInt(part, 16));
        }
        return result;
    }
    private static byte[] ipv4(String value) {
        String[] parts = value.split("\\.", -1);
        if (parts.length != 4) throw new IllegalArgumentException("Invalid IPv4 literal");
        byte[] bytes = new byte[4];
        for (int i = 0; i < 4; i++) {
            if (!parts[i].matches("0|[1-9][0-9]{0,2}")) throw new IllegalArgumentException("Invalid IPv4 octet");
            int v = Integer.parseInt(parts[i]);
            if (v > 255) throw new IllegalArgumentException("Invalid IPv4 octet");
            bytes[i] = (byte) v;
        }
        return bytes;
    }
    static boolean mapped(byte[] bytes) {
        if (bytes.length != 16) return false;
        for (int i = 0; i < 10; i++) if (bytes[i] != 0) return false;
        return bytes[10] == (byte) 255 && bytes[11] == (byte) 255;
    }
    @Override public String toString() {
        StringBuilder out = new StringBuilder();
        if (bytes.length == 4) {
            for (int i = 0; i < 4; i++) { if (i > 0) out.append('.'); out.append(bytes[i] & 255); }
        } else {
            for (int i = 0; i < 16; i += 2) { if (i > 0) out.append(':'); out.append(Integer.toHexString(((bytes[i] & 255) << 8) | (bytes[i + 1] & 255))); }
        }
        return out.toString();
    }
}
