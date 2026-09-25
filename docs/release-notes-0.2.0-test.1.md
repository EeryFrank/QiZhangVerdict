# 七章的裁决 0.2.0-test.1

公开测试版，原创代码使用 **GPL-3.0-only**。包含 13 个独立安装包：一个 Bukkit 插件，以及 1.8.9、1.12.2 Forge，1.16.5、1.18.2、1.19.4、1.20.1 Fabric / Forge，1.21.1 Fabric / NeoForge 模组。

首次安装的默认名单扩展为 37 个有固定源码证据的精确 ID（33 DENY、4 ALERT）；已有名单、OFF 设置和删除记录保持原样。修复自动化规则设为 DENY、处罚设为 BAN 时未登记账号及设备关联封禁的问题。

支持黑白名单增删、GLOB 模糊匹配、IP/CIDR 限制、账号和设备关联封禁。默认同 IP 同设备最多 1 人在线，同 IP 不同设备最多 3 人在线；可配置。设备报告和虚拟机信号来自客户端，不能保证识别伪造报告或所有作弊。

安装和升级步骤见[本版指南](release-0.2.0-test.1.md)，逐包散列和验收范围见[验证汇总](../outputs/validation-0.2.0-test.1.json)。源码 ZIP 对应本标签的完整 Git 文件，`SHA256SUMS.txt` 可用于核对下载。只安装对应平台的一个 JAR；Fabric 另需匹配的 Fabric API，插件服玩家也需要配套客户端模组。

1.8.9 本机图形验收使用 `config/splash.properties` 的 `enabled=false`；没有原生 Forge 1.8.8 包，Paper 1.8.8 配套使用 Forge 1.8.9 客户端。其他小版本、混合核心、代理网络和大型整合包需要单独验证。Grim 与 AntiXray 独立安装，不包含在这 13 个 JAR 中。
