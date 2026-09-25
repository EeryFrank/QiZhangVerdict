# 七章的裁决：已固定的防护组件

这些组件保持独立 JAR，不会打入 QiZhangVerdict 自身产物。`dependencies.lock.json` 保存官方 Modrinth 项目和不可变版本 ID、下载地址、许可证/源码地址、平台范围、真实 JAR 描述符、官方 SHA-512 和下载后计算的 SHA-256。清单已实际下载核验；启动、玩家联机和反作弊准确率是不同层次的验证。

旧版组件使用独立的 `legacy-dependencies.lock.json`。该暂存清单自身仍保留最初的输入核验范围；后续独立实测不能当成清单中每个组合都已通过。Paper 1.8.8 / 1.12.2 / 1.16.5 的 Grim 2.3.67 联动和原生矿物混淆已完成 [42 组检查](../docs/legacy-paper-integration-validation.md)，对应的三个 `paper-*-anti-xray.example.yml` 和 `grim-legacy-2.3.67-verdict.example.yml` 需人工合并到实际配置，保留原有版本字段。Fabric 1.16.5 官方 AntiXray 1.1.0 的 refmap 启动故障和独立补丁见 [Java 17 兼容说明](../docs/legacy-fabric116-antixray-qzcompat1-java17.md)与[补丁工具](compat/README.md)。上述运行记录均使用报告指定的旧 Verdict JAR；其余旧版组合的 Java 要求和待验证项见[候选说明](../docs/legacy-integration-candidates.md)。

| profile | 已固定组件 | 能力范围 |
| --- | --- | --- |
| `paper-1.20.1` | Grim Bukkit 2.3.71 + Paper 内置 Anti-Xray 配置片段 | 行为检测与矿物混淆；已验证 Purpur 1.20.1 |
| `paper-1.21.1` | Grim Bukkit 2.3.73 + Paper 内置 Anti-Xray 配置片段 | 行为检测与矿物混淆；已验证 Purpur 1.21.1 |
| `fabric-1.20.1` | Grim Fabric 2.3.73 + AntiXray 1.4.6 + Fabric API 0.92.12 + SQLite JDBC 3.53.2.0 | 行为检测、历史库与矿物混淆 |
| `fabric-1.21.1` | Grim Fabric 2.3.73 + AntiXray 1.4.8 + Fabric API 0.116.17 + SQLite JDBC 3.53.2.0 + Cloud beta.10 | 行为检测、历史库、Grim 命令与矿物混淆 |
| `forge-1.20.1` | AntiXray 1.4.6 | 矿物混淆；未宣称具有 Grim 行为检测 |
| `neoforge-1.21.1` | AntiXray 1.4.8 | 矿物混淆；未宣称具有 Grim 行为检测 |

