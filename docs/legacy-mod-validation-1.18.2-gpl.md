# Minecraft 1.18.2 专用服务器验收

2026-09-25 对 **GPL-3.0-only、0.2.0-dev** 两个最终 JAR 完成了独立专服验证。本记录不属于已发布的 0.1.1 五个成品，也不修改原 0.1.1 证据。[结构化报告](../outputs/legacy-mod-validation-1.18.2-gpl.json)保存成品、依赖、JDK、实际执行脚本及原始日志的路径和 SHA-256。[公开原始证据索引](../outputs/legacy-mod-evidence-index-1.18.2-gpl.json)提供 20 份逐字节复制的 JSON / 日志，包括首次失败；不分发 Minecraft 的导出类文件或第三方 JAR。

| 平台 | 实际依赖 | 本轮通过范围 | 正常退出 |
| --- | --- | --- | --- |
| Fabric 1.18.2 | Loader 0.16.14；Fabric API 完整发行版 0.77.0+1.18.2 | 启动、控制台 status、运行时 Mixin 注入、26 项真实 TCP 断言 | 安装器及专服均为 0；专服 110.84 秒 |
| Forge 1.18.2 | Forge 40.3.12 | 启动、控制台 status、运行时 Mixin 注入 | 安装器及专服均为 0；专服 49.79 秒 |

Fabric 成品 SHA-256：`65ad6fafe4eee0f326d3eebe67465e30022972e800fd1d93ac7c068cf6d613c5`。

Forge 成品 SHA-256：`c2823b070719ace443fca7ad48ae58a13f6b70d575dafbeaeb0f676aa682e4ff`。

两端使用 Temurin 17.0.20.1+1、独立新目录，按顺序启动；结束后均确认测试端口释放。原始记录位于 `E:\CodexTemp\QiZhangVerdict\legacy-runtime\fabric-1.18.2-guard-02` 和 `forge-1.18.2-guard-01`。没有安装 Grim 或 AntiXray。

## 实际断言与边界

Fabric 的 26 项通过记录包括：正常报告、缺失报告超时、畸形报告不永久封禁、同 IP 同设备拒绝第二账号、不同设备允许三个账号、第四账号拒绝、退出释放配额、作弊命中封号及关联设备、分别解除账号和设备封禁、GLOB 黑名单、白名单优先及删除、含冒号的默认规则 ID 删除恢复、CIDR 拒绝、VMware 信号拒绝、仅 HypervisorPresent 不封禁，以及将 IP 在线数改为 2 的结果。

命令门禁使用已获得 OP 权限的真实 TCP 测试账号：报告前 `/say QZ_PRE_GATE` 没有执行，报告通过后 `/say QZ_POST_GATE` 出现在服务端日志。这不是仅检查注解或类文件存在。

两端均启用 Mixin verbose、export 和 countInjections。日志记录了 `CommandGate118Mixin` 混入 Fabric 的 `net.minecraft.class_2170`、Forge 的 `net.minecraft.commands.Commands`。实际导出的目标类有独立 SHA；额外对其 JVM 指令进行解析，确认注入方法中存在调用 `MinecraftGuard.isWaiting` 的 `invokestatic`。Forge 本轮没有连接玩家，因此不把该加载证据视为 Forge 报告前后门禁行为测试。

TCP 客户端使用合成账号和自行构造的报告，并非渲染运行的模组客户端或真实虚拟机。Fabric 分支测试保持 companion/device 必填，但将正常报告超时改为 4 秒、命令门禁用例改为 10 秒，将历史账号和尝试频率上限分别设为 100、1000；VM 平常使用 ALERT，在对应断言时切换 DENY。它不证明默认 20 秒窗口下的持续在线，也不证明作弊识别率、硬件可信证明、任意整合包、旧世界迁移或性能。真实客户端结果另行记录。

## 保留的失败与告警

