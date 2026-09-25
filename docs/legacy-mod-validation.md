# 1.19.4 模组适配开发版验证

2026-09-25，独立验证 `0.2.0-dev` 的 Minecraft 1.19.4 Fabric / Forge 适配。**两份产物均未发布，不属于 0.1.1 的五个正式候选产物。** 本报告只记录本轮服务端测试，后续真实客户端验证应另行关联实际成品散列。

| 平台 | 加载器 / 依赖 | 实际验证 | 服务端退出 |
| --- | --- | --- | --- |
| Fabric 1.19.4 | Loader 0.16.14，Fabric API 0.87.2+1.19.4 | 启动、状态命令、26 项真实 TCP 断言 | 0 |
| Forge 1.19.4 | Forge 45.4.5 | 物理专服启动、状态命令、正常停止 | 0 |

实际使用 Temurin Java 17.0.20.1+1。安装器先下载并校验官方 Maven 的 SHA-256，安装与运行分开、串行执行；每次启动前确认物理可用内存大于 3 GiB。所有目录都独立位于 `E:/CodexTemp/QiZhangVerdict/legacy-runtime`，仅监听 `127.0.0.1`。本轮没有安装 Grim 或 AntiXray，不能据此宣称两者兼容或已提供行为检测/矿物混淆。

## 成品与来源

| 文件 | SHA-256 |
| --- | --- |
| `qizhangverdict-fabric-1.19.4-0.2.0-dev.jar` | `20b992e1dde08bfd017d6ef87ca489f9d6354d0251e9dbe4242e73e0a6709c66` |
| `qizhangverdict-forge-1.19.4-0.2.0-dev.jar` | `65c3d8160124c7e73ad7073de8435a3200fcabf28a9e84a70a7f7e57462ae469` |

上表是本轮运行时实际使用的许可调整前内部候选散列。随后 GPL 重建只改变许可文件和描述符，所有类文件逐字节相同，见 [许可迁移记录](../outputs/license-transition.json) 与 [最终构建记录](../outputs/build-validation-0.1.1-gpl.json)。本报告保留原散列，不把历史运行改称为重建后 JAR 的新实测。

Fabric 安装器来自 [Fabric 官方 Maven](https://maven.fabricmc.net/net/fabricmc/fabric-installer/1.1.1/)，Fabric API 来自[固定 0.87.2+1.19.4 目录](https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/0.87.2%2B1.19.4/)，Forge 安装器来自 [Forge 官方 Maven](https://maven.minecraftforge.net/net/minecraftforge/forge/1.19.4-45.4.5/)。完整下载地址、校验值、Java 版本、安装器退出码、原始运行记录及散列在 [legacy-mod-validation.json](../outputs/legacy-mod-validation.json)。

两个最终 JAR 均包含 `required=true` / `defaultRequire=1` 的命令门禁 Mixin 和相应 refmap。实际 Fabric 网络测试使用具有 OP 权限的账号验证：完整报告前 `/say` 标记不执行，报告通过后标记执行。Forge 本轮没有玩家登录，因此不会用它的成功启动替代网络方向、客户端上报或指令门禁实际执行证明。

## Fabric 的 26 项网络检查

测试通过真实 TCP 连接发送合成报告，涵盖正常准入、缺失和畸形报告、同 IP 与设备并发规则、退出释放、黑名单、GLOB、白名单、关联账号/设备封禁及独立解封、带冒号 ID 的默认规则删除/恢复、CIDR、已知 VM 指标拒绝，以及单独 HypervisorPresent 不封物理机的策略分支。全部断言名称保存在 JSON 中。

启动日志确认初始严格默认策略：报告必需、设备码必需、VM DENY。随后分支夹具保持报告/设备必需，但把超时设为通常 4 秒、门禁用例 10 秒，提高合成账号的频率/滚动上限，并针对具体分支切换 VM 策略。本组不宣称验证了默认 20 秒窗口，也不代表真实 VM 检测或防篡改设备证明。

Fabric 本轮原始日志没有记录 ERROR/Exception。Forge 测试服出现一条 LAN 广播 `Network is unreachable: sendto` 告警，之后仍完成实际状态响应和正常保存退出；日志原样保留，PASS 不等于完全无告警。

## Forge 网络方向复核及边界

另从官方且经 SHA-256 校验的 Forge 45.4.5 源码确认：`PLAY_TO_SERVER` 创建 `ClientCustomPayloadEvent`，`PLAY_TO_CLIENT` 创建 `ServerCustomPayloadEvent`，事件名按发送方区分。这项源码复核支持修复先前把事件类型写反的问题，但**源码复核与专服启动都不能替代 1.19.4 Forge 真实配套客户端报告测试**。

复现入口：[legacy_mod_smoke.py](https://github.com/EeryFrank/QiZhangVerdict/blob/v0.1.1-test.1/scripts/legacy_mod_smoke.py)。`stage` 只下载与校验，不运行 Java；`install` 执行官方安装器；`run` 接受明确的待测成品与可选 SHA-256，复用既有运行器并保存实际进程证据。Fabric 运行器要求 26 项协议用例；Forge 当前只执行启动/状态/退出。本报告不覆盖图形客户端、完整玩法、性能、外部反作弊、整合包、混合端或其他 Minecraft 版本。
