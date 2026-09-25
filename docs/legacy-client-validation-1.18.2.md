# 1.18.2 生产客户端验证

本记录针对未发布的 `0.2.0-dev` GPL 候选，独立于冻结的 0.1.1 与 1.19.4 验收。两个加载器均实际运行官方生产 Minecraft 1.18.2 客户端、对应专服和下表精确模组 JAR，没有以开发类路径或协议机器人代替客户端。

| 平台 | 加载器 / API | 报告通过后的在线观察 | 生存模式 / 设备关联 | 客户端 / 专服退出码 |
| --- | --- | --- | --- | --- |
| Fabric 1.18.2 | Loader 0.16.14 / 完整 Fabric API 0.77.0+1.18.2 | 65 秒 | 均通过 | 0 / 0 |
| Forge 1.18.2 | Forge 40.3.12 | 65 秒 | 均通过 | 0 / 0 |

计时从首次查询到服务端 `playerGameType=0` 开始。严格必需报告隔离解除说明报告最迟已在这次查询前通过；随后再保持在线至少 60 秒。客户端启动前后均逐键核对完整默认策略，`companion.required=true`、`device.required=true`、`vm.action=DENY`、黑名单拒绝和封禁策略未放宽，配置 SHA256 相同。两个通过轮次均无本模组的资源包元数据警告。

[验收摘要](../outputs/legacy-client-matrix/1.18.2-0.2.0-dev-gpl/acceptance.json)记录精确 JAR 哈希、官方原版客户端 SHA1、加载入口、QA 脚本哈希、配置哈希、模式/在线日志，以及原字节公开结果和控制台日志。设备关联仅检查存在性，不公开设备摘要、原始系统安装 ID、账户状态文件、完整启动计划或底层调试日志。

| 候选 JAR | SHA256 |
| --- | --- |
| `qizhangverdict-fabric-1.18.2-0.2.0-dev.jar` | `65ad6fafe4eee0f326d3eebe67465e30022972e800fd1d93ac7c068cf6d613c5` |
| `qizhangverdict-forge-1.18.2-0.2.0-dev.jar` | `c2823b070719ace443fca7ad48ae58a13f6b70d575dafbeaeb0f676aa682e4ff` |

Fabric 客户端与专服均锁定完整官方 API 发行包，SHA256 为 `6f822fb5aa481b4a6c1cfb8612bbfecc62a58e69d2c792f61a0eafa580e75999`，大小 1,472,259 字节，包含 45 个子模块。同版本 Maven 根 JAR 只有 4,877 字节，是聚合包，不能作为完整 API 直接部署。

[Fabric 游戏内截图](../outputs/legacy-client-matrix/1.18.2-0.2.0-dev-gpl/fabric-1.18.2.png)和[Forge 游戏内截图](../outputs/legacy-client-matrix/1.18.2-0.2.0-dev-gpl/forge-1.18.2.png)均已逐张目视确认，并校验 640×360 尺寸、PNG 块 CRC、图像数据解压及 SHA256。

## 保留的失败轮次

最终通过轮次均为 `candidate-0.2.0-dev-gpl-02`，没有覆盖首轮记录。

- Fabric 首轮专服停在资源重载，启动线程等待异步任务，尚未进入 Guard 生命周期，也未启动客户端。采集线程记录后结束该测试进程；测试夹具改为生成新世界，使用相同模组与完整 API 后通过。原因未确定，不能据此声称产品修复或旧存档兼容通过。
- Forge 首轮客户端在渲染、登录之前以 `0xC0000005` 退出；对应 Windows 应用错误记录指出 `lwjgl.dll`，专服正常退出。保持同一模组、启动参数和默认策略的新目录重试通过，未修改 JVM 参数或产品代码。原因未确定，原生崩溃的脱敏系统事件摘要一并公开。

失败结果和控制台日志均纳入验收摘要的 `retained_unsuccessful_attempts`；通过记录不代表上述偶发问题已被定位或消除。

## 复现与隔离

脚本为 `platforms/legacy-client-smoke.py`，本轮通过时 SHA256 为 `4c89e97421706f599ccdc3367f75c72cb4ac7e5eb7c35a5d00e3306294337134`。为 1.18.2 增加旧版本地库清单解析、完整 API 校验与新世界夹具；保留 1.19.4 的原平台路径和默认克隆语义。既有 1.19.4 结果仍保留当时测试脚本的哈希，没有改写历史验收。

```powershell
python platforms/legacy-client-smoke.py prepare-base fabric-1.18.2
python platforms/legacy-client-smoke.py install-client fabric-1.18.2 `
  --guard-jar <候选JAR绝对路径> --guard-sha256 <预期SHA256>
python platforms/legacy-client-smoke.py run fabric-1.18.2 `
  --run-name candidate-0.2.0-dev-gpl-03
```

Forge 将平台参数改为 `forge-1.18.2`。准备文件阶段不执行 Java，Forge 安装阶段使用官方客户端安装器。脚本依赖此机器的官方内容缓存、已停止的隔离专服夹具及 Java 17。运行数据位于 `E:\CodexTemp\QiZhangVerdict\legacy-client-matrix`，端口为 Fabric 25631、Forge 25632，仅监听回环地址；离线认证只用于合成测试账号。每次使用新运行目录，重建严格配置，不继承协议测试中的账号或设备封禁状态。

这组验证覆盖真实加载、配套报告、隔离解除和设备关联；不涵盖作弊检测准确率、对抗伪造报告、真实虚拟机型号矩阵、大型模组包、旧存档或性能验收。客户端报告仍可伪造。
