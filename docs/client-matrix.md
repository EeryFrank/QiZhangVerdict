# 真实客户端兼容验证

这组验证使用官方生产 Minecraft 客户端、正式 Fabric/Forge/NeoForge 加载器和指定 SHA256 的发布 JAR；没有使用开发环境类路径替代模组产物。客户端和同加载器专服均在 `E:\CodexTemp\QiZhangVerdict\client-matrix` 的隔离目录运行，服务器仅监听本机回环地址，离线认证仅用于这些测试。

测试保持默认严格策略：需要配套客户端、需要设备报告、VM 策略为 DENY。判定条件包括：实际进入服务器，在 20 秒报告期限之后仍在线，恢复为生存模式，持久化设备关联，客户端和专服均正常退出。设备标识只检查是否存在，不在汇总中公开摘要或原始系统安装 ID。

## 0.1.1 最终 GPL 成品验收

加入 `GPL-3.0-only` 许可及 `LICENSE`、`NOTICE` 后，四个最终 JAR 均重新运行了生产客户端与匹配专服。最终结果见 [GPL 精确产物与验收摘要](../outputs/client-matrix/0.1.1-gpl/acceptance.json)，与下方历史候选证据分开保存。

| 平台 | 加入后仍在线 | 生存模式 / 设备关联 | 客户端 / 专服退出码 |
| --- | --- | --- | --- |
| Forge 1.20.1 | 60 秒 | 均通过 | 0 / 0 |
| Fabric 1.20.1 | 61 秒 | 均通过 | 0 / 0 |
| Fabric 1.21.1 | 60 秒 | 均通过 | 0 / 0 |
| NeoForge 1.21.1 | 61 秒 | 均通过 | 0 / 0 |

每轮均核对完整严格默认配置，`companion.required=true`、`device.required=true`、`vm.action=DENY` 等设置未放宽，客户端启动前后配置哈希一致。四端都未出现本模组的资源包元数据警告。四张新截图逐张确认是游戏内画面，并验证 PNG 块 CRC、图像解压数据和 SHA256：[Forge 1.20.1](../outputs/client-matrix/0.1.1-gpl/forge-1.20.1.png)、[Fabric 1.20.1](../outputs/client-matrix/0.1.1-gpl/fabric-1.20.1.png)、[Fabric 1.21.1](../outputs/client-matrix/0.1.1-gpl/fabric-1.21.1.png)、[NeoForge 1.21.1](../outputs/client-matrix/0.1.1-gpl/neoforge-1.21.1.png)。

Forge 1.20.1、Fabric 1.20.1 的首轮各出现一次进入世界前的登录超时，尚未进入防作弊挑战/报告流程；相同 JAR、相同默认策略在新的隔离目录重试通过。超时原因未确定，这两次失败也保留在摘要和[公开证据索引](../outputs/client-evidence-index-0.1.1-gpl.json)中，没有以重试覆盖。索引中的 18 份结果及控制台日志为原字节副本；账号状态文件、设备摘要、原始系统安装 ID 和底层调试日志不公开。

## 0.1.1 历史候选验收（加入 GPL 文件前）

这组较早候选均已通过，原记录保留；其 JAR 哈希与上方最终 GPL 成品不同。每一轮精确检查完整默认配置，并记录客户端启动前和退出后的 `guard.properties` SHA256；两次哈希一致。`vm.action=DENY`、必需配套模组、必需设备报告、黑名单拒绝及封禁策略均未放宽，修复版本还要求没有本模组的资源包元数据警告。

| 平台 | 加入后仍在线 | 生存模式 / 设备关联 | 客户端 / 专服退出码 |
| --- | --- | --- | --- |
| Forge 1.20.1 | 61 秒 | 均通过 | 0 / 0 |
| Fabric 1.20.1 | 61 秒 | 均通过 | 0 / 0 |
| Fabric 1.21.1 | 60 秒 | 均通过 | 0 / 0 |
| NeoForge 1.21.1 | 60 秒 | 均通过 | 0 / 0 |

