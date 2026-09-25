# 七章的裁决 · QiZhang's Verdict

插件标识 **QiZhangVerdict**，模组 ID `qizhangverdict`，管理命令 `/qzverdict`。本项目提供 IP/账号/设备准入、可管理的黑白名单、客户端协作检查和设备关联封禁。行为预测与矿物混淆使用独立安装、固定版本的开源组件，具体见 [集成安装](integrations/README.md)。

## 测试版 0.2.0-test.1

公开源码及 13 个安装包：[GitHub](https://github.com/EeryFrank/QiZhangVerdict/releases/tag/v0.2.0-test.1) · [GitLab](https://gitlab.com/EeryFrank/QiZhangVerdict/-/releases/v0.2.0-test.1)。原创代码使用 **GPL-3.0-only**，附完整许可证、对应源码 ZIP 和 SHA256 校验文件。

包括一个 Bukkit 插件和 12 个模组：1.8.9、1.12.2 Forge，1.16.5、1.18.2、1.19.4、1.20.1 Fabric / Forge，以及 1.21.1 Fabric / NeoForge。安装包选择、Java 要求和升级步骤见[本版指南](docs/release-0.2.0-test.1.md)。插件服玩家也需要匹配的客户端模组；同一服务器只安装一个 Verdict 服务端实现。

本版首次默认名单为 37 条，保留已有管理员规则；修复自动化规则设为 DENY 时 BAN 策略漏记账号及设备关联封禁的问题。13 个原始成品均通过核心回归；14 组真实图形客户端/专服组合和插件服 75 组协议检查通过。准确散列、条件及证据见[验证汇总](outputs/validation-0.2.0-test.1.json)。这些测试不代表全部版本、全部作弊或真实多人实战均已验证。

1.8.9 本机图形验收需关闭 Forge 启动画面；Paper 1.8.8 使用 Forge 1.8.9 配套客户端，没有原生 Forge 1.8.8 成品。Grim / AntiXray 独立安装，不包含在这 13 个 JAR 中。

历史版本保持原字节和原验证范围：[0.1.1](docs/validation-0.1.1.md)、[preview.1](docs/preview-0.2.0-dev-preview.1.md)、[preview.2](docs/preview-0.2.0-dev-preview.2.md)。

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

0.2.0-test.1 首次生成的 `blacklist.tsv` 包含 **37 个精确 ID：33 条 DENY、4 条 ALERT**。`baritone`、`baritoe`、`atianxray`、`keystrokesmod` 默认仅告警，服主可按玩法调整。不会因 `xray` 子串封掉正常的 `antixray`，也不默认封 Sodium、Iris、JEI、地图、投影等正常模组；存在正常项目重名的 `bigrat` 和通用 `template` ID 未设为默认拒绝。

完整 [37 条可核验目录与合并工具](docs/catalog.md) 包含固定源码提交和描述符证据。已有安装的名单文件保持原样，包括管理员的 OFF 设置和删除记录；升级不会自动回填。管理员可审阅后显式合并新增规则。历史发布包的默认规则与目录数量以对应 tag 为准。

名单不是全市场数据库，也无法发现所有改名、注入或伪造上报的作弊。资源包透视和未知外挂需要服务端矿物混淆及行为检测；[锁定依赖与配置](integrations/README.md) 提供 Paper、Fabric、Forge、NeoForge 安装组合。Forge/NeoForge 组合含矿物混淆，目前没有 Grim 行为预测引擎，不能宣称各平台行为检测能力相同。

1.20.1 / 1.21.1 插件组合完成了真实 Grim 检查触发、账号与设备关联封禁、重启持久化及解封验证，共 24 组断言；具体版本、处罚阈值及限制见 [现代联动验收](docs/grim-linked-ban-validation.md)。Paper 1.8.8 / 1.12.2 / 1.16.5 另通过 42 组联动与明确坐标矿石隐藏检查，见 [旧版 Paper 记录](docs/legacy-paper-integration-validation.md)。两份报告均使用历史 Bukkit 0.1.1，不替代 0.2.0-test.1 的成品验收。

## 构建与验证

构建路径及工具链见[CI 说明](docs/ci.md)；1.8.9 / 1.12.2 使用独立旧版 Gradle 和 JDK 8，其余版本各自使用固定工具链。缓存放 `E:\CodexTemp`，成品在对应模块的 `build/libs/`。

本版使用 `scripts/package_preview.py` 的显式清单打包流程。先提交审阅后的源码、报告与 `outputs/release-manifest-0.2.0-test.1.json`，再以完整提交 SHA 执行 `verify` 和 `package`；产物输出 `outputs/`。打包器核对每个 JAR 的原始散列、GPL/NOTICE、固定 Git 源码与证据，拒绝覆盖既有发布目录。`scripts/package_release.py` 保留历史 0.1.1 流程，不用于本版 13 包发行。

当前原始实现按 **GPL-3.0-only** 提供，全文见 [LICENSE](LICENSE)；独立第三方组件保留各自许可证与来源，本项目 JAR 未打包 Grim 或 AntiXray 的实现。
