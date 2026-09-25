# 可核验标识扩展目录

本目录供七章的裁决管理员审阅、按服规选用。2026-09-25 更新包含 **39 个公开源码仓库、36 个归并条目、37 个精确 ID（33 DENY / 4 ALERT）**，另有 **8 个待验证品牌或资源包**。本次更新属于下一版本源码，不能据此认定新 JAR 已构建、测试或交付。目录工具不会连接服务器、修改服务器配置或自动恢复管理员删除的规则；已发布版本的目录和默认规则以各自 tag 与发布包为准。

这里的 HIGH 表示“固定官方源码能证明这个标识和相应功能”，不表示服务端能可靠证明玩家运行了未经修改的原版客户端。目录覆盖本次有一手证据的已知项目，不声称囊括全部商业客户端、私有分支、注入器或未来版本。

## 文件与证据

| 文件 | 内容 |
| --- | --- |
| `catalog/identifiers.json` | 主目录；完整提交 SHA、源文件 URL、获取日期、文本 SHA256、真实 ID 的解析路径、模板绑定、用途与版本证据 |
| `catalog/identifiers.tsv` | 便于人工审阅的展开表 |
| `catalog/blacklist-extension.tsv` | 与 `blacklist.tsv` 四列格式兼容的候选规则；不能未经审阅直接覆盖服务器文件 |
| `catalog/catalog_tool.py` | Python 3.11+ 标准库校验、只读来源核验、导出、显式选择合并 |
| `catalog/test_catalog.py` | 离线负向和管理员规则保留测试 |
| `catalog/minecraft-versions.json` | Mojang 官方版本元数据快照和候选测试矩阵，不代表本项目已支持这些版本 |
| `catalog/verification.json` | 本次来源核验和工具测试的摘要与文件哈希 |

`identifierProofs` 仅提取 loader 描述符中的主体字段：Fabric `/id`，旧 Forge `/0/modid`，Forge/NeoForge `/mods/0/modId`。Lambda/TrollHack/CheatUtils 的模板 ID 从**同仓库同提交**的 `gradle.properties` 读取，不执行 Gradle 或源码。LiquidBounce 描述符中的裸 JSON 模板值只替换为 `null` 后读取 ID，不执行模板表达式。版本项分别保留 `sourceBuildTarget` 和原样的 `descriptorRange`；模板范围、宽泛下限和遗留描述符均不等于实际运行兼容性。本次没有下载、构建或运行作弊二进制。

源文件只存在校验者指定的缓存目录。本仓库记录事实、哈希、链接和自行撰写的说明，没有移植 GPL/AGPL/LGPL 客户端实现，也不分发作弊 JAR。`githubLicenseMetadata` 是抓取时 GitHub 仓库级许可证分类，不能替代逐文件授权；若描述符与仓库声明不一致，不据此推断可重新分发源码。

## 标识与建议

精确 ID 列只按整个标识匹配，不按产品名称、JAR 文件名或子串匹配。每个 ID 的固定源码链接见上述 JSON/TSV。

| 项目或归并身份 | 精确 ID | 建议 |
| --- | --- | --- |
| Meteor Client / Wurst 7 / LiquidBounce | `meteor-client`, `wurst`, `liquidbounce` | DENY |
| BleachHack / ThunderHack Recode / 3arthh4ck | `bleachhack`, `thunderhack`, `earthhack` | DENY |
| KAMI Blue / KAMI | `kamiblue`, `kami` | DENY |
| SalHack 与 Creepy SalHack / ForgeHax | `salhack`, `forgehax` | DENY |
| Lambda 新旧实现 / Ares / Wurst+2 | `lambda`, `ares`, `wurstplus` | DENY |
| Seppuku / FDPClient | `seppukumod`, `fdpclient` | DENY |
| Meteor Rejects / Trouser Streak / BlackOut 扩展 | `meteor-rejects`, `streak-addon`, `blackout` | DENY |
| Alien / Aoba / TrollHack / Jex | `alien`, `aoba`, `trollhack`, `jex` | DENY |
| Aegis / MasterMind / Hypnotic | `aegis`, `mastermind`, `hypnotic` | DENY |
| CheatUtils / GameSense | `cheatutils`, `gamesense` | DENY |
| NightX / Krs / Cigarette | `nightx`, `krs`, `cigarette` | DENY；NightX 的上报限制见下文 |
| Meteor+ 扩展 | `meteorplus` | DENY；不是展示名 `Meteor+` 或产物名 `meteor-plus` |
| Advanced XRay 旧 Fabric 实现 | `advanced-xray-fabric` | DENY |
| Advanced XRay、ate47 和 Deltinha 的独立实现共用身份 | `xray` | DENY |
| ate47 遗留 Forge 描述符 | `atianxray` | ALERT：尚未核验该旧 Forge 发布包 |
| Raven 的混同身份 | `keystrokesmod` | ALERT：不能据此认定普通按键显示用户使用 Raven |
| Baritone Fabric / Forge、NeoForge | `baritone`, `baritoe` | ALERT：自动化是否允许由服规决定 |

