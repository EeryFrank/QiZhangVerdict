# GPL 版 Bukkit 0.1.1 最终验证

验证日期：2026-09-25。实际运行的 `qizhangverdict-bukkit-0.1.1.jar` 为 GPL-3.0-only 构建，SHA-256：

`e1194b8b694763afbc431e22799f40d357dd80493d194f680edfb219afe94845`

## 最终 GPL JAR 的两轮真实集成回归

| Minecraft | 服务端 | Java | 固定 Grim | 实际 TCP 断言 | 实际混淆矿物种类 | 服务端退出 |
| --- | --- | --- | --- | --- | --- | --- |
| 1.20.1 | Purpur 2062 | Temurin 17.0.20.1+1 | 2.3.71 | 27 / 27 | 16 | 0 |
| 1.21.1 | Purpur 2329 | Oracle Java 21.0.8+12-LTS-250 | 2.3.73 | 27 / 27 | 16 | 0 |

这两轮是用上面的最终 GPL 散列实际重新启动的独立服务器，不是将之前的散列替换进旧报告。两台服务器完成启动、状态命令、真实 TCP 测试及正常 `stop`，分别运行 109.21 秒和 128.34 秒；协议测试进程和服务器退出码均为 0。网络压缩阈值保持 256，测试世界为受控的无矿石超平坦世界。

27 项断言覆盖准入与报告、IP/设备并发配额、退出释放、畸形报告不永久封号、关联账号/设备封禁和解封、黑白名单/GLOB、带冒号的默认规则删除与恢复、CIDR、VM 策略，以及 OP 玩家报告前后 `/say` 的阻断和恢复。矿物调色板中实际收到铜、煤、铁、金、红石、青金石、钻石、绿宝石及各自深板岩变体，共 16 种；不是根据 Anti-Xray 开关推断生效。

完整实测散列、依赖、断言、矿石类型、日志位置及校验值见 [bukkit-modern-validation-0.1.1-gpl.json](../outputs/bukkit-modern-validation-0.1.1-gpl.json)。原先 [pre-GPL 现代版报告](../outputs/bukkit-modern-validation-0.1.1.json) 原样保留。

## 五个旧版的证据如何继承

Paper 1.8.8、1.12.2、1.16.5、1.18.2、1.19.4 的五版各 12 项实测，实际运行的是许可转换前候选：

`5688683392ff59aee0bfbbe3f1f41ca056cebc06a063afad608714848d7d7639`

该组保持严格默认配置，包含合法报告后至少 22 秒持续在线并从服务端复查会话、无报告账号在默认约 20 秒后断开。原始记录在 [旧版 0.1.1 验证](../outputs/legacy-bukkit-validation-0.1.1.json)。**最终 E119 GPL JAR 没有在这五个旧版服务器上再跑一遍；不能将其标成最终散列的新运行证据。**

[统一许可转换证明](../outputs/license-transition.json) 记录两个 Bukkit JAR 的 17 个 `.class` 文件集合及内容逐字节相同。归档变化只有新增 `LICENSE`、`NOTICE`，以及 `META-INF/MANIFEST.MF` 的许可和项目地址字段；根许可证与 JAR 内许可证也一致。因此旧版兼容判断采用“原候选的真实运行＋许可转换的字节码一致性证明”，与本页前两行最终 GPL JAR 的直接运行验证明确区分。

## 保留的问题与验证范围

首次 Purpur 1.20.1 搭配 Grim 2.3.73 的 PacketEvents LOGIN 随机大 Packet ID 故障仍按事实保留，见 [组件说明](../integrations/README.md)。当前固定 1.20.1 使用 Grim 2.3.71，1.21.1 使用 2.3.73；本次通过不意味着可以直接升级这些组件后沿用相同结论。

本页现代版 TCP 用例发送合成报告，并为了分支测试将报告期限设为通常 4 秒、OP 门禁 10 秒，提高频率/滚动账号上限，针对用例切换 VM 策略；报告与设备验证始终必需。它不是默认 20 秒超时、图形配套客户端、真实 VM、防篡改设备身份或 Grim 检测准确率的证明。假矿石证据仅覆盖该受控主世界，不覆盖全部维度、模组矿物与 ESP。所有测试仅使用回环监听和隔离数据目录；不验证生产认证、代理转发或外部登录插件。

复现时明确选择最终散列：

```powershell
python scripts/runtime_smoke.py 1.20.1 --mode integrated --compression 256 --guard-jar bukkit/build/libs/qizhangverdict-bukkit-0.1.1.jar --expected-guard-sha256 e1194b8b694763afbc431e22799f40d357dd80493d194f680edfb219afe94845
python scripts/runtime_smoke.py 1.21.1 --mode integrated --compression 256 --guard-jar bukkit/build/libs/qizhangverdict-bukkit-0.1.1.jar --expected-guard-sha256 e1194b8b694763afbc431e22799f40d357dd80493d194f680edfb219afe94845
```
