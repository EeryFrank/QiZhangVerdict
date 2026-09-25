# 1.19.4 生产客户端验证

本记录针对未发布的 `0.2.0-dev` GPL 候选，独立于已经冻结的 `0.1.1-test.1` 发布验收。Fabric 和 Forge 均使用官方生产 Minecraft 1.19.4 客户端与匹配专服，实际加载指定 SHA256 的模组 JAR；没有使用开发类路径，也没有用协议机器人代替客户端。

| 平台 | 加载器 / API | 报告通过后的在线观察 | 生存模式 / 设备关联 | 客户端 / 专服退出码 |
| --- | --- | --- | --- | --- |
| Fabric 1.19.4 | Loader 0.16.14 / Fabric API 0.87.2+1.19.4 | 65 秒 | 均通过 | 0 / 0 |
| Forge 1.19.4 | Forge 45.4.5 | 66 秒 | 均通过 | 0 / 0 |

计时从服务端首次查询到 `playerGameType=0` 开始。在必需报告隔离开启的情况下，恢复生存模式说明报告最迟已在这次查询前被接受；随后持续查询在线状态至少 60 秒，因此没有把加载或等待报告的时间算入这一窗口。

两端的完整默认配置均在客户端启动前及退出后核对，配置 SHA256 相同。`companion.required=true`、`device.required=true`、`vm.action=DENY`、黑名单拒绝和封禁策略没有放宽。设备关联只记录存在性，不导出账户状态或设备摘要。两端均无本模组的资源包元数据警告。

[验收摘要](../outputs/legacy-client-matrix/0.2.0-dev-gpl/acceptance.json)包含精确产物哈希、官方原版客户端 SHA1、加载入口、测试脚本哈希、配置哈希、模式恢复与最后在线日志，以及公开原始结果和控制台日志索引。公开文件均为原字节副本，排除系统安装 ID、设备状态文件、完整启动计划和底层调试日志。

| 候选 JAR | SHA256 |
| --- | --- |
| `qizhangverdict-fabric-1.19.4-0.2.0-dev.jar` | `c626ba359aa3a79c3e5215b590f990a6134b0de2060251701bec3eeae999a21f` |
| `qizhangverdict-forge-1.19.4-0.2.0-dev.jar` | `b4e724bb64514ce75263e9c92f2ebbb9a2b95a90c11855708e76d64cc234d154` |

[Fabric 游戏内截图](../outputs/legacy-client-matrix/0.2.0-dev-gpl/fabric-1.19.4.png)和[Forge 游戏内截图](../outputs/legacy-client-matrix/0.2.0-dev-gpl/forge-1.19.4.png)均为客户端 F2 捕获，已逐张目视确认，并验证 640×360 尺寸、PNG 块 CRC、图像数据解压及 SHA256。

## 复现与运行隔离

脚本为 `platforms/legacy-client-smoke.py`，复用冻结主测试脚本的下载和窗口操作辅助函数，不修改该主脚本。运行数据位于 `E:\CodexTemp\QiZhangVerdict\legacy-client-matrix`；Fabric 使用 25611，Forge 使用 25612，仅监听回环地址。离线认证仅用于合成账号测试实例。

```powershell
python platforms/legacy-client-smoke.py prepare-base fabric-1.19.4
python platforms/legacy-client-smoke.py install-client fabric-1.19.4 `
  --guard-jar <候选JAR绝对路径> --guard-sha256 <预期SHA256>
python platforms/legacy-client-smoke.py run fabric-1.19.4 `
  --run-name candidate-0.2.0-dev-gpl-02
```

Forge 将平台参数改为 `forge-1.19.4`。`prepare-base` 只准备官方文件；`install-client` 为 Forge 执行官方安装器。脚本依赖此机器已有的隔离专服夹具、官方内容缓存及 Java 17，每次运行拒绝复用已有证据目录。实际验收轮次均为 `candidate-0.2.0-dev-gpl-01`，本次两个平台均首轮通过，结束后客户端和专服已全部退出。

本验证覆盖真实加载、配套报告、隔离解除和设备关联，不代表作弊检测准确率、对抗伪造报告、真实虚拟机型号矩阵、大型模组包、旧存档或性能验收。客户端报告仍可被修改或伪造。
