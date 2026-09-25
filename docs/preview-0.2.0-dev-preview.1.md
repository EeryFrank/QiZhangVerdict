# 旧版适配测试包 0.2.0-dev-preview.1

本包提供 1.12.2、1.16.5、1.18.2、1.19.4 的七个配套模组，以及已发布的 Bukkit 0.1.1 插件。模组内部版本仍为 `0.2.0-dev`，所有 JAR 保留实际验收的原字节，采用 GPL-3.0-only。1.20.1 / 1.21.1 请使用 [GitHub 0.1.1](https://github.com/EeryFrank/QiZhangVerdict/releases/tag/v0.1.1-test.1) 或 [GitLab 0.1.1](https://gitlab.com/EeryFrank/QiZhangVerdict/-/releases/v0.1.1-test.1) 的对应模组。

## 安装组合

| 游戏版本 | 已验证加载器与依赖 | Java | 本包模组文件 |
|---|---|---|---|
| 1.12.2 | Forge 14.23.5.2864 | 8 | `qizhangverdict-forge-1.12.2-0.2.0-dev.jar` |
| 1.16.5 | Fabric Loader 0.16.14 + 完整 Fabric API 0.42.0+1.16 | 8 | `qizhangverdict-fabric-1.16.5-0.2.0-dev.jar` |
| 1.16.5 | Forge 36.2.42 | 8 | `qizhangverdict-forge-1.16.5-0.2.0-dev.jar` |
| 1.18.2 | Fabric Loader 0.16.14 + 完整 Fabric API 0.77.0+1.18.2 | 17 | `qizhangverdict-fabric-1.18.2-0.2.0-dev.jar` |
| 1.18.2 | Forge 40.3.12 | 17 | `qizhangverdict-forge-1.18.2-0.2.0-dev.jar` |
| 1.19.4 | Fabric Loader 0.16.14 + 完整 Fabric API 0.87.2+1.19.4 | 17 | `qizhangverdict-fabric-1.19.4-0.2.0-dev.jar` |
| 1.19.4 | Forge 45.4.5 | 17 | `qizhangverdict-forge-1.19.4-0.2.0-dev.jar` |

模组服：服务器和玩家客户端均安装同版本、同加载器的一份 JAR 到 `mods/`。Fabric 两端另装完整 Fabric API 发行文件；只有空聚合描述符的 Maven JAR 不能代替它。Minecraft、Forge、Fabric 和 Fabric API 不随本包分发，请从各自官方渠道安装。

插件服：服务器安装 `qizhangverdict-bukkit-0.1.1.jar` 到 `plugins/`；玩家仍需上表匹配游戏版本和加载器的客户端模组。1.12.2 Forge 客户端连接 Paper 1620 已实际验证。1.16.5 / 1.18.2 / 1.19.4 的本轮图形客户端连接的是对应模组专服，旧 Paper 的 TCP 回归不能替代这些客户端与插件服组合的完整验收。同一服务器只安装 QiZhangVerdict 插件或服务器模组中的一种。

## 配置与升级

先在独立测试实例安装，备份世界及 `plugins/QiZhangVerdict/` 或 `config/qizhangverdict/`。迁移时同时保留 `accounts.state` 与 `server-id.txt`；后者决定设备标识的服务器范围。不要把玩家数据或设备摘要上传到公开问题中。

默认要求配套报告和设备标识，报告期限 20 秒；同 IP、同设备最多 1 个在线账号，同 IP 总计最多 3 个，可把 `limits.max-online-per-ip` 改为 2。保留黑白名单增删、EXACT/GLOB、IP/CIDR、账号和设备关联封禁；详细配置与命令见 [项目说明](../README.md)。本预览没有新增可绕过封禁的白名单优先级。

本包提供准入和自报规则检查；没有新增旧版行为预测或矿物混淆引擎。现有 [外部组件安装表](../integrations/README.md) 的版本范围不可直接套用于旧版。设备标识和 VM 信息可以被修改的客户端伪造，黑名单不可能穷尽市面外挂，边界见 [数据与信任](privacy-and-limits.md)。

## 实测范围

七种模组客户端均以正式 JAR 进入匹配专服并完成渲染、设备关联和严格默认报告策略；另有 1.12.2 Forge → Paper 实测，共八个最终通过组合。每组报告获准后继续在线至少 65 秒，客户端和服务器退出码均为 0。依据与原始失败记录见 [聚合验收](../outputs/validation-0.2.0-dev-preview.1.json) 和 [兼容矩阵](compatibility-matrix.md)。

- 1.12.2 两次早期失败源于 QA 关闭窗口、识别旧 Paper 日志的逻辑，修正 QA 后通过，产品字节没有改变。
- 1.16.5 首次 Fabric 未连接；最终本机合成账号夹具使用官方 authlib 的离线回退，不构成在线认证验收。
- 1.18.2 首次 Fabric 资源重载等待、首次 Forge 原生 LWJGL 崩溃均保留；重试通过，原因未确定。
- 1.19.4 的早期专服记录使用许可调整前的 JAR；许可迁移类文件一致性与最终 GPL 客户端/专服记录分别保留，不改写历史散列。

GitHub 对提交 `34e323b656af4f7a49edcf646e0d5b8d62ebb919` 的四项旧版及四项现代构建均通过；对应 GitLab 因共享额度不足未执行。CI 重编字节与本机运行成品不同，不使用 CI 下载物替换本包已实测 JAR。记录见 [CI 证据](../outputs/legacy-ci-validation-0.2.0-dev.json)。

1.8.x 尚未通过模组构建验收，不在本包中。生产认证、混合端、代理转发、跨服共享状态、大型整合包、旧存档、性能压力、真实 VM 矩阵和作弊误报率均未验收。

## 源码与校验

安装 ZIP 中的 `preview-manifest.json` 指定全部安装文件和证据散列，`packaging-summary.json` 指定完整源码提交；`SHA256SUMS.txt` 用于校验解压后的文件。独立源码 ZIP 由该提交的 Git 文件生成，构建说明见 [1.12.2](legacy-1.12.2-adapter.md)、[1.16.5](legacy-1.16.5-adapter.md)、[旧版适配](legacy-mod-adapters.md) 和 [打包流程](packaging-preview.md)。附件外层 `SHA256SUMS.txt` 校验公开的 ZIP、JAR 和验收文件。
