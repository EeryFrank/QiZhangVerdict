# 兼容验证进度

本页按已发布的 `0.1.1` GPL 测试版及独立 `0.2.0-dev` 适配记录验证范围，不能替代每个成品的散列与验收记录。当前测试版下载：[GitHub v0.1.1-test.1](https://github.com/EeryFrank/QiZhangVerdict/releases/tag/v0.1.1-test.1) / [GitLab v0.1.1-test.1](https://gitlab.com/EeryFrank/QiZhangVerdict/-/releases/v0.1.1-test.1)。两站共 22 个公开附件均已匿名下载并核对 SHA256，见 [发布回执](../outputs/publish-receipt-0.1.1.json)。首个 0.1.0 的文件仍保留原字节；其 Forge 客户端后续发现的问题已在原发布说明中标明。

旧版开发预览已发布：[GitHub 0.2.0-dev-preview.1](https://github.com/EeryFrank/QiZhangVerdict/releases/tag/v0.2.0-dev-preview.1) / [GitLab 0.2.0-dev-preview.1](https://gitlab.com/EeryFrank/QiZhangVerdict/-/releases/v0.2.0-dev-preview.1)。固定提交为 `0f5335649573a2cb3f0ee4c11d264cd17a116c6e`；两站共 32 个附件匿名下载和 SHA256 验证通过，见 [预览发布回执](../outputs/publish-receipt-0.2.0-dev-preview.1.json)。七个模组与已有 Bukkit 0.1.1 的字节均保持验收原样。

新增 1.8.9 的预览为 [GitHub 0.2.0-dev-preview.2](https://github.com/EeryFrank/QiZhangVerdict/releases/tag/v0.2.0-dev-preview.2) / [GitLab 0.2.0-dev-preview.2](https://gitlab.com/EeryFrank/QiZhangVerdict/-/releases/v0.2.0-dev-preview.2)，共八个模组及一个 Bukkit 插件；安装和验证条件见 [preview.2 说明](preview-0.2.0-dev-preview.2.md)。新增的两个 1.8.9 客户端用例需要本地关闭 Forge 启动画面，保留原画面故障和无插件对照记录。

| Minecraft | 插件服务端 | 配套模组 |
|---|---|---|
| 1.8.8 | Paper 445：最终 GPL Bukkit 0.1.1 + Forge 1.8.9 真实客户端通过；早期 12 项 TCP 检查另有记录 | Forge 1.8.9 客户端跨版连接通过；没有原生 Forge 1.8.8 成品 |
| 1.8.9 | 配套客户端已连接 Paper 1.8.8；未另测此版插件服 | 原生 Forge 构建、Java 8 检查、14 项 TCP/OP 门禁及真实客户端通过；本机关闭 Forge 加载动画后画面正常 |
| 1.12.2 | Paper 1620：旧版 TCP 回归及最终 GPL Bukkit 0.1.1 + Forge 客户端实测通过 | Forge 0.2.0-dev 已构建、通过 Java 8 回归、13 项严格默认策略 TCP 检查及真实客户端；报告获准后在线超过 65 秒 |
| 1.16.5 | Paper 794：许可调整前候选通过严格默认配置 12 项 TCP 检查；最终 GPL 类文件等值 | Fabric / Forge 0.2.0-dev 专服及真实 Java 8 客户端通过；严格默认策略、报告通过后在线 66 / 65 秒，收入旧版开发预览 |
| 1.18.2 | Paper 388：许可调整前候选通过严格默认配置 12 项 TCP 检查；最终 GPL 类文件等值 | Fabric / Forge 0.2.0-dev 专服及真实客户端通过；严格默认配置、报告通过后在线 65 秒，收入旧版开发预览 |
| 1.19.4 | Paper 550：许可调整前候选通过严格默认配置 12 项 TCP 检查；最终 GPL 类文件等值 | Fabric / Forge 0.2.0-dev 专服及真实客户端通过；严格默认配置、报告通过后在线 65 / 66 秒，收入旧版开发预览 |
| 1.20.1 | Purpur 2062：最终 GPL JAR，27 项 TCP、矿物混淆包及 Grim 关联封禁/重启/解封检查 | Fabric / Forge 最终 GPL JAR 真实客户端与专服验收见客户端记录 |
| 1.21.1 | Purpur 2329：最终 GPL JAR，27 项 TCP、矿物混淆包及 Grim 关联封禁/重启/解封检查 | Fabric / NeoForge 最终 GPL JAR 真实客户端与专服验收见客户端记录 |

五版旧 Paper 的新版回归实际使用许可调整前的 `568868…` 候选，各 12 项、共 60 项 TCP 断言；核心的 55 项安全回归是另一组测试。原始默认的同 IP 3 人、同设备 1 人、20 秒报告期限及非空设备要求均未放宽。最终 GPL JAR 的全部类文件与该候选逐字节相同，旧版运行记录仍保留实际原散列。详见 [最终 Bukkit 验收与许可迁移边界](validation-0.1.1-gpl-bukkit.md)。

旧版协议夹具能提交合成报告，但普通玩家仍需对应版本的真实客户端模组。尚无配套客户端的版本不应被宣传为可直接部署完整设备验证；不能通过关闭设备要求把它算作功能已兼容。旧 Paper 的历史 TCP 检查不证明命令隔离或完整游戏操作；新增模组的命令门禁测试以各自报告为准。旧版 Grim、AntiXray 尚未完成运行验收。

旧版用例包含合法报告后超过默认期限仍在线的实际状态检查；历史首版另有五站各 11 项的冻结 JAR 记录，均见 [旧版插件验收](legacy-bukkit-validation.md)。四端真实客户端的精确成品、截图、配置和登录重试记录见 [客户端验收](client-matrix.md)。

旧版模组开发记录分别见 [1.8.9 构建](legacy-1.8.9-adapter.md)、[1.8.9 真实客户端](legacy-client-validation-1.8.9.md)、[1.12.2 构建](legacy-1.12.2-adapter.md)、[1.12.2 真实客户端](legacy-client-validation-1.12.2.md)、[1.16.5 专服](legacy-mod-validation-1.16.5-gpl.md)、[1.16.5 真实客户端](legacy-client-validation-1.16.5.md)、[1.18.2 专服](legacy-mod-validation-1.18.2-gpl.md)、[1.18.2 真实客户端](legacy-client-validation-1.18.2.md)及 [1.19.4 真实客户端](legacy-client-validation.md)。1.16.5 / 1.18.2 / 1.19.4 客户端连接的是对应加载器专服，不能当成连接旧 Paper 的实测。1.16.5 使用官方 authlib 离线回退的合成账号夹具；1.18.2 首次资源重载等待和原生 LWJGL 崩溃记录均保留，重试通过不表示原因已经定位。

现代插件组合的真实 Grim 触发、设备关联封禁与重启后解封见 [24 组联动验收](grim-linked-ban-validation.md)，仅覆盖报告列出的两个版本及依赖。

其他 Minecraft 版本、Folia、代理转发、多服共享处罚、混合端、基岩互通、长期负载及真实作弊误报率仍需独立适配和验收。首批证据保留在 [原始验收报告](validation.md)。

## 1.19.4 开发构建

此目标使用 Java 17、Fabric Loader 0.16.14 / Fabric API 0.87.2+1.19.4 或 Forge 45.4.5，开发版本号为 `0.2.0-dev`。从仓库根目录执行：

```text
gradlew.bat -p platforms/1.19.4 build :fabric:commandParserSmoke
```

构建机需提供 JDK 17 工具链，Gradle 可运行在 JDK 21。新目标共享核心与 1.20.1 加载器代码，只在生成的目标源码中适配 1.19.4 的 `ServerPlayer.getLevel()` 和 `sendSuccess(Component, boolean)`；不会修改已发布版本的实现。构建成功、运行通过及客户端验收分别记录，不把其中一步当成其他步骤已经通过。
