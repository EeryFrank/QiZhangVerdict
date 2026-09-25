# Bukkit 延迟挑战竞态：旧成品复现与修复验收

2026-09-25，在两个新建、仅监听回环地址的 Purpur 1.21.1 build 2329 实例上顺序验证。旧版 `0.2.0-test.1` 实际复现误踢；修复版 `0.2.1-dev` 通过同一时序检查。完整索引、原始日志和 SHA-256 见[验收报告](../outputs/bukkit-challenge-race-validation.json)。没有覆盖旧发布包或历史验收记录。

| 对象 | 实际最后挑战顺序 | 结果 |
| --- | --- | --- |
| 已发布 Bukkit `0.2.0-test.1`，SHA-256 `1e54c48f744b61cc23efe28b8516132d13dba601d9b36beab88c1da3a849f1b7` | A → B → A | 只回答最后收到的 A；没有设备关联；加入后 **20.224 秒**收到插件的必需报告超时踢出。旧产品结果保持 `passed=false`，`knownBugReproduced=true`。 |
| 开发版 Bukkit `0.2.1-dev`，SHA-256 `9849a60374ea1bb18aae2af0ee479593312437a9665b803a3f847a07c570b2c8` | A → B → B | 只回答最后收到的 B；服务器保存正确的合成账号／设备关联；报告后 **22.043 秒**仍在线，新的控制台状态确认严格策略、会话数 1、账号和设备禁令均为 0。 |

两轮各收到三个真实 `qzguard:main` 挑战包，公共记录保存其 SHA-256 和顺序，不保存服务器作用域原值。两轮 Node 和服务器均退出 0，正常保存世界；客户端均正常结束，端口 25679 已用实际 bind/listen 检查释放。共 11 组观察断言：旧版 5 组用于确认缺陷，新版 6 组用于确认修复，不能将其表述为 11 组产品通过。

## 时序如何建立

独立 QA 插件声明依赖 QiZhangVerdict，通过真实 `PlayerJoinEvent`、`PlayerRegisterChannelEvent`、Bukkit 调度和控制台命令工作。它没有反射读取核心、替换产品类或伪造 Bukkit 事件。

加入后，QA 插件临时执行原版 `tick rate 1`，为实际 TCP 通道注册提供稳定窗口。Guard 的通道注册监听先发送 A；QA 的 MONITOR 监听随后在独立控制通道发送 `BEFORE_RELOAD`，同步执行 `qzverdict reload`，再发送 `AFTER_RELOAD`。这两个标记之间的真实 Guard 报文唯一确定当前挑战 B。原产品安排的两 tick 延迟回调仍由 Bukkit 实际执行。

加入后第四个 tick，QA 插件发送 `CHECKPOINT` 并恢复 `tick rate 20`。客户端在此之前只收集挑战，之后仅回答最后收到的一份。旧轮 join／reload／checkpoint 的计数为 28／29／32，新轮为 27／28／31，均确实在原两 tick 回调前完成重载。若注册未赶上窗口，夹具会判定时序未建立，不得据此宣称产品失败或修复通过。

这是受控 TCP 客户端对慢探测及最新请求合并行为的模型。**本轮没有执行生产 `ClientReporter` 或系统／虚拟机探测**。但服务器、原有加入与重载流程、生产延迟任务、真实挑战包、设备关联和最终断线／继续在线结果均来自实际运行的产品 JAR。此前直接调用修复后生产 Runnable 的 Java 8 检查见[限定行为回归](../outputs/bukkit-challenge-scheduling-validation.json)。

## 配置、告警与范围

两轮均保持完整 **13 项默认 Guard 配置**，前后文件 SHA-256 为 `47310c31b47287ab805bfdbf8ddddf80e8169385bd9c862239a0a0075644da4e`。没有提高账号额度、修改 VM／设备／封禁策略或报告期限。临时 tick rate 仅作用于独立 QA 服务器 JVM；插件结束和 runner 的停服流程也会恢复 20。每次只运行一台服务器，堆上限 1536 MiB，启动前要求空闲内存至少 3.5 GiB；QA 编译器堆上限 128 MiB。

两轮 `minecraft-protocol 1.66.2` 日志均保留一次 `PartialReadError`，位于注册表／物品组件解析。它没有阻断本轮独立检查的 Guard 报文顺序、关联、严格状态和正常退出；这些结果不证明协议库能正确解码所有游戏包。离线模式等原始服务器告警也全部保留。测试没有安装 Grim 或矿石隐藏引擎，不外推作弊识别、透视防护、游戏体验或性能。

首次 `old-01` 仅完成文件准备，从未启动 Java。其协议记录设计包含完整挑战十六进制；在执行前改为只记录报文哈希，并另建 `old-02`，原准备目录和脚本快照保留。实际执行只有 `old-02` 与 `fixed-01` 两次，均未省略失败事实。

公开附件按报告中的 23 文件白名单逐字节复制，共 179,093 字节。复制前使用缓存内的实际作用域和设备摘要进行私下比对；未复制这些原值、`accounts.state`、`server-id.txt`、世界、Minecraft 二进制或凭据。仅保留合成玩家名称和 UUID。

复现工具为 [Python runner](../scripts/bukkit_challenge_race_smoke.py) 和 [TCP 检查](../scripts/bukkit_challenge_race_smoke.cjs)。`prepare` 不启动 Java；`run` 需要显式隔离目录与已校验的成品，拒绝覆盖已有执行结果。此处只证明所列两个 JAR 在这一 Purpur 版本上的竞态差异，不等同于所有 Bukkit 版本完成实测。
