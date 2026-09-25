# 0.2.0-test.1 测试版

本轮统一插件与模组版本号，包含 13 个独立安装包。项目原创实现使用 **GPL-3.0-only**；第三方 Grim、AntiXray 不包含在这些 JAR 内，分别安装并保留其原许可证。

## 本轮变化

- 首次生成的 `blacklist.tsv` 从 11 条扩展为 37 条精确 ID：33 条 DENY、4 条 ALERT，每条附固定提交的来源。完整目录见[标识目录](catalog.md)。
- 已有名单文件保留原字节，包括管理员的 OFF 设置和删除记录。升级不会自动填回默认规则；按需使用目录合并工具。
- 修复 `blacklist.tsv` 中 `automation` 规则设为 DENY 时，`sanctions.on-deny=BAN` 只拒绝会话却未登记关联封禁的问题。现在会记录该账号、已关联设备和关联账号；KICK 模式仍只断开会话。
- IP/设备并发限制、黑白名单增删、GLOB 模糊规则、虚拟机信号策略和管理员命令继续使用原配置格式。

## 选择安装包

每台服务器安装表中一个服务端实现；玩家安装与其游戏版本及加载器相符的同版本客户端模组。插件服玩家也需要客户端模组完成设备与规则报告。

| 游戏版本 / 平台 | 安装包 | Java |
| --- | --- | --- |
| Paper / Spigot 系插件服 | `qizhangverdict-bukkit-0.2.0-test.1.jar`，放入 `plugins/` | 依服务器版本选择 |
| 1.8.9 Forge | `qizhangverdict-forge-1.8.9-0.2.0-test.1.jar` | 8 |
| 1.12.2 Forge | `qizhangverdict-forge-1.12.2-0.2.0-test.1.jar` | 8 |
| 1.16.5 Fabric / Forge | `qizhangverdict-fabric-1.16.5-0.2.0-test.1.jar` / `qizhangverdict-forge-1.16.5-0.2.0-test.1.jar` | 8 |
| 1.18.2 Fabric / Forge | `qizhangverdict-fabric-1.18.2-0.2.0-test.1.jar` / `qizhangverdict-forge-1.18.2-0.2.0-test.1.jar` | 17 |
| 1.19.4 Fabric / Forge | `qizhangverdict-fabric-1.19.4-0.2.0-test.1.jar` / `qizhangverdict-forge-1.19.4-0.2.0-test.1.jar` | 17 |
| 1.20.1 Fabric / Forge | `qizhangverdict-fabric-1.20.1-0.2.0-test.1.jar` / `qizhangverdict-forge-1.20.1-0.2.0-test.1.jar` | 17 |
| 1.21.1 Fabric / NeoForge | `qizhangverdict-fabric-1.21.1-0.2.0-test.1.jar` / `qizhangverdict-neoforge-1.21.1-0.2.0-test.1.jar` | 21 |

Fabric 另需匹配游戏版本的 Fabric API。没有原生 Forge 1.8.8 产物，Paper 1.8.8 的配套客户端组合使用 Forge 1.8.9。1.8.9 在本机的图形验收使用 `config/splash.properties` 中 `enabled=false` 关闭 Forge 启动画面；不能将这一条件省略为所有硬件默认配置均通过。

## 升级

正常停服后备份配置目录、`accounts.state` 和 `server-id.txt`；插件目录为 `plugins/QiZhangVerdict/`，模组目录为 `config/qizhangverdict/`。替换相应旧 JAR，同一目录只保留该平台的一个 Verdict 版本，再更新玩家端的匹配模组。不要删除设备范围标识或已有账号状态来完成升级。

已有名单不会自动扩充。先审阅[目录合并说明](catalog.md)，再选择需要的条目；保留服务器自己的白名单与 OFF 规则。默认在线配额仍为同 IP 最多 3 人、同 IP 同设备最多 1 人；`limits.max-online-per-ip=2` 可改为最多两台不同设备同时在线。

## 验证范围

13 个指定散列的成品均已构建，并分别运行同一套 57 项核心安全回归、37 条目录检查和 3 项控制检查。14 组真实图形客户端/专服检查通过，覆盖 12 个模组连接对应专服及两个旧 Forge 客户端连接插件服；每组保持完整默认策略并在报告获准后继续在线。插件端另有 75 组真实 TCP 检查，含自动化关联封禁、重启持久化、默认目录与已有管理规则保留。

证据：[构建与静态检查](../outputs/build-validation-0.2.0-test.1.json)、[逐 JAR 核心回归](../outputs/artifact-core-validation-0.2.0-test.1.json)、[真实客户端](client-0.2.0-test.1.md)、[插件协议检查](validation-0.2.0-test.1-bukkit.md)、[汇总与散列](../outputs/validation-0.2.0-test.1.json)。客户端使用本机离线认证夹具；协议测试使用合成账号/设备并明确列出临时测试配置。这些不是正版认证、真实虚拟机样本、多人实战或检测准确率测试。

1.12.2 最初构建遇到 Gradle 下载证书错误；后续复用已核验官方 ZIP 的缓存。中间候选另发现旧 Forge 注解版本号未更新，已修正并重新构建后才运行客户端。失败记录与未分发候选保留在构建报告，历史发布 JAR 未改变。旧版 0.1.1 / 0.2.0-dev 的运行记录不能替代本轮验收。

## 第三方组件与限制

Grim 负责已集成平台的行为检查，矿石混淆通过 Paper 或独立 AntiXray 实现。安装说明见[集成指南](../integrations/README.md)。旧 Paper 三版的历史联动证据见[42 组检查](legacy-paper-integration-validation.md)。Fabric 1.16.5 官方 AntiXray 1.1.0 有 refmap 启动故障，独立兼容补丁及 Java 17 条件见[专门说明](legacy-fabric116-antixray-qzcompat1-java17.md)；该报告使用明确列出的旧 Verdict JAR，不证明所有新组合均通过。

37 条目录不是全市场清单。改名、隐藏模组、注入器或伪造客户端报告可能绕过标识检查；设备哈希与虚拟机信号也不是不可伪造的硬件认证。测试包不代表所有 Minecraft 小版本、混合核心、代理网络或大型整合包已兼容。详细边界见[隐私与限制](privacy-and-limits.md)。
