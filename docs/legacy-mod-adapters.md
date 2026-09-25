# Minecraft 1.18.2 开发适配

`platforms/1.18.2` 是 Fabric + Forge 的 **0.2.0-dev 开发工程**。两端已完成编译、打包及各 7 项实际命令解析检查，随后按 GPL-3.0-only 重建并核验内置 LICENSE / NOTICE。最终 GPL JAR 已完成[独立专服验收](legacy-mod-validation-1.18.2-gpl.md)和[真实图形客户端验收](legacy-client-validation-1.18.2.md)。开发 JAR 尚未发布，不属于 0.1.1 的五个发布成品。

## 固定工具链与依赖

| 项目 | 固定版本 | 一手依据 |
| --- | --- | --- |
| Minecraft | 1.18.2，Java 17 字节码 | Mojang 官方版本元数据和客户端/服务端 mappings |
| Fabric Loader | 0.16.14 | [官方 1.18.2 loader profile](https://meta.fabricmc.net/v2/versions/loader/1.18.2/0.16.14/profile/json) |
| Fabric API | 0.77.0+1.18.2 | [官方 Maven](https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/0.77.0%2B1.18.2/)；实读 JAR 描述符为 `fabric-api`，提供别名 `fabric` |
| Forge | 1.18.2-40.3.12 | [官方版本页](https://files.minecraftforge.net/net/minecraftforge/forge/index_1.18.2.html) 与同版本 sources JAR |
| Architectury Loom / plugin | 1.11.456 / 3.4.164 | 与项目 1.19.4 开发工程保持相同构建插件版本，两端构建已通过 |
| Gradle Wrapper | 8.14.1 | 复制仓库现有 wrapper；新工程另固定官方 distribution SHA256 |

来源 URL、获取日期、SHA256 和接口核对记录在 `platforms/1.18.2/api-evidence.json`。Mojang mappings 已按版本元数据中的 SHA1 校验；Forge sources JAR、Fabric API JAR 已按官方 Maven SHA1 校验。第三方源码、依赖和读取缓存都在 `E:\CodexTemp\QiZhangVerdict\legacy-build\1.18.2`，不打进本项目源码或产物。

## 版本差异与实现位置

| 接口差异 | 1.18.2 处理 |
| --- | --- |
| `Component.literal(String)` 尚不存在 | 生成共享源码时改为 `new TextComponent(String)`；本地 loader 入口直接使用旧类型 |
| `ServerPlayer.serverLevel()` | 生成共享源码时改为 `getLevel()` |
| `CommandSourceStack.sendSuccess` | 使用 `(Component, boolean)`，去掉新 API 的 supplier lambda |
| `Commands.performCommand` | 1.18.2 参数是 `(CommandSourceStack, String)`，使用独立 `CommandGate118Mixin`；不加载 1.20 的 `ParseResults` Mixin |
| Fabric 命令注册 | 使用 `command.v1.CommandRegistrationCallback`，参数为 `(dispatcher, dedicated)`；[官方 API 文档](https://maven.fabricmc.net/docs/fabric-api-0.77.0%2B1.18.2/net/fabricmc/fabric/api/command/v1/CommandRegistrationCallback.html) |
| Forge 玩家事件 | 使用 `PlayerEvent.getPlayer()` |
| Forge 服务器 tick 事件 | 没有 `getServer()`；在 `ServerStartingEvent` 保存服务器，停止时清空引用 |
| Forge payload 事件方向 | `ClientCustomPayloadEvent` 对应 `PLAY_TO_SERVER`，`ServerCustomPayloadEvent` 对应 `PLAY_TO_CLIENT`；检查精确方向以排除登录阶段子类 |
| Forge 客户端回包 | 保留来源连接检查，避免旧连接挑战通过新连接响应 |
| 资源包列表 | Mojang 1.18.2 映射确认 `getResourcePackRepository().getSelectedPacks()` 和 `Pack.getId()` 可用 |

`core` 与 `client-common` 从现有源码直接编译；策略判断、设备标识、wire 协议仍共用实现。`MinecraftGuard`、`GuardCommands` 与真实 Brigadier 命令解析检查在新工程的 `build/generated/sources/shared1182` 下生成版本适配副本。任务不会回写 `platforms/shared`。只有 loader 入口和 `CommandGate118Mixin` 位于新版本目录内。

两端 Mixin 均为 `required: true`，注入 `require = 1`；不能通过禁用注入绕过旧版命令隔离。专服测试已实际导出注入后的目标类，并核验调用 `MinecraftGuard.isWaiting` 的 JVM 指令；Fabric 另通过了 OP 报告前命令拒绝、报告后允许的 TCP 行为测试。Forge 的类注入证据不替代相同的玩家命令行为测试。

## 构建安排

以下是独立构建示例。实际本地构建使用已有完整依赖缓存，两端均通过。Gradle 使用 Java 21 运行，Java 17 toolchain 负责目标编译和命令解析检查。示例 Java 17 路径有 `bin/javac.exe`，工程本身不写入 Windows 专用 toolchain 路径。

```powershell
$env:JAVA_HOME = 'D:\Java\jdk-21'
$env:GRADLE_USER_HOME = 'E:\CodexTemp\QiZhangVerdict\legacy-build\1.18.2\gradle-home'
Set-Location E:\Codex_work\QiZhangVerdict\platforms\1.18.2
.\gradlew.bat --no-daemon --project-cache-dir E:\CodexTemp\QiZhangVerdict\legacy-build\1.18.2\project-cache '-Porg.gradle.java.installations.paths=D:/Java/jdk-21,E:/CodexTemp/mods-danzi/minecraft/runtime/java-runtime-gamma/windows-x64/java-runtime-gamma' :fabric:build :forge:build
```

两端 `check` 均依赖 `commandParserSmoke`，因此 `build` 不会跳过实际命令树的解析检查。还需在仓库根工程运行现有 `:core:securityTest` 等验收任务，不能用此开发工程的静态检查代替。Linux 使用自己的 Java 17/21 安装路径及临时缓存目录。

已构建的开发产物为：

- `platforms/1.18.2/fabric/build/libs/qizhangverdict-fabric-1.18.2-0.2.0-dev.jar`
- `platforms/1.18.2/forge/build/libs/qizhangverdict-forge-1.18.2-0.2.0-dev.jar`

开发启动目录在 Windows 默认归入 `E:\CodexTemp\QiZhangVerdict\legacy-build\1.18.2\runtime`，可用 `-PqzRuntimeRoot=...` 显式覆盖；不会指向现有服务器目录。

## 当前证据与剩余验收

`platforms/1.18.2/static-checks.json` 保留首次源码交付时的 10 项静态检查快照。它先于首次构建、GPL 许可调整和 parser 临时目录修正，因此其中 `compiled=false`、`runtimeTested=false` 与文件 SHA256 只描述当时状态，不能用作当前源码散列。之后的实际构建见 [开发版首次构建](../outputs/legacy-mod-builds.json)；GPL 重建见 [最终构建记录](../outputs/build-validation-0.1.1-gpl.json)，新旧成品的类文件逐字节比较见 [许可迁移记录](../outputs/license-transition.json)。

两端专服均正常启动和退出；Fabric 另通过 26 项 TCP 分支断言。两个真实客户端均在完整默认策略下完成报告、生存模式恢复及设备关联，再持续在线 65 秒，客户端和专服退出码均为 0。Fabric 首轮资源重载等待、Forge 首轮原生 LWJGL 崩溃保留在客户端记录中，原因尚未确定。待验证项目包括客户端连接 Bukkit、Forge 的 OP 命令隔离行为、大型整合包、旧存档和性能。本适配任务没有选定或验证 1.18.2 的 Grim/AntiXray 第三方防护组合；不能把现有 1.20.1/1.21.1 集成证据外推到这个版本。
