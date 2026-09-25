# 七章的裁决 · QiZhang's Verdict

插件标识 **QiZhangVerdict**，模组 ID `qizhangverdict`，管理命令 `/qzverdict`。本项目提供 IP/账号/设备准入、可管理的黑白名单、客户端协作检查和设备关联封禁。行为预测与矿物混淆使用独立安装、固定版本的开源组件，具体见 [集成安装](integrations/README.md)。

开发分支版本为 **0.2.0-test.1**，正在对新构建的各平台 JAR 重新验收；下方下载链接仍对应各自已经发布的历史版本。开发版将首次安装的默认名单扩展到 37 条，并修复管理员将自动化规则设为 DENY 后，BAN 策略漏记账号及设备关联封禁的问题。源码回归见 [默认名单检查](outputs/core-default-catalog-validation.json) 和 [自动化封禁回归](outputs/core-automation-sanction-validation.json)，这些报告本身不代表新版已发布。

## 测试版本 0.1.1

公开源码及测试安装包：[GitHub](https://github.com/EeryFrank/QiZhangVerdict/releases/tag/v0.1.1-test.1) · [GitLab](https://gitlab.com/EeryFrank/QiZhangVerdict/-/releases/v0.1.1-test.1)。当前版本采用 **GPL-3.0-only**，附完整许可证、对应源码包和 SHA256 校验文件。

| 安装位置 | 文件 |
|---|---|
| Paper/Spigot 系插件服 | `qizhangverdict-bukkit-0.1.1.jar` 放 `plugins/` |
| Fabric 1.20.1 服务端和客户端 | `qizhangverdict-fabric-1.20.1-0.1.1.jar` 放 `mods/`，另装 Fabric API |
| Forge 1.20.1 服务端和客户端 | `qizhangverdict-forge-1.20.1-0.1.1.jar` 放 `mods/` |
| Fabric 1.21.1 服务端和客户端 | `qizhangverdict-fabric-1.21.1-0.1.1.jar` 放 `mods/`，另装 Fabric API |
| NeoForge 1.21.1 服务端和客户端 | `qizhangverdict-neoforge-1.21.1-0.1.1.jar` 放 `mods/` |

1.20.1 使用 Java 17；1.21.1 使用 Java 21。新版修复 Forge 1.20.1 的报告事件方向和资源元数据警告；首个 0.1.0 测试版的 Forge 组合未通过后续真实客户端验收。当前验收与开发状态见 [兼容矩阵](docs/compatibility-matrix.md) 和 [客户端记录](docs/client-matrix.md)。插件在 Java 8 上兼容旧 Bukkit API，并已补测五个旧 Paper 版本的准入规则；尚无配套客户端的旧版仍不能直接部署完整设备验证。插件服玩家也需要匹配游戏版本/加载器的客户端模组。

同一服务器只安装插件或服务器模组中的一种。第三方 Grim/AntiXray 是另外的组件。不要把所有平台 JAR 一起放进一个 `mods` 文件夹。服务端插件无法自动安装到玩家客户端。

## 旧版开发预览

1.8.9 / 1.12.2 Forge，以及 1.16.5 / 1.18.2 / 1.19.4 Fabric、Forge 的八个模组已完成构建与真实客户端/专服测试；另有 1.8.9 Forge 客户端连接 Paper 1.8.8、1.12.2 Forge 客户端连接 Paper 1.12.2 的验收。下载：[GitHub 0.2.0-dev-preview.2](https://github.com/EeryFrank/QiZhangVerdict/releases/tag/v0.2.0-dev-preview.2) · [GitLab 0.2.0-dev-preview.2](https://gitlab.com/EeryFrank/QiZhangVerdict/-/releases/v0.2.0-dev-preview.2)。安装组合、证据和限制见 [旧版测试包说明](docs/preview-0.2.0-dev-preview.2.md)。本机 1.8.9 图形客户端验收需要关闭 Forge 启动画面，具体设置见说明；没有原生 Forge 1.8.8 模组。预览沿用已发布 0.1.1 Bukkit 和 preview.1 七个模组的原始文件，新增 1.8.9 模组。

preview.2 已在两站公开发布，每站 17 个附件均经匿名下载核对 SHA256，见 [发布回执](outputs/publish-receipt-0.2.0-dev-preview.2.json)。最终标签的 GitHub 9 项构建检查通过；GitLab 9 项因 CI 配额不足未执行。

## 默认登录规则

- 同一个 IP、同一个设备标识：最多 **1 个同时在线账号**。
- 同一个 IP、不同设备标识：最多 **3 个同时在线账号**，可改为 2。
- 同 IP 30 天内：最多 5 个不同 UUID，滚动窗口与同时在线限制独立。
- 每 IP 每分钟最多 20 次已进入服务端准入事件的登录尝试。它不是网卡级 DDoS 防护。
- 强制配套模组及非空设备标识；20 秒未完成报告则断开，等待期间限制操作。
- 已知虚拟机信号默认拒绝；未知/探测失败/VBS 单项信号仅告警。
- 已确认的黑名单规则命中默认持久化封禁账号、已关联设备和关联账号；并发人数、IP 拒绝、格式错误、报告超时只拒绝本次会话。

设备为客户端自报哈希标识，并不是不可伪造的硬件认证。相同机器不同启动器通常会使用相同系统安装 ID；重装系统、修改客户端或随机 ID 回退可能改变标识。详情见 [隐私与边界](docs/privacy-and-limits.md)。

## 配置与备份

插件目录为 `plugins/QiZhangVerdict/`，模组目录为 `config/qizhangverdict/`。首次启动生成：

- `guard.properties`：IP/账号/设备/报告/处罚策略。
- `blacklist.tsv`：附官方来源的精确默认规则。
- `rules.tsv`：管理员增删的黑白名单，支持 `EXACT` 和 `GLOB`。
- `accounts.state`：滚动账号记录、设备关联与账号/设备封禁。
- `server-id.txt`：设备哈希使用的本服公开范围标识，必须随账号状态一起备份；不要每次启动删除。

常用设置：

```properties
limits.max-online-per-ip=3
limits.max-online-per-ip-device=1
limits.max-accounts-per-ip=5
limits.account-window-hours=720
limits.attempts-per-minute=20
ip.allow=
ip.deny=192.0.2.0/24,2001:db8::/32
companion.required=true
companion.timeout-seconds=20
device.required=true
vm.action=DENY
blacklist.action=DENY
sanctions.on-deny=BAN
```

`ip.allow` 留空表示允许任意 IP，再应用拒绝名单；有内容则只允许列出的地址/网段。`ip.deny` 优先。支持 IPv4、IPv6、CIDR，IPv4-mapped IPv6 不另算一个地址。示例网段是文档保留地址，请替换为服主实际规则。

修改配置后 `/qzverdict reload`。无效配置会拒绝重载并保留上一份有效规则；Bukkit 首次加载失败会保留拒绝登录的监听器，修复后重启。规则和封禁管理立即影响新登录，在线关联封禁最迟下一次每秒检查被踢出。自动封禁由后台定期写盘、正常停服再次刷新；断电前尚未落盘的最近记录可能丢失。

`sanctions.on-deny=KICK` 可把规则命中改为只踢出。`blacklist.action`、`vm.action` 支持 `OFF/ALERT/DENY`。关闭 `companion.required` 前必须同时关闭 `device.required`，且不能保持 `vm.action=DENY`；这样运行会失去可靠执行客户端报告策略的前提。

## 管理命令

插件需 `qzverdict.admin`（默认 OP）；模组需权限等级 3。以下命令在两端通用：

```text
/qzverdict status
/qzverdict reload
/qzverdict rule list
/qzverdict rule list 2
/qzverdict rule add BLACK MOD EXACT meteor-client
/qzverdict rule add BLACK MOD GLOB customcheat*
/qzverdict rule add BLACK PACK GLOB *xray*
/qzverdict rule add WHITE MOD EXACT allowed_example
/qzverdict rule remove <规则ID>
/qzverdict ban <玩家UUID> <原因>
/qzverdict bans
/qzverdict bans 2
/qzverdict unban <玩家UUID>
/qzverdict unban device:<64位设备哈希>
```

列表为 `BLACK/WHITE`；类别为 `MOD/PACK/BRAND/PLAYER/DEVICE`；`PLAYER` 值为 UUID，`DEVICE` 值为哈希。默认规则也可删除，例如 `legacy:mod:meteor-client`。`*` 匹配任意字符，`?` 匹配一个字符，不支持正则表达式；采用完整值匹配，模组 ID 忽略大小写。不要配置过宽的规则（如 `*`），资源包模糊规则同样可能误伤。

白名单只允许对应项目，不解除已经产生的账号/设备封禁，不绕过 IP 配额。账号与设备需要分别解封；关联的其他账号也需按封禁列表逐项确认。`ban` 也支持当前在线玩家的精确名字，离线玩家使用 UUID。插件额外提供 `/qzverdict integrations` 查看外部组件是否启用。`BRAND` 由插件端收集；模组端目前不收集品牌，该类别在模组服不执行。

## 黑名单与防透视

开发版首次生成的 `blacklist.tsv` 包含 **37 个精确 ID：33 条 DENY、4 条 ALERT**。`baritone`、`baritoe`、`atianxray`、`keystrokesmod` 默认仅告警，服主可按玩法调整。不会因 `xray` 子串封掉正常的 `antixray`，也不默认封 Sodium、Iris、JEI、地图、投影等正常模组；存在正常项目重名的 `bigrat` 和通用 `template` ID 未设为默认拒绝。

完整 [37 条可核验目录与合并工具](docs/catalog.md) 包含固定源码提交和描述符证据。已有安装的名单文件保持原样，包括管理员的 OFF 设置和删除记录；升级不会自动回填。管理员可审阅后显式合并新增规则。历史发布包的默认规则与目录数量以对应 tag 为准。

名单不是全市场数据库，也无法发现所有改名、注入或伪造上报的作弊。资源包透视和未知外挂需要服务端矿物混淆及行为检测；[锁定依赖与配置](integrations/README.md) 提供 Paper、Fabric、Forge、NeoForge 安装组合。Forge/NeoForge 组合含矿物混淆，目前没有 Grim 行为预测引擎，不能宣称各平台行为检测能力相同。

1.20.1 / 1.21.1 插件组合完成了真实 Grim 检查触发、账号与设备关联封禁、重启持久化及解封验证，共 24 组断言；具体版本、处罚阈值及限制见 [现代联动验收](docs/grim-linked-ban-validation.md)。Paper 1.8.8 / 1.12.2 / 1.16.5 另通过 42 组联动与明确坐标矿石隐藏检查，见 [旧版 Paper 记录](docs/legacy-paper-integration-validation.md)。两份报告均使用历史 Bukkit 0.1.1，不替代开发版的成品验收。

## 构建与验证

Windows 使用 JDK 21 运行 `scripts/build.ps1`，1.20.1 工程另需可发现的 JDK 17 工具链；构建机的 JDK 路径可在版本工程 `gradle.properties` 中调整。缓存放 `E:\CodexTemp`，JAR 在各模块的 `build/libs/`。根构建 `gradlew.bat build` 构建核心与插件，两个平台工程分别构建模组；完成验收后用 Python 3.12+ 执行 `scripts/package_release.py`，发行 ZIP 输出到 `outputs/`，脚本拒绝打包与验收散列不符的 JAR。真实验证范围、产物散列及证据路径记录在 `outputs/validation-0.1.1.json`（发行包根目录为 `validation.json`）和 `docs/validation-0.1.1.md`，未列为通过的项目均未验收。

当前原始实现按 **GPL-3.0-only** 提供，全文见 [LICENSE](LICENSE)；独立第三方组件保留各自许可证与来源，本项目 JAR 未打包 Grim 或 AntiXray 的实现。