[0.1.1 精确产物与验收摘要](../outputs/client-matrix/0.1.1/acceptance.json)包含各 JAR 的 SHA256、加载器版本、官方原版客户端 SHA1、配置哈希、原始日志及结果文件的哈希。四张 F2 游戏内截图分别来自 [Forge 1.20.1](../outputs/client-matrix/0.1.1/forge-1.20.1.png)、[Fabric 1.20.1](../outputs/client-matrix/0.1.1/fabric-1.20.1.png)、[Fabric 1.21.1](../outputs/client-matrix/0.1.1/fabric-1.21.1.png)、[NeoForge 1.21.1](../outputs/client-matrix/0.1.1/neoforge-1.21.1.png)。截图均独立验证为 640×360 的有效 PNG，所有块 CRC、图像压缩数据和文件 SHA256 均经过检查，也已逐张目视确认处于游戏内。

Forge 0.1.1 会直接完成 QuickPlay 登录，无需手动越过旧版加载警告；方向修复后真实报告成功完成。该结果适用于摘要中的精确产物，不应移用于未重测的其他构建。

## 冻结的 0.1.0 成品

| 平台 | 结果 | 关键证据 |
| --- | --- | --- |
| Fabric 1.20.1 / Loader 0.16.14 / Fabric API 0.92.12 | 通过 | 加入后 61 秒仍在线，生存模式，设备关联，两端退出码 0 |
| Forge 1.20.1 / Forge 47.4.23 | **未通过** | 缺少资源包元数据导致加载警告；手动继续并进入服务器后，20 秒内没有完成报告而被踢出 |
| NeoForge 1.21.1 / NeoForge 21.1.244 | 通过 | 加入后 61 秒仍在线，生存模式，设备关联，两端退出码 0；未出现 Forge 的资源元数据警告界面 |

Forge 的功能性问题来自 `EventNetworkChannel` 的事件命名：`PLAY_TO_SERVER` 创建的是 `ClientCustomPayloadEvent`，`PLAY_TO_CLIENT` 创建的是 `ServerCustomPayloadEvent`。旧适配器把两者按接收端理解，导致服务器挑战没有到达客户端报告处理器。后续源码已改为正确的事件类型，并明确只接收对应的 PLAY 方向。这个错误由实际客户端联机发现，早先的专服启动检查不能证明客户端握手可用。

[冻结 Forge 成品的真实加载警告截图](../outputs/client-matrix/forge-0.1.0-loading-warning.png)和[三端补测摘要](../outputs/client-matrix/baseline-0.1.0.json)单独保留。

冻结的 0.1.0 发布产物及其旧证据没有被覆盖。第一次 Forge 测试还暴露了新测试启动器自身的继承版本 JAR 文件名问题：现已使官方原版 JAR 的别名与加载器 `${version_name}.jar` 规则一致；原始 Mojang 文件字节和 SHA1 不变。该启动器失败日志也保留，和产品握手故障分开记录。

## 复现

脚本为 `platforms/client-matrix-smoke.py`，依赖此机器已经安装的官方加载器和内容地址资源缓存。默认 `prepare` 使用冻结的 0.1.0 成品；自定义候选必须同时提供文件路径与预期 SHA256。每次 `run` 使用新的运行目录，拒绝复用既有运行证据。

```powershell
python platforms/client-matrix-smoke.py prepare forge-1.20.1 `
  --guard-jar <候选JAR绝对路径> --guard-sha256 <预期SHA256>
python platforms/client-matrix-smoke.py run forge-1.20.1 --run-name candidate-01
```

可选平台为 `fabric-1.20.1`、`fabric-1.21.1`、`forge-1.20.1`、`neoforge-1.21.1`。测试端口依次为 25594、25597、25595、25596；运行前检查端口空闲。真实渲染窗口在后台隐藏，通过正常窗口关闭事件退出。超过等待上限或发生错误时也会关闭本次客户端和服务器。

该验证覆盖加载、配套报告和隔离解除，不代表作弊客户端攻防测试、虚拟机型号矩阵、旧存档兼容性或性能验收。客户端上报的模组列表、VM 信号和设备摘要仍然可以伪造，不是可信硬件证明。
