# 0.3.0-dev-preview.1 预览合集

本预览按平台分别提供安装包：[GitHub](https://github.com/EeryFrank/QiZhangVerdict/releases/tag/v0.3.0-dev-preview.1) · [GitLab](https://gitlab.com/EeryFrank/QiZhangVerdict/-/releases/v0.3.0-dev-preview.1)。它保留已验证旧模组的原始字节，新增适配和修复使用各自的成品散列。

这次合集增加 Minecraft 1.19.2、1.20.4 适配，并修复 Bukkit 登录期间重载配置时，旧延迟任务再次发送过期挑战的问题。共 18 个独立 JAR，内部组件版本分别保留。原创实现采用 **GPL-3.0-only**；安装 ZIP、对应源码 ZIP、LICENSE、NOTICE 和 SHA256 校验文件随正式预览发布。

发布后核验：两站各 26 个附件已匿名下载并核对 SHA256，见[发布回执](../outputs/publish-receipt-0.3.0-dev-preview.1.json)。安装 ZIP 和对应源码 ZIP 通过[独立审查](../outputs/packaging-validation-0.3.0-dev-preview.1.json)。标签固定源码为 `f633a30badb882cfdb8606a7fefd88e5ce28bb2b`；GitHub 同标签 11 项构建成功，GitLab 11 项因额度不足未启动，准确状态见 [CI 记录](ci.md)。后续文档补录不会改动已发布附件。

## 选择安装包

每台服务器只选一个适合其平台的 Verdict 实现；每位玩家只装一个适合其游戏版本和加载器的配套模组。插件服玩家也需要配套模组完成设备与规则报告。不能把合集中的所有 JAR 一起放入服务器或客户端。

| 游戏 / 平台 | 文件名 | Java |
| --- | --- | --- |
| Paper / Spigot 系插件服 | `qizhangverdict-bukkit-0.2.1-dev.jar` | 依服务器版本选择 |
| 1.8.9 Forge | `qizhangverdict-forge-1.8.9-0.2.0-test.1.jar` | 8 |
| 1.12.2 Forge | `qizhangverdict-forge-1.12.2-0.2.0-test.1.jar` | 8 |
| 1.16.5 Fabric / Forge | `qizhangverdict-fabric-1.16.5-0.2.0-test.1.jar` / `qizhangverdict-forge-1.16.5-0.2.0-test.1.jar` | 8 |
| 1.18.2 Fabric / Forge | `qizhangverdict-fabric-1.18.2-0.2.0-test.1.jar` / `qizhangverdict-forge-1.18.2-0.2.0-test.1.jar` | 17 |
| 1.19.2 Fabric / Forge | `qizhangverdict-fabric-1.19.2-0.3.0-dev.jar` / `qizhangverdict-forge-1.19.2-0.3.0-dev.jar` | 17 |
| 1.19.4 Fabric / Forge | `qizhangverdict-fabric-1.19.4-0.2.0-test.1.jar` / `qizhangverdict-forge-1.19.4-0.2.0-test.1.jar` | 17 |
| 1.20.1 Fabric / Forge | `qizhangverdict-fabric-1.20.1-0.2.0-test.1.jar` / `qizhangverdict-forge-1.20.1-0.2.0-test.1.jar` | 17 |
| 1.20.4 Fabric / Forge / NeoForge | `qizhangverdict-fabric-1.20.4-0.3.0-dev.jar` / `qizhangverdict-forge-1.20.4-0.3.0-dev.jar` / `qizhangverdict-neoforge-1.20.4-0.3.0-dev.jar` | 17 |
| 1.21.1 Fabric / NeoForge | `qizhangverdict-fabric-1.21.1-0.2.0-test.1.jar` / `qizhangverdict-neoforge-1.21.1-0.2.0-test.1.jar` | 21 |

新增适配固定使用 Fabric Loader `0.16.14`，1.19.2 Fabric API `0.77.0+1.19.2`、Forge `43.5.2`；1.20.4 Fabric API `0.97.3+1.20.4`、Forge `49.2.9`、NeoForge `20.4.251`。Fabric API 和加载器均单独安装。构建说明见 [1.19.2](adapter-1.19.2.md) 与 [1.20.4](adapter-1.20.4.md)。

旧 12 个模组与 [0.2.0-test.1](release-0.2.0-test.1.md) 的原件散列相同，无需重复升级。1.8.9 本机图形验证需要关闭 Forge 启动画面；Paper 1.8.8 的配套客户端使用 Forge 1.8.9，没有原生 Forge 1.8.8 JAR。

## 安装和升级

1. 正常停服，备份配置目录：插件为 `plugins/QiZhangVerdict/`，模组为 `config/qizhangverdict/`。
2. 连同管理员规则一起保留 `accounts.state` 和 `server-id.txt`，不要通过删除设备范围标识来升级。
3. 替换适用平台的 JAR，目录中只保留一个 Verdict 版本。插件放 `plugins/`；服务端和玩家端模组放各自的 `mods/`。
4. 启服后检查 `/qzverdict status`，再用匹配客户端登录。集成 Grim 或矿物混淆时另按[集成指南](../integrations/README.md)安装相应组件。

首次配置仍为同 IP 最多 3 个同时在线账号，同 IP 同设备最多 1 个；`limits.max-online-per-ip=2` 可改为最多两台不同设备。已确认黑名单命中可关联封禁账号、设备与已关联账号。黑白名单支持增删与 GLOB 模糊规则；现有 OFF 设置、管理员白名单和删除记录不会在升级时重置。管理命令见 [README](../README.md)。

## 证据与适用范围

新 Bukkit 修复已完成[真实服务器新旧对照](bukkit-challenge-race.md)。旧成品确实复现超时，新成品在相同受控调度下正常验证。新安装包另通过 97 项成品内核心检查，以及 1.20.1、1.21.1 各 26 项连接检查，见[新版插件验收](validation-0.2.1-dev-bukkit.md)。1.21.1 的协议测试日志保留了 22 次物品数据解码告警；通过的是报告列出的准入断言，不是完整游戏数据解码验收。

新增五个模组均通过成品内核心检查、匹配专服的各 26 项连接检查和真实图形客户端验证。客户端保持全部 13 项默认政策和 37 条目录，在独立设备摘要比对通过后继续在线至少 60 秒，确认生存模式、正常画面和客户端/服务端退出 0。具体见[专服报告](next-platform-server-validation.md)、[真实客户端报告](next-platform-client-validation.md)及[发行汇总](../outputs/validation-0.3.0-dev-preview.1.json)。它们使用本机离线认证夹具，不证明正版账户认证、真实虚拟机样本或多人实战。

NeoForge 1.20.4 的首个候选在真实客户端检查中报告超时。最终成品将挑战绑定到原连接，在客户端主线程处理，避免依赖网络线程提前捕获的玩家对象，并拒绝换连接或断线后的处理。修复后的成品重新完成核心、专服和客户端检查，旧失败记录保留，见[定向修复报告](neoforge-1.20.4-client-fix.md)。

其他历史尝试也单独保留：Forge 1.19.2 的合成客户端注册报文最初缺少 NUL；Fabric 1.19.2 的首个测试用户名过长；Fabric 1.20.4 前两次协议尝试未观察到部分拒绝原因，后续完整一轮实际收到原因并通过，但前两次原因缺失的根因尚未确认。诊断脚本增加观察记录不等于修复了产品。

旧 12 个原始模组沿用其 [0.2.0-test.1 验证汇总](../outputs/validation-0.2.0-test.1.json)中的对应证据。该历史版本的另外两组插件服客户端、75 组插件协议检查使用旧 Bukkit，不属于本次替换插件的重新验收。CI 重新构建的 Linux JAR 与本机实测成品分别记录，不相互替换。GitLab 因额度不足未执行的流水线也不计为通过。

默认名单仍为 37 条，目录来源见[黑名单目录](catalog.md)。它不包含全市场作弊，也不能可靠发现隐藏、改名或伪造报告的客户端。设备与虚拟机信号由客户端报告，不能当作不可伪造的硬件认证；未知虚拟机信号或单独 VBS 信号不会默认永久封禁。

Grim、AntiXray 独立安装，不包含在这 18 个 JAR 中。旧版集成结果不自动证明新增版本的第三方组合。原版资源包透视需要服务端矿物混淆；本预览不代表全部 Minecraft 小版本、混合核心、代理网络或大型整合包已兼容。具体边界见[隐私与限制](privacy-and-limits.md)。
