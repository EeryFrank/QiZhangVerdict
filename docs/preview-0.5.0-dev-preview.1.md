# 0.5.0-dev-preview.1 测试预览合集

本合集包含 23 个独立 JAR：保留 [0.4 预览的 20 份原件](preview-0.4.0-dev-preview.1.md)，新增 Minecraft 1.20.6 Fabric、NeoForge、Forge 三份 `0.5.0-dev` 模组。旧组件不重新打包，其历史结果继续绑定原始散列。本说明随冻结源码分发；上传、最终标签 CI 和匿名下载验证以发布页面与后续回执为准。

## 选择安装包

| 游戏与加载器 | Verdict JAR | 已验证的运行依赖 |
| --- | --- | --- |
| 1.20.6 Fabric | `qizhangverdict-fabric-1.20.6-0.5.0-dev.jar` | Java 21；Fabric Loader 0.19.5；Fabric API 0.100.8+1.20.6 |
| 1.20.6 NeoForge | `qizhangverdict-neoforge-1.20.6-0.5.0-dev.jar` | Java 21；NeoForge 20.6.141 |
| 1.20.6 Forge | `qizhangverdict-forge-1.20.6-0.5.0-dev.jar` | Java 21；Forge 50.2.0 |
| 既有 Bukkit 与其他指定模组版本 | 保留原组件版本和文件名 | 按 [0.4 安装表及其历史指南](preview-0.4.0-dev-preview.1.md#选择安装包)选择 |

每个实例只安装与其版本、加载器匹配的一份 Verdict。匹配模组服的服务端与玩家客户端都要安装；Fabric API 另行安装。插件服使用 Bukkit 服务端实现及匹配的玩家模组。不要把 23 份全部放到同一目录。本轮三组实际联机只覆盖匹配模组服，不据此证明 1.20.6 Bukkit、代理或跨加载器组合。

三份新 JAR 的 SHA-256 与大小：

| 加载器 | 字节 | SHA-256 |
| --- | ---: | --- |
| Fabric | 97447 | `984a9ba2699008f857b2dc4679319944b1fdc7e2c32fcda9bd59d0e623eba59e` |
| NeoForge | 95765 | `a669cd344d41f6f79bbb3e19a0555030cc7d3da271ef8b97bc5281d50b78e077` |
| Forge | 97107 | `eee8d545fdce4372dad51bfba4ae57159810267555077e6a2e73d21736c9f09a` |

## 安装与升级

1. 正常停服，备份 Verdict 全部配置：插件目录为 `plugins/QiZhangVerdict/`，模组目录为 `config/qizhangverdict/`。
2. 保留 `guard.properties`、`blacklist.tsv`、`rules.tsv`、`accounts.state` 和 `server-id.txt`。后两项共同维持设备关联，不要因升级删除，也不要上传到公开仓库。
3. 替换对应平台的 JAR，每个实例只保留一个版本。插件放入 `plugins/`，模组放入匹配服务端与客户端的 `mods/`。
4. 启动后用测试账号检查 `/qzverdict status`、准入和日志，再开放服务器。[命令与配置](../README.md#默认登录规则)包含名单增删、GLOB、账号及设备解封。生产认证、代理地址转发和第三方整合需要单独验证。

默认同 IP 同设备最多 1 个同时在线账号，同 IP 不同设备最多 3 个；`limits.max-online-per-ip=2` 可改为总共 2 个。30 天内每 IP 最多 5 个 UUID 的滚动记录与在线人数独立。报告及设备标识默认必需，20 秒未完成则断开；已知 VM 信号拒绝，未知或单独 VBS 信号仅告警。黑名单命中默认关联封禁账号、已知设备与关联账号；配额、IP 拒绝、超时或格式错误只拒绝本次会话。

## 规则与对应源码

新增三份 `0.5.0-dev` 首次安装默认 **42 条规则（38 DENY、4 ALERT）**，在 39 条基础上新增 `gateclient`、`genshin`、`meteor-crash-addon`。旧两份 1.21.11 仍默认 39 条，其他 18 份仍默认 37 条。合集编号不改变旧二进制内容。

现有名单、白名单、`OFF` 和删除项不会自动覆盖或恢复。按[目录工具说明](catalog.md)备份、生成合并候选并审阅后更新；显式选择缺失 ID 才会加入。精确 ID 和 GLOB 是服规工具，不保证识别所有商业作弊、注入器或资源包透视。设备与 VM 信号来自客户端自报，能被修改或伪造；矿物透视还需服务端混淆，见[隐私与限制](privacy-and-limits.md)。

原创实现采用 **GPL-3.0-only**。本次同时提供四份对应源码 ZIP：

| 组件来源 | 对应源码 | 固定提交 |
| --- | --- | --- |
| 12 个 `0.2.0-test.1` 模组 | `QiZhangVerdict-0.2.0-test.1-sources.zip` | `310e20b117183182d7767e349aa81cb1d935075c` |
| Bukkit `0.2.1-dev` 与五个 `0.3.0-dev` 模组 | `QiZhangVerdict-0.3.0-dev-preview.1-sources.zip` | `f633a30badb882cfdb8606a7fefd88e5ce28bb2b` |
| 两个 1.21.11 `0.4.0-dev` 模组 | `QiZhangVerdict-0.4.0-dev-preview.1-sources.zip` | `eb6d483e64e29a15501df953f7d59a9645a6905a` |
| 三个 1.20.6 `0.5.0-dev` 模组 | `QiZhangVerdict-0.5.0-dev-preview.1-sources.zip` | 由本次 `packaging.json` 和最终标签绑定 |

三份历史源码 ZIP 保留原始字节，SHA-256 分别为 `2a0ee6445ceed36baf6beb03218d3709993aebd1b47400eeed39ba344709d6cc`、`75f59676ebd7c033ab051705e6214b2e0fea5f2a0c00311cdc69908593e22940`、`b10d67cb010ade8dd36ba2a94d093675b8fb7521f5a8dd67a89502496ccb1955`。对应历史记录见 [0.2 回执](../outputs/publish-receipt-0.2.0-test.1.json)、[0.3 回执](../outputs/publish-receipt-0.3.0-dev-preview.1.json)、[0.4 回执](../outputs/publish-receipt-0.4.0-dev-preview.1.json)。当前 42 条源码不能声称可重建旧 37/39 条成品的原字节；各代源码分别附许可、NOTICE 和构建文件。

## 已验证范围

三份新成品各通过 **102 项包内核心检查**：57 项安全回归、42 条目录规则、3 项保留/普通 ID 控制。三包共 306 次执行，不是 306 个不同用例，也不将用例内部断言另计。Fabric/NeoForge 见[构建记录](adapter-1.20.6.md)，Forge 见[独立构建记录](adapter-forge-1.20.6.md)。Forge 使用独立 Gradle 8.12.1 工程，Fabric/NeoForge 使用 Gradle 9.2.1；不能用同一父 wrapper 构建三端。

三种加载器各通过 26 组 TCP 准入检查，共 78 次执行，覆盖配额、规则编辑、GLOB、黑白名单、IP、VM 自报信号、账号与设备关联封禁及解封。这是合成报告测试，会显式调整账号、频率和超时配置，结束后恢复 13 项默认策略。规则编辑留下的测试规则不能作为首次部署模板。[Fabric/NeoForge 专服报告](runtime-server-1.20.6.md)与 [Forge 专服报告](runtime-server-forge-1.20.6.md)保留执行与恢复证据。

三组真实图形客户端分别保持严格 13 项默认策略及 42 条目录，核对独立计算的实际本服设备摘要、报告接受、生存模式和超过 60 秒连续在线，最后正常退出。三份 PNG 已由根代理实际打开检查；见 [Fabric/NeoForge 客户端报告](runtime-client-1.20.6.md)和 [Forge 客户端报告](runtime-client-forge-1.20.6.md)。用户正式验收仍为 false；本机离线环境不证明正版认证、真实 VM 对抗、负载性能或全部整合包兼容。

失败尝试保持可查：Forge 首包的 Mixin 配置与官方 0.8.5 不兼容，修复为兼容特征集声明并加入真实库检查后重建；下一轮机器人仅在登录后观察约 1.2 秒，未收到挑战便断言失败。增加有界等待及观测后，以相同产品 JAR 重跑 26 组通过；原失败现场没有完整握手观测，不能唯一确定其原因。测试协议库的 `PartialReadError` 日志仍公开保留，不据此宣称完整游戏协议兼容。详见上述构建、专服报告及[本轮汇总](../outputs/validation-0.5.0-dev-preview.1.json)。

当前 CI 配置收集 15 个现代 JAR，加上 8 个旧版 JAR，共 23 个。[开发提交 CI](ci-development-1.20.6.md)只验证较早的 `d342248`（当时现代收集器为 14 份，尚无 Forge 1.20.6）；GitHub 13 项通过，GitLab 13 项因额度不足未启动。最终标签需要独立检查，CI 重建字节不替代本机实测安装包。Grim / AntiXray 等第三方组件单独安装，本轮未验证它们的 1.20.6 组合。
