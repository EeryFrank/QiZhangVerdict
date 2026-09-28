# Minecraft 1.17.1 构建候选

Fabric 与 Forge 的 `0.6.0-dev` 使用 Java 16 字节码和运行环境；Gradle 8.14.1 由 JDK 21 启动，Java 16 工具链负责编译。固定输入为 Architectury Loom 1.11.456、Architectury 3.4.164、Fabric Loader 0.19.5、Fabric API 0.46.1+1.17、Forge 37.1.1。首方代码采用 GPL-3.0-only，完整记录见[构建报告](../outputs/adapter-build-1.17.1.json)。

| 最终成品 | 字节 | SHA-256 |
| --- | ---: | --- |
| Fabric | 95434 | `bda006d24663acb3698c8fb76d06d14220dfca18422c8eb9177499f5c498e497` |
| Forge | 99008 | `a71d6bb215426927b5db4cf2ea6278aa4bc92615d750d1bfa42b7d1469dde813` |

两份精确成品各通过 104 项包内核心检查：57 项安全回归、44 条目录规则和 3 项管理员配置保留及普通 ID 控制；合计 208 次执行，不是 208 个不同用例。平台命令解析、连接调度和 payload 检查另计。ZIP、CRC、描述符、GPL、NOTICE、Mixin/refmap 和首方 class major 60 均另行检查。没有打入 Minecraft 类、测试类或第三方嵌套 JAR。

首次双端构建的 29 项任务全部执行。之后实际 Forge 专服测试发现 `isRemotePresent` 只读取 FML 登录握手记录，标准 `minecraft:register` 客户端因而收不到挑战。最终 Forge 包删除这一发送前提，仍检查原连接、当前 PLAY listener 和存活状态；挑战报告、设备要求、隔离与超时策略保持不变。第二次 Forge 构建退出 0：15 项可执行任务中 13 项实际执行，两个测试编译任务来自缓存；命令解析、连接调度、legacy payload 和测试任务实际执行。图形客户端启动前检查随后发现 Forge 没有 SLF4J provider，共享代码的裁决和状态保存错误日志会被吞掉；第三次构建将 Forge 入口及生成的共享类接到其现有 Log4j 后端，Fabric 字节保持不变。第三次构建同为 15 项任务中 13 项执行、两个编译任务来自缓存，三个 smoke 和测试任务实际执行，退出 0。所有旧构建报告及失败运行仍保留，不能以旧 Forge 包的结果代替最终包。

两端继续使用原始 `qzguard:main` 字节协议，上限 30,000 字节，异步处理和延迟回复绑定原连接。客户端类仅在物理客户端加载。命令门禁为 required Mixin，注入 `Commands.performCommand(CommandSourceStack,String):int` 的 HEAD，允许取消且要求至少匹配一次；实际生产注入与准入效果由独立运行报告证明。

新包首次启动默认 44 个精确 ID（40 DENY、4 ALERT）；管理员已有名单、OFF 和删除项不会自动恢复。更新及同名普通模组的处理见[目录说明](catalog.md)。已发布的 23 个旧 JAR 保留原字节及各自默认目录，未因此次构建重新验收。

本机运行使用经过官方散列核验的 Temurin 16.0.2+7。Forge 安装配置只为 SLIM 和 EXTRA 声明必须匹配的输出散列；其未被 processor outputs 使用的 PATCHED_SHA 与本机生成文件不同。验证保留这一差异，并独立重放官方补丁，逐一核对 1252 个输出类及完整条目集合，不能把未声明的散列差异静默忽略，也未断言差异原因。

构建和包内检查不证明全部游戏行为、正版认证、真实 VM 对抗、代理或插件服互通。对应专服和图形客户端结果分别记录。
