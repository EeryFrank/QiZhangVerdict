# 七章的裁决 · QiZhang's Verdict

插件标识 **QiZhangVerdict**，模组 ID `qizhangverdict`，管理命令 `/qzverdict`。本项目提供 IP/账号/设备准入、可管理的黑白名单、客户端协作检查和设备关联封禁。行为预测与矿物混淆使用独立安装、固定版本的开源组件，具体见 [集成安装](integrations/README.md)。

## 首批版本

| 安装位置 | 文件 |
|---|---|
| Paper/Spigot 系插件服 | `qizhangverdict-bukkit-0.1.0.jar` 放 `plugins/` |
| Fabric 1.20.1 服务端和客户端 | `qizhangverdict-fabric-1.20.1-0.1.0.jar` 放 `mods/`，另装 Fabric API |
| Forge 1.20.1 服务端和客户端 | `qizhangverdict-forge-1.20.1-0.1.0.jar` 放 `mods/` |
| Fabric 1.21.1 服务端和客户端 | `qizhangverdict-fabric-1.21.1-0.1.0.jar` 放 `mods/`，另装 Fabric API |
| NeoForge 1.21.1 服务端和客户端 | `qizhangverdict-neoforge-1.21.1-0.1.0.jar` 放 `mods/` |

1.20.1 使用 Java 17；1.21.1 使用 Java 21。插件在旧 Bukkit API 上编译为 Java 8 字节码，但“可编译”不等于所有旧版本已经启动/联机实测。首批明确以 1.20.1/1.21.1 为验收目标；其他版本、Folia、代理群服、混合端、基岩互通须单独验证，不能用本报告冒充支持。插件服的玩家也需要安装匹配游戏版本/加载器的客户端模组，才能执行默认设备规则。

同一服务器只安装插件或服务器模组中的一种。第三方 Grim/AntiXray 是另外的组件。不要把所有平台 JAR 一起放进一个 `mods` 文件夹。服务端插件无法自动安装到玩家客户端。

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

默认精确拒绝 Meteor、Wurst、LiquidBounce、BleachHack、Advanced XRay Fabric、Advanced XRay、ThunderHack、3arthh4ck、KAMI Blue、SalHack 的已核验标识。Baritone 默认仅告警，服主可按玩法添加拒绝规则。不会因 `xray` 子串封掉正常的 `antixray`，也不默认封 Sodium、Iris、JEI、地图、投影等正常模组。

名单不是全市场数据库，也无法发现所有改名、注入或伪造上报的作弊。资源包透视和未知外挂需要服务端矿物混淆及行为检测；[锁定依赖与配置](integrations/README.md) 提供 Paper、Fabric、Forge、NeoForge 安装组合。Forge/NeoForge 组合含矿物混淆，目前没有 Grim 行为预测引擎，不能宣称各平台行为检测能力相同。

## 构建与验证

Windows 使用 JDK 21 运行 `scripts/build.ps1`，1.20.1 工程另需可发现的 JDK 17 工具链；构建机的 JDK 路径可在版本工程 `gradle.properties` 中调整。缓存放 `E:\CodexTemp`，JAR 在各模块的 `build/libs/`。根构建 `gradlew.bat build` 构建核心与插件，两个平台工程分别构建模组；完成验收后用 Python 3.12+ 执行 `scripts/package_release.py`，发行 ZIP 输出到 `outputs/`，脚本拒绝打包与验收散列不符的 JAR。真实验证范围、产物散列及证据路径记录在 `outputs/validation.json`（发行包根目录为 `validation.json`）和 `docs/validation.md`，未列为通过的项目均未验收。

原始实现按 Apache-2.0 提供；独立第三方组件保留各自许可证与来源，本项目 JAR 未打包 Grim 或 AntiXray 的实现。
