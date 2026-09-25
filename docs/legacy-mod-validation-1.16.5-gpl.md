# 1.16.5 双模组专服开发版验收

本记录针对 GPL-3.0-only `0.2.0-dev`，不改写已发布 `0.1.1` 的验收结果。完整来源、版本、SHA、运行参数和原始证据索引见 [验收 JSON](../outputs/legacy-mod-validation-1.16.5-gpl.json)。

| 平台 | 实际加载器 | 最终成品 SHA-256 | 本轮结果 |
| --- | --- | --- | --- |
| Fabric | Loader 0.16.14、完整 Fabric API 0.42.0+1.16（44 个内嵌模块） | `d9bb0837f97ccf30c4b0f19a5cd8b65197eab4b2c5137b246b0e56c94fe6aae6` | 启动、控制台状态、26 项真实 TCP 断言、实际 Mixin、正常退出 0；111.61 秒 |
| Forge | 36.2.42 | `52e68051478f7e9b257432e895d81f48b54a8974f2a2a03d5f9af14d59e15779` | 启动、控制台状态、实际 Mixin、保存三维度并正常退出 0；34.65 秒 |

两端均使用 Temurin JDK `8u504-b01`，有效最大堆为 `1536M`，官方安装器均退出 `0`。安装器由官方仓库校验和核验；Fabric API 使用 FabricMC 完整发行文件并核对 Modrinth 官方项目 SHA-512，避免旧版 Maven 聚合包缺内嵌模块的问题。两份实际安装的 Mojang `server.jar` 均与官方版本元数据的 SHA-1、大小一致。测试只监听 `127.0.0.1:25651/25652`；进程及端口均已释放。

Fabric 真实 TCP 回归包括正常报告、等待期 OP 指令门禁、报告超时、异常报文、同 IP/同设备与不同设备配额、退出释放、关联设备封禁、账号与设备分别解封、精确/模糊黑白名单增删、带冒号默认规则 ID、CIDR 拒绝和 VM 信号策略。真实 OP 在报告前发送的命令未执行，报告后命令出现在服务器日志。26 项对应 [原始协议结果](../outputs/evidence/legacy-1165-gpl-fabric-protocol-result.json) 的实际条目，不是估算测试数。

两端运行时分别导出了实际变换后的 `class_2170` / `net.minecraft.command.Commands`。服务器停止后，使用原生 Java 8 `javap` 核对命令分派方法确实调用注入处理方法，处理方法确实调用 `MinecraftGuard.isWaiting`；公开 [字节码核验摘要](../outputs/evidence/legacy-1165-gpl-mixin-bytecode-verification.json) 包含对应调用证据和原始文件 SHA。Minecraft 整个类文件及完整反汇编留在缓存，不作为产品源码发布。

两端首次状态均显示报告必需、设备必需、VM `DENY`。**Fabric TCP 回归会修改测试策略**：报告期限通常 4 秒、门禁用例 10 秒，账号/频率上限分别改为 100/1000，VM 通常 `ALERT` 并在专门用例切换 `DENY`，另测试在线上限 2 和 IP 拒绝。故本记录不证明默认 20 秒期限下的持续在线；真实客户端严格默认策略的验收另行记录。Forge 本轮未连接玩家，仅完成专服及实际 Mixin 验收。

Fabric/Forge 原日志分别保留 21/22 行 WARN，均无 ERROR 级日志；Mixin 调试文本中的 `Exception` 字符不等于 ERROR。准备阶段曾因旧版 Modrinth 元数据把全部文件标为 `primary=false` 而停止下载选择；在任何 Fabric Java 执行前已改用唯一匹配固定 SHA-512 的文件。产品 JAR 未改变。请求的平坦地形配置在此版本未被解析为平坦世界，实际生成普通主世界；本轮没有透视矿物数据或世界生成验收。

本轮没有图形客户端、真实 VM 硬件探测、外部 Grim/AntiXray、作弊准确率、误报矩阵、整合包、旧存档或性能结论。TCP 玩家及设备报告均为合成数据，未公开账号状态、世界或原始系统标识。

独立入口为 [legacy_mod_smoke.py](../scripts/legacy_mod_smoke.py)：`stage --minecraft 1.16.5 --loader fabric|forge --mixin-audit --directory <新目录>`，然后 `install --directory <目录> --accept-eula`、`run --directory <目录> --guard-jar <对应成品> --expected-guard-sha256 <固定SHA>`。脚本保留 1.18.2 / 1.19.4 的原行为，未修改冻结的现代运行器及协议夹具。1.16.5 安装/运行前要求至少 4 GiB 空闲物理内存。
