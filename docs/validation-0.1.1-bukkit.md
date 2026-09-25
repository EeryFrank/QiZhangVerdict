# Bukkit 0.1.1 独立验证

验证日期：2026-09-25。成品为 `qizhangverdict-bukkit-0.1.1.jar`，SHA-256：`5688683392ff59aee0bfbbe3f1f41ca056cebc06a063afad608714848d7d7639`。没有替换已发布的 `v0.1.0-test.1` 或改写其历史证据。

## 现代插件服集成回归

| Minecraft | 服务端 | Java | 固定 Grim | 实际 TCP 断言 | 假矿石类型 | 服务端退出 |
| --- | --- | --- | --- | --- | --- | --- |
| 1.20.1 | Purpur 2062 | Temurin 17.0.20.1+1 | 2.3.71 | 27 / 27 | 16 | 0 |
| 1.21.1 | Purpur 2329 | Oracle Java 21.0.8+12-LTS-250 | 2.3.73 | 27 / 27 | 16 | 0 |

两轮都实际启动、执行状态命令、完成真实 TCP 协议测试后正常 `stop`，网络压缩阈值保持 256。每次只运行一台测试服，启动前确认可用物理内存大于 3 GiB。测试使用固定服务端与 Grim 文件，运行前重新计算散列并核对原官方下载收据/依赖锁。

当前根协议脚本包含 27 项，较首版 Bukkit 的 25 项多出“删除带冒号 ID 的默认规则”和“恢复该规则”。其余检查包括正常报告、缺失/畸形报告、同 IP 与设备配额、退出释放、黑白名单/GLOB、账号与设备关联封禁及独立解封、CIDR、VM 策略，以及具有 OP 权限的玩家在报告前不能执行 `/say`、报告通过后能够执行。

矿物混淆证明来自客户端收到的实际区块调色板。测试世界是明确生成层的无矿石超平坦世界，发送给客户端的数据中出现了铜、煤、铁、金、红石、青金石、钻石、绿宝石及各自深板岩变体，共 16 种。两轮均使用项目固定的 Paper 原生 Anti-Xray 配置片段。这不是仅凭插件存在、配置开关或启动横幅推断防透视生效。

机器可读证据：[bukkit-modern-validation-0.1.1.json](../outputs/bukkit-modern-validation-0.1.1.json)。其中包含每个实际断言名称、矿石类型、精确服务端/插件/Grim 散列、Java 版本、原始日志和结果文件位置与散列，以及非致命错误记录。

本组分支测试保持报告与设备必需，但为减少测试时长把报告期限设为 4 秒，OP 指令门禁用例为 10 秒；滚动账号与频率上限提高至适合合成测试账号的值，VM 正常分支使用 ALERT、专门用例切换为 DENY。**因此本组证明所列分支行为，不将其宣称为默认 20 秒策略的完整实测。** 旧版默认策略的 22 秒合法在线与默认超时证据单独记录在下一节。

## 五个旧版的严格默认策略

同一 0.1.1 成品另在 Paper 1.8.8、1.12.2、1.16.5、1.18.2、1.19.4 各通过 12 项 TCP 检查，共 60 项；五台服务器均正常退出 0。该组完全保留初始 `guard.properties`，实际验证合法报告后至少 22 秒仍在线，并随后从服务端查询严格策略下的有效会话；未上报账号则在默认约 20 秒后断开。

具体构建、频道、Java、时间及历史区别见 [旧版 Bukkit 验证](legacy-bukkit-validation.md) 和 [0.1.1 旧版 JSON](../outputs/legacy-bukkit-validation-0.1.1.json)。这些是合成报告的插件适配证据，不表示五个旧游戏版本的图形客户端模组已发布。

## 保留的首次故障与范围限制

首次把 Purpur 1.20.1 与 Grim 2.3.73 组合时，确实出现 PacketEvents 在 LOGIN 阶段报随机大 Packet ID 并拒绝普通客户端的问题。原始故障说明保留在 [固定组件说明](../integrations/README.md)；1.20.1 因此固定官方 Grim 2.3.71，1.21.1 保持 2.3.73。本次成功不是把先前失败删除或解释为成功，也不能据此批准随意升级 Grim、Paper/Purpur 或网络插件。

客户端通过实际 TCP 连接，但模组、设备和 VM 内容是合成自报告。此报告不替代真实配套客户端测试、真实 VM 矩阵、Grim 各项行为检测准确率、反误封测试、全部维度/模组矿石混淆、多人玩法或性能验收。原生 Anti-Xray 的矿物调色板证据也不证明能够阻止所有 ESP。测试服仅监听回环地址并使用离线身份，不能推导生产认证、代理转发或登录插件集成已受验证。

可复现入口保留旧版默认参数，同时允许显式选择新成品并拒绝散列漂移：

```powershell
python scripts/runtime_smoke.py 1.20.1 --mode integrated --compression 256 --guard-jar bukkit/build/libs/qizhangverdict-bukkit-0.1.1.jar --expected-guard-sha256 5688683392ff59aee0bfbbe3f1f41ca056cebc06a063afad608714848d7d7639
python scripts/runtime_smoke.py 1.21.1 --mode integrated --compression 256 --guard-jar bukkit/build/libs/qizhangverdict-bukkit-0.1.1.jar --expected-guard-sha256 5688683392ff59aee0bfbbe3f1f41ca056cebc06a063afad608714848d7d7639
```
