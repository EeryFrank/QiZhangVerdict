// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge189;

import java.net.InetSocketAddress;
import java.net.SocketAddress;
import net.minecraft.entity.player.EntityPlayerMP;

/** Literal address only. Integrated-owner handling remains in the shared guard. */
public final class LegacyAddress {
    private LegacyAddress() { }
    public static String address(EntityPlayerMP player) {
        SocketAddress remote = player.playerNetServerHandler.getNetworkManager().getRemoteAddress();
        if (remote instanceof InetSocketAddress) {
            InetSocketAddress inet = (InetSocketAddress) remote;
            return inet.getAddress() == null ? "" : inet.getAddress().getHostAddress();
        }
        return "<unknown>";
    }
}
