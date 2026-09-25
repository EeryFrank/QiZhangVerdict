# Minecraft 1.8.9 Forge 开发适配

截至 2026-09-25，本目录包含 **0.2.0-dev 的官方输入研究和独立源码适配**。源码已完成原生 **Java 8 / Gradle 2.7 构建和全部五项必需 Java 检查**，二进制与源码 JAR 已通过 GPL/字节码审计。随后已完成官方安装器及 **Forge 专服无玩家启动、严格控制台状态和正常停服**；**真实玩家联机、客户端与命令门禁仍未由本报告验证**。构建记录见 [build-verification.json](../platforms/1.8.9/build-verification.json)。本目录不属于 0.1.1 发布，也不继承其他版本的验收结果。[api-evidence.json](../platforms/1.8.9/api-evidence.json) 保留先前“未实现”的研究时间点快照；后续源码阶段由独立 [static-checks.json](../platforms/1.8.9/static-checks.json) 描述，未改写研究快照。

后续的[独立 TCP 验收](legacy-mod-tcp-validation-1.8.9-gpl.md)已完成 14 项真实连接检查，包括默认配额、20 秒报告超时及实际 OP 命令门禁，服务器正常退出。图形客户端验收仍在进行；本候选未纳入已发布的 `0.2.0-dev-preview.1`，也不声称能够安装到原生 Forge 1.8.8。

## 目标与 1.8.8 边界

