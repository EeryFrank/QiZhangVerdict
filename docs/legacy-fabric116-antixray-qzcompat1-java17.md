# Fabric 1.16.5 AntiXray 独立兼容补丁验收

2026-09-25，**独立维护的 AntiXray `1.1.0-qzcompat.1`** 在固定 Fabric 1.16.5 / Java 17 组合中通过了受限集成验收：严格配套报告、OP 等待期命令隔离、实际区块坐标矿石隐藏／暴露对照、邻石移除后的矿石揭露，以及报告后持续在线 22.063 秒。两次专服启动和协议客户端均正常退出 0，端口 25673 已释放。详见[验收 JSON 与 53 份附件](../outputs/legacy-fabric116-antixray-qzcompat1-java17-validation.json)。

这是第三方 MIT 兼容副本，**不是 Drex 官方发布，也不是 QiZhangVerdict 的 GPL 插件／模组**。原官方 1.1.0 的[启动失败记录](legacy-fabric116-antixray110-java17.md)原样保留。

| 固定输入 | 版本／SHA256 |
|---|---|
| Minecraft / Loader / API | 1.16.5 / Fabric 0.16.14 / Fabric API 0.42.0+1.16 完整发行 |
| Java / 内存门槛 | Temurin 17.0.20.1+1；服务端最大堆 1536 MiB；每次启动前可用物理内存至少 3.5 GiB |
| Verdict | `0.2.0-dev`，`d9bb0837f97ccf30c4b0f19a5cd8b65197eab4b2c5137b246b0e56c94fe6aae6` |
| 原官方 AntiXray | `1.1.0`，`7c8d22a2e9c8d0f88a33ce76cdb7bade18c63bb2a5cc9b3a11991bd28c742f43` |
| 独立兼容副本 | `1.1.0-qzcompat.1`，`fa72bb5e4424bc8ffb9cda83298f8c27b704dd36c3bd413660a3a58d69cc9484` |

[确定性补丁工具与说明](../integrations/compat/README.md)只接受上述原官方输入。两次独立 CLI 生成结果逐字节一致；32 个 class、嵌套 JAR、默认配置与 Mixin 必需检查全部保持原字节。只补充 refmap 的两个对应方法映射、变更显示名／版本并添加 NOTICE。原 MIT 许可正文保留；原描述符 CC0-1.0 与实际 MIT 的矛盾在 NOTICE 中明确记录。兼容 JAR 只生成在临时缓存中，本任务未提交、发布或改动 pins／lock。

最终 `run04` 使用标准平坦世界。运行前读取实际 `level.dat`，确认 `minecraft:flat`、1 层基岩／2 层泥土／1 层草方块和关闭结构生成。控制台随后填充局部石头测试盒，并确认两颗真实钻石矿、隐藏矿石的六个石头邻居及暴露矿石旁的空气。

| 位置 | 服务端控制台确认的真实方块 | 真实 `map_chunk` 解码结果 |
|---|---|---|
| `(8,32,8)` 隐藏对照 | `diamond_ore`，六面石头 | `stone`，状态 ID 1 |
| `(12,32,8)` 暴露对照 | `diamond_ore`，邻接空气 | `diamond_ore`，状态 ID 3354 |
| `(9,32,8)` 普通石头 | `stone` | `stone`，状态 ID 1 |
| `(13,32,8)` 空气对照 | `air` | `air`，状态 ID 0 |

这些判断来自实际 TCP 客户端收到的区块位置，而不是调色板中“出现过矿石”。最终 7549 字节区块数据已保存，SHA256 为 `5b2b25b8eb3c81762edcd37ded4073cb9da19693de13a689a4ad6f9dfe8f596f`。另一个不使用 prismarine-chunk 的[独立 Python 解码器](../outputs/evidence/legacy-fabric116-antixray-qzcompat1-java17-independent-packet-decoder.py)直接解析 palette 和 64 位 no-span 数组，重新确认四个坐标。移除 `(8,32,7)` 的邻石后，同一已验证客户端收到了 `(8,32,8)` 的真实钻石矿方块更新。

Verdict 完整 13 项严格默认策略始终不变，原字节 SHA256 为 `47310c31b47287ab805bfdbf8ddddf80e8169385bd9c862239a0a0075644da4e`。同一个已授予 OP 的合成协议玩家在报告前无法执行 `/say`，报告后能执行同一权限命令，随后撤去 OP。精确合成 UUID 的设备关联持久化、报告后至少 22 秒仍在线，以及该窗口之后的新生存模式查询均通过。原始策略包含 `companion.required=true`、`device.required=true`、20 秒报告期限、VM `DENY` 和拒绝后 `BAN`，没有降低策略来换取通过。

历史运行均保留，不用最终结果覆盖：

| 运行 | 实际结果与边界 |
|---|---|
| 原官方 `java17-02` | Mixin 目标缺失，世界初始化前崩溃；未执行报告或矿石用例。 |
| 兼容 `run01` | 启动、报告、OP 门禁与设备关联完成；协议夹具只确认传送而未回传位置，等待目标区块重发超时，整体失败。 |
| 兼容 `run02` | 局部控制场景、真实区块、揭露更新和严格准入全部通过；后查世界 NBT 是 noise，保留原自动 PASS，但不称为最终平坦夹具验收。 |
| 兼容 `run03` | 已是 flat，但旧版自定义生成配置被拒并回退标准层；新增 NBT 层断言在玩家登录前正确拦住测试，整体失败。 |
| 兼容 `run04` | 采用标准 flat 与显式局部填充，11 项断言通过，作为本轮最终验收。 |

最终传送阶段仍有 59 行原版 `moved too quickly` 警告，原日志未删改；本报告不声称零告警或运动／战斗反作弊通过。没有安装 Grim。此测试使用合成 Wire2 报告的协议客户端，没有图形客户端、可信设备或真实 VM 证明；只覆盖主世界模式 1 的受控位置，不证明下界、模式 2、大型整合包、性能、代理或所有透视手段。固定 Verdict JAR 仍为原有 11 条规则，不包含之后未发布的源码更新。

公开文件使用显式白名单并逐字节校验；私下比对所有本轮设备摘要与服务器 scope，未发现公开副本泄漏。未公开账户状态、原始系统 ID、世界文件、Minecraft 二进制或完整反编译结果；保存的区块样本仅为上述合成测试场景的网络数据。
