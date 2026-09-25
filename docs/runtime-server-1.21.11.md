# Minecraft 1.21.11 双加载器专服 TCP 验收

Fabric Loader 0.19.5 与 NeoForge 21.11.45 两服均完成 **26/26 项真实 TCP 用例**，服务器和 Node 进程均正常退出 0，共 52 次用例执行、26 个独立用例定义。测试使用 Java 21、Minecraft 协议 774、minecraft-protocol 1.66.2 / minecraft-data 3.117.0。这里只验证专服与合成伴随报告；不代替图形客户端、真实虚拟机、透视混淆或行为反作弊验收。

| 成品 | SHA-256 | 服务器总时长 | TCP 时长 |
|---|---|---:|---:|
| Fabric 0.4.0-dev | `732ba77c6978785a8969c6f92476b8c57009be464b9210bfef2c9bb19c0d6ce5` | 94.707 秒 | 75.046 秒 |
| NeoForge 0.4.0-dev | `47dc8edff5faeb9c41ce19575bd37f49a2205877d99f814aa7acc33c0440d789` | 90.299 秒 | 76.732 秒 |

两服均先验证全新 **39 条默认规则（35 DENY / 4 ALERT）和 13 项严格策略**。实际日志记录 required `CommandGate12111Mixin` 注入；已获 OP 的测试账号在报告前发送 `/say QZ_PRE_GATE` 未执行，报告后 `/say QZ_POST_GATE` 执行。另覆盖超时、畸形报告、同 IP / 同设备配额、封号及设备联动、解除封禁、精确/通配黑白名单、删除带冒号的旧规则 ID、CIDR，以及合成 VM/VBS 信号策略。

测试经显式授权暂调账号窗口配额、速率、报告超时和 VM 策略，以便顺序运行用例。结束时 `guard.properties` 的 **13 项策略已逐字节恢复**。规则编辑用例则留下 **38 条 legacy 行 + 2 条管理员规则 = 40 条有效规则**：删除旧 `meteor-client` 行后新增精确替代，并保留测试 `test*cheat` 通配规则。不能把这个隔离测试目录作为默认部署模板，也不能称测试后规则仍保持 39 条。

Node 完整控制台未观察到解码错误；另独立核对了每服 4 份 metadata trace（`CheatAccount` 三次、`QVBot14` 一次），没有 error 事件、error 状态或丢弃事件。每服 13 次拒绝均有真实 deserializer 解码的 `kick_disconnect` 理由，未用服务端日志或 socket 关闭猜测理由。这个范围不代表所有连接、所有网络包都经逐包验收。

原始上游告警完整保留：Fabric 有环境库路径、Mixin 兼容级别、shadow/final、局部变量 discriminator 等警告；NeoForge 有 DebugFile Appender 触发 kqueue/epoll 的 OSX/BSD/Linux 平台异常。Neo debug 原日志随后记录了 NIO 连接，且两服均完成用例、保存全部维度并正常退出。因此此报告不声称日志零错误。

两次原始回执保留了 subprocess.wait 的退出 0 与正常关服结果，审查时原 PID 均已不存在。原运行没有保存关服后端口 bind 回执；本审查未占用端口，也未把之后独立 GUI 测试对相同端口的复用冒充当时的证据。

完整逐项结果、安装回执、原日志、metadata trace、前后配置和实际执行辅助脚本见[机器报告](../outputs/runtime-server-1.21.11.json)。[Fabric 原回执](../outputs/runtime-server-1.21.11/fabric-smoke-result.json)和[NeoForge 原回执](../outputs/runtime-server-1.21.11/neoforge-smoke-result.json)均保留原字节；每个公开附件在机器报告 `evidence` 中列出 SHA-256、长度与来源。只收明确白名单文本；不包含 MC/第三方二进制或源码、世界、账户状态、server-id 或 installation-id。TCP 日志中的设备摘要仅对应公开 QA 常量，不是真实硬件标识。
