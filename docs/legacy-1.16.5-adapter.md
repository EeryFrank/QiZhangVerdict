# Minecraft 1.16.5 开发适配

截至 2026-09-25，本目标为 `platforms/1.16.5` 下的 **`0.2.0-dev` 开发适配**，包括 Fabric、Forge 和 Java 8 共用逻辑检查子工程。两端已完整构建、通过真实 Java 8 回归，并完成[独立专服](legacy-mod-validation-1.16.5-gpl.md)及[真实图形客户端](legacy-client-validation-1.16.5.md)验证。它尚未发布，不属于已冻结的 0.1.1 五个安装包。

## 固定依赖与命名空间

| 项目 | 本工程选择 |
| --- | --- |
| Minecraft | 1.16.5，Mojang 官方映射 |
| Fabric | Loader 0.16.14，Fabric API 0.42.0+1.16；其真实 mod ID 为 `fabric` |
| Forge | 36.2.42；网络 API 位于 `net.minecraftforge.fml.network` |
| 构建 | Architectury Loom 1.11.456、Architectury Plugin 3.4.164、Gradle Wrapper 8.14.1 |
| Java | **JDK 21 运行 Gradle**；JDK 17 编译并使用 `--release 8`；测试和首轮游戏运行基线为 Java 8 |
| 许可 | GPL-3.0-only；复用根 `gradle/license-resources.gradle` 内置 LICENSE、NOTICE 和 manifest 许可字段 |