Purpur 1.20.1 搭配 Grim Bukkit 2.3.73 时实际复现 LOGIN 阶段 PacketEvents 随机大 Packet ID 错误，普通客户端会被拒绝；上游也有[相似报告 #2569](https://github.com/GrimAnticheat/Grim/issues/2569)。该 profile 单独固定较旧稳定版 2.3.71（2025-04-17，Modrinth `4CqWKZph`），在默认网络压缩阈值 256 下通过 25 项实际 TCP 协议检查，包括准入限制、设备联动、OP 命令隔离与原生 Anti-Xray 假矿石。1.21.1 保持已验证的 2.3.73。旧版本不代表覆盖之后所有检查修复；升级、换 Paper/Purpur 构建或添加网络插件后必须重新验证，不能直接替换为 `latest`。

Grim 官方没有 Forge/NeoForge 发行包，不向模组服强装 Bukkit 插件。Grim Fabric 2.3.73 自带嵌套 PacketEvents 与 GrimAPI 1.2.4.0；无需额外安装 PacketEvents。Grim 要求 Java 17+、Fabric Loader 0.16+，MC 1.21.1 服务端本身要求 Java 21；最终还应满足实际所选 Loader 要求。其他会改变移动、攻击距离和碰撞的模组必须做兼容性测试。Geyser 玩家由 Grim 豁免，不能声称这些玩家已获得相同行为检查。

实际 Fabric 专服启动暴露出 Grim 默认历史库缺少 SQLite 驱动的问题，已把其启动日志指定的 [Minecraft SQLite JDBC](https://github.com/Axionize/minecraft-sqlite-jdbc) 独立模组加入固定组合（Apache-2.0）。这项依赖没有出现在 Grim 的 Modrinth 必需依赖列表，仅静态清单检查发现不了。Paper 组合不重复添加 JDBC 驱动。

Grim 2.3.73 内嵌的 Cloud beta.15 描述符限定 Minecraft >=1.21.11，在较旧版本会被跳过。1.21.1 组合额外固定官方兼容的 [Cloud beta.10](https://modrinth.com/mod/cloud-minecraft-modded/version/WGE6VNhn)（MIT），实际启动已不再出现命令框架缺失告警。Cloud 2 官方发行列表没有 1.20.1 构建，因此 Fabric 1.20.1 的 Grim 检测可启动，但其自带 `/grim` 命令不可用；QiZhangVerdict 的 `/qzverdict` 不受影响。不要强改第三方版本声明来掩盖这个缺口。

Fabric 日志仍保留上游 PacketEvents 的非致命 `Failed reading REFMAP JSON` / NPE：实际嵌套包中的 `PacketEventsMixinManager.getRefMapperConfig()` 返回空字符串，三个相关 mixin JSON 均指定该插件；已用真实 JAR 元数据和 `javap` 字节码核实，记录在 `upstream-runtime-notices.json`。这不是 QiZhangVerdict 自身 mixin 的加载失败。启动 PASS 的定义是服务达到 Done、自己的状态命令响应、依赖初始化与正常退出，**不等于日志没有错误，也不证明 Grim 每项检测准确**。

Forge 1.20.1 的 AntiXray 1.4.6 还会对自身两份 mixin 配置缺少 `minVersion` 打印 ERROR，随后初始化成功；该上游描述符问题同样保留在上述记录和原始日志中。

## 安全下载与准备安装

只需 Python 3.10+ 和标准库。以下命令读取已经固定的清单，不追踪 `latest`。`--output` 必须是不存在或完全空的文件夹，路径不允许经过符号链接或 junction；已有服务器会被拒绝。运行结果是可审查的安装目录，不会修改现存服。

```powershell
python E:\Codex_work\QiZhangVerdict\integrations\manage_integrations.py stage --profile fabric-1.21.1 --cache E:\CodexTemp\QiZhangGuard\downloads\integrations --output E:\CodexTemp\QiZhangVerdict\staged-fabric-1.21.1
```

将 `--profile` 换成表中的其他组合即可。产出包含 `mods` 或 `plugins`、`config-fragments` 和 `integration-receipt.json`。收据保存每个文件的两种散列。脚本会校验缓存与目标副本，缓存污染或下载错误会失败，不会静默接受。

创建全新测试服时：使用对应 Loader/Minecraft；安装该 profile 的独立 JAR；添加匹配的 QiZhangVerdict 产物；按下面说明应用配置；启动并检查日志。此脚本不捆绑 Minecraft 服务端、Loader，也不替用户接受第三方 EULA。

## 配置应用

Paper 的三份文件是 **片段**。将 `paper-world-defaults.fragment.yml` 合并到 `config/paper-world-defaults.yml` 的 `anticheat.anti-xray`；Nether/End 片段合并到相应世界实际目录的 `paper-world.yml`（通常为 `world_nether`、`world_the_end`）。保留其他已有设置和 `_version`。重启生效，不要使用 `/reload`。1.20.1 和 1.21.1 分目录保存，均使用兼容的 `engine-mode: 2`。主世界高度 320、下界 128，隐藏列表列明所有原版矿石与深板岩变体。

Fabric/Forge/NeoForge 片段是各版本完整的 AntiXray TOML 示例，文件名分别为 `antixray-fabric.toml`、`antixray-forge.toml`、`antixray-neoforge.toml`，目标为新测试服的 `config/`。主世界 `engineMode=3`，下界 `engineMode=1`，`usePermission=false`。配置根据实际下载 JAR 内默认文件及源码核对；1.20.1 未套用 1.21.1 的标签排除语法。原版矿石使用明确 ID，并加上 Loader 对应的矿石 tag；没有被正确打 tag 的模组矿石仍需逐项加入。自定义维度默认不启用，应以实际维度 ID 增加单独表并验证。

这些默认配置没有把空气加入隐藏块。已暴露矿物、种子推导、玩家/实体 ESP 仍有边界；需要更强遮蔽时先测试客户端帧率、区块流量与恢复延迟。不能把普通矿物混淆说成“封禁所有透视”。

## Grim 行为违规联动账号与设备封禁

锁定 Grim 2.3.71/2.3.73 的默认处罚文件只有告警、日志等动作，没有自动账号封禁命令。需要联动时，将 `grim-punishments-verdict.example.yml` 中选定的分类合并到 Grim 实际生成的 `punishments.yml`，保留其余分类；按上游支持的配置重载方式或重启应用。脚本只把这个可选模板放到 `config-fragments`，不会擅自激活自动封禁。

模板使用经锁定 JAR 的 `punishments/en.yml` 核实的 `Threshold:Interval Command` 格式与 `%player%` 占位符。三个示例阈值为 Simulation `250:0`、Reach `30:0`、BadPackets `120:0`，触发 `qzverdict ban %player% Grim-<category>`。`0` 表示在达到该阈值时执行一次。这些数值是本项目配置示例，并非 Grim 官方推荐，应按服务器模组、战斗机制、延迟和服规调参。

QiZhangVerdict 按当前在线玩家名解析账号 UUID，关联已有设备记录并执行封禁；没有有效设备上报就没有可靠设备关联，设备标识也可重置或伪造。管理员应先在隔离服验证命令、持久化和关联在线账号的踢出行为。安装 Grim 本身不等于这个自动封禁流程已启用。

已对表中两种 Paper/Purpur 固定组合完成[真实 Grim 联动验证](../docs/grim-linked-ban-validation.md)：重复槽位数据包实际触发 `BadPacketsA x120`，原样示例执行封禁，关联的两个账号与一个合成设备写入状态；正常重启后拒绝已封账号/设备，显式解封后恢复准入。两版共 24 组检查通过，完整默认策略和处罚模板均未改动。该证据不覆盖所有 Grim 检查、模组端或真实硬件可信性。

## 维护固定清单

先审查 `pins.json` 中明确的版本 ID，再输出新文件，比较差异后决定是否替换发布清单。`lock` 子命令拒绝覆盖已有文件。

```powershell
python E:\Codex_work\QiZhangVerdict\integrations\manage_integrations.py lock --cache E:\CodexTemp\QiZhangGuard\downloads\integrations --output E:\Codex_work\QiZhangVerdict\integrations\dependencies.next.lock.json
```

更新必须重新核对 Loader/Minecraft 元数据、真实描述符、嵌套依赖、许可证、启动日志及兼容性。当前清单只保存下载链接和元数据，不再发布第三方二进制。GPL 组件若另行重新分发，应同时遵循版权、许可证和对应源码义务。

研究与边界见 `../docs/reference-research.md`。所有本次自动运行证据以具体运行报告为准；此文档不替代最终产物启动/联机报告。

## 最终模组运行证据

`runtime-verification.json` 指向最终冻结四个自研 JAR 的实际服务进程报告、SHA-256、日志与退出码。Fabric 1.20.1、Forge 1.20.1、Fabric 1.21.1、NeoForge 1.21.1 都完成启动、真实控制台 `/qzverdict status` 响应和正常停止，退出码为 0。Fabric 1.21.1 另外通过 26 项真实 TCP 协议测试，覆盖准入、账号/设备配额、黑白名单、关联封禁/解封、带冒号规则 ID 删除和未上报 OP 的命令隔离。

这些协议客户端发送合成自报告，不是图形模组客户端或真实作弊/虚拟机样本；它们解析部分 Fabric 网络数据仍输出 `PartialReadError`（堆栈涉及 `ArmorTrimMaterial`/`SlotComponent`），相关错误原样保留，测试仅依据实际准入、命令和封禁结果。不能由此推导所有网络数据解析、多人实战、所有检测准确率或所有模组兼容。

证据解析器 v2 只认可第三方自身初始化标记，依赖期望来自安装收据；不会把自研诊断中的 `grimac=false`/`antixray=false` 当加载成功，也不会把启动横幅当状态命令响应。已完成报告通过 `mod_runtime_smoke.py refresh` 在校验原日志 SHA-256 不变后重算，保留 `smoke-result.pre-parser-v2.json` 和前后解析信息；这一步没有重启服务器。
