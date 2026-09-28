# Minecraft 1.20.6 构建候选

Fabric 与 NeoForge 的 `0.5.0-dev` 最终两份成品已通过构建、静态包检查和精确 JAR 核心回归。[构建报告](../outputs/adapter-build-1.20.6.json)列出 30 份显式公开附件及其原文件哈希。报告只覆盖构建和包内核心；服务器、TCP、真实图形客户端及生产服 Mixin 隔离的验收分别记录，不在这里宣称通过。

| 输入 | 固定版本 |
| --- | --- |
| Minecraft / Java | 1.20.6 / Java 21 |
| Gradle | 9.2.1 |
| Fabric Loom / Loader / API | 1.14.10 / 0.19.5 / 0.100.8+1.20.6 |
| NeoForge / ModDevGradle / FML | 20.6.141 / 2.0.147 / 3.0.45 |
| 首方源码和成品许可证 | GPL-3.0-only |

| 最终成品 | 字节 | SHA-256 |
| --- | ---: | --- |
| Fabric | 97,447 | `984a9ba2699008f857b2dc4679319944b1fdc7e2c32fcda9bd59d0e623eba59e` |
| NeoForge | 95,765 | `a669cd344d41f6f79bbb3e19a0555030cc7d3da271ef8b97bc5281d50b78e077` |

两份成品各含 29 个首方类，class major 均为 65。ZIP/CRC、版本、GPL 元数据及根目录 `LICENSE`、`NOTICE` 与仓库逐字节一致；没有打入 Minecraft 类、测试类或嵌套第三方 JAR。源码 JAR 的哈希另列在报告中。

最终 [all-42-01 原日志](../outputs/adapter-build-1.20.6/build-all-42-01-console.log)记录 **23 项可执行 Gradle 任务全部实际执行**，用时 64.386 秒、退出码 0。Fabric 的连接调度 12 项、命令解析和原始 payload 编解码实际通过；标准 JUnit 为 `NO-SOURCE`。NeoForge 的连接调度 9 项，以及官方 FML 引导下的两项 JUnit 均在本轮实际执行，零失败、错误、跳过，没有把 `FROM-CACHE` 算作执行。[JUnit 派生摘要](../outputs/adapter-build-1.20.6/neoforge-junit-summary.json)绑定原 XML 哈希和本轮时间，原 XML 因含本机 hostname 未公开。FML 配置实际位于 `E:/CodexTemp/QiZhangVerdict/compat-1.20.6/builds/all-42-01/runtime/neoforge-junit/config`。

按报告口径共 **102 项核心检查**：57 项安全回归、42 条目录规则、3 项管理员配置保留及普通 ID 控制。对 [Fabric 精确成品](../outputs/adapter-build-1.20.6/core-fabric-result.json)和 [NeoForge 精确成品](../outputs/adapter-build-1.20.6/core-neoforge-result.json)各执行一次，共 **204 次包内核心检查执行**；平台调度及 JUnit 不加入此数字。测试先核验 `GuardService` 的 CodeSource 是指定 JAR，测试运行器只有 4 个测试/来源检查类，编译禁止生产源码搜索。运行器以 Java 8 语法编译，实际运行及成品使用 Java 21，不意味着 1.20.6 支持 Java 8。本报告不另计源码核心测试。

[本轮目录快照](../outputs/adapter-build-1.20.6/catalog-42.tsv)包含 42 个精确 ID，其中 38 条 `DENY`、4 条 `ALERT`。核心回归验证管理员已有配置、`OFF` 和删除项不会被默认目录自动覆盖；目录数量不证明覆盖所有作弊工具，设备及虚拟机信号仍为可伪造的客户端自报。

构建历史全部保留，旧候选没有冒充最终成品：

| 轮次 | 退出码 | 范围 |
| --- | ---: | --- |
| [fabric-01](../outputs/adapter-build-1.20.6/build-fabric-01-result.json) | 0 | 首轮 39 条规则；原始 JAR 在缓存独立保留，已由 42 条候选替代。 |
| [neoforge-01](../outputs/adapter-build-1.20.6/build-neoforge-01-result.json) | 0 | 首轮 39 条规则；原始 JAR 在缓存独立保留，已由 42 条候选替代。 |
| [all-42-01](../outputs/adapter-build-1.20.6/build-all-42-01-result.json) | 0 | 最终 42 条规则，两端构建和本报告的成品验证对象。 |

最终构建的 47 个输入源码文件哈希复查一致，此前发布的 20 份制品逐一重算哈希均未变化。这不是对旧 20 份重新构建或重新运行验收。原日志中的 Gradle 弃用、API 弃用和 FML 初始化配置警告均原样保留。

本适配使用 1.20.6 的 `ResourceLocation`、`RegistryFriendlyByteBuf` 与 FML 3 接口。两端 `qzguard:main` 保持原始字节协议、30,000 字节上限和数组隔离，不加第二层 VarInt 长度。Fabric 绑定原接收 handler 的稳定 sender，Neo 绑定原 listener/connection；异步报告回复前仍检查连接归属及存活。物理客户端入口不会加载到专用服。

`CommandGate1206Mixin` 为 `HEAD`、`cancellable=true`、`require=1`，配置 `required=true`、`defaultRequire=1`。Fabric 包内 refmap 指向 `class_2170.method_9249(ParseResults,String):void`；Neo 使用生产 Mojang 名称，不带 refmap。只读检查官方 1.20.6 服务端类确认有签名、无签名玩家命令都调用这一目标方法；实际生产注入和玩家门禁仍须运行证据。

公开附件仅包含逐项白名单内的日志、回执、目录快照、首方测试与整理工具。没有复制第三方源码/安装器、失败或历史二进制、世界、账号状态、设备标识或服务器 scope。整理过程没有启动 Java、安装器或游戏。

随后完成的实际运行记录见[专服 TCP](runtime-server-1.20.6.md)和[图形客户端](runtime-client-1.20.6.md)。本地重新构建需 JDK 21，在仓库根目录执行：

```text
platforms\1.20.6\gradlew.bat -p platforms/1.20.6 build :fabric:commandParserSmoke
```

可通过 `-PqzRuntimeRoot=<临时目录>` 指定开发运行和 JUnit 游戏目录。远端 CI 另行执行，构建成功不替代对应 JAR 的运行验收。
