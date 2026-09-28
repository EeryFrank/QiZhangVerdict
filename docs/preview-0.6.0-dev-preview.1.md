# 0.6.0-dev-preview.1 测试预览合集

本合集包含 **25 个独立 JAR**：保留 [0.5 预览的 23 份原件](preview-0.5.0-dev-preview.1.md)，新增 Minecraft **1.17.1 Fabric / Forge** 两份 `0.6.0-dev` 模组。旧组件不重新打包或冒充重新验收。本说明随冻结源码分发；上传、最终标签 CI 与匿名下载验证以发布页面和后续回执为准。

## 选择安装包

| 游戏与加载器 | Verdict JAR | 已验证依赖 |
| --- | --- | --- |
| 1.17.1 Fabric | `qizhangverdict-fabric-1.17.1-0.6.0-dev.jar` | Java 16；Fabric Loader 0.19.5；Fabric API 0.46.1+1.17 |
| 1.17.1 Forge | `qizhangverdict-forge-1.17.1-0.6.0-dev.jar` | Java 16；Forge 37.1.1 |
| 既有 Bukkit 与其他指定模组版本 | 保留原组件版本和文件名 | 见 [0.5 安装表及历史指南](preview-0.5.0-dev-preview.1.md#选择安装包) |

每个实例只装匹配游戏版本和加载器的一份 Verdict；模组服的服务器和玩家客户端都需安装。Fabric API 另装，不要把合集所有 JAR 放入同一实例。1.17.1 本轮实际图形联机只覆盖同加载器专服，不证明插件服、代理或跨加载器互通。

| 新成品 | 字节 | SHA-256 |
| --- | ---: | --- |
| Fabric | 95434 | `bda006d24663acb3698c8fb76d06d14220dfca18422c8eb9177499f5c498e497` |
| Forge | 99008 | `a71d6bb215426927b5db4cf2ea6278aa4bc92615d750d1bfa42b7d1469dde813` |

## 安装与升级

1. 正常停服并备份整个 Verdict 配置目录：插件为 `plugins/QiZhangVerdict/`，模组为 `config/qizhangverdict/`。
2. 保留 `guard.properties`、`blacklist.tsv`、`rules.tsv`、`accounts.state` 和 `server-id.txt`。后两项维持设备关联，不应删除或上传公开仓库。
3. 替换对应平台 JAR，每个实例只保留一个版本。使用测试账号检查 `/qzverdict status`、准入、日志和管理员操作后再开放服务器。

默认同 IP 同设备最多 1 个同时在线账号；同 IP 不同设备合计最多 3 个，`limits.max-online-per-ip=2` 可改为总共 2 个。30 天内每 IP 最多 5 个 UUID 的记录与同时在线人数独立。报告及设备标识默认必需，20 秒未完成则断开；已知 VM 信号拒绝，未知或单独 VBS 信号仅告警。黑名单命中默认关联封禁账号、已知设备与关联账号；配额、IP 拒绝、超时和格式错误只拒绝本次会话。配置、GLOB 与解封方法见 [README](../README.md#默认登录规则)。

新包首次启动默认 **44 条规则：40 DENY、4 ALERT**，新增 `dualviewxray`、`simplexray`。同名普通模组使用的 `hydrogen`、`lumina` 不加入默认拒绝。现有名单、白名单、OFF 和删除项不会自动覆盖或回填；需管理员按[目录流程](catalog.md)审阅后显式合并。旧 18 份仍默认 37 条、两个 1.21.11 包仍默认 39 条、三个 1.20.6 包仍默认 42 条。

设备和 VM 信号来自客户端自报，可被伪造或重置，不能视作硬件认证。名单与 GLOB 也无法保证识别全部商业作弊、注入器和资源包透视；矿物隐藏仍需服务端混淆。Grim、AntiXray 等第三方组件单独安装，本轮没有验证其 1.17.1 组合。

## 对应源码与验证范围

原创实现采用 **GPL-3.0-only**。合集提供五代对应源码，每代保留 LICENSE、NOTICE 和构建文件：

| 组件来源 | 对应源码 ZIP | 固定源码提交 |
| --- | --- | --- |
| 12 个 `0.2.0-test.1` 模组 | `QiZhangVerdict-0.2.0-test.1-sources.zip` | `310e20b117183182d7767e349aa81cb1d935075c` |
| Bukkit `0.2.1-dev` 与五个 `0.3.0-dev` 模组 | `QiZhangVerdict-0.3.0-dev-preview.1-sources.zip` | `f633a30badb882cfdb8606a7fefd88e5ce28bb2b` |
| 两个 1.21.11 `0.4.0-dev` 模组 | `QiZhangVerdict-0.4.0-dev-preview.1-sources.zip` | `eb6d483e64e29a15501df953f7d59a9645a6905a` |
| 三个 1.20.6 `0.5.0-dev` 模组 | `QiZhangVerdict-0.5.0-dev-preview.1-sources.zip` | `13b3e05996f2abaf97a4616fe7c9a2e5d5288916` |
| 两个 1.17.1 `0.6.0-dev` 模组 | `QiZhangVerdict-0.6.0-dev-preview.1-sources.zip` | 由本次 `packaging.json` 和最终标签绑定 |

四份历史源码 ZIP 保留原字节；最新 44 条目录源码不被表述为可重建旧默认目录成品的原字节。旧源包散列与发布入口见 [0.5 指南](preview-0.5.0-dev-preview.1.md#规则与对应源码)和[回执](../outputs/publish-receipt-0.5.0-dev-preview.1.json)。

两份新包各通过 **104 项包内核心检查**（57 安全回归、44 目录、3 保留和普通 ID 控制），共 208 次执行；各通过 **26 组 TCP 准入**，共 52 次执行。TCP 使用明示临时测试策略并在结束后恢复全部 13 项默认属性，不能说全程默认配置。平台 smoke 另计，测试数量不代表不同作弊样本数量。[构建](adapter-1.17.1.md)、[专服](runtime-server-1.17.1.md)分别保留成品、日志和历史尝试。

两组图形客户端均保持严格 13 项默认策略、44 条规则，独立重算实际本服设备摘要，核对报告、生存模式和报告后超过 60 秒持续在线，双端正常退出 0，截图已由根代理打开检查。详见[图形报告](runtime-client-1.17.1.md)。用户正式验收为 false；本机离线验证不证明正版认证、真实 VM 对抗、生产负载或完整整合包玩法。

**已知问题保留：** Fabric 首次以同一最终 JAR 启动曾发生模型初始化崩溃；无 Guard 对照和同包复测成功，但根因未定，不能据此宣称问题已修复。Forge 的标准通道挑战发送和 NOP 日志问题已修复并用最终包重新跑完专服及图形验证；旧安装校验、报告超时和客户端启动前等待失败均单独保留。

CI 收集 17 个现代 JAR，加 8 个旧版 JAR，共 25 个。开发提交与最终标签必须分别核验；CI 重建不会替换本机实测的发布字节，配额导致未启动的任务不计通过。