容易误用的细节：

- `baritoe` 是当前 Baritone 官方 Forge/NeoForge 描述符的真实拼写，不是根据产品名猜测的别名。
- SalHack 的 `mcmod.info` 还列出普通依赖 `lunatriuscore`、`schematica`。它们不进入作弊黑名单。
- 多个不同 Xray 作者共用 `xray`，因此合并来源但不宣称属于同一客户端。`antixray` 不会命中 `xray`。
- 不将性能优化、地图、配方查看、投影或无障碍辅助整类默认封禁。Sodium、Iris、JEI、REI、Litematica 等不是本目录的 DENY 条目。
- `wurst_testmod`、`lambda-tests` 等开发测试描述符不导出。
- ThunderHack 开源分支已声明停止开发；这不证明闭源后继使用同一个 ID。
- NightX 的 [`mcmod.info`](https://raw.githubusercontent.com/Aspw-w/NightX-Client/1c771444a9120d8c06fe7d88a3f5849402849bb4/src/main/resources/mcmod.info) 确实声明 `nightx`，但其 [IFMLLoadingPlugin 入口](https://raw.githubusercontent.com/Aspw-w/NightX-Client/1c771444a9120d8c06fe7d88a3f5849402849bb4/src/main/java/net/aspw/client/injection/forge/TransformerLoader.java) 使用 Mixin 且 `getModContainerClass` 返回 `null`。本次未证明普通 Forge Loader 列表一定包含它；该规则只会匹配实际收到的精确 ID，不能把加入规则说成能识别所有注入形式。
- `bigrat` **不加入规则**：[作弊衍生客户端](https://raw.githubusercontent.com/ZimnyCat/BigRat/3dc274a18e5912f904f30734fdcf858b0aaf964f/src/main/resources/fabric.mod.json) 与[正常实体/物品模组](https://raw.githubusercontent.com/dodogang/bigrat/68bf3add5a5f73f39c0a7248acb3b9bf9b1da879/src/main/resources/fabric.mod.json) 在 Fabric 1.16.5 使用完全相同的 ID，不能据此默认封禁。
- Achilles 的[实际描述符](https://raw.githubusercontent.com/NoboKik/Achilles/b63a84fdec014ed8015559671cda9f4ea2721103/client/src/main/resources/fabric.mod.json) 使用通用 ID `template`。`template` 和猜测出的 `achilles` 均不加入规则。

新增来源保留许可差异：Meteor+ 根 [LICENSE](https://raw.githubusercontent.com/MeteorClientPlus/MeteorPlus/657959e9b46faa0c1228c5978d3afe844351c911/LICENSE) 为 AGPL-3.0，而同提交描述符写 GPL-3.0，不能消除冲突后冒称有统一再分发许可。CheatUtils 现代源码为 MIT；所读 1.16.5 历史描述符写 All rights reserved 且该提交没有根 LICENSE，不把现代授权追溯套用到旧源码。这些标准许可证文本也纳入来源 SHA256 核验。Cigarette 记录的是其官方 GitHub 仓库固定提交，仓库声明已迁移，不能据此宣称掌握新托管站的最新状态。

Aristois、Impact、Future、RusherHack、Inertia、CatLean、Raven b+ 和 Xray Ultimate 留在 `pending`。官网、产品名或功能说明不足以证明真实 mod ID；其中 Aristois 官网抓取失败，Raven b+ 官方 API 返回 451，未绕过访问限制。资源包没有可推断的稳定 mod ID，文件名和本地 pack ID 都可修改，所以没有虚构 PACK/BRAND 封禁规则。验证器目前只允许 MOD 身份进入已验证列表。

服务端插件本身由服务器管理员安装，不能被普通玩家当作客户端插件“带进服务器”。客户端自报列表和品牌可伪造，改名的衍生客户端也可能避开精确匹配；原生服务端矿物混淆与行为检测仍然必要。

## 校验与维护

从项目根目录执行。Windows 示例将运行缓存放在 `E:\CodexTemp\QiZhangVerdict\catalog`；Linux/CI 可使用各自临时工作目录。所有输出文件必须尚不存在，工具拒绝覆盖。

```powershell
python -B catalog/catalog_tool.py validate
python -B catalog/catalog_tool.py verify-sources --cache E:\CodexTemp\QiZhangVerdict\catalog\verified
python -B catalog/catalog_tool.py verify-sources --cache E:\CodexTemp\QiZhangVerdict\catalog\verified --offline
python -B catalog/catalog_tool.py export --cache E:\CodexTemp\QiZhangVerdict\catalog\verified --format blacklist --output E:\CodexTemp\QiZhangVerdict\catalog\reviewed-extension-new.tsv
$env:QV_CATALOG_TEST_TEMP = 'E:\CodexTemp\QiZhangVerdict\catalog\tests'
python -B -m unittest discover -s catalog -p 'test_catalog.py' -v
```

`validate` 校验 JSON 结构、重复身份、精确匹配语法、用途/标识来源、固定提交、默认动作与模板绑定。`verify-sources` 仅请求固定提交下的文本源码/元数据，以及明确允许的 `LICENSE`、`LICENSE.txt`、`COPYING`、`COPYING.txt` 文件，限制 1 MiB、拒绝重定向和二进制路径，校验 SHA256 后解析每个标识。`export`、`merge` 必须指定已有缓存并重新离线核验来源，缺失或损坏时停止。校验器不擅自更新上游提交或现有哈希。

新增条目时，人工确认官方仓库和用途，再固定完整提交，记录真实主体描述符及同提交构建属性。遇到相同 ID 应归并证据或解释歧义，不能新增冲突规则；同一源码中出现的普通依赖不得一并封禁。取得新的固定提交后重新执行来源核验和全部工具测试，再审阅 TSV 差异。

## 与管理员规则合并

先将现有服务器的 `blacklist.tsv` 复制到临时目录审阅。工具只读取 `--existing`，不会自己定位服务器，也没有自动应用功能。下面只选择 ForgeHax 和 Raven 的两项候选；不能省略 `--add` 来批量添加整个目录。

```powershell
python -B catalog/catalog_tool.py merge --cache E:\CodexTemp\QiZhangVerdict\catalog\verified --existing E:\CodexTemp\QiZhangVerdict\catalog\admin-blacklist-copy.tsv --output E:\CodexTemp\QiZhangVerdict\catalog\blacklist-candidate-new.tsv --report E:\CodexTemp\QiZhangVerdict\catalog\merge-report-new.json --add mod:forgehax --add mod:keystrokesmod
```

按照核心读取器规范化 kind/ID 后已存在时，**保留管理员原 action 和 source**，即使是 `OFF`；建议有差异会进入冲突报告。`automation` 与 `mod` 共用同一键，忽略 ASCII 大小写及 Java `trim` 去除的两端空白，因此现有 `mod / baritone / OFF` 不会因选择 `automation:baritone` 被重加或覆盖。未明确选择的缺失项不会加入，所以不会静默恢复删除的规则。若管理员明确选择一个此前删除的 ID，该项才会成为候选新增。输入里已有重复/冲突行会报错，要求人工整理。工具还检查核心的 4 MiB、10000 条、mod ID 128 字符、值 256 UTF-8 字节限制及来源 URL。输出与输入路径必须不同，候选文件和报告也不能已存在。

人工审阅冲突报告和候选差异后，安排维护窗口，停服，备份当前规则与相关配置，再将审定候选替换为服务器的 `blacklist.tsv`。重新启动后运行 `/qzverdict reload` 并检查日志、`/qzverdict status` 与测试账号；如果服务已在线且确认只更新可热加载规则，也可在完成备份后按项目管理文档使用 reload。工具本身不会执行替换、重启或 reload。

## Minecraft 官方版本快照

截至本次读取，[Mojang 官方 version manifest](https://piston-meta.mojang.com/mc/game/version_manifest_v2.json) 的最新稳定版为 **26.3**，发布时间为 **2026-09-15**，元数据要求 Java **25**；最新快照为 **26.4-snapshot-1**。各候选元数据均已按 manifest 的 SHA1 校验。下表是工程测试优先级建议，不是市场占有率，也不代表已有构建或运行证据。

| 候选 Minecraft 版本 | 官方元数据 Java 主版本 | 建议关注点 |
| --- | --- | --- |
| 1.8.9、1.12.2 | 8 | 老服协议和旧 Forge；需单独适配，不能外推现代模组实现 |
| 1.16.5 | 8 | 老 Forge/Fabric 分界；实际模组工具链可能另有要求 |
| 1.18.2、1.19.2、1.19.4 | 17 | 中间代际协议与 loader 差异 |
| 1.20.1、1.20.4 | 17 | 现有服务器生态及协议变更边界 |
| 1.20.6、1.21.1、1.21.4、1.21.8、1.21.11 | 21 | 网络、物品组件与多 loader 的独立验证 |
| 26.1.2、26.2、26.3 | 25 | 新版本编号与工具链代际；不能沿用 Java 21 假设 |

客户端源码快照可能仍以较旧游戏版本为构建目标；这与官方最新 Minecraft 版本并不矛盾。目录里的声明版本不用于夸大本项目的兼容矩阵。
