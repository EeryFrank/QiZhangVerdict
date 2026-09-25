# 旧版防作弊组件候选与输入验证

截至 2026-09-25，已校验 **7 个官方 JAR 输入、8 个离线暂存组合**。本轮没有启动 Java、服务器或客户端，不能据此宣称这些组合已经兼容、行为检查有效或防透视已启用。第三方二进制没有加入源码仓库或 Verdict JAR。

[公开输入报告](../outputs/legacy-integration-input-validation.json) 包含官方版本 API、下载 URL、完整 SHA256/SHA512/SHA1、实际描述符、源码提交与许可哈希，以及八次暂存的文件哈希和 receipt。临时目录只是附加历史位置，不是唯一证据。[旧版 pins](../integrations/legacy-pins.json) 与[独立旧版锁](../integrations/legacy-dependencies.lock.json) 已逐字段核对；现代 pins、锁、管理脚本及配置未改动。

| 候选 profile | 已固定的第三方输入 | 后续运行条件与边界 |
|---|---|---|
| `paper-1.8.8-candidate` | Grim Bukkit 2.3.67 | Java8 候选；另配置、验证 Paper 内置 Anti-Xray |
| `paper-1.12.2-candidate` | Grim Bukkit 2.3.67 | Java8 候选；另配置、验证 Paper 内置 Anti-Xray |
| `paper-1.16.5-candidate` | Grim Bukkit 2.3.67 | Java8 候选；另配置、验证 Paper 内置 Anti-Xray |
| `fabric-1.16.5-candidate` | Drex AntiXray 1.1.0 | **独立 Java17 实验待测**；不能沿用 Java8 基线结论 |
| `fabric-1.18.2-candidate` | Drex AntiXray 1.2.1 | Java17；只选了矿物混淆组件 |
| `forge-1.18.2-candidate` | Drex AntiXray 1.2.1、Architectury 4.12.94 | Java17、Forge ≥40.1.14；只选了矿物混淆组件 |
| `fabric-1.19.4-candidate` | Drex AntiXray 1.3.0 | Java17；只选了矿物混淆组件 |
| `forge-1.19.4-candidate` | Drex AntiXray 1.3.0 | Java17、精确 Minecraft 1.19.4 Forge；只选了矿物混淆组件 |

Grim 2.3.67 的 3159 个基础类最高 major52（Java8）；仅 `META-INF/versions/9/module-info.class` 为 major53。它是历史版本，字节码要求满足不等于当前作弊覆盖完整。其 [Modrinth 发布输入](https://api.modrinth.com/v2/version/4lbMNftz)还与 Hangar 官方 SHA256 相符。

Fabric 1.16.5 的 AntiXray 实际 32 个模组类均为 major60（Java16），JAR 描述符要求 Java ≥16，Mixin 配置为 `JAVA_16`；选择 Java17 是下一轮实验方案，尚未启动验证。1.18.2/1.19.4 的 AntiXray 模组类为 major61（Java17）。

Forge 1.18.2 的 AntiXray 发布 API 漏列依赖，但[官方固定源码](https://github.com/DrexHD/AntiXray/blob/5ca6fa96fa21e6e4afac27dad956b437e9ccdd6c/forge/src/main/resources/META-INF/mods.toml)及实际 JAR 都强制要求 `architectury >=3.2.57`。本清单补入[官方 Forge 1.18.2 的 Architectury 4.12.94](https://api.modrinth.com/v2/version/3ChyUkZQ)，其实际描述符要求 Forge ≥40.1.14。

**Forge 1.16.5 仍有集成缺口**：此次核对的 Drex 官方发布目录没有该版本的 Forge 构建，不能把 Fabric JAR 当作 Forge JAR。旧版 Fabric 的 Grim 依赖也尚未完成验证，因此没有加入这些 profile；Fabric/Forge 表中不承诺额外行为检测。Minecraft 服务端、对应 loader、Verdict 和原有依赖均须单独准备。

八次 `stage` 只证明：官方 JAR 能按锁下载或读取缓存，复制后哈希一致，必需依赖已纳入目标组合。另确认非空输出目录及改单字节文件被拒绝。**没有复制配置片段、没有应用配置，更没有验证 Anti-Xray 已启用。**

`legacy-grim-*` 键名是有意选择的：管理器只对 `startswith("grim-")` 的键复制现代处罚模板，因此本次不会套用 2.3.71/2.3.73 模板。2.3.67 的默认处罚是告警等通知；仅安装 Grim 不会自动执行 Verdict 封禁。若要联动，须单独验证旧版命令格式、检查名称及实际封禁行为。

Paper 1.8.8 使用 `spigot.yml` 的数字 `hide-blocks` / `replace-blocks`；1.12.2 与 1.16.5 使用 `paper.yml`、命名方块列表及 `max-chunk-section-index`。不要复用现代 `paper-world-defaults.yml` 片段。依据分别为官方历史源码 [1.8.8](https://github.com/PaperMC/Paper-archive/blob/2894af04dc378d6a61e55e37a8c0b1a478c09c3d/Spigot-Server-Patches/0063-Optimize-Spigot-s-Anti-X-Ray.patch)、[1.12.2](https://github.com/PaperMC/Paper-archive/blob/e39995d213616cc7d60c38e6e86e562f30637ef7/Spigot-Server-Patches/0235-Anti-Xray.patch)、[1.16.5](https://github.com/PaperMC/Paper-archive/blob/fa1a7c180c6fcba779e583fc4ed550b48954bcc4/Spigot-Server-Patches/0362-Anti-Xray.patch)。Drex 则应让精确版本生成自身配置后审查。

许可记录保持上游原貌：Grim 官方项目声明 GPL-3.0-or-later，Drex 为 MIT，Architectury 为 LGPL-3.0-only，toml4j 0.7.2 为 MIT。Drex 1.16.5 的描述符仍写 CC0-1.0，但内嵌 LICENSE 与固定源码均为 MIT，此矛盾已保留。其余四个 Drex JAR、Grim 和 Architectury 没有内嵌完整许可正文；锁文件保留固定源码许可 URL。以后若重新分发这些二进制，需另满足各自许可与对应源码要求。描述符与固定源码字段相符不等于可重复构建；Architectury 仅核对了 4.12 系列源码，未证明构建号 94 精确对应所记录提交。

从仓库根目录可在一个新的空目录暂存候选（不会修改现有服）：

```powershell
python -B integrations/manage_integrations.py stage --lock integrations/legacy-dependencies.lock.json --profile forge-1.18.2-candidate --cache E:\CodexTemp\QiZhangVerdict\legacy-integration-downloads --output E:\CodexTemp\QiZhangVerdict\legacy-integration-stage-new
```

下一轮优先在独立 Paper 1.12.2/1.16.5 夹具验证 Grim 2.3.67 与内置 Anti-Xray，再测试 Java17 的模组组合。每轮保留 Verdict 默认严格策略，检查实际组件加载、准入报告与 OP 命令门禁、正常停服，并用可控矿石场景的网络区块数据证明混淆。启动成功或玩家登录成功都不能代替防透视功能验证。