首轮 `fabric-1.18.2-guard-01` 失败属于测试依赖选择问题：官方 Maven 的 `fabric-api-0.77.0+1.18.2.jar` 只有 4,877 字节，不含嵌套 API 模块。它适合构建工具通过 POM 解析依赖，不能作为完整模组直接部署。启动因此缺少 `ServerLifecycleEvents`。虽然 JVM 返回 0，测试脚本仍依据未出现 Done 和 status 将结果判定失败，未将其计入通过。

第二个全新目录改用 [FabricMC 官方完整发行包](https://github.com/FabricMC/fabric-api/releases/tag/0.77.0%2B1.18.2)，并逐字节匹配[官方 Fabric API 发行元数据](https://api.modrinth.com/v2/version/qk28POfr)中的 SHA-512 和 SHA-1。完整包为 1,472,259 字节、45 个嵌套模块，SHA-256 为 `6f822fb5aa481b4a6c1cfb8612bbfecc62a58e69d2c792f61a0eafa580e75999`。防作弊成品 JAR 没有修改。

成功日志仍保留 Fabric 74 条、Forge 29 条 WARN：包括 Mixin 兼容级别提示、Forge 首次配置生成、库文件缺少 mods.toml、资源 URL、原版命令参数歧义、离线测试提示和断线回调提示。调试导出无法加载可选 Fernflower 反编译器，但类文件已实际导出。两次成功日志没有 ERROR 级别条目；原始 Fabric 结果中的一条 `error_lines` 来自宽泛的 `Exception` 字符串匹配，实际是 INFO 级别的 `getFailedException` 方法重命名记录。原始报告未重写以隐藏这些内容。

## 复现入口

`scripts/legacy_mod_smoke.py` 新增 `stage --minecraft 1.18.2` 和 `--mixin-audit`；未指定版本时仍默认 1.19.4。`install`、`run` 从目录标记读取版本。1.18.2 会下载完整 Fabric API 并核对嵌套模块，避免重复使用 Maven 聚合壳。

以下命令必须使用新的测试目录，先完成一个服务器再启动另一个。Fabric 的 run 会自动执行 26 项 TCP 测试；Forge 的 run 执行专服基础验证。

```powershell
python scripts/legacy_mod_smoke.py stage --minecraft 1.18.2 --loader fabric --mixin-audit --directory E:\CodexTemp\QiZhangVerdict\legacy-runtime\fabric-1.18.2-repeat-01
python scripts/legacy_mod_smoke.py install --directory E:\CodexTemp\QiZhangVerdict\legacy-runtime\fabric-1.18.2-repeat-01 --accept-eula
python scripts/legacy_mod_smoke.py run --directory E:\CodexTemp\QiZhangVerdict\legacy-runtime\fabric-1.18.2-repeat-01 --guard-jar platforms/1.18.2/fabric/build/libs/qizhangverdict-fabric-1.18.2-0.2.0-dev.jar --expected-guard-sha256 65ad6fafe4eee0f326d3eebe67465e30022972e800fd1d93ac7c068cf6d613c5

python scripts/legacy_mod_smoke.py stage --minecraft 1.18.2 --loader forge --mixin-audit --directory E:\CodexTemp\QiZhangVerdict\legacy-runtime\forge-1.18.2-repeat-01
python scripts/legacy_mod_smoke.py install --directory E:\CodexTemp\QiZhangVerdict\legacy-runtime\forge-1.18.2-repeat-01 --accept-eula
python scripts/legacy_mod_smoke.py run --directory E:\CodexTemp\QiZhangVerdict\legacy-runtime\forge-1.18.2-repeat-01 --guard-jar platforms/1.18.2/forge/build/libs/qizhangverdict-forge-1.18.2-0.2.0-dev.jar --expected-guard-sha256 c2823b070719ace443fca7ad48ae58a13f6b70d575dafbeaeb0f676aa682e4ff
```

上述专服结果实际由缓存中的外部适配器调用当时冻结的运行脚本产生，精确脚本 SHA 已写入报告。之后整理进仓库的通用入口已通过 Python 语法检查、1.18.2 与默认 1.19.4 的真实 stage-only 检查，并对原导出目标类重新审计得到相同结果；不声称用整理后的脚本重新运行了一轮专服。
