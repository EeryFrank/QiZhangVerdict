# 七章的裁决：参考研究与能力边界

核对日期：2026-09-25。来源优先上游仓库、官方文档、项目官方 Modrinth API；不使用盗版收费插件或泄漏代码。已实际固定下载组件详见 `integrations/dependencies.lock.json`，其中 SHA-512 与官方 API 一致，SHA-256 来自下载字节；下载通过不代表联机或反作弊准确率通过。

| 参考 | 核实结果与用途 |
| --- | --- |
| [GrimAC](https://github.com/GrimAnticheat/Grim) | 当前 README 宣称 1.8–26.2、Java 17+、Spigot/Paper/Folia/Fabric；核心 GPLv3，Modrinth 标记 GPL-3.0-or-later。本项目固定稳定发行 2.3.73 的 Bukkit/Fabric 包，均明确列出 1.20.1 和 1.21.1。参考移动模拟、延迟补偿和事件审计，不复制整套核心。 |
| [GrimAPI](https://github.com/GrimAnticheat/GrimAPI) | 独立 API 为 MIT。当前 master 已是 1.3+ EventChannel 风格，但固定 Grim 2.3.73 内真实嵌套 API 为 1.2.4.0，集成代码必须按固定包核对。 |
| [Updated-NoCheatPlus](https://github.com/Updated-NoCheatPlus/NoCheatPlus) | 简介宣称 MC 1.5–1.21、Bukkit/Spigot、GPLv3；适合作旧版研究。README 要求对应服务器与 ProtocolLib 版本；不能同时叠加多个处罚引擎而不检验冲突。 |
| [Orebfuscator](https://github.com/Imprex-Development/orebfuscator) | 当前要求 Java 17+、Spigot/Paper/Folia 1.16.5+、ProtocolLib 5.4.0+；GPLv3。提供矿物/方块实体混淆及距离可见性。不作为本次 Paper 默认依赖，以免与原生 Anti-Xray 重复处理区块。 |
| [Paper Anti-Xray](https://docs.papermc.io/paper/anti-xray/) | 服务端混淆区块，支持三种模式。官方明确种子逆推、已暴露矿物、范围扩展等边界；更强混淆需测量客户端和网络影响。配置已分别提供 1.20.1/1.21.1 片段。 |
| [DrexHD AntiXray](https://github.com/DrexHD/AntiXray)、[官方发行页](https://modrinth.com/mod/anti-xray) | MIT；官方有 Fabric、Forge、NeoForge 构建。已固定 Fabric/Forge 1.20.1 1.4.6 和 Fabric/NeoForge 1.21.1 1.4.8。不是仅有 Fabric 版本。源码分支 1.21 对应所查 1.21.1 发行系列。 |
| [Minecraft SQLite JDBC](https://github.com/Axionize/minecraft-sqlite-jdbc) | Apache-2.0。Fabric 首次实启动显示 Grim 默认历史库缺少驱动，已额外固定 3.53.2.0+2026-06-06 官方版本 EEE7nXWy，补齐历史库依赖。 |
| [Cloud Minecraft Modded](https://github.com/Incendo/cloud-minecraft-modded) | MIT。Grim 2.3.73 嵌套 Cloud beta.15 仅支持 >=1.21.11，1.21.1 必须另装官方 beta.10（WGE6VNhn）才能提供 Grim 管理命令；官方 Cloud 2 没有 1.20.1 构建，该版本的 Grim 自带命令仍不可用。 |

上游各页面可能更新不同步，宽泛 README 不能替代具体发行包支持。Grim 未发现官方 Forge/NeoForge 构建，因此这些组合只声称具备 QiZhangVerdict 的准入能力与 AntiXray，不冒充同等移动检测。混合端、ViaVersion、Geyser、Folia 和大型模组包也必须分别实测；Grim 明确豁免 Geyser 玩家。

## 黑名单证据

| 精确 mod ID | 一手元数据 |
| --- | --- |
| `meteor-client` | [Meteor fabric.mod.json](https://github.com/MeteorDevelopment/meteor-client/blob/master/src/main/resources/fabric.mod.json) |
| `wurst` | [Wurst fabric.mod.json](https://raw.githubusercontent.com/Wurst-Imperium/Wurst7/master/src/main/resources/fabric.mod.json) |
| `liquidbounce` | [LiquidBounce fabric.mod.json](https://raw.githubusercontent.com/CCBlueX/LiquidBounce/nextgen/src/main/resources/fabric.mod.json) |
| `bleachhack` | [BleachHack fabric.mod.json](https://raw.githubusercontent.com/BleachDev/BleachHack/master/src/main/resources/fabric.mod.json) |
| `advanced-xray-fabric` | [Advanced XRay fabric.mod.json](https://raw.githubusercontent.com/AdvancedXRay/XRay-Fabric/main/src/main/resources/fabric.mod.json) |
| `baritone` | [Baritone fabric.mod.json](https://raw.githubusercontent.com/cabaletta/baritone/1.21.4/fabric/src/main/resources/fabric.mod.json)；自动寻路/挖矿属于独立 automation 类，默认告警，由服规决定是否拒绝。 |

[Impact](https://impactclient.net/)、[Aristois 官方安装器](https://gitlab.com/Aristois/Installer)、[Inertia](https://inertiaclient.com/)、[Future](https://www.futureclient.net/)、[RusherHack](https://rusherhack.org/) 是有上游出处的候选品牌；本次没有验证这些全部版本的稳定 mod ID 或散列，因此不能把品牌名单说成覆盖指纹。Aristois 官网功能页本次无法获取。散列规则必须来自实际已确认样本，不能编造。

不能用 `contains("xray")` 当封禁条件，会误伤 `antixray`。Sodium、Iris、OptiFine、JEI/REI、地图和投影等工具不能因名字或类别默认误封；它们的特定功能可由服务器规则单独管理。玩家也不能把 Bukkit 服务端插件随客户端带进服务器；服务端插件审计属于管理员的供应链检查。

## 客户端上报与虚拟机

[FabricLoader API](https://github.com/FabricMC/fabric-loader/blob/master/src/main/java/net/fabricmc/loader/api/FabricLoader.java) 的 `getAllMods()` 只返回当前 Loader 实例。服务器无法直接读取远端文件；客户端模组必须主动上报。Forge 也正式支持[单边模组](https://docs.minecraftforge.net/en/1.19.x/concepts/sides/)。玩家控制自己的客户端时，可改名、删掉上报条目、改包、替换收集逻辑或伪造上报。nonce、会话绑定和过期控制可以防重放，不能证明进程未被修改。内置共享密钥不等于硬件可信证明。

纯服务端不能可靠识别虚拟机。协作客户端可以上报明确说明的少量厂商/设备信号，提供 `off/audit/deny-known`，未知状态保持可见。不要把 JVM 本身当作虚拟机作弊，也不能将 `HypervisorPresent=true` 一票拒绝：微软[Windows VBS](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/oem-vbs) 与内存完整性在正常物理机器上也使用 hypervisor；[QEMU 官方文档](https://www.qemu.org/docs/master/system/qemu-manpage.html)允许配置 SMBIOS 字段，说明厂商字符串只是启发式。

IP 配额应区分同时在线、滚动时间窗不同账号与长期绑定，考虑 NAT、家庭/网吧、IPv6 地址轮换和可信代理转发。设备标识同样可以重置/伪造，不应声称等于现实中的唯一自然人。封禁日志保存规则与证据类型，便于复核。

## 验证范围

本研究已实际核验 11 个独立第三方文件的字节散列、ZIP 完整性和描述符，6 个 profile 的版本/Loader 与官方依赖声明匹配。Purpur 1.20.1 + Grim Bukkit 2.3.73 实测存在 LOGIN 阶段 PacketEvents 错误，与[上游 #2569](https://github.com/GrimAnticheat/Grim/issues/2569)相似；该 profile 已改锁通过实际 TCP 测试的 2.3.71（4CqWKZph），1.21.1 仍锁 2.3.73。不能把本次具体组合的结果推广到所有服务器构建。

`integrations/manage_integrations.py` 只会输出到新目录，拒绝覆盖已有服务器；不自动将第三方并入自研 JAR。各平台启动日志及退出码由运行脚本独立生成，黑名单、设备识别、VM、协议与多人实战需要对应测试，不能由下载校验推导通过。
