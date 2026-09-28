# 0.4.0-dev-preview.1 测试预览合集

本合集含 20 个独立 JAR：完整保留 [0.3.0-dev-preview.1 的 18 份原件](preview-0.3.0-dev-preview.1.md)，新增 Minecraft 1.21.11 的 Fabric、NeoForge 两份 `0.4.0-dev` 成品。旧 JAR 不改版本号、不重新打包，历史运行证据只绑定原哈希。本说明随冻结源码分发；实际发布状态、最终标签 CI 和匿名下载验证以发布页面及后续回执为准。

## 选择安装包

| 服务器 / 玩家版本 | 使用的 Verdict JAR | Java 与依赖 |
| --- | --- | --- |
| 1.21.11 Fabric | `qizhangverdict-fabric-1.21.11-0.4.0-dev.jar` | Java 21；Fabric Loader 0.19.5；Fabric API 0.141.6+1.21.11 |
| 1.21.11 NeoForge | `qizhangverdict-neoforge-1.21.11-0.4.0-dev.jar` | Java 21；NeoForge 21.11.45 |
| 已有 Bukkit 或 1.8.9—1.21.1 指定适配 | 沿用旧合集对应的原始 JAR | 按[旧安装表](preview-0.3.0-dev-preview.1.md)选择具体游戏版本、加载器及 Java |

每个模组端仅放入与其游戏版本、加载器匹配的一份 Verdict JAR。匹配模组服的服务器和客户端均须安装；插件服服务器使用 Bukkit 实现，玩家安装匹配客户端模组。依赖另外安装，不能将 20 份 JAR 全部放入同一 `mods/`。本轮只验收两种 1.21.11 模组端的匹配组合，没有据此证明新客户端与 Bukkit 1.21.11、其他核心或代理网络兼容。

两份新 JAR 的固定 SHA-256：

- Fabric：`732ba77c6978785a8969c6f92476b8c57009be464b9210bfef2c9bb19c0d6ce5`，97,169 字节。
- NeoForge：`47dc8edff5faeb9c41ce19575bd37f49a2205877d99f814aa7acc33c0440d789`，95,394 字节。

## 安装与升级

1. 正常停服，备份全部 Verdict 配置。插件目录为 `plugins/QiZhangVerdict/`，模组目录为 `config/qizhangverdict/`。
2. 保留管理员的 `guard.properties`、`blacklist.tsv`、`rules.tsv`，以及 `accounts.state`、`server-id.txt`。设备关联依赖持久化的服务器范围；不要为升级删除这些文件，也不要公开上传它们。
3. 替换正确平台的 Verdict JAR，每个实例只保留一个版本。插件放入 `plugins/`；模组放入服务器及玩家对应实例的 `mods/`。Fabric API 单独放入 Fabric 实例。
4. 启动后检查 `/qzverdict status`、日志和测试账号准入，再开放服务器。命令和配置说明见 [README](../README.md)。生产服务器的账户认证、代理地址转发与第三方整合仍需独立确认。

首次生成配置保持严格策略：同 IP 最多 3 个同时在线账号，同 IP 同设备最多 1 个；`limits.max-online-per-ip=2` 可改成最多两台不同设备。配套报告和设备码默认必需，报告期限 20 秒；已识别的 VM 默认拒绝，黑名单拒绝处罚默认关联账号和已知设备。滚动窗口内的账号数量上限与在线人数上限独立。未知 VM 或单独 VBS 信号不能被当作已确认虚拟机。设备、模组和 VM 信号来自客户端自报，不是不可伪造的硬件证明。

## 37 条与 39 条规则的区别

**只有新增两份 1.21.11 成品首次安装时默认 39 条**：35 条 `DENY`、4 条 `ALERT`，新增 `ferox` 和 `wurstplusthree`。继承的 18 份 JAR 保留其原来的 **37 条**默认规则，并没有随着合集名称升级。现有管理员规则文件在任一版本都不会被构造器或 reload 自动覆盖；`OFF`、管理员白名单和已删除规则不会自动恢复。

旧服务器可按[目录合并流程](catalog.md)人工选择新增项：先复制并备份当前 `blacklist.tsv`，使用目录工具的 `merge --add mod:ferox --add mod:wurstplusthree` 生成独立候选，审阅冲突后再安装。此处两个 `--add` 必须与目录文档要求的 `--cache`、`--existing`、`--output`、`--report` 一起使用。已有相同 ID 的动作和来源保留，包括 `OFF`；只有管理员明确选择的缺失项才加入。若该 ID 曾被删除，显式 `--add` 是管理员重新加入的决定，不是后台恢复。

默认四条 `ALERT` 不等于封禁；精确 ID 与 GLOB 黑白名单须按服规审阅。目录只是已取得固定来源证明的规则，不保证包括全部作弊客户端、注入器、商业软件或资源包透视。

## 验证范围

[构建与静态审查](adapter-1.21.11.md)保留全部失败尝试、最终源码与成品哈希，以及两份精确 JAR 各 99 项核心断言。相同的 99 项还在源码环境执行一次；这不是 297 个不同用例。平台解析、编解码和连接调度测试另外列示，不能代替玩家联机。

