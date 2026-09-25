package cn.qizhang.guard.core;

import java.util.Arrays;

final class Cidr {
    private final byte[] network;
    private final int prefix;
    private Cidr(byte[] network, int prefix) { this.network = network; this.prefix = prefix; }
    static Cidr parse(String text) {
        String[] pieces = text.split("/", -1);
        if (pieces.length > 2) throw new IllegalArgumentException("Invalid CIDR");
        byte[] raw = IpAddress.raw(pieces[0]);
        int prefix = raw.length * 8;
        if (pieces.length == 2) {
            if (!pieces[1].matches("0|[1-9][0-9]{0,2}")) throw new IllegalArgumentException("Invalid CIDR prefix");
            prefix = Integer.parseInt(pieces[1]);
        }
        if (prefix > raw.length * 8) throw new IllegalArgumentException("CIDR prefix out of range");
        if (IpAddress.mapped(raw)) {
            if (prefix < 96) throw new IllegalArgumentException("IPv4-mapped CIDR must use prefix 96..128; use an IPv4 CIDR otherwise");
            raw = Arrays.copyOfRange(raw, 12, 16); prefix -= 96;
        }
        return new Cidr(raw, prefix);
    }
    boolean contains(IpAddress address) {
        if (address.bytes.length != network.length) return false;
        int full = prefix / 8;
        for (int i = 0; i < full; i++) if (address.bytes[i] != network[i]) return false;
        int tail = prefix % 8;
        return tail == 0 || ((address.bytes[full] ^ network[full]) & (255 << (8 - tail))) == 0;
    }
}
