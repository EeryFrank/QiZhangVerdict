# 旧版客户端移植计划：1.16.5 / 1.12.2

审计日期：2026-09-25。**本文是只读源码、映射及发布元数据分析，不是实现或兼容性验收。** 没有新增 platform、修改共享实现或启动 Java/Gradle。官方 MDK、源码、Mojang/MCP 映射及 SHA256 清单存于 `E:\CodexTemp\QiZhangVerdict\legacy-build\analysis`，其中 `audit-source-lock.json`、`fabric-source-lock.json` 可追溯本次输入。

## 共同前置工作：先恢复 Java 8 基线

`core/build.gradle` 已采用 `options.release = 8`；阻碍主要在客户端报告器和 Minecraft 接口层：

| 现有代码 | 旧版处理与必须保留的行为 |
| --- | --- |
| `ClientReporter` 的 5 处 `InputStream.readNBytes(int)` | 此重载从 Java 11 才提供；改为有长度上限的 Java 8 读取函数，保留 128/256/1024/4096/8192 字节限制，不能改成无界读取 |
| 1 处 `Files.writeString` | Java 11 API；改用 UTF-8 字节写入，保留 `CREATE_NEW` 和现有安装 ID，不重新生成已有设备标识 |
| 2 处 `ProcessBuilder.Redirect.DISCARD` | Java 9 API；采用 Java 8 可用的空设备重定向或受限错误流消费，保留超时、进程结束和 `unknown` 处理 |
| loader 中的 `var`、`Stream.toList()`，Mixin 的模式匹配 `instanceof` | 分别需要 Java 10、16、16；改为显式类型、收集器和显式转换。共享命令源也有 `var`；测试中的 `String.repeat` 需替换 |
| 共享 `org.slf4j` 日志 | 两个旧版的 Mojang 元数据均有 Log4j，未列 SLF4J；旧接口层改接原生日志，不假设现代运行库存在 |

