// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge189;

import net.minecraftforge.fml.common.network.FMLEventChannel;

/** Keeps client-only Minecraft types out of dedicated-server initialization. */
public class CommonProxy {
    public void register(FMLEventChannel channel) { }
}
