# 可核验标识扩展目录

本目录供七章的裁决管理员审阅、按服规选用。2026-09-28 当前开发目录包含 **43 个归并条目、44 个精确 ID（40 DENY / 4 ALERT）**，另有 **8 个待验证品牌或资源包**。已验证条目的仓库声明共 46 个；加上同 ID 冲突复核的 4 个额外仓库，来源文本共覆盖 50 个公开仓库。本轮首次默认规则新增透视身份 `dualviewxray`、`simplexray`。目录工具不会连接服务器、修改服务器配置或自动恢复管理员删除的规则；已发布版本的目录和默认规则以各自 tag 与发布包为准。

历史 **0.2.0-test.1 的 37 条默认规则（33 DENY / 4 ALERT）**及其[验证汇总](../outputs/validation-0.2.0-test.1.json)保持原事实。此前 **39 条目录（35 DENY / 4 ALERT）**、**42 条目录（38 DENY / 4 ALERT）**及 [0.5 预览合集的 23 个已发布 JAR](preview-0.5.0-dev-preview.1.md)保留各自的 37/39/42 条默认规则与原字节，不由本次源码更新改写。当前 [Python 目录核验](../catalog/verification.json)实际运行仓库中的 **27 项测试**，离线复核 **297 条固定来源的 SHA256 与 59 个描述符证明**；另核对四份冲突描述符的实际同 ID 值，它们不产生规则。两份重新导出的 TSV 与仓库文件逐字节一致。原 42 条规则、41 个条目、271 个来源与 8 个待验证项均保持不变。新增 26 条来源在本轮候选研究中联网获取；合入检查复用其固定字节，没有冒称重新联网扫描全部旧来源。

首次默认数据的 44 行已与导出 TSV 作静态比对。另有独立的 [1.17.1 Fabric/Forge 构建与包内核心报告](../outputs/adapter-build-1.17.1.json)：两个 `0.6.0-dev` 精确 JAR 各完成 **104 项检查（57 安全 + 44 目录 + 3 普通身份及管理员配置保留）**，合计 208 次执行。新增两条分别覆盖 OFF 与 API 删除后 reload、重建仍保留，已有稀疏文件不会自动补齐。构建和核心检查不证明专服、图形客户端或正式用户验收；那些结果应另读对应运行报告。

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
| Wurst+3 / Ferox | `wurstplusthree`, `ferox` | DENY；此前 39 条目录已纳入，均为固定 Forge 1.12.2 源码身份 |
| Seppuku / FDPClient | `seppukumod`, `fdpclient` | DENY |
| Meteor Rejects / Trouser Streak / BlackOut 扩展 | `meteor-rejects`, `streak-addon`, `blackout` | DENY |
| Alien / Aoba / TrollHack / Jex | `alien`, `aoba`, `trollhack`, `jex` | DENY |
| Aegis / MasterMind / Hypnotic | `aegis`, `mastermind`, `hypnotic` | DENY |
| CheatUtils / GameSense | `cheatutils`, `gamesense` | DENY |
| NightX / Krs / Cigarette | `nightx`, `krs`, `cigarette` | DENY；NightX 的上报限制见下文 |
| Meteor+ 扩展 | `meteorplus` | DENY；不是展示名 `Meteor+` 或产物名 `meteor-plus` |
| Gate Client | `gateclient` | DENY；Forge 1.12.2 描述符与入口常量一致，实现许可未决 |
| Gensh1n | `genshin` | DENY；Fabric 1.20.4 描述符身份，不是仓库拼写 `gensh1n` |
| Meteor Crash Addon | `meteor-crash-addon` | DENY；源码构建目标 Fabric 1.20.6，未运行该客户端 |
| Advanced XRay 旧 Fabric 实现 | `advanced-xray-fabric` | DENY |
| Advanced XRay、ate47 和 Deltinha 的独立实现共用身份 | `xray` | DENY |
| DualView X-ray | `dualviewxray` | DENY；Fabric/Forge 的固定 1.20.1 源码描述符与属性相互印证 |
| SimpleXray | `simplexray` | DENY；Fabric 固定描述符身份，根 MIT 与描述符 CC0 声明冲突保留 |
| ate47 遗留 Forge 描述符 | `atianxray` | ALERT：尚未核验该旧 Forge 发布包 |
| Raven 的混同身份 | `keystrokesmod` | ALERT：不能据此认定普通按键显示用户使用 Raven |
| Baritone Fabric / Forge、NeoForge | `baritone`, `baritoe` | ALERT：自动化是否允许由服规决定 |