先在独立检查任务中以 `--release 8` 编译 core + client-common，并实际用 Java 8 执行设备 ID、超时/截断、nonce/scope、并发 reload 和跨连接响应测试；只设置 `targetCompatibility=1.8` 不足以排除误用新 JDK API。保留 wire2、按服务器 scope 派生设备 ID、有限工作队列和主线程回包行为。API 年代依据见 [InputStream](https://docs.oracle.com/en/java/javase/11/docs/api/java.base/java/io/InputStream.html#readNBytes(int))、[Redirect.DISCARD](https://docs.oracle.com/en/java/javase/11/docs/api/java.base/java/lang/ProcessBuilder.Redirect.html#DISCARD)。

## 1.16.5：先 Fabric，再 Forge

**依赖与 Java。** 固定 Fabric Loader `0.16.14`、Fabric API `0.42.0+1.16`；[官方 loader profile](https://meta.fabricmc.net/v2/versions/loader/1.16.5/0.16.14/profile/json) 可解析，已实读 API 描述符，其 ID 是 **`fabric`**，没有 `fabric-api` 别名。固定 Forge `36.2.42`，来自[官方版本页](https://files.minecraftforge.net/net/minecraftforge/forge/index_1.16.5.html)。该版 MDK 实际使用 **ForgeGradle `[6.0,6.2)`、Gradle 8.4、Java 8 toolchain**，不是旧教程的 FG3/Gradle4；下一轮应把范围固定为本次官方 Maven 元数据存在的 `6.0.54` 后验证解析。

Mojang 的 1.16.5 元数据标注 Java 8；[Forge 官方 1.16 开发文档](https://docs.minecraftforge.net/en/1.16.x/gettingstarted/) 同样以 Java 8 为目标。首轮游戏运行基线用 Java 8，Forge MDK 构建进程可安排 Java 17 + Java 8 toolchain；Gradle 8.4 可在 Java 17 运行，**不可沿用本机 Java 21 启动该 wrapper**，Java 21 运行 Gradle 要求至少 8.5。[Gradle 兼容表](https://docs.gradle.org/current/userguide/compatibility.html) 支持这个区分。Fabric/Forge 在 Java 17 上运行游戏的兼容性本次未测试，不能从“构建 JVM 是 17”外推，也不能仅凭目标字节码 8 断言所有较新 JVM 都不可能运行。

**接口清单。** Fabric 的官方模块源码确认 command API v1 双参回调、networking v1 和 `SERVER_STARTING` 均存在，可先沿用 1.18.2 的薄入口结构。Mojang 1.16.5 映射确认 `TextComponent(String)`、`ServerPlayer.getLevel()`、`sendSuccess(Component, boolean)`；命令执行仍是传入命令源的形式：

```text
Mojmap owner: net.minecraft.commands.Commands
performCommand(Lnet/minecraft/commands/CommandSourceStack;Ljava/lang/String;)I

Forge MCP/SRG owner: net.minecraft.command.Commands
func_197059_a(Lnet/minecraft/command/CommandSource;Ljava/lang/String;)I
```

这是同一方法在不同命名空间中的描述，不能混搭类名和 refmap。官方 Forge MDK 的 `official` 配置说明字段/方法映射；其发布源码和 MCP config 使用 `ServerPlayerEntity`、`CommandSource`、`PacketBuffer`、`StringTextComponent` 等旧类名。Forge 端应先生成工作区确认最终类名，再实现独立桥接，不能假定新 Loom/共享源码会自动转换全部包名。Fabric 若用全 Mojmap，使用上面第一行；Forge 按最终构建命名空间生成 SRG refmap，运行时必须核验注入。

Forge 网络包位于 **`net.minecraftforge.fml.network`**，生命周期是 `FMLServerStartingEvent/FMLServerStoppingEvent`，玩家事件取 `getPlayer()`，tick 事件不提供服务器对象。官方 `NetworkDirection` 确认 `PLAY_TO_SERVER → ClientCustomPayloadEvent`、`PLAY_TO_CLIENT → ServerCustomPayloadEvent`；保留精确方向、连接来源和负载长度检查。两端原生 1.16.5 联机使用 `qzguard:main`，配套插件品牌频道为 `minecraft:brand`；不承诺 ViaVersion 跨代转换。

接口依据为 [Forge 36.2.42 官方源码包](https://maven.minecraftforge.net/net/minecraftforge/forge/1.16.5-36.2.42/forge-1.16.5-36.2.42-sources.jar)、[Mojang 1.16.5 服务端映射](https://piston-data.mojang.com/v1/objects/41285beda6d251d190f2bf33beadd4fee187df7a/server.txt)及 [Fabric API 官方 Maven 发布目录](https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/0.42.0+1.16/)。

**下一轮执行顺序。** 完成共同 Java 8 检查后，新建独立 1.16.5 Fabric 工程，先做“收到挑战→回报真实 mod/pack→恢复模式”的最小双端闭环，再接入旧版命令隔离与管理命令；随后用上述官方 MDK 建 Forge 桥接，不把 Fabric 构建成功当作 Forge 成功。每端依次验收 Java 8 编译/测试、最终 class major ≤52 与 refmap、独立专服启停、真实客户端→同 loader 服务端和 Bukkit 插件、OP 等待报告时命令拒绝、规则/关联封禁。Java 17 游戏运行作为额外矩阵独立记录。

## 1.12.2 Forge：独立旧 API 入口与原生频道

**依赖与 Java。** 固定 [Forge `14.23.5.2864`](https://files.minecraftforge.net/net/minecraftforge/forge/index_1.12.2.html)。实读该版 MDK 为 **ForgeGradle `3.+`、Gradle 5.6.4、MCP snapshot `20171003-1.12`、Java 8 源码/字节码**；下一轮固定本次官方 Maven 元数据存在的 `3.0.197`。Mojang 1.12.2 元数据没有官方 client/server mappings 下载项，不能照搬 `officialMojangMappings()`；本次核对的是官方 Forge Maven 的 MCP snapshot CSV 与 1.12.2 SRG。

本端构建和原生游戏运行都先用 Java 8。[Forge 1.12 文档](https://docs.minecraftforge.net/en/1.12.x/gettingstarted/) 明确以 JDK8 开发；Gradle 5.6.4 不支持 Java 17 运行。原生 LaunchWrapper 1.12 源码还把应用加载器强转成 `URLClassLoader`，而 [JDK 9+ 已改变应用加载器类型](https://docs.oracle.com/en/java/javase/17/migrate/migrating-jdk-8-later-jdk-releases.html)。因此，按这些官方原版组件直接换成标准 Java 17 启动并不是可接受的兼容方案；第三方补丁启动器应另立评估，不能作为本端默认要求。

**实现边界。** 1.12.2 没有原生 Brigadier，不能只替换几处字符串就复用 `GuardCommands`。新建旧版命令适配，继承 `CommandBase`、在 `FMLServerStartingEvent.registerServerCommand` 注册，单独解析 `device:...`、`legacy:...`、含空格规则值和封禁理由；权限及调用 `GuardService` 的行为与现代端保持一致。Minecraft 对象桥接使用 `EntityPlayerMP`、`WorldServer`、`TextComponentString` 等旧类型；模组列表从 `Loader` 获取，选中资源包从 `ResourcePackRepository.getRepositoryEntries()` 获取，不能误报 `getRepositoryEntriesAll()` 的全部可用包。

首选使用 Forge 自带、可取消的 `CommandEvent`，由 `event.getSender().getCommandSenderEntity()` 定位待验证玩家，取消包括 OP 在内的执行。官方补丁确认该事件位于命令执行之前；必须在纯 Forge 服务端做真实命令隔离回归，不外推混合服命令路由。若实际测试要求更早的 Mixin 拦截，准确目标已由 MCP CSV/SRG 对照确认：

```text
owner: net.minecraft.command.CommandHandler
MCP: executeCommand(Lnet/minecraft/command/ICommandSender;Ljava/lang/String;)I
SRG: func_71556_a(Lnet/minecraft/command/ICommandSender;Ljava/lang/String;)I
```

旧 Forge 不因放入 `mixins.json` 就自动提供现代 Mixin 初始化；若选择 Mixin 路线，必须另行固定兼容 LaunchWrapper 的初始化器/注解处理器并核验 SRG refmap，不能复用 1.20 的 Mixin 描述符。原生 `CommandEvent` 路线可以先避免这个额外构建依赖。

**网络必须重写旧通道适配。** 当前 Bukkit 插件对 `<1.13` 使用大小写敏感的 **`QZGuard`** 和品牌频道 **`MC|Brand`**。1.12.2 客户端应注册旧 `REGISTER` 通道声明，发原始 wire2 字节到 `QZGuard`，不能发 `qzguard:main`，也不能改协议常量影响现代端。可用 `NetworkRegistry.INSTANCE.newEventDrivenChannel("QZGuard")` / `FMLEventChannel` + `FMLProxyPacket`，或经过核验的原始 custom payload；避免 `SimpleNetworkWrapper` 自动添加 discriminator 导致 Bukkit 无法解码。**旧 `FMLNetworkEvent.ClientCustomPacketEvent` 是客户端接收，`ServerCustomPacketEvent` 是服务端接收**，与现代 `*CustomPayloadEvent` 的命名语义不同。读取 Netty 缓冲区后应复制数据，再调度到各自游戏主线程。

接口依据为 [Forge 2864 官方源码包](https://maven.minecraftforge.net/net/minecraftforge/forge/1.12.2-14.23.5.2864/forge-1.12.2-14.23.5.2864-sources.jar)、[官方 Maven 的 MCP snapshot](https://maven.minecraftforge.net/de/oceanlabs/mcp/mcp_snapshot/20171003-1.12/mcp_snapshot-20171003-1.12.zip)及 [1.12.2 SRG](https://maven.minecraftforge.net/de/oceanlabs/mcp/mcp/1.12.2/mcp-1.12.2-srg.zip)；加载器强转依据为 [LaunchWrapper 官方源码包](https://libraries.minecraft.net/net/minecraft/launchwrapper/1.12/launchwrapper-1.12-sources.jar)。

**下一轮执行顺序。** 先只做 Java 8 companion→现有 Bukkit 1.12.2 插件闭环，验证频道、mod/pack 清单、scope/设备 ID、reload 和重连；此时不能宣称 Forge 服务端防护完成。再实现 Forge 服务端生命周期、会话隔离与旧命令适配，分别执行真实客户端↔Forge 和客户端↔Bukkit 两组测试，覆盖 OP 命令隔离、白黑名单、IP 配额、设备关联封禁、超长包和正常退出。旧端无 Brigadier 测试可以复用，但必须增加等价的真实 `CommandBase` 参数/权限回归和 Java 8 核心测试。

## 1.19.4 现有开发工程的只读补充

`build.gradle` 的 `serverLevel→getLevel` 和 `sendSuccess` 转换与所用接口相符，未发现明显括号错误。初审发现 `commandParserSmoke` 未接入 `check`、`runDir` 硬编码 Windows 路径，已通知主任务；交付前再次只读检查，主任务已接入 parser 检查、固定 Java 17 launcher，并加入跨平台临时目录默认值及 `qzRuntimeRoot` 覆盖。本次没有改动该工程，也没有用编译结果替代接口审计。
