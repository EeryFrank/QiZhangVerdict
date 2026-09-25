# Minecraft 1.19.2 适配候选

本目录新增 Fabric 与 Forge 的 `0.3.0-dev` 候选。它没有替换 `0.2.0-test.1` 的任何已发布 JAR。两端生产 JAR 已构建成功，通过每端命令参数解析、客户端报告、57 项安全回归、37 条目录规则及 3 个控制；另用 Java 17 从最终两个 JAR 中运行共 194 项核心检查。详见[本版本报告](../outputs/adapter-build-1.19.2.json)。Minecraft 专服与真实客户端尚未启动，不能据此宣称实际联机兼容。

| 项目 | 固定输入 |
| --- | --- |
| Minecraft / Java | 1.19.2 / Java 17，class major 61 |
| Fabric Loader | 0.16.14 |
| Fabric API | 0.77.0+1.19.2，官方完整发行 JAR，1,892,953 字节、50 个嵌套 JAR |
| Forge | 43.5.2；核验时官方 latest 为 43.5.2、recommended 为 43.5.0 |
| 构建 | Gradle 8.14.1、Architectury Loom 1.11.456；JDK 21 启动 Gradle，Java 17 编译与测试 |
| 许可证 | GPL-3.0-only；JAR 根目录随构建收录仓库 LICENSE、NOTICE |

来源是 [Minecraft 官方版本元数据](https://piston-meta.mojang.com/v1/packages/ed548106acf3ac7e8205a6ee8fd2710facfa164f/1.19.2.json)、[Fabric 官方 Loader 配置](https://meta.fabricmc.net/v2/versions/loader/1.19.2/0.16.14)、[Fabric API 官方 Maven](https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/0.77.0+1.19.2/)、[Forge 官方版本列表](https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json)及 [Forge 43.5.2 官方源码](https://maven.minecraftforge.net/net/minecraftforge/forge/1.19.2-43.5.2/forge-1.19.2-43.5.2-sources.jar)。逐文件 SHA、官方校验值和必要签名保存在 [API 证据](../platforms/1.19.2/api-evidence.json)。完整 Minecraft 文件及反汇编没有收入项目。

构建时在各子项目的生成目录复制共享源码，仅将 `ServerPlayer.serverLevel()` 转为本版 `getLevel()`，将 `sendSuccess(Supplier<Component>, boolean)` 调用转为本版的 `sendSuccess(Component, boolean)`。`Component.literal` 与单人房主识别接口在官方映射中存在。共享核心、严格策略、设备关联及已有版本源码保持原样。

命令隔离使用本版本独立的 `CommandGate119Mixin`，目标是 `Commands.performCommand(ParseResults, String):int`，配置要求 `required=true`、注入 `require=1`。Forge 的事件名描述发送方，因此发往服务器的载荷由 `ClientCustomPayloadEvent` 接收；客户端保留原连接对象并验证归属，避免切服后发送过期报告。Fabric 保留同样的连接检查。Forge 资源包格式 9 已由官方客户端内 `version.json` 核实。

两份最终 JAR 的 ZIP/CRC、版本、根目录许可证及 NOTICE、class major 61、必需的 Mixin/refmap 与 JAR 内核心来源均通过核验。Fabric SHA-256 为 `305560f297b785acc3047638415138e763d7f1d73947b67e2fb627d587fe2d9d`，Forge 为 `2ed923a874817d9176c7c5e4499fbad91273e755ce23f358e5e0462ff2a966da`。

首轮配置阶段因新 Forge 子项目漏配 `loom.platform=forge` 而失败，未生成成品；补齐后第二轮成功。两轮原日志及回执均保留。Forge 的一项 `ResourceLocation` 弃用警告和 Gradle/Loom 警告仍在日志中，没有当作无警告构建。专服登录/命令门禁及真实客户端验收必须另开隔离实例，不能沿用其他 Minecraft 版本的通过记录。

在有 Java 17 toolchain 的环境，可从 `platforms/1.19.2` 执行：

```powershell
$env:JAVA_HOME = 'D:\Java\jdk-21'
$env:GRADLE_USER_HOME = 'E:\CodexTemp\Gradle\QiZhang_Games'
$env:CI = 'true'
.\gradlew.bat --no-daemon --max-workers=1 --console=plain `
  --project-cache-dir E:\CodexTemp\QiZhangVerdict\next-platforms\1.19.2\manual-project-cache `
  '-Porg.gradle.java.installations.paths=E:/CodexTemp/mods-danzi/minecraft/runtime/java-runtime-gamma/windows-x64/java-runtime-gamma,D:/Java/jdk-21' `
  -Porg.gradle.java.installations.auto-detect=false `
  -Porg.gradle.java.installations.auto-download=false build
```

路径是此次 Windows 工作区示例，其他机器应替换为自己的 JDK 与缓存目录。测试运行目录默认位于 `E:/CodexTemp/QiZhangVerdict/next-platforms/1.19.2/runtime`，可用 `-PqzRuntimeRoot` 指定；Linux 默认位于系统临时目录。自动验收使用独立 attempt 目录、启动前 5 GiB 可用内存硬门槛，并记录源码与既有 JAR 的前后 SHA。