建议先实现原生 **Minecraft 1.8.9 + Forge 11.15.1.2318**，再单独验证其客户端连接用户原定的 1.8.8 Bukkit/Paper 插件服。[Forge 1.8.9 官方页](https://files.minecraftforge.net/net/minecraftforge/forge/index_1.8.9.html) 同时列它为 latest/recommended；[1.8.8 官方分支](https://files.minecraftforge.net/net/minecraftforge/forge/index_1.8.8.html) 也实际存在，latest 为 **11.15.0.1655**。不能把 1.8.9 成品标为可安装到 1.8.8 Forge。

已下载并按官方 SHA1 核对两版 userdev：各自 `patches.zip!/net/minecraft/client/multiplayer/GuiConnecting.java.patch` 明确构造 `C00Handshake(47, ...)`。这是**两版协议号均为 47 的一手静态依据**，不是已经互通的测试结果。Forge 还在握手中加入 FML 标记及后续握手，因此原生同版 Forge 联机、1.8.9 客户端至 1.8.8 插件服、1.8.8 原生 Forge 模组必须作为三个不同目标；跨版 Forge 服务器不作默认承诺。插件联机必须实测大小写精确的 `QZGuard` / `REGISTER` 频道以及完整 wire2 报告。

## 已固定的输入和构建路线

| 输入 | 实际核对结果 |
| --- | --- |
| 1.8.9 Forge MDK | `1.8.9-11.15.1.2318-1.8.9`；官方 SHA1 `58756308abbd2a7e29ad634862bcdc378682b708` |
| 1.8.9 userdev | 内含 `sources.zip`、`patches.zip`、`merged.srg` 和 `dev.json`；单独 `-sources.jar` URL 返回 404，未伪造来源 |
| 原 MDK 构建 | ForgeGradle `2.1-SNAPSHOT`、插件 ID `net.minecraftforge.gradle.forge`、Gradle **2.7**、`stable_20` |
| ForgeGradle 可固定候选 | 官方 Maven 时间戳 **`2.1-20211118.174922-42`**；JAR manifest 为 `2.1.3-g6a7c715`；源提交 `6a7c7156fa1e8b5228203d5d1e5d6e97c2b0473e` |
| 映射 | MDK 的 `stable_20` 实际属于 **`20-1.8.8`**；当前实际构建使用官方专属 **`22-1.8.9`**。选查的 52 个方法/字段映射无名称变化，目标源码已实际编译通过 |
| Java | Mojang 两版元数据均标记 Java **8**；构建、编译及首轮测试统一使用完整 JDK 8 |
| Gradle 2.7 分发校验 | 官方 `gradle-2.7-bin.zip.sha256` 为 `cde43b90945b5304c43ee36e58aab4cc6fb3a3d5f9bd9449bb1709a68371cb06`；已独立下载、核验、解压并用于首次构建 |

候选路线为 **JDK 8 + Gradle 2.7 + 固定 ForgeGradle 时间戳 + stable_22**。该精确组合已完成本项目原生 Java 8 构建和五项检查；不代表游戏运行兼容已经验证。[Gradle 官方兼容表](https://docs.gradle.org/current/userguide/compatibility.html) 将 Java 8 支持范围列为 Gradle 2.0–8.14.x；不能直接使用本机默认 Java 21 启动旧构建。

首次实现时需处理以下已经查实的构建问题：

- MDK 含 `jcenter()` 和旧 HTTP Forge Maven；改用已验证的官方 HTTPS Maven 和 Maven Central。固定候选 FG 的源码已使用 HTTPS Forge/Mojang 元数据地址，但资源下载地址仍为 HTTP。首轮采用 MDK README 明确支持的 **`setupCIWorkspace`** 路线，仅准备编译环境；游戏资源另由官方 HTTPS 元数据准备，不修改验证逻辑或跳过测试。
- ForgeGradle 当前分支提交与上述发布 JAR 的提交不同。本记录以 manifest 指向的 **6a7c715** 源码解释该候选，不能拿较新分支代码声称旧 JAR 已修复。
- 原 MDK 内的 Wrapper JAR 经只读常量检查**没有 `distributionSha256Sum` 支持**。首次启动前应独立下载并核对 Gradle 2.7 ZIP，再使用已验证的分发；不能仅给旧 properties 添加校验值便声称已执行校验。
- 根 `gradle/license-resources.gradle` 使用 `configureEach`，该 API [从 Gradle 4.9 才提供](https://docs.gradle.org/current/javadoc/org/gradle/api/DomainObjectCollection.html#configureEach(org.gradle.api.Action))。Gradle 2.7 工程须在自己目录内实现等效的旧 DSL `tasks.withType(Jar) { ... }`，继续把根 LICENSE/NOTICE 原字节及 GPL manifest 放入 binary/sourceJar；不修改现代目标的公共脚本。`tasks.register`、`layout`、Java toolchain DSL 同样不能从 1.12/1.16 工程照搬。

全部下载只进入 `E:\CodexTemp\QiZhangVerdict\legacy-build\1.8.9`；来源、时间、SHA256、官方 SHA1、嵌套条目哈希及失败探测记录见 [api-evidence.json](../platforms/1.8.9/api-evidence.json)。本轮完整构建依赖解析及构建已经通过；已校验的实际 ForgeGradle、userdev 和 Mojang 输入另记于构建报告。历史研究快照不改写。

## 相对 1.12.2 的真实 API 差异

以下来自固定 userdev 源码、Forge 补丁以及官方 MCP SRG/CSV 的对应关系，现已通过本项目目标源码编译；运行行为仍须专服和客户端测试：

| 1.12.2 用法 | 1.8.9 必需桥接 |
| --- | --- |
| `TextComponentString` / `ITextComponent` | `net.minecraft.util.ChatComponentText` / `IChatComponent` |
| `GameType` | `net.minecraft.world.WorldSettings.GameType`；保留 SPECTATOR 隔离 |
| `player.connection` / `interactionManager` | `player.playerNetServerHandler` / `theItemInWorldManager` |
| `getServerWorld()`、`player.getServer()` | `getServerForPlayer()`，再由 `WorldServer.getMinecraftServer()` 取所属服务器，或使用明确保存的生命周期对象 |
| `server.getPlayerList()` | `server.getConfigurationManager()`；其 `getPlayerList()`、`getPlayerByUUID()`、`getPlayerByUsername()` 已确认 |
| `connection.disconnect(component)` | `playerNetServerHandler.kickPlayerFromServer(String)` |
| `CPacketCustomPayload` / `SPacketCustomPayload` | `C17PacketCustomPayload` / `S3FPacketCustomPayload` |
| `client.getConnection()`、`player`、`world` | `getNetHandler()`、`thePlayer`、`theWorld`；发送用 `addToSendQueue(Packet)` |
| 网络事件 `getHandler/getManager/getPacket` | **公开字段** `handler/manager/packet`；事件名按接收端：`ServerCustomPacketEvent` 收客户端报告，`ClientCustomPacketEvent` 收服务端挑战 |
| `CommandEvent.getSender()` | **公开字段** `sender`；同理 `command/parameters/exception` 也是字段 |
| `CommandBase.getName/getUsage/execute(server, sender, args)` | `getCommandName()`、`getCommandUsage(sender)`、`processCommand(sender, args)`；权限为 `getRequiredPermissionLevel()` + `canCommandSenderUseCommand(sender)` |
| `sender.sendMessage()` | `sender.addChatMessage(IChatComponent)` |

`FMLServerStartingEvent.registerServerCommand`、`FMLPreInitializationEvent.getModConfigurationDirectory`、`FMLCommonHandler.getWorldThread` 仍可用。2318 的 `FMLCommonHandler.bus()` 已指向 `MinecraftForge.EVENT_BUS`，**不要同时注册两遍**导致重复挑战或报告。模组列表继续读取 `Loader.getActiveModList()`；资源包使用 `getRepositoryEntries()` 的选中列表，不用所有可用包。

命令门禁可沿用 1.12.2 的 **Forge 原生命令事件**，不必先引入 Mixin/coremod。固定 Forge 的 `CommandHandler.java.patch` 在权限检查通过后、命令执行前发布可取消 `CommandEvent`，取消时立即返回。因此 OP 也必须在 pending 状态被取消。待核验的分发描述符是：

```text
net/minecraft/command/CommandHandler.func_71556_a
(Lnet/minecraft/command/ICommandSender;Ljava/lang/String;)I
```

如果最后选择 Mixin，必须另行锁定兼容 LaunchWrapper 的引导组件及 refmap；当前没有该实现或注入成功证据。原生事件路线也必须通过真实 OP 等待期间命令阻断测试。

## 保持的策略、许可与下一阶段

直接复用 Java 8 兼容的 core；ClientReporter 继续使用已审核的有界读取、空设备错误流和 UTF-8 `CREATE_NEW` 桥接。1.12 的独立命令参数解析器可以复用或生成副本，但 CommandBase 入口需改签名。MinecraftGuard 的版本生成适配必须逐项计数核对，不放宽 nonce、固定 scope、设备限制、VM 策略、报告期限、连接归属、STALE_REPORT、异步保存或 OP 门禁。跨维度等待仍采取拒绝连接的保守处理，不能丢弃隔离。

第一方新增文件使用 **GPL-3.0-only**。官方 MDK 的 `MinecraftForge-License.txt` 是 **Minecraft Forge Public Licence 1.0**，FML 的 `LICENSE-fml.txt` 是 **LGPL-2.1-or-later**，固定 ForgeGradle POM/源 LICENSE 为 **LGPL 2.1**；不能把旧 Forge 统称为现代 LGPL/本项目 GPL。FML 许可还明确区分 MCP 数据的再分发权限，因此完整 CSV/SRG、Forge/Minecraft 源码和第三方二进制仅留在临时研究缓存，不收入第一方 sourceJar；这里只记录必要接口事实和校验值。Wrapper 的 Apache 许可保持其原归属。

获安排后的验收顺序是：先解析依赖、编译现有独立 1.8.9 工程并完成原生 JDK 8 全量核心、目录、报告器及旧命令解析测试；再核验重混淆 JAR、class major ≤52、GPL 文件和源码包；随后运行独立 Forge 1.8.9 专服及真实客户端同版联机；最后单独验证真实 1.8.9 客户端连接现有 **1.8.8 插件服**，覆盖注册频道、真实 mod/pack 报告、报告期限后模式恢复、OP 门禁、设备/IP/黑白名单、reconnect/reload。仅这最后一项通过后，才能声明覆盖用户的 1.8.8 插件服目标；若要求 **1.8.8 原生 Forge 安装**，仍需独立适配及验收。

## 历史源码静态阶段

独立工程位于 `platforms/1.8.9`，包含 Forge 入口、物理侧代理、旧 CommandBase 命令、IP 字面量桥接以及 1.12 已审参数解析器。`gradle/adaptations.json` 从共享 ClientReporter/MinecraftGuard 生成目标副本；每项替换有固定出现次数，变化时中止构建。FG2 在 javac 前复制源码，因此 `sourceMainJava`、`sourceTestJava` 也明确依赖生成任务。未修改 core、shared、1.12.2 或 1.16.5。

`static_check.py` 的 6 组检查通过，12 份本地/生成 Java 源经 javalang 完成 Java 8 语法解析，没有解析 Minecraft 类型。已配置且必需的 5 个 Java 回归任务为核心安全、生产目录解析、客户端报告器、有界读取和 13 项旧命令权限/参数检查；**该历史阶段均未执行，后续构建阶段已全部通过**。旧版 `CommandEvent` 门禁不依赖额外 Mixin 引导，默认策略和 `QZGuard`/`REGISTER` 仍保留。

首次构建已在任务缓存外置平台及子项目的 `.gradle` 并使用完整 JDK 8。下面为基础复现命令；已执行尝试的完整参数和退出码另见下方记录：

```powershell
python -B .\platforms\1.8.9\prepare_gradle.py --download
# 核验成功后，将临时目录中已验证的 gradle-2.7-bin.zip 解压到同一临时 tools 目录。
# 使用该分发的 bin/gradle.bat，不以旧 MDK wrapper 的 properties 充当校验。
$env:JAVA_HOME = 'E:\CodexTemp\QiZhangVerdict\toolchains\jdk8\jdk8u504-b01'
$env:GRADLE_USER_HOME = 'E:\CodexTemp\QiZhangVerdict\legacy-build\1.8.9\gradle-user-home'
& E:\CodexTemp\QiZhangVerdict\legacy-build\1.8.9\tools\gradle-2.7\bin\gradle.bat -p platforms/1.8.9 --no-daemon --max-workers 1 setupCIWorkspace build
```

`prepare_gradle.py` 仅下载/校验官方固定 ZIP，不解压、不启动 Java、不覆盖已有 ZIP；校验失败保留文件供诊断。静态阶段仅执行 `--help`；首次构建前已实际完成下载、SHA256 核验和安全解压。Gradle 2.7 使用旧 DSL，没有现代 toolchain API；其官方分发实际支持 `--max-workers 1`，本轮已成功接收该参数。原 MDK Wrapper 文件保持原字节及 Apache 归属，项目源发布仍须携带根 `LICENSES/Apache-2.0.txt`。

若后续实现原生 1.8.8，建议从相同的第一方桥接输入生成一个**独立目标**，固定其官方 Forge 11.15.0.1655 与映射；当前没有建立该目标，也不会放宽 1.8.9 的 `acceptedMinecraftVersions = "[1.8.9]"` 来冒充兼容。

## 当前构建结果与运行边界

第二次完整构建于 2026-09-25 完成，**exit 0，Gradle 用时 2 分 15.22 秒**。原生 JDK 8 执行了全部五项检查：核心安全 **55 项**、真实生产目录解析 **31 条**、客户端报告器含 **20 次快速 reload**、Java 8 有界读取、旧命令权限/参数 **13 项**。构建使用单 worker、1536 MiB 堆，各 JavaExec 限制 256 MiB；没有跳过检查。ForgeGradle 的“上游不再支持此版本”告警保留在原日志中，成功定义不等于日志完全没有告警。

首次失败是 Gradle 2.7 缺少 `findProperty()`，已局部修为 `hasProperty/property`；没有改共享策略或为过测放宽门禁。首次退出码 1 和第二次退出码 0 的日志、时间、命令与 SHA256 均保存在 `E:\CodexTemp\QiZhangVerdict\legacy-build\1.8.9\build-01.*`、`build-02.*`，并纳入 [build-verification.json](../platforms/1.8.9/build-verification.json)。历史 api/static 快照保留原字节，当前构建输入哈希单独记录。

产物位于 `platforms/1.8.9/forge/build/libs`：

| 产物 | SHA256 / 审计 |
| --- | --- |
| `qizhangverdict-forge-1.8.9-0.2.0-dev.jar` | `f00943b06e87dbfc04e88336134ab4ae1a571a6e9b53924ab6bc06b311918424`；91,765 字节；31 class，全部 major **52** |
| `qizhangverdict-forge-1.8.9-0.2.0-dev-sources.jar` | `d58a945226691f17a9b0dd2c4ceef296a941b1ab2ba8015161051fd3c2e62748`；48,626 字节；19 份第一方 Java 源 |

两包 `LICENSE/NOTICE` 与根文件逐字节一致，manifest 声明 GPL-3.0-only；二进制已完成 `reobfJar` 并核对 SRG 字段，未打入 Minecraft/Forge 类、第三方源码或嵌套 JAR。源码包是 FG2 正常产生的映射后来源包，完整构建工程仍需项目根的共享源码与许可文件。

历史准备阶段：无玩家专服夹具先纯文件准备于 `E:\CodexTemp\QiZhangVerdict\legacy-runtime\forge-1.8.9-guard-01`，计划绑定回环地址端口 **25641**；官方 installer 的 SHA1 `ec0293ff0776b8831f2ed90511bab76e635dda0c` 与实际下载一致，SHA256 为 `f9fdf4945ca02d73ec6cc46300942f4e199e4add068877d517157b3677563656`，Mojang server JAR 也与官方元数据校验一致。安装前实测 free **1.662 GiB**，低于 3 GiB 门槛，因此没有启动安装器或服务端 JVM，未生成安装/停服成功结果。见 [runtime-preparation.json](../platforms/1.8.9/runtime-preparation.json)。

下方记录的安装与无玩家运行后来已经执行成功；不要重跑覆盖该夹具。后续 TCP/OP 检查使用了全新目录，结论单独记录于前述 TCP 验收。真实伴随模组的图形验收、VM 准确率、完整游戏兼容及 **1.8.8** 跨版联机均不能由此无玩家记录推出。该适配尚未发布安装包。

历史内存窗口：随后仅安装窗口单独调整为 **384 MiB 堆 / free ≥1.25 GiB**，服务器运行仍要求 **1536 MiB 堆 / free ≥3 GiB**，当时没有服务端启动授权。两次即时观测分别为 **1.068 GiB、1.043 GiB**，均不足，当时安装器未启动并已停止等待；恢复窗口后的结果另见下节。旧阶段 helper 按 SHA256 `339a1d8ad38977ac583f752d04f8957536ac11fbd853266d2ae6c8fdd5e9c8fc` 保存在 `runtime_basic.stage-snapshot-339a1d8ad389.py`，新 helper SHA256 为 `d9b1dc375f45ad69ce6f21911356ce3f8e4ec6bae47f199c6b63aa2c0ef3275a`；两份均在同一临时构建目录。新门槛仅影响测试安装器，不改变产品或默认策略，原 stage 历史记录未覆盖。

## 无玩家专服运行结果

恢复窗口后，官方安装器以 **384 MiB** 堆实际运行，**exit 0**，用时 **3.372 秒**；产生的 `forge-1.8.9-11.15.1.2318-1.8.9-universal.jar` SHA256 为 `596512ad5f12f95d8a3170321543d4455d23b8fe649c68580c5f828fe74f6668`，与已验证安装器内的同名条目逐字节一致。

同一独立夹具随后以完整 Java 8、**1536 MiB** 堆启动；日志出现 `Done`，控制台 `qzverdict status` 确认 `companion=required`、`vm=DENY`、`blacklist=DENY`、`deviceRequired=true`、零会话。生成后的默认配置在检查前后 SHA256 相同。通过 `stop` 正常保存世界，**server exit 0**；owned PID **92996** 已退出，端口 **25641** 可重新绑定。所有结果与原日志哈希见 [runtime-verification.json](../platforms/1.8.9/runtime-verification.json)。

原日志保留旧 Forge 的 missing-signature ERROR、首次缺 ban/ops/white-list 文件 WARN，以及回环离线测试模式 WARN；这些没有阻止实际启动或正常停服。本结果**只有无玩家专服基础检查**，没有发送 TCP 报告、运行玩家命令或图形客户端，不能计为客户端、反作弊准确率或 1.8.8 互通通过。既有内存拒启记录和 stage/helper 快照仍保留，独立 TCP 测试另用新目录执行。
