# Fabric 1.16.5 + AntiXray 1.1.0：Java 17 集成失败记录

2026-09-25 的独立专服测试在世界初始化前失败，**没有通过集成验收**。[公开结果](../outputs/legacy-fabric116-antixray110-java17-validation.json) 保留原始结果、控制台、崩溃报告、完整严格策略、配置、依赖哈希和实际运行脚本快照。首次目录 `java17-01` 只有文件准备；唯一实际运行为 `java17-02`。

固定组合为 Minecraft 1.16.5、Fabric Loader 0.16.14、完整 Fabric API 0.42.0+1.16、Drex AntiXray 1.1.0 和 Verdict `0.2.0-dev`。AntiXray SHA256 为 `7c8d22a2e9c8d0f88a33ce76cdb7bade18c63bb2a5cc9b3a11991bd28c742f43`，Verdict 为 `d9bb0837f97ccf30c4b0f19a5cd8b65197eab4b2c5137b246b0e56c94fe6aae6`。它们均按原字节运行，未重新构建；之后的核心源码修复不属于这个成品。

服务端使用 Temurin 17.0.20.1+1、最大堆 1536 MiB，启动前可用物理内存 10.2502 GiB，通过 3.5 GiB 硬门槛。原 Java 8 夹具仅提供不可变安装文件，没有复制其世界、账户、封禁、配置或日志，也没有修改旧夹具。

原始日志中的致命异常来自 `antixray.mixins.json:ChunkMapMixin`：其 Redirect 无法在实际 `net/minecraft/class_3898` 上找到 `lambda$scheduleChunkLoad$14`。没有出现 `Done`，随后世界保存路径也发生空引用异常。Java 自行返回 0；**本报告将此判为启动失败，而非正常启停通过**。进程已结束，端口 25673 已重新绑定核验释放。

Verdict 已生成完整 13 项默认策略，包含必需配套报告、必需设备字段、20 秒期限、VM `DENY`、黑名单 `DENY` 与拒绝后 `BAN`。策略 SHA256 为 `47310c31b47287ab805bfdbf8ddddf80e8169385bd9c862239a0a0075644da4e`，没有放宽。AntiXray 生成配置与精确发布 JAR 的资源逐字节一致，主世界仍为默认 `enabled=true / engineMode=2`；计划中的模式 1 修改尚未执行。**合法报告、OP 命令门禁、设备绑定、在线期限、真实区块矿石混淆和挖掘揭露均未执行。**

上游精确源码中的 [ChunkMapMixin](https://github.com/DrexHD/AntiXray/blob/a113ce0b0616052de80ca8719986a09849348ce0/src/main/java/me/drex/antixray/mixin/ChunkMapMixin.java) 使用了同一个方法名。本轮对发布 JAR 和实际运行时 class 做了只读二进制检查：Mixin 保留该 named 选择器，其 refmap 只有 ProtoChunk 类映射，目标类 106 个方法里没有该名称。检查摘要见[上游审查](../outputs/evidence/legacy-fabric116-antixray110-java17-failed-upstream-review.json)；完整 Minecraft 方法清单只留临时缓存。

[官方 issue #48](https://github.com/DrexHD/AntiXray/issues/48) 已在 2024 年报告同一错误，涉及 Loader 0.15.11、Java 21 和 AntiXray 1.1.0。[作者回复](https://github.com/DrexHD/AntiXray/issues/48#issuecomment-2231846519)表示不再调查 1.16.5。官方 Modrinth 对 1.16.5 的本次查询仅列出 1.1.0、1.0.2、1.0.1；三个官方 JAR 均按官方 SHA512 校验，并静态发现相同选择器及映射缺项。两个旧版本未启动，不能当作可用替代。GitHub 部分列表 API 限流，未据此声称穷尽所有分支或未来修复。

[独立 QA 入口](../scripts/legacy_fabric_antixray_smoke.py) 保留了后续测试计划：无天然矿石的平坦世界，在同一高度放置六面石头包围的钻石矿与邻接空气的钻石矿；控制台确认真实方块后，对实际 `map_chunk` 的明确坐标解码，再检查移除邻石的揭露更新。这些目前只是未执行的验收步骤，不能算现有防透视证据。

没有改 Loader、跳过 Mixin、修改第三方 JAR 或发布补丁。所有公开附件均采用显式白名单；没有发布账户状态、设备摘要、原始系统 ID、世界、Minecraft 二进制或完整反编译结果。
