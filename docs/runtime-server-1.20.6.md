# Minecraft 1.20.6 双加载器专服 TCP 验证

Fabric Loader 0.19.5 与 NeoForge 20.6.141 各完成 **26/26 个真实 TCP 准入用例**，合计 52 组执行、26 个不同定义。两台专服及其 Node 测试进程均正常退出 0。本轮仅验证合成伴随报告的专服准入；不作为图形客户端、真实设备或虚拟机探测、行为反作弊、Anti-Xray、性能或用户正式验收。

| 成品 | SHA-256 | 专服测试总时长 | TCP 时长 |
|---|---|---:|---:|
| Fabric 0.5.0-dev | `984a9ba2699008f857b2dc4679319944b1fdc7e2c32fcda9bd59d0e623eba59e` | 89.505 秒 | 69.453 秒 |
| NeoForge 0.5.0-dev | `a669cd344d41f6f79bbb3e19a0555030cc7d3da271ef8b97bc5281d50b78e077` | 84.407 秒 | 68.493 秒 |

两端使用 Java 21、Minecraft 协议 766、minecraft-protocol 1.66.2 / minecraft-data 3.117.0。后者对 1.20.6 使用 1.20.5 的协议 schema；本协议没有 `player_loaded` 包。Fabric API 为 0.100.8+1.20.6，Fabric Installer 为 1.1.2；Neo 使用官方 20.6.141 安装器产生的 FML 3 服务端参数和 patched server。安装退出码、原始参数、固定输入哈希和执行脚本均在附件中；生成的 patched JAR 只声明本地 SHA/CRC，不伪称有上游预期哈希。

首次启动逐行核对 **42 条默认规则（38 DENY / 4 ALERT）及全部 13 项严格默认配置**，包括来源、种类、动作和精确 ID。两端日志均记录 required `CommandGate1206Mixin` 的实际注入。获得 OP 的测试账号在报告前发送 `/say QZ_PRE_GATE` 未执行，报告后 `/say QZ_POST_GATE` 实际执行。其余用例涵盖缺失/畸形报告、同 IP 同设备仅一个账号、同 IP 不同设备三个账号上限、退出释放、关联封禁/解除、精确与通配黑白名单、含冒号旧规则 ID、CIDR 和合成 VM/VBS 信号。

批量测试明确临时提高账号累计上限到 100、每分钟尝试到 1000，报告超时缩为 4 秒（OP 门禁用例 10 秒）；开始采用 VM ALERT，VM 用例切 DENY，CIDR 用例临时加入回环网段，最后将 IP 在线上限改为 2。伴随报告、设备码必需和 BAN 策略保留。结束时 `guard.properties` 全部 13 项恢复为初始原字节，并先等待 reload 回调的状态，再发独立 status 读取新状态；两个实际回执均显示 companion required、VM DENY、blacklist DENY、device required。规则编辑用例另留下 **41 条 legacy + 2 条管理员规则 = 43 条有效规则**：`meteor-client` 换为管理员精确规则，另加 `test*cheat` 通配规则。因此这两个运行目录不适合作为默认配置模板。

Node 原日志分别保留 **Fabric 22 次、NeoForge 26 次 `PartialReadError`**，栈中包含 `ArmorTrimMaterial` / `SlotComponent`。这些错误不能被 26 项准入断言通过掩盖，也没有在本报告中归因为已测明的单一根因；不能据此声称游戏数据完整解码。每端另保留四条诊断连接 trace，未记录 error 事件或丢事件，但它们不覆盖所有连接，也不否定全局控制台的上述错误。每端 13 条拒绝原因均来自真实 deserializer 输出的 `kick_disconnect`，没有从 socket 关闭或服务端日志推测原因。

原始告警全部保留：Fabric 有库路径、Mixin 兼容级别/类版本等警告；Neo 有初始 FML/Neo 配置补默认、日志插件扫描、终端能力及 union 资源 URL 警告。两端也保留本地合成测试使用 offline-mode 的警告。两台专服均保存三个维度并正常 stop；采集时原 PID 已不存在。原执行没有独立的停服后端口 bind 回执，本次只读审查也未占用可能被后续任务复用的端口。

[机器报告](../outputs/runtime-server-1.20.6.json)逐项列出 34 份、1,220,590 字节的原始附件及 SHA-256；可从 [Fabric 执行回执](../outputs/runtime-server-1.20.6/fabric-smoke-result.json)、[NeoForge 执行回执](../outputs/runtime-server-1.20.6/neoforge-smoke-result.json)核对。执行的四份首方 helper、Node lock、完整目录快照、默认和测试后规则均明确列入白名单。没有公开账户状态、server-id、世界、设备安装标识或第三方二进制/源码；原日志中出现的设备摘要已逐一对照发布的合成 Node 输入，不是真实硬件标识。实际私密 scope 与本机 MachineGuid 仅在内存中比对，选定附件未命中。

构建、平台契约及每个精确 JAR 的 102 项核心断言另见[构建报告](adapter-1.20.6.md)，没有混入上述 52 组 TCP 计数。本轮结论只绑定表中两个 42 规则成品，不将历史 39 规则候选或旧已发布 20 个 JAR 计为本轮运行通过。
