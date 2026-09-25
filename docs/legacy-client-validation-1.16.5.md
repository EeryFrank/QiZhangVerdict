# Minecraft 1.16.5 客户端验收记录

2026-09-25，GPL-3.0-only 的 `0.2.0-dev` 候选在 Fabric 和 Forge 的真实图形客户端上完成本地联机验收。使用官方游戏、加载器和已构建的成品模组 JAR，没有使用开发环境类文件。此记录仅覆盖表内哈希，不表示已经发布 0.2.0，也不替代 0.1.1、1.18.2 或 1.19.4 的独立证据。

| 平台 | 加载器 | 报告获准并恢复生存后仍在线 | 客户端 / 专服退出码 |
| --- | --- | --- | --- |
| Fabric 1.16.5 | Fabric Loader 0.16.14、Fabric API 0.42.0+1.16 | 66 秒 | 0 / 0 |
| Forge 1.16.5 | Forge 36.2.42 | 65 秒 | 0 / 0 |

两端都使用 Temurin Java 8u504、全新世界和重新生成的防作弊默认配置。克隆夹具时排除了账户状态、玩家存档、封禁列表和 OP 列表。验收要求全部默认值逐项相符：`companion.required=true`、`device.required=true`、`vm.action=DENY`，以及默认 IP、设备并发限制和处罚策略。配置在客户端运行前后的 SHA-256 均为 `47310c31b47287ab805bfdbf8ddddf80e8169385bd9c862239a0a0075644da4e`。

两端都确认账户与设备摘要关联已持久保存，客户端完成图形和声音初始化，并无本模组资源包元数据警告。截图为 640×360，已校验 PNG 数据、CRC、解压、尺寸和 SHA-256，并实际查看生存模式 HUD。测试完成后，客户端、专服和辅助端口都已退出或释放。

| 成品 | SHA-256 |
| --- | --- |
| qizhangverdict-fabric-1.16.5-0.2.0-dev.jar | `d9bb0837f97ccf30c4b0f19a5cd8b65197eab4b2c5137b246b0e56c94fe6aae6` |
| qizhangverdict-forge-1.16.5-0.2.0-dev.jar | `52e68051478f7e9b257432e895d81f48b54a8974f2a2a03d5f9af14d59e15779` |
| 完整 Fabric API 0.42.0+1.16 发行 JAR | `3df8dd503f35aa0ac9fab8ad9f9a369fdfd0b1ab544af19a3d626d948fb4586c` |

Fabric API 来自 FabricMC 官方发行文件，并与官方项目发布的校验值核对，实际含 44 个嵌套模块。Maven 上同版本的小型聚合 JAR 不用于运行。Java 8 客户端同时保留了官方启动元数据指定、已校验的日志配置。

首轮 Fabric 失败记录完整保留：客户端渲染到了主菜单，但没有接入专服，客户端和服务器随后均正常退出。官方 1.16.5 / authlib 2.1.28 的字节码检查确认，`--server`、`--port` 已正确传入，客户端会先用旧的社交权限服务判断是否允许多人游戏；测试用合成 token `0` 在该轮未进入允许本地离线联机的回退分支。截图中多人游戏按钮禁用，专服没有玩家加入记录。

后续验收只在测试客户端进程中使用 authlib 官方支持的环境参数，将 `services` 地址设为已保留但不监听的 `127.0.0.1` 端口，触发原版 `OfflineSocialInteractions` 回退。认证、账户和会话地址仍保持官方值；游戏、加载器、认证库及本模组的字节均未修改，也未修改用户启动器或全局设置。两端仅连接本机 `online-mode=false` 的专服。因此，这是明确的**本地合成离线认证夹具**，不证明正版账户登录或互联网认证链路已通过。

最终两端使用的验收脚本 SHA-256 为 `92d2423de37a3cd268cabf0374b94280cc0425b52359107edd66bb69c339950c`。首轮失败使用的脚本为 `e031da4f0cb34816f3e5db49fb1be6498c3ec5ac6c425c859bc896458163cd9f`。两个脚本快照均与各自结果一起保存，避免以后修改脚本混淆历史结论。

完整摘要见 [acceptance.json](../outputs/legacy-client-matrix/1.16.5-0.2.0-dev-gpl/acceptance.json)，其中索引了原字节复制的日志、结果、诊断说明、脚本快照与截图及其校验值。只公开设备关联是否存在，不公开原始系统标识、设备摘要、账户状态文件、完整启动计划或 debug 日志。

复现使用 [legacy-client-smoke.py](../platforms/legacy-client-smoke.py)。先完成官方资源准备和停止状态的对应专服夹具，再暂存候选、安装 Forge 客户端，最后用全新的 `--run-name` 串行运行。所有运行数据均放在 `E:\CodexTemp\QiZhangVerdict\legacy-client-matrix`，专服夹具位于相邻的 `legacy-runtime`；`prepare-base` 与 `stage-candidate` 不执行 Java。实际 `run` 会创建独立的严格默认配置，不继承协议测试修改过的策略。

```powershell
python platforms/legacy-client-smoke.py prepare-base fabric-1.16.5
python platforms/legacy-client-smoke.py stage-candidate fabric-1.16.5 --guard-jar platforms/1.16.5/fabric/build/libs/qizhangverdict-fabric-1.16.5-0.2.0-dev.jar --guard-sha256 d9bb0837f97ccf30c4b0f19a5cd8b65197eab4b2c5137b246b0e56c94fe6aae6
python platforms/legacy-client-smoke.py run fabric-1.16.5 --run-name new-independent-run

python platforms/legacy-client-smoke.py prepare-base forge-1.16.5
python platforms/legacy-client-smoke.py install-client forge-1.16.5 --guard-jar platforms/1.16.5/forge/build/libs/qizhangverdict-forge-1.16.5-0.2.0-dev.jar --guard-sha256 52e68051478f7e9b257432e895d81f48b54a8974f2a2a03d5f9af14d59e15779
python platforms/legacy-client-smoke.py run forge-1.16.5 --run-name new-independent-run
```

这轮未覆盖大型整合包、长期负载、旧存档、真实虚拟机厂商矩阵或恶意修改客户端报告的对抗测试。报告仍为客户端自报，设备摘要和虚拟机粗信号不能视为可信硬件证明。
