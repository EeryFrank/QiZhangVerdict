// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.neoforge;

import cn.qizhang.guard.minecraft.CommandParserSmoke;
import cn.qizhang.guard.minecraft.PayloadCodecSmoke;
import org.junit.jupiter.api.Test;

/** Runs production command and packet contracts under the official FML test loader. */
final class PlatformContractTest {
    @Test
    void administratorCommandTree() {
        CommandParserSmoke.main(new String[0]);
    }

    @Test
    void boundedBukkitCompatiblePayload() {
        PayloadCodecSmoke.main(new String[0]);
    }
}
