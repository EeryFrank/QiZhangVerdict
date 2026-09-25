# Minecraft 1.20.4 适配候选

本目录为 Fabric、Forge、NeoForge 三端的 `0.3.0-dev` 候选，尚未发布。三端生产 JAR 已构建成功，通过静态打包检查及每端命令解析、报文编解码测试；另在 Java 17 上分别从三份精确 JAR 运行核心回归。核心回归是 **97 项独立断言在三个制品中各执行一次，共 291 次执行**（每端 57 项安全、37 条目录规则、3 项管理员配置保留及普通 ID 控制），不是 291 项不同用例。[本版本报告](../outputs/adapter-build-1.20.4.json)保留实际范围与原始附件。

本报告截止时，专服启动、实际 Mixin 注入、协议客户端和真实渲染客户端尚未验收；不采集进行中的测试作为通过记录，也不以其他版本或远端 CI 的构建结果替代。已有 `0.2.0-test.1` 公开安装包保持原样。

| 输入 | 固定版本 |
| --- | --- |
| Minecraft / Java | 1.20.4 / Java 17 |
| Fabric Loader / Fabric API | 0.16.14 / 0.97.3+1.20.4 |
| Forge | 49.2.9 |
| NeoForge | 20.4.251 |
| Gradle / Architectury Loom | 8.14.1 / 1.11.456 |
| 首方源码与制品许可证 | GPL-3.0-only |

| 最终制品 | 字节 | SHA-256 |
| --- | ---: | --- |
| Fabric | 93,904 | `b8d1d1ad6e2afd41acd15aeb2fb93221b9b5a8803da5e8be0c2da86805c571e4` |
| Forge | 94,793 | `9e8ad322c83469b686671bda0e6d86207cd8a2e838085dcf53b0c65253a7b9cf` |
| NeoForge | 93,937 | `c3e742892ef723d035b81e165eed3ef4a560aa249349183298dd0f9b45e48f66` |

依据 [Mojang 官方版本元数据](https://piston-meta.mojang.com/v1/packages/a8203fe4dde85f7ff8fa480a6fbf645d9d29b04f/1.20.4.json)、[Fabric API 官方 Maven](https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/0.97.3+1.20.4/)、[Forge 官方版本列表](https://files.minecraftforge.net/net/minecraftforge/forge/index_1.20.4.html)以及 [NeoForge 20.4 网络文档](https://docs.neoforged.net/docs/1.20.4/networking/payload/)确定适配接口。Forge 49.2.9 和 NeoForge 20.4.251 的实际源码包也已通过官方 SHA-1 核验。运行输入使用 Fabric API 的[完整官方发行包](https://api.modrinth.com/v2/version/BPX6fK06)，核对 SHA-1、SHA-512、描述符与嵌套 JAR；不能用 Maven 聚合根包替代完整运行依赖。报告记录官方 URL 与文件哈希，Minecraft 二进制、映射和第三方源代码未收入公开附件。

这个版本的命令执行方法返回 `void`，使用独立且必须成功注入的 `CommandGate1204Mixin`。静态解析三个成品的 class 注解确认 `HEAD`、`cancellable=true`、`require=1`，Mixin 配置均为 `required=true`、`defaultRequire=1`。Fabric 成品 refmap 映射到 `class_2170.method_9249(...):void`，Forge 映射到 `Commands.m_242674_(...):void`。NeoForge 成品没有 refmap，保留命名目标 `Commands.performCommand(...):void`；这属于静态发现，必须另用真实 NeoForge 进程证明注入成功及等待报告期间的命令门禁。

Fabric 保留该版本仍提供的 buffer 网络接口；Forge 49 使用 `ChannelBuilder` 和统一的 `CustomPayloadEvent`；NeoForge 20.4 使用 `RegisterPayloadHandlerEvent`、带命名空间的 registrar 和显式主线程调度。不能把 1.20.1 或 1.21.1 的网络注册调用原样当成本版本实现。

网络报文保持 `qzguard:main` 原始字节格式，没有添加长度前缀或消息编号，以便后续核验与 Bukkit 服务器的兼容性。Forge 限定 PLAY 阶段与收发方向，异步回复重新核对客户端连接；NeoForge 在主线程处理玩家报告。所有端均复用核心策略、设备关联与名单规则，客户端上报的身份仍可伪造，不是可信硬件证明。

三份 JAR 的 ZIP/CRC、内部版本、GPL-3.0-only 元数据、与仓库逐字节一致的根目录 `LICENSE`/`NOTICE`、全部 class major 61 均通过核验。所有 class 均在首方 `cn/qizhang/guard` 命名空间内，没有打包 Minecraft/加载器 class 或嵌套第三方 JAR。三端嵌入核心的 class 哈希一致；核心回归另外验证生产 `GuardService` 确实来自被指定的 JAR，而不是源码编译目录。

构建第 01 轮退出 0，原日志保留 Loom beta 与 Gradle 9 不兼容的弃用警告。本轮构建前后 53 个输入文件稳定，63 个旧制品重新核对未变。构建命令从 `platforms/1.20.4` 执行 `gradlew build`，由 JDK 21 启动 Gradle，Java 17 编译与测试。此次 Gradle `check` 仅包含三个加载器各自的命令解析和原始报文编解码任务，覆盖 30000 字节边界与调用方数组隔离；核心 97 项断言由后续独立 JAR 回归执行，不能混称为 Gradle 已执行。

[独立测试工具](../outputs/adapter-build-1.20.4/run-exact-jar-checks.py)默认仅检查路径、哈希并打印计划，不启动 Java。获得测试窗口后，从项目根目录执行下列命令可复验；输出目录必须为全新目录。编译测试入口的 JVM 上限为 256 MiB，测试 JVM 为 128 MiB，不编译产品源码，也不启动游戏：

```powershell
python -B outputs/adapter-build-1.20.4/run-exact-jar-checks.py `
  --output-root E:/CodexTemp/QiZhangVerdict/next-platforms/1.20.4/artifact-core/02 `
  --execute
```

此次实际运行使用 `artifact-core/01`；Java/Javac 精确路径、工具和用例源码哈希、全部退出码及原字节日志均见附件。[静态审计工具](../outputs/adapter-build-1.20.4/audit-static.py)只解析文件与公开来源，不加载或执行 Minecraft 字节码。Windows 缓存位于 `E:/CodexTemp/QiZhangVerdict/next-platforms/1.20.4`；服务器、客户端与远端 CI 应分别追加自己的完整验收记录。