实际下载的 [Forge 官方 MDK](https://maven.minecraftforge.net/net/minecraftforge/forge/1.16.5-36.2.42/forge-1.16.5-36.2.42-mdk.zip) 使用 FG6、Gradle 8.4 和 Java 8 toolchain；那是另一套可选构建方案。本工程为了共用完整 Mojmap 类型而采用 Loom，不能把 MDK 的构建 JVM 指令直接套用到这里。已静态读取 [Loom 1.11.456 官方发布包](https://maven.architectury.dev/dev/architectury/architectury-loom/1.11.456/)：插件 class major 为 65，故 Gradle 进程需 Java 21；源包包含旧 TSRG 到 named 的映射合并、Forge 源码转换及明确的 1.16.5 资源处理分支。首次实际构建结果另列于下文。

所有输入的官方 URL、SHA256、可用的官方 SHA1 校验值、版本和接口结论记录在 `platforms/1.16.5/api-evidence.json`；原始输入仅缓存于 `E:\CodexTemp\QiZhangVerdict\legacy-build\1.16.5`。不把第三方加载器或 API 二进制打进本项目 JAR。Loom 上游 [issue 320](https://github.com/architectury/architectury-loom/issues/320) 报告过 1.13.467 的 1.16.5 SRG 重映射错误，因此首次构建后仍须检查实际成品和启动；此处没有推断本次固定版本已通过运行验证。

## Java 8 与旧 Minecraft API 桥接

核心策略继续直接编译仓库的 `core/src/main/java`，没有复制另一套黑名单、设备规则或 VM 策略。`gradle/adapt-sources.gradle` 从共享文件生成本目标副本，每项替换核对预期出现次数；共享源码改变导致匹配数量不符时直接使构建失败，要求重新审阅。

- `ClientReporter` 的 5 次 `readNBytes` 换成 `LegacyJava8.readBounded`，保留 128/256/1024/4096/8192 字节上限。错误流重定向到 Java 8 可用的空设备，保留进程超时；随机安装标识改用 UTF-8 `Files.write`，继续使用 `CREATE_NEW`。
- nonce、固定服务器 scope、安装 ID 派生、有限队列、generation/coalescing、主线程回包及连接归属检查保持原逻辑。未关闭设备要求、VM 拒绝或报告时限。
- 依据 [Mojang 1.16.5 映射](https://piston-data.mojang.com/v1/objects/374c6b789574afbdc901371207155661e0509e17/client.txt)，改用 `TextComponent(String)`、`ServerPlayer.getLevel()`、`sendSuccess(Component, boolean)`，视角读取为 `Entity.yRot/xRot` 字段。旧端使用原生 Log4j，移除共享入口对 SLF4J 的假定。
- Forge 使用 `FMLServerStartingEvent/FMLServerStoppingEvent`、`PlayerEvent.getPlayer()`，保存本次服务器对象供不提供 `getServer()` 的旧 tick 事件使用。[Forge 36.2.42 源码](https://maven.minecraftforge.net/net/minecraftforge/forge/1.16.5-36.2.42/forge-1.16.5-36.2.42-sources.jar) 确认事件按发送端命名：`ClientCustomPayloadEvent` 对应 `PLAY_TO_SERVER`，`ServerCustomPayloadEvent` 对应 `PLAY_TO_CLIENT`。两端均检查方向、长度和连接归属。
- Fabric 使用该固定 API 的 command v1 双参回调和 networking v1；元数据依赖 `fabric`，没有误写成后续版本的 `fabric-api`。资源包只报告已选中的包。

两端继续使用 `qzguard:main` 和共享 wire2；1.12.2 插件使用的 `QZGuard` 频道不属于这个原生 1.16.5 适配。

命令隔离采用必需 Mixin，`required=true`、`defaultRequire=1` 和注入 `require=1` 均保留。Java 8 兼容的 `CommandGate116Mixin` 在 Minecraft 命令分发器执行前拦截等待报告的玩家，包括 OP：

```text
Mojmap: net.minecraft.commands.Commands
performCommand(Lnet/minecraft/commands/CommandSourceStack;Ljava/lang/String;)I

对应 Forge SRG：net.minecraft.command.Commands
func_197059_a(Lnet/minecraft/command/CommandSource;Ljava/lang/String;)I
```

工程源码统一采用完整 Mojmap；Forge 源包中旧 MCP 类名由 Loom 重映射，不能直接与 Mojmap 描述符混搭。首次构建必须核验实际 refmap，缺失或注入失败不能作为成功忽略。

## 历史静态检查与实际构建

`static_check.py` 不启动 Java，可核对适配锚点、元数据、门禁、网络方向与已知 Java 9+ API 残留；可选外部 `javalang 0.13.0` 只做 Java 8 语法解析，不解析 Minecraft 类型。[static-checks.json](../platforms/1.16.5/static-checks.json) 是首次构建前的历史快照，保留原字节和当时源码哈希；其中“未编译”只描述当时状态。生成预览和 Python 检查依赖均在指定临时缓存，不改动共享文件。

实际执行的构建参数等价于下面命令。平台根目录及三个子项目的 `.gradle` 均为指向本任务临时缓存的 junction，未移动既有目录。Windows 工具链目录仅适用于本机，Linux 应传入自己的 JDK 8/17/21 路径。

```powershell
$env:JAVA_HOME = 'D:\Java\jdk-21'
$env:GRADLE_USER_HOME = 'E:\CodexTemp\Gradle\XiuXianZhuan'
$env:JAVA_TOOL_OPTIONS = '-Djavax.net.ssl.trustStoreType=Windows-ROOT -Djavax.net.ssl.trustStore=NONE'
.\platforms\1.16.5\gradlew.bat -p platforms/1.16.5 --no-daemon --console=plain --max-workers=1 --project-cache-dir E:\CodexTemp\QiZhangVerdict\legacy-build\1.16.5\gradle-project-root '-Dorg.gradle.jvmargs=-Xmx2G -Dfile.encoding=UTF-8' '-Dorg.gradle.internal.http.connectionTimeout=15000' '-Dorg.gradle.internal.http.socketTimeout=15000' '-Porg.gradle.java.installations.paths=D:/Java/jdk-21,E:/CodexTemp/mods-danzi/minecraft/runtime/java-runtime-gamma/windows-x64/java-runtime-gamma,E:/CodexTemp/QiZhangVerdict/toolchains/jdk8/jdk8u504-b01' build
```

`compat:check` 在真实 Java 8 launcher 上执行现有核心安全回归、目录生产解析器、转换后的客户端报告器回归及有界读取检查。两个 loader 的 `check` 都依赖它，并分别运行转换后的真实 Brigadier 命令树检查；没有跳过检查。`compat` 是内部验证模块，不是玩家安装用的模组。两个预期安装产物为 `qizhangverdict-fabric-1.16.5-0.2.0-dev.jar` 和 `qizhangverdict-forge-1.16.5-0.2.0-dev.jar`。

首次执行 `build-01.log` 因 Loom 运行配置中的 `rootProject` 属性遮蔽而失败；修复为进入 DSL 前捕获 `runtimeRoot` 后，`build-02.log` 完整通过，退出码 0，耗时 8 分 55 秒，30 个任务全部执行。没有为通过构建关闭测试或修改默认策略。两份原始日志保留于 `E:\CodexTemp\QiZhangVerdict\legacy-build\1.16.5`，对应哈希和当前源码清单记录在 [build-verification.json](../platforms/1.16.5/build-verification.json)。

通过结果包括：Java 8 上 55 项核心安全回归、31 条目录规则生产解析、客户端报告器的 scope/异步/20 次 reload 合并测试、有界读取桥接，以及 Fabric 和 Forge 各自 7 项实际 Brigadier 命令树案例。两个正式模组各 27 个 class，全部 class major 52；两份二进制和两份 sourceJar 的 LICENSE、NOTICE 均与项目根文件逐字节一致，manifest/加载器元数据为 GPL-3.0-only。必需 Mixin refmap 分别映射到 Fabric `method_9249` 和 Forge `func_197059_a`，两者完整方法描述符已核对。

| 成品 | SHA256 |
| --- | --- |
| Fabric `qizhangverdict-fabric-1.16.5-0.2.0-dev.jar` | `d9bb0837f97ccf30c4b0f19a5cd8b65197eab4b2c5137b246b0e56c94fe6aae6` |
| Forge `qizhangverdict-forge-1.16.5-0.2.0-dev.jar` | `52e68051478f7e9b257432e895d81f48b54a8974f2a2a03d5f9af14d59e15779` |

构建保留 Loom beta 和 Gradle 9 弃用提示；通过定义是任务执行成功及包体核验，不是日志完全没有提示。后续专服验收中，两端均正常启停并证明实际 Mixin 注入；Fabric 通过 26 项 TCP 断言，含 OP 等待期命令拒绝。两个真实 Java 8 客户端在严格默认策略下分别于报告通过后持续在线 66 / 65 秒，生存恢复、设备关联及正常退出均通过；使用了官方 authlib 的本地离线回退，不能作为正版认证证明。仍待验证客户端连接 Bukkit、Forge OP 门禁行为、重连/reload、大型整合包和旧存档。Java 17 游戏运行、代理/ViaVersion和第三方 Grim/AntiXray 组合均未验证。
