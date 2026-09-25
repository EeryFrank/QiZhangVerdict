# 1.8.9 真实客户端验收与图形诊断

本次两个正式组合通过：原始生产版 Forge 1.8.9 客户端分别连接 Forge 1.8.9 专服、Paper 1.8.8 插件服。客户端采用独立配置 `config/splash.properties` 中的 `enabled=false`，关闭 Forge 加载动画；这是本次图形验收的明确条件。游戏、加载器和 QiZhangVerdict JAR 未修改，服务端完整严格默认策略未放宽。

[完整验收与文件哈希](../outputs/legacy-client-matrix/1.8.9-0.2.0-dev-gpl/acceptance.json)包含 19 个新增原字节证据文件。两个正式运行均使用 Java 8u504、客户端最大堆 2 GiB、服务端最大堆 1536 MiB，启动前脚本强制检查可用物理内存至少 5 GiB，并按顺序运行。

| 客户端 → 服务端 | 报告证据出现后的在线观察 | 客户端 / 服务端退出码 | 图形检查 |
| --- | ---: | --- | --- |
| Forge 1.8.9 → Forge 11.15.1.2318 | 65.157 秒 | 0 / 0 | 纹理、生存 HUD、文字正常 |
| Forge 1.8.9 → PaperSpigot 445 / MC 1.8.8 | 65.213 秒 | 0 / 0 | 纹理、生存 HUD、文字正常 |

两轮均先确认准确的合成玩家 UUID 已存在设备关联，再用单调时钟计时；观察满 65 秒后发送新的 `testfor @a[name=VerdictClient,m=0]`，只接受此后新增日志中的成功响应。两轮的 `companion.required=true`、`device.required=true`、`vm.action=DENY` 等完整默认策略前后相同，配置 SHA256 均为 `47310c31b47287ab805bfdbf8ddddf80e8169385bd9c862239a0a0075644da4e`。

Forge 的成功生存查询发生在报告隔离解除后。Bukkit 的等待隔离不切换游戏模式，因此 Bukkit 结果只称“确认生存模式”；其报告通过证据来自准确 UUID 的设备关联落盘、严格 20 秒期限及随后超过 65 秒的实时在线查询。所有自有进程正常退出，端口 25661 重新绑定检查通过。

实际截图均已解码并人工检查：

- [Forge → Forge 正式截图](../outputs/legacy-client-matrix/1.8.9-0.2.0-dev-gpl/evidence/forge-1.8.9-candidate-03.png)
- [Forge → Paper 正式截图](../outputs/legacy-client-matrix/1.8.9-0.2.0-dev-gpl/evidence/forge-1.8.9-paper-01.png)

## 精确成品与执行脚本

| 文件 | SHA256 |
| --- | --- |
| `qizhangverdict-forge-1.8.9-0.2.0-dev.jar` | `f00943b06e87dbfc04e88336134ab4ae1a571a6e9b53924ab6bc06b311918424` |
| `qizhangverdict-bukkit-0.1.1.jar` | `e1194b8b694763afbc431e22799f40d357dd80493d194f680edfb219afe94845` |
| 两轮实际执行 QA | `72a7a9ec475180845cef9fd8302b17c256057e7c2009a2716c03a692797f4dc1` |

[QA 源文件](../platforms/legacy189-client-smoke.py)默认不关闭加载动画；这两轮显式使用 `--forge-splash disabled`。实际执行的原字节脚本快照随验收证据保留。运行目录分别为 `candidate-0.2.0-dev-gpl-03` 和 `paper-candidate-0.2.0-dev-gpl-01`，工具拒绝复用已有运行目录。

官方旧版 SimpleInstaller 不支持 `--installClient`，首次调用的退出码 1 和日志仍保留。最终启动采用已验证官方 `install_profile.json` 的 `versionInfo`、安装包内未经修改的 universal JAR，以及经过官方哈希验证的依赖；不宣称存在已通过的客户端 CLI 安装步骤。客户端使用生产 LaunchWrapper，未使用开发类、修改游戏字节码或在线账户认证。

## 保留的失败与对照

[初始诊断](../outputs/legacy-client-matrix/1.8.9-0.2.0-dev-gpl/diagnostic.json)继续保持 `formal_acceptance_passed=false`，没有用新结果覆盖旧事实：

- 首轮严格报告、65.224 秒在线和双端退出通过，但截图纹理与 HUD 明显异常。原始 `passed=true` 只表示当时的自动检查，人工视觉验收失败。
- 仅启用 VBO 的第二轮仍有视觉异常。它在可用内存 4.513 GiB、低于要求的 5 GiB 时被错误启动，随后正常提前停止；阈值偏差和未完成 65 秒观察均保留。后续脚本已加入启动硬门槛。
- [无 Guard 基线 01](../outputs/legacy-client-matrix/1.8.9-0.2.0-dev-gpl/no-guard-baseline-01.json)在双方均未安装 QiZhangVerdict 时复现相同异常，双端退出 0。
- [无 Guard 基线 02](../outputs/legacy-client-matrix/1.8.9-0.2.0-dev-gpl/no-guard-baseline-02.json)仅预置客户端 `splash.properties` 的 `enabled=false`，普通视频选项、依赖及堆参数与基线 01 相同；截图恢复正常，双端退出 0。两个基线都是图形诊断，不计作反作弊验收。

关闭加载动画的实验线索来自[官方 Forge 论坛中另一位 1.8.9 用户的报告](https://forums.minecraftforge.net/topic/36881-189-black-screen-on-menu-only-in-forge-mode-fixed/)。本机对照支持这一局部缓解方法，尚未确定底层原因；不能据此归因于某个 AMD 驱动，也不保证所有机器在默认加载动画配置下都正常。

原始日志、配置前后副本、失败截图和脚本快照均保留原字节。公开材料不包含账号状态文件、真实系统安装 ID、设备摘要、完整启动计划或 Minecraft 反汇编。

本次实际证明的是 Forge **1.8.9 客户端连接 Paper 1.8.8**，没有完成原生 Forge 1.8.8 模组适配验收。其他机器、加载器、整合包、正版登录基础设施、修改过的报告客户端、真实虚拟机矩阵和长时间负载仍需分别验证。