[专服连接报告](runtime-server-1.21.11.md)中两种加载器各通过 26 组准入检查，共 52 次执行；这是 26 组定义在两端重复执行。该批量合成 TCP 夹具明确调整账号/频率/超时等测试配置，结束后逐字节恢复 13 项默认策略；规则编辑用例留下 40 条有效规则，不能把隔离夹具当成默认部署模板，也不能称为全程默认策略下的真实玩家测试。

两端真实图形客户端已经在匹配服务器完成自动检查，并由 Codex 根代理实际打开两份 PNG 逐图确认。该轮保持 13 项默认策略和首次 39 条目录，核对实际设备摘要、报告接受、生存模式及至少 60 秒持续在线，客户端和服务器正常退出。[真实客户端报告](runtime-client-1.21.11.md)公开原始结果、日志和两份截图的显式白名单。[本轮汇总](../outputs/validation-0.4.0-dev-preview.1.json)记录构建、运行与历史来源关系，打包元数据另行绑定具体源码提交。这是受控本机验证，**用户正式验收仍为 false**，也不证明正版登录、真实虚拟机样本、多玩家攻防或性能。

本版现代 CI 配置覆盖 12 个 JAR，旧版 CI 覆盖 8 个。[开发提交 CI](../outputs/ci-development-1.21.11.json)记录 `429284ed0fa296b04cf7a13253b2e95af048e5d6` 的 GitHub 12 项作业成功，GitLab 12 项因额度不足在启动前被拒绝，未计为通过。开发提交与最终发布标签分别记录；开发流水线不替代最终标签检查，CI 重建包也不替换本机实测的 20 个固定 JAR。打包清单取明确 Git 提交中的文档与证据原字节；ZIP 审计、最终标签 CI 及双站公开下载均为独立步骤，清单本身不代表发布成功。

Grim 和矿物混淆组件单独安装，本合集不分发这些第三方 JAR。历史集成证据不自动证明 1.21.11 的第三方组合；资源包透视仍需服务端矿物混淆。更多边界见[隐私与限制](privacy-and-limits.md)。原创实现为 **GPL-3.0-only**；发行附件包含 LICENSE、NOTICE、对应源码及 SHA256 文件。

## 对应源码与历史原件

这是一份混合组件合集，不能用本次单一源码 ZIP 声称重建全部旧 18 个原始 JAR。本次源码已将首次默认改为 39 条；旧二进制保留 37 条。新两份 `0.4.0-dev` 对应最终冻结的本次源码提交；继承的六份 Bukkit / 1.19.2 / 1.20.4 成品对应原 `0.3.0-dev-preview.1` 源码，其余 12 份 `0.2.0-test.1` 模组对应更早的原始源码提交。

| 原始源码关系 | 固定提交 | 原始源码 ZIP |
| --- | --- | --- |
| 12 份 `0.2.0-test.1` 模组 | `310e20b117183182d7767e349aa81cb1d935075c` | [GitHub 原件](https://github.com/EeryFrank/QiZhangVerdict/releases/download/v0.2.0-test.1/QiZhangVerdict-0.2.0-test.1-sources.zip) · [GitLab 原件](https://gitlab.com/EeryFrank/QiZhangVerdict/-/releases/v0.2.0-test.1/downloads/QiZhangVerdict-0.2.0-test.1-sources.zip) |
| Bukkit `0.2.1-dev` 与五份 `0.3.0-dev` 模组 | `f633a30badb882cfdb8606a7fefd88e5ce28bb2b` | [GitHub 原件](https://github.com/EeryFrank/QiZhangVerdict/releases/download/v0.3.0-dev-preview.1/QiZhangVerdict-0.3.0-dev-preview.1-sources.zip) · [GitLab 原件](https://gitlab.com/EeryFrank/QiZhangVerdict/-/releases/v0.3.0-dev-preview.1/downloads/QiZhangVerdict-0.3.0-dev-preview.1-sources.zip) |

旧 0.3 合集的 [GitHub 标签与安装包](https://github.com/EeryFrank/QiZhangVerdict/releases/tag/v0.3.0-dev-preview.1)、[GitLab 标签与安装包](https://gitlab.com/EeryFrank/QiZhangVerdict/-/releases/v0.3.0-dev-preview.1)继续保留。历史回执记录的源码 ZIP SHA-256 分别为 `2a0ee6445ceed36baf6beb03218d3709993aebd1b47400eeed39ba344709d6cc`（0.2，7,844,940 字节）与 `75f59676ebd7c033ab051705e6214b2e0fea5f2a0c00311cdc69908593e22940`（0.3，9,725,615 字节），可见 [0.2 回执](../outputs/publish-receipt-0.2.0-test.1.json)和 [0.3 回执](../outputs/publish-receipt-0.3.0-dev-preview.1.json)。这些是既有发布记录，不是本轮重新下载验证声明。

本合集另外提供上述两份旧源码 ZIP 的原始字节，并保留原发布入口。连同本次源码，共三个对应源码 ZIP，按组件来源选择；不将旧源码包重新打包冒称原件。源码 ZIP 不进入运行 JAR 清单；各自许可、NOTICE、构建脚本和依赖版本随对应源码提供。