容易误用的细节：

- `baritoe` 是当前 Baritone 官方 Forge/NeoForge 描述符的真实拼写，不是根据产品名猜测的别名。
- SalHack 的 `mcmod.info` 还列出普通依赖 `lunatriuscore`、`schematica`。它们不进入作弊黑名单。
- 多个不同 Xray 作者共用 `xray`，因此合并来源但不宣称属于同一客户端。`antixray` 不会命中 `xray`。
- 不将性能优化、地图、配方查看、投影或无障碍辅助整类默认封禁。Sodium、Iris、JEI、REI、Litematica 等不是本目录的 DENY 条目。
- `wurst_testmod`、`lambda-tests` 等开发测试描述符不导出。
- Wurst+3 的 `wurstplusthree` 与 Wurst+2 的 `wurstplus` 不同；新增项都从 `mcmod.info` 主体读取，并与同提交 Forge `@Mod` 常量交叉核对。Ferox 的透视证据包含实际取消非目标方块绘制的 Mixin，不只依赖模块展示名。
- Xulu 公开反编译归档的注解写 `eclient`，但本轮缺少明确游戏版本、加载器描述符与许可证据，因此 `eclient` 和猜测的 `xulu` 都不新增。Coffee、Atomic 未取得可固定提交的官方描述符，也不根据名字生成规则。
- ThunderHack 开源分支已声明停止开发；这不证明闭源后继使用同一个 ID。
- NightX 的 [`mcmod.info`](https://raw.githubusercontent.com/Aspw-w/NightX-Client/1c771444a9120d8c06fe7d88a3f5849402849bb4/src/main/resources/mcmod.info) 确实声明 `nightx`，但其 [IFMLLoadingPlugin 入口](https://raw.githubusercontent.com/Aspw-w/NightX-Client/1c771444a9120d8c06fe7d88a3f5849402849bb4/src/main/java/net/aspw/client/injection/forge/TransformerLoader.java) 使用 Mixin 且 `getModContainerClass` 返回 `null`。本次未证明普通 Forge Loader 列表一定包含它；该规则只会匹配实际收到的精确 ID，不能把加入规则说成能识别所有注入形式。
- `bigrat` **不加入规则**：[作弊衍生客户端](https://raw.githubusercontent.com/ZimnyCat/BigRat/3dc274a18e5912f904f30734fdcf858b0aaf964f/src/main/resources/fabric.mod.json) 与[正常实体/物品模组](https://raw.githubusercontent.com/dodogang/bigrat/68bf3add5a5f73f39c0a7248acb3b9bf9b1da879/src/main/resources/fabric.mod.json) 在 Fabric 1.16.5 使用完全相同的 ID，不能据此默认封禁。
- Achilles 的[实际描述符](https://raw.githubusercontent.com/NoboKik/Achilles/b63a84fdec014ed8015559671cda9f4ea2721103/client/src/main/resources/fabric.mod.json) 使用通用 ID `template`。`template` 和猜测出的 `achilles` 均不加入规则。
- `hydrogen` **不加入默认规则**：[ghost 客户端描述符](https://raw.githubusercontent.com/zPeanut/Hydrogen/c84fd6a32504bfdcd9b85b420b57b50c52caf882/src/main/resources/mcmod.info) 与 [CaffeineMC 内存优化模组描述符](https://raw.githubusercontent.com/CaffeineMC/hydrogen-fabric/95da36046c2f55617a76ebb8ea1e1f2a330330e5/src/main/resources/fabric.mod.json) 都使用该 ID。当前 MOD 规则不按加载器、版本或仓库区分，不能一并封禁。
- `lumina` **不加入默认规则**：[作弊客户端描述符](https://raw.githubusercontent.com/stormcoph/LuminaClient/3e64dc0af5694bd5ac0fe7ebab1cbf63743646f9/src/main/resources/fabric.mod.json) 与 [westernbear 普通光照模组描述符](https://raw.githubusercontent.com/westernbear/lumina/7f857d2d3908335ebfd1705778caaa2460c545fa/src/main/resources/fabric.mod.json) 使用相同 ID。目录校验器和生产普通 ID 控制均防止将其误加为默认 DENY；管理员自定规则仍由管理员负责。

新增来源保留许可差异：Meteor+ 根 [LICENSE](https://raw.githubusercontent.com/MeteorClientPlus/MeteorPlus/657959e9b46faa0c1228c5978d3afe844351c911/LICENSE) 为 AGPL-3.0，而同提交描述符写 GPL-3.0，不能消除冲突后冒称有统一再分发许可。CheatUtils 现代源码为 MIT；所读 1.16.5 历史描述符写 All rights reserved 且该提交没有根 LICENSE，不把现代授权追溯套用到旧源码。这些标准许可证文本也纳入来源 SHA256 核验。Cigarette 记录的是其官方 GitHub 仓库固定提交，仓库声明已迁移，不能据此宣称掌握新托管站的最新状态。

Wurst+3 的固定 [LICENSE.md](https://raw.githubusercontent.com/WurstPlus/wurst-plus-three/4eca774c0998dfc06d2f378bf0d939b8ad59318c/LICENSE.md) 为 AGPLv3 文本；Ferox 的固定 [LICENSE](https://raw.githubusercontent.com/olliem5/ferox/627205bf13f3a8ff65780a60b319defdcab73eb4/LICENSE) 为 GPLv3 文本，未另行确定 only/or-later 授权选择。本轮只纳入 ID、事实说明和来源哈希，没有复制其实现或分发其二进制。

Gate Client 的固定 [mcmod.info](https://raw.githubusercontent.com/TheF1xer/GateClient-1.12.2/3ddadc1c0fe024ceccbc7c9b7b72e8cf4aabeb5a/src/main/resources/mcmod.info) 声明 `gateclient`，同提交标准 Forge `@Mod` 入口使用相同常量，源码有自动攻击与 XRay 绘制过滤。其 [LICENSE.txt](https://raw.githubusercontent.com/TheF1xer/GateClient-1.12.2/3ddadc1c0fe024ceccbc7c9b7b72e8cf4aabeb5a/LICENSE.txt) 是 Forge/FML LGPL 模板，明确普通模组实现不受该许可约束；因此 Gate 实现的授权仍未决，不把模板当作再分发授权。

Gensh1n 的固定 [fabric.mod.json](https://raw.githubusercontent.com/Undef1nedTeam/Gensh1n/bf6b6cbb596ce4782b20627a2a9360386fd79d02/src/main/resources/fabric.mod.json) 声明 `genshin`；同提交注册并实现 KillAura，根 LICENSE/README 的 GPL 与描述符 `IDK-0.0` 冲突保留。有限正常模组复核读取同提交描述符与属性后，得到 [Genshin Instruments](https://raw.githubusercontent.com/StavWasPlayZ/Genshin-Instruments/dd8ab22e9dac5c61ba9d5456abcf2ca339af4b7e/gradle.properties) 的 `genshinstrument`、[HoYoI](https://raw.githubusercontent.com/DeeChael/HoYoI/0938781c8268332eb88e66ca50381ad879ec0024/gradle.properties) 的 `hoyoi`、[MineGenshin](https://raw.githubusercontent.com/Violet-Molder/MineGenshin/6957d5f9f18dc89eff61b28cd2f89d6fab16b46e/gradle.properties) 的 `minegenshin`，均不等于 `genshin`；这不保证全球唯一，不能扩展为产品名、文件名或子串封禁。

Meteor Crash Addon 的固定 [描述符](https://raw.githubusercontent.com/AntiCope/meteor-crash-addon/0d64cc11330447d2821747f0b7f7566d6192b258/src/main/resources/fabric.mod.json) 直接说明服务器破坏用途，身份为 `meteor-crash-addon`。其 GPL 文本未另行确定 only/or-later；构建目标是 Minecraft 1.20.6 / Java release 21，尽管描述符声明 Java >=17，不能据此声称 Java 17 或整个版本下限范围可运行。它依赖 Meteor，诚实上报中的父模组本已受 `meteor-client` 规则覆盖；新增身份不代表不可绕过的新检测能力。

DualView X-ray 的固定 [Fabric 描述符](https://raw.githubusercontent.com/TACOWASA059/DualViewXray/2be44cfd6e2f1ed1b7dfde71dfafd76155a8cc3b/fabric/src/main/resources/fabric.mod.json) 明写 `dualviewxray`；Forge 描述符通过同提交 `mod_id` 属性解析为同值。源码实现独立的矿物透视视图，根 LICENSE 与构建属性均为 MIT，源码目标为 Minecraft 1.20.1 / Java 17；没有运行其作弊客户端或验证全部声明版本范围。

SimpleXray 的固定 [描述符](https://raw.githubusercontent.com/Gudu0/SimpleXray/eb20fecc273d669e6a21e430d1136928c718e973/src/main/resources/fabric.mod.json) 明写 `simplexray`，源码绘制层使用始终通过的深度测试显示被遮挡目标轮廓。[根 LICENSE](https://raw.githubusercontent.com/Gudu0/SimpleXray/eb20fecc273d669e6a21e430d1136928c718e973/LICENSE) 为 MIT，描述符却写 `CC0-1.0` 并保留示例说明、作者和联系字段；冲突未解决，不据此推定统一再分发许可。默认源码目标为 1.20.1，构建允许显式 `mcVersion`；README 列出的其它版本不作为运行证据。普通服务端插件 SimpleXRayDetector 不等于这个客户端 MOD 身份，也不会因名字含 `xray` 而命中精确规则。

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

在此前保存的 [Mojang 官方 version manifest](https://piston-meta.mojang.com/mc/game/version_manifest_v2.json) 快照中（本轮未重新联网读取），最新稳定版为 **26.3**，发布时间为 **2026-09-15**，元数据要求 Java **25**；最新快照为 **26.4-snapshot-1**。各候选元数据均已按 manifest 的 SHA1 校验。下表是工程测试优先级建议，不是市场占有率，也不代表已有构建或运行证据。

| 候选 Minecraft 版本 | 官方元数据 Java 主版本 | 建议关注点 |
| --- | --- | --- |
| 1.8.9、1.12.2 | 8 | 老服协议和旧 Forge；需单独适配，不能外推现代模组实现 |
| 1.16.5 | 8 | 老 Forge/Fabric 分界；实际模组工具链可能另有要求 |
| 1.18.2、1.19.2、1.19.4 | 17 | 中间代际协议与 loader 差异 |
| 1.20.1、1.20.4 | 17 | 现有服务器生态及协议变更边界 |
| 1.20.6、1.21.1、1.21.4、1.21.8、1.21.11 | 21 | 网络、物品组件与多 loader 的独立验证 |
| 26.1.2、26.2、26.3 | 25 | 新版本编号与工具链代际；不能沿用 Java 21 假设 |

客户端源码快照可能仍以较旧游戏版本为构建目标；这与官方最新 Minecraft 版本并不矛盾。目录里的声明版本不用于夸大本项目的兼容矩阵。
