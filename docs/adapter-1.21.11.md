# Minecraft 1.21.11 构建候选

Fabric 与 NeoForge 的 `0.4.0-dev` 两份成品已构建成功，通过静态制品审查、平台契约测试和精确 JAR 核心回归。[构建报告](../outputs/adapter-build-1.21.11.json)附有 74 份原字节证据，保留失败尝试，不覆盖此前发布的 18 份制品。

这是一份**构建阶段报告**。服务器启动、生产环境中的 Mixin 注入、实际玩家命令隔离、TCP 准入和真实渲染客户端须分别验收；本报告不引用进行中的游戏测试作为通过依据，也不以 Java 编译或 FML 测试引导代替这些结果。

| 输入 | 固定版本 |
| --- | --- |
| Minecraft / Java | 1.21.11 / Java 21 |
| Gradle | 9.2.1 |
| Fabric Loom / Loader / API | 1.14.10 / 0.19.5 / 0.141.6+1.21.11 |
| NeoForge / ModDevGradle / FML | 21.11.45 / 2.0.147 / 10.0.36 |
| 首方源码和成品许可证 | GPL-3.0-only |

| 最终成品 | 字节 | SHA-256 |
| --- | ---: | --- |
| Fabric | 97,169 | `732ba77c6978785a8969c6f92476b8c57009be464b9210bfef2c9bb19c0d6ce5` |
| NeoForge | 95,394 | `47dc8edff5faeb9c41ce19575bd37f49a2205877d99f814aa7acc33c0440d789` |

两份 JAR 各含 29 个首方类，均为 Java 21 的 class major 65；ZIP/CRC、内部版本、GPL 元数据、与仓库逐字节一致的 `LICENSE`/`NOTICE` 均通过检查。没有打包 Minecraft 类、测试类或嵌套第三方 JAR。源码 JAR 的哈希另列在报告中。[静态审查原记录](../outputs/adapter-build-1.21.11/static-result.json)记录了具体类注解、来源和边界。

核心是 **99 项独立断言**：57 项安全回归、39 条目录规则、3 项管理员配置保留及普通 ID 控制。它们在源码环境和两份精确成品中各执行一次，共 **297 次执行**，不是 297 项不同用例。成品回归先验证生产 `GuardService` 来自指定 JAR，再执行相同测试；测试运行器以 Java 8 语法编译，运行及被测成品使用 Java 21，不能据此声称本版支持 Java 8。[源码回归](../outputs/adapter-build-1.21.11/core-source-result.json)、[Fabric 成品回归](../outputs/adapter-build-1.21.11/core-fabric-result.json)、[NeoForge 成品回归](../outputs/adapter-build-1.21.11/core-neoforge-result.json)均保留命令、退出码和原日志哈希。

平台测试分别记录，不能加入上面的核心用例数：

- Fabric 的连接调度 12 项断言、命令解析和原始报文编解码三组 `JavaExec` 在第 06 轮实际执行。主函数测试位于独立 `src/smoke`，由 `check` 必需依赖；标准 JUnit 任务没有测试源，因此为 `NO-SOURCE`，没有关闭“发现不到测试则失败”的检查。
- NeoForge 的连接调度 9 项断言在第 05、06 轮实际执行。命令和报文两项 JUnit 在第 **05** 轮通过官方 ModDev/FML 测试引导实际执行，零失败、零错误、零跳过；第 **06** 轮该任务为 `FROM-CACHE`，不重复计作一次执行。[第 05 轮原日志](../outputs/adapter-build-1.21.11/build-05-neoforge-junit-console.log)保留两项 `PASSED` 和 FML 引导过程。

原始构建历史如下，各轮完整日志与结果均在报告白名单内：

| 轮次 | 退出码 | 实际结果 |
| --- | ---: | --- |
| 工具链 01 | 1 | 下载官方 Gradle 时发生 TLS PKIX 信任链错误。 |
| 工具链 02 | 0 | 使用 Windows ROOT 信任库后成功，保留校验值核验，没有关闭 TLS 证书验证。 |
| 构建 01 Fabric | 1 | 源码编译和调度测试完成；命令测试因未引导 Minecraft 注册表而失败。 |
| 构建 02 Fabric | 1 | 三组主函数测试通过；Gradle 9 的标准 Test 因测试源中没有可发现的 JUnit 测试而失败。 |
| 构建 03 Fabric | 0 | 主函数测试移至独立 smoke 源集，三组实际通过。 |
| 构建 04 NeoForge | 1 | 源码编译和调度测试完成；普通 JavaExec 缺少当前 FML Loader，命令测试失败。 |
| 构建 05 NeoForge | 0 | 两项契约改用官方 FML JUnit 环境，实际通过；调度 9 项通过。 |
| 构建 06 合并 | 0 | 两端构建通过；Fabric 三组和 Neo 调度实际执行，Neo JUnit 复用第 05 轮缓存。 |

最终合并构建输入稳定，旧 18 份制品逐份重新核对未变。[第 06 轮结果](../outputs/adapter-build-1.21.11/build-06-combined-result.json)保留全部源码哈希和旧制品哈希。原日志中的 Gradle、加载器与本机环境警告均未删改；成功范围不等于日志没有任何警告。

本版使用 [Mojang 1.21.11 官方元数据](https://piston-meta.mojang.com/v1/packages/bc03bf4398acc192063d758aecb1cb299f05d793/1.21.11.json)、[Fabric 官方发行输入](../outputs/adapter-build-1.21.11/official-fabric-inputs.json)及[NeoForge 官方输入校验记录](../outputs/adapter-build-1.21.11/official-neoforge-inputs.json)。NeoForge 网络 API 分别注册服务端与客户端处理器；客户端入口仅在物理客户端加载，回调保持主线程和连接归属检查。`qzguard:main` 的报文仍为原始字节，不加额外长度前缀。构建契约检查了 0、1、127、30000 字节、超长拒绝和数组隔离；与 Bukkit 的实际联机兼容须另测。

`CommandGate12111Mixin` 使用 `HEAD`、`cancellable=true`、`require=1`，配置同样为 `required=true`、`defaultRequire=1`。Fabric 成品包含指向 `class_2170.method_9249(ParseResults,String):void` 的 refmap，映射链经官方映射和目标类文件检查；NeoForge 保留具名 `Commands.performCommand(ParseResults,String):void`，不含 refmap。静态目标存在不能证明生产服已经执行注入或玩家门禁。

首次安装的目录现有 39 个精确 ID，其中 35 条 `DENY`、4 条 `ALERT`。新增 `ferox`、`wurstplusthree` 来自固定源码描述符；已有管理员文件、`OFF`、删除项不自动补回。该轮[目录核验快照](../outputs/adapter-build-1.21.11/catalog-verification.json)重验了 249 项来源记录与 53 项描述符证明，新增的 16 个固定 URL 实际请求；旧来源复用已验哈希缓存，没有声称本轮重新请求全部 249 个 URL。25 项目录 Python 测试及 9 项核心日志判据回归均通过。目录不是所有作弊工具的穷尽清单，真实检测和客户端自报可信度也不由目录数量证明。

公开附件只复制明确列出的首方测试、工具、原日志、结果及来源哈希元数据。Minecraft/第三方二进制、完整源码和映射、失败 JAR、世界、账号状态、设备标识与服务器 scope 均未纳入。JUnit XML 因带有本机主机名元数据未复制，保留其 SHA-256、静态审计结果和第 05 轮实际执行日志。缓存中的第一次静态审查遇到源码调整、第二次读到并发构建输出，这两条记录也保留，未误记为最终产品失败。
