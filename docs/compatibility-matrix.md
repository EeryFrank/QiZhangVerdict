# 兼容验证进度

本页按 `0.1.1` GPL 测试候选及独立 `0.2.0-dev` 适配记录验证范围，不能替代每个成品的散列与验收记录。首个 [GitHub v0.1.0-test.1](https://github.com/EeryFrank/QiZhangVerdict/releases/tag/v0.1.0-test.1) / [GitLab v0.1.0-test.1](https://gitlab.com/EeryFrank/QiZhangVerdict/-/releases/v0.1.0-test.1) 的文件仍保留原字节；其 Forge 客户端后续发现的问题已在原发布说明中标明。

| Minecraft | 插件服务端 | 配套模组 |
|---|---|---|
| 1.8.8 | Paper 445：0.1.1 许可调整前候选、严格默认配置、12 项 TCP 登录检查、正常停服 | 未实现此版客户端 |
| 1.12.2 | Paper 1620：同上 | 未实现此版客户端 |
| 1.16.5 | Paper 794：同上 | 未实现此版客户端 |
| 1.18.2 | Paper 388：同上 | Fabric / Forge 0.2.0-dev 已构建及命令树检查通过；未完成真实客户端验收，尚未发布 |
| 1.19.4 | Paper 550：同上 | Fabric / Forge 0.2.0-dev 已构建及专服检查；真实客户端验收推进中，尚未发布 |
| 1.20.1 | Purpur 2062：最终 GPL JAR，27 项 TCP 检查及矿物混淆包检查 | Fabric / Forge 最终 GPL JAR 真实客户端与专服验收见客户端记录 |
| 1.21.1 | Purpur 2329：最终 GPL JAR，27 项 TCP 检查及矿物混淆包检查 | Fabric / NeoForge 最终 GPL JAR 真实客户端与专服验收见客户端记录 |

五版旧 Paper 的新版回归实际使用许可调整前的 `568868…` 候选，各 12 项、共 60 项 TCP 断言；核心的 55 项安全回归是另一组测试。原始默认的同 IP 3 人、同设备 1 人、20 秒报告期限及非空设备要求均未放宽。最终 GPL JAR 的全部类文件与该候选逐字节相同，旧版运行记录仍保留实际原散列。详见 [最终 Bukkit 验收与许可迁移边界](validation-0.1.1-gpl-bukkit.md)。

旧版协议夹具能提交合成报告，但普通玩家仍需对应版本的真实客户端模组。尚无配套客户端的版本不应被宣传为可直接部署完整设备验证；不能通过关闭设备要求把它算作功能已兼容。旧版测试也没有验证这些版本的 Grim、AntiXray、命令隔离或完整游戏操作。

旧版用例包含合法报告后超过默认期限仍在线的实际状态检查；历史首版另有五站各 11 项的冻结 JAR 记录，均见 [旧版插件验收](legacy-bukkit-validation.md)。四端真实客户端的精确成品、截图、配置和登录重试记录见 [客户端验收](client-matrix.md)。

其他 Minecraft 版本、Folia、代理转发、多服共享处罚、混合端、基岩互通、长期负载及真实作弊误报率仍需独立适配和验收。首批证据保留在 [原始验收报告](validation.md)。

## 1.19.4 开发构建

此目标使用 Java 17、Fabric Loader 0.16.14 / Fabric API 0.87.2+1.19.4 或 Forge 45.4.5，开发版本号为 `0.2.0-dev`。从仓库根目录执行：

```text
gradlew.bat -p platforms/1.19.4 build :fabric:commandParserSmoke
```

构建机需提供 JDK 17 工具链，Gradle 可运行在 JDK 21。新目标共享核心与 1.20.1 加载器代码，只在生成的目标源码中适配 1.19.4 的 `ServerPlayer.getLevel()` 和 `sendSuccess(Component, boolean)`；不会修改已发布版本的实现。构建成功、运行通过及客户端验收分别记录，不把其中一步当成其他步骤已经通过。
