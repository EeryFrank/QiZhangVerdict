# Forge 1.20.6 适配：构建与包内核心检查

`0.5.0-dev` 使用 Forge **50.2.0**、ForgeGradle **6.0.54**、Gradle **8.12.1** 和 Java **21**，许可为 **GPL-3.0-only**。这是独立工程，不加入 Fabric/NeoForge 使用的 Gradle 9 父工程。

本报告只确认构建、静态包检查和精确 JAR 内核心规则；不宣称专服、真实客户端、网络握手或 Mixin 实际注入已经通过。完整记录见[机器可读报告](../outputs/adapter-build-forge-1.20.6.json)。原有 [Fabric/NeoForge 报告](adapter-1.20.6.md)保持独立。

| 成品 | 字节 | SHA-256 |
| --- | ---: | --- |
| 二进制 JAR | 97107 | `eee8d545fdce4372dad51bfba4ae57159810267555077e6a2e73d21736c9f09a` |
| sources JAR | 50579 | `98eb114f40f2756eafa7e5fd79395036bca5343503d26180e1b1d29702ccfb25` |

成品位于 `platforms/1.20.6/forge/build/libs/`，文件名分别为 `qizhangverdict-forge-1.20.6-0.5.0-dev.jar` 和同名 `-sources.jar`。

最终构建 `forge-42-02` 退出码 **0**，用时 **25.551 秒**。9 个 actionable tasks 中 **8 项实际执行、`compileJava` 1 项 FROM-CACHE**；生产 Java 没有变化，不能称 9 项全部重新执行。构建前后 44 个输入指纹一致，最终适配目录 22 个文件与原始冻结清单及明确修复清单闭合。20 个既有发布 JAR 和另外 4 个 1.20.6 Fabric/NeoForge 二进制与源码包仅复核哈希未变，未计作本轮重新构建或验证。

四个必需 JavaExec 检查确实执行：生产命令树解析/权限、15 项生产连接调度断言、实际 EventNetworkChannel 原始载荷编码与 30000 字节边界/缓冲区所有权，以及实际成品 JAR 的 Mixin 配置/字节码检查。后者使用真实 Mixin **0.8.5** 枚举，得到 `JAVA_17`、class major **65**、`LanguageFeatures.scan=0`、实际 ASM 最大 major **68**。`test NO-SOURCE` 表示本工程没有 JUnit 测试，不能计为 JUnit 通过。详见[最终原始构建日志](../outputs/adapter-build-forge-1.20.6/build-console.log)。

精确二进制 JAR 中的核心通过 **57 项安全回归 + 42 条目录规则 + 3 项保留/普通 ID 控制 = 102 项**。42 条规则包含 **38 DENY、4 ALERT**。运行器只编译测试类，`GuardService` 的 CodeSource 指向该成品；没有把产品源码临时重编译后当成包内检查。见[包内检查原始回执](../outputs/adapter-build-forge-1.20.6/core-result.json)。

二进制和 sources JAR 的 ZIP CRC、根目录 LICENSE/NOTICE 与项目原文一致；二进制 descriptor 和 manifest 为 `0.5.0-dev`，所有 29 个 class 的 major 为 **65**。必需 `CommandGate1206Mixin` 类、配置 `required=true`/`defaultRequire=1` 和 manifest 入口均存在。Mixin 的兼容特征集声明为 `JAVA_17`，Minecraft 运行和 javac 仍使用 Java 21。sources JAR 的 18 份生产 Java 文件与构建输入逐字节一致，其 `mods.toml` 保留 `${version}` 原始模板；它不作为可安装的二进制包。

首轮 `forge-42-01` 构建退出 0、8 项任务实际执行、包内 102 项检查通过，但其第一次专服启动 **4.012 秒后退出 1，未到 Done，未执行 wire/登录检查**：固定 Forge 50 所带 Mixin 0.8.5 不识别 `JAVA_21` 配置值。该失败见[原始启动回执](../outputs/adapter-build-forge-1.20.6/failed-server01-result.json)和[原始启动日志](../outputs/adapter-build-forge-1.20.6/failed-server01-console.log)。旧二进制 `c2999ef8e8f55aae0d8400c2d6bf7fbba6b5c0e4d0a0e6219bed1fbb7f11e29d` 已保留且被新成品替代，不能因为它的构建或核心检查成功就视作游戏验收通过。

最小修复把 Forge 模块配置改为 `JAVA_17`，新增真实 Mixin 配置与字节码检查，并保留必需隔离声明；未修改共享 core/common、生产 Java 或固定官方依赖。独立解 ZIP 比对确认：两版全部 29 个生产 class 逐字节相同，唯一变化的包内条目是 `qizhangverdict.mixins.json`。首轮 43 份源码输入快照仍保留在缓存，逐项哈希复核；公开附件保留原回执，不将历史 static-only 记录改写为新版执行证明。

警告如实保留：首轮主编译 2 条弃用待移除警告（`ResourceLocation(String,String)`、`TickEvent.phase`），smoke 编译 1 条同类 ResourceLocation 警告。最终第二轮主编译来自缓存，smoke 重新编译仍有 1 条 ResourceLocation 警告。另有 IDE 资源复制、生成缓存覆盖、Log4j 扫描、终端能力和 Gradle 9 不兼容弃用提示，具体以各轮原日志为准。本工程使用 Gradle 8.12.1，未通过删除检查或忽略失败取得成功。

原始日志、回执、冻结检查和首方测试快照共 33 个明确白名单附件，逐字节复制并记录 SHA-256/字节数；未复制世界、账号状态、设备/安装标识、第三方二进制或 Minecraft 反编译源码。设备与虚拟机信号仍是客户端自报信息，并非可信硬件证明。

复现入口为 [Forge 独立工程说明](../platforms/1.20.6/forge/README.md)。所有构建缓存、测试工作目录与临时数据应放在 `E:/CodexTemp`；实际运行前需要单独的可用内存检查。
