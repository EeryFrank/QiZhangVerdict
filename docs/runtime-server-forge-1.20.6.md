# Forge 1.20.6 专服 TCP 验证

最终 Forge 50.2.0 / QiZhangVerdict 0.5.0-dev 完成 **26/26 项真实 TCP 准入断言**，专服与 Node 测试进程均退出 0。最终 JAR SHA-256 为 `eee8d545fdce4372dad51bfba4ae57159810267555077e6a2e73d21736c9f09a`，本轮总时长 96.158 秒，TCP 81.792 秒。这是合成报告测试，不是图形伴随客户端、真实设备或 VM 探测、行为反作弊、Anti-Xray、性能或用户正式验收。

首轮 `forge-42-01` 保留为产品启动失败：旧 JAR `c2999ef8e8f55aae0d8400c2d6bf7fbba6b5c0e4d0a0e6219bed1fbb7f11e29d` 在 4.012 秒内退出 1。Forge 内置 Mixin 0.8.5 明确拒绝配置中的 `JAVA_21`；尚未到 Done、未创建世界或 Guard 状态，也未执行 TCP。该尝试没有计入通过数量。成功尝试 `forge-42-03` 的 required `CommandGate1206Mixin` 实际注入，配置兼容级别为 `JAVA_17`，仍要求 defaultRequire=1。

另保留 1 次已到 Done 但首条 TCP 断言失败的历史尝试：`joined=true`、`sent=false`，后续 26 组没有完成。它们的严格默认、恢复回执和正常 stop 属于各自已观察范围；退出 0 不等于 TCP 通过，也不能据后来别的夹具成功反推唯一根因。

首次配置逐行核对全部 **42 条规则（38 DENY / 4 ALERT）与 13 项严格默认属性**。实际 OP 账号在报告前发送的命令未执行，报告后命令执行。其余用例涵盖同 IP 同设备并发限制、不同设备 IP 配额、退出释放、缺失/畸形报告、关联封禁/解除、黑白名单与通配规则、CIDR 及合成 VM 信号。

批量 QA 临时提高滚动账号/尝试限制、缩短报告超时，并通过用例修改 VM、CIDR 和在线人数配置；机器报告完整保留实际 overrides 与恢复前属性。结束时严格 13 项属性恢复原字节，先等异步 reload 回调返回，再发新 status，两个实时回执均核对 required companion/device 与 DENY 策略。名单编辑后保留 41 条 legacy + 2 条管理员规则，共 43 条有效规则，测试目录不能直接当作生产默认模板。

协议为 766，Node 所用准确依赖版本见原执行回执。Node 控制台保留 **26 次 PartialReadError**，有关栈与所有加载器告警原样公开；26 项准入断言不代表游戏包完整解码。13 条拒绝原因来自真实 deserializer 的 kick_disconnect，而非从断线或服务器日志反推；四条诊断 trace 的边界单独记录。专服正常保存维度并退出，未捏造原执行没有记录的停服后端口 bind 证据。

第三轮首连接的注册写入为 272.0718 ms，公开挑战为 763.9881 ms，报告写入为 763.9929 ms，注册到挑战间隔 **491.9163 ms**。它短于旧版约 1200 ms 的登录后观察窗，因此本轮时序不能证明第二轮一定是挑战超过旧窗才失败。新 QA 改为等待实际发报告或断线、最多 10 秒，并保留发送后 1200 ms 拒绝观察；26 项断言、wire 序列化及 silent/hold 时序保持。15 项纯 Node 假时钟/事件测试与前后执行脚本哈希单独附上，不计入真实 TCP 数量。第二轮没有这份 trace，原失败的唯一原因仍未测明。

[机器报告](../outputs/runtime-server-forge-1.20.6.json)明确列出 43 份、7,095,730 字节附件，含[首轮失败](../outputs/runtime-server-forge-1.20.6/forge-42-01-smoke-result.json)、[最终成功](../outputs/runtime-server-forge-1.20.6/forge-42-03-smoke-result.json)、实际执行脚本与 Node lock、配置快照、官方安装器回执及原始日志。没有复制状态、scope、世界或依赖 JAR；日志里的设备摘要逐一由执行的合成输入复算，真实 MachineGuid 与 scope 仅内存扫描，选定内容零命中。

构建和精确 JAR 核心检查另见[Forge 构建报告](adapter-forge-1.20.6.md)；原 [Fabric/NeoForge 专服报告](runtime-server-1.20.6.md)独立保留，不将其他加载器的 52 次执行计入本报告。
