# Bukkit 0.2.0-test.1 实际 TCP 验证

2026-09-25，新的 `qizhangverdict-bukkit-0.2.0-test.1.jar` 通过 **75 组**独立隔离服务器检查：目录与关联封禁专项 23 组，以及 Minecraft 1.20.1、1.21.1 各 26 组基础规则。四次服务器运行及四次协议客户端进程均退出 0，服务器均执行正常保存、停止；25675、25581、25582 已实际重新绑定并监听，确认释放。

本页唯一成品 SHA-256 为 `1e54c48f744b61cc23efe28b8516132d13dba601d9b36beab88c1da3a849f1b7`，大小 73,684 字节。每次部署前后均核对同一成品。完整断言、脚本快照、配置差异和 **44 份原字节附件（360,868 字节）**见[机器可读报告](../outputs/bukkit-validation-0.2.0-test.1.json)。附件使用显式白名单并按相同字节去重，不包含账号状态库、服务器设备盐、世界或游戏二进制。

| 实际服务器 | Java | 检查组 | 服务器运行时间 | 结果 |
| --- | --- | ---: | ---: | --- |
| Purpur 1.21.1 build 2329，专项初始阶段 | Oracle 21.0.8 | 14 | 137.353 秒 | PASS，正常停止 |
| 同一专项数据目录，正常重启阶段 | Oracle 21.0.8 | 9 | 85.341 秒 | PASS，正常停止 |
| Purpur 1.20.1 build 2062，独立 `full` | OpenJDK 17.0.20.1+1 | 26 | 105.17 秒 | PASS，正常停止 |
| Purpur 1.21.1 build 2329，独立 `full` | Oracle 21.0.8 | 26 | 115.39 秒 | PASS，正常停止 |

服务器取自已固定的官方 [Purpur 1.20.1/2062](https://api.purpurmc.org/v2/purpur/1.20.1/2062/download) 与 [1.21.1/2329](https://api.purpurmc.org/v2/purpur/1.21.1/2329/download) 缓存；对应 SHA-256 为 `238e64b33e5c7c9b87506cf1a23f239e6ce7fb71edd9d31837f229c94f4dfa1a`、`30403cf54f981f16e1403f172645e82d3e4a59ad6c9f1d8e98df99edb1f8ae4c`。每次启动前可用物理内存必须至少 3.5 GiB，单台最大堆 1536 MiB，四次顺序执行。

## 新目录与自动操作封禁

首次启动由成品自行生成 `blacklist.tsv`，逐行比较完整目录的种类、精确 ID、动作与固定来源地址：**37 条，33 DENY、4 ALERT**。[首次生成文件](../outputs/evidence/bukkit-0.2.0-test.1-catalog-blacklist-first-install.tsv)与[当时目录快照](../outputs/evidence/bukkit-0.2.0-test.1-catalog-catalog-snapshot.tsv)均保留。

- 六个新增精确 ID `cheatutils`、`cigarette`、`gamesense`、`krs`、`meteorplus`、`nightx` 分别通过真实报告触发拒绝，并各自持久化账号和设备两条封禁。
- `baritoe`、`baritone`、`atianxray`、`keystrokesmod` 保持默认 ALERT；检查到对应账号的实际告警与持久设备关联，且未增加封禁。这四项分别观察约 4.3–4.6 秒，未宣称超过 20 秒超时窗口。
- 普通或含糊 ID `bigrat`、`template`、`antixray`、`sodium`、`iris`、`jei`、`fabricloader`、`meteor-client-helper` 联合报告后持续在线 22.013 秒，无封禁。
- 管理员将 `meteor-client` 改为 OFF，通过命令 API 删除 `legacy:mod:xray`；重载及正常重启后文件字节保持不变，报告仍获准，并在重启阶段持续在线 22.004 秒。
- 管理员把 `baritone` 从 ALERT 改为 DENY 后，在 BAN 模式下命中 `AUTOMATION_DENIED`：此前使用同一设备的两个账号和一个设备恰好新增三条封禁。正常重启后，历史账号、换设备的违规账号以及使用原设备的新账号均被拒绝。
- KICK 对照阶段同样拒绝自动操作报告，但不增加永久封禁；同账号同设备清洁重连后持续在线 22.002 秒，历史关联账号也可进入。阶段结束恢复 BAN，黑名单编辑保持不变。

专项原始[初始结果](../outputs/evidence/bukkit-0.2.0-test.1-catalog-protocol-initial.json)和[重启结果](../outputs/evidence/bukkit-0.2.0-test.1-catalog-protocol-restart.json)逐项记录 14+9 组实际断言。实现与复现入口为[专用服务器助手](../scripts/bukkit_catalog_smoke.py)及[两阶段协议检查](../scripts/bukkit_catalog_protocol.cjs)。

## 两个现代版本的基础规则

沿用原 [runtime_smoke.py](../scripts/runtime_smoke.py) 与 [protocol_smoke.cjs](../scripts/protocol_smoke.cjs)，显式指定新 JAR 和预期 SHA，分别使用全新时间戳目录运行 `--mode full`。本轮只给服务器助手增加隐藏窗口和非 startup 目录拒绝覆盖措施，未修改历史协议脚本或历史结果。

每版 26 组覆盖：正常报告、真实 OP 在报告前不能执行命令且报告后恢复、缺失与畸形报告、同 IP 同设备第二账号拒绝、不同设备允许三账号且第四账号拒绝、退出释放配额、黑名单与设备关联封禁、账号/设备解封、BLACK GLOB 与 WHITE EXACT 优先级及删除、带冒号默认规则删除恢复、CIDR 拒绝、已知 VM 信号拒绝、单项 `hypervisor-present` 不永久封禁，以及 IP 在线上限改为 2 的对照。

两版均实际使用 `minecraft-protocol 1.66.2`、`minecraft-data 3.117.0`、`protodef 1.19.0`，网络压缩阈值 256。专项与基础夹具来自两个不同的依赖缓存，各自锁文件均已快照，不能视作同一锁文件。`full` 启用命令门禁检查、关闭 Anti-Xray 检查，未安装 Grim，因此实际数量是每版 **26**，不是历史 `integrated` 的 27 组。[1.20.1 原始结果](../outputs/evidence/bukkit-0.2.0-test.1-base-1.20.1-protocol-result.json)和[1.21.1 原始结果](../outputs/evidence/bukkit-0.2.0-test.1-base-1.21.1-protocol-result.json)列出全部断言。

## 配置与证据边界

完整默认配置参考 SHA-256 为 `47310c31b47287ab805bfdbf8ddddf80e8169385bd9c862239a0a0075644da4e`。为顺序创建合成账号，本轮有以下明确 QA 改动；这些夹具配置不应作为部署配置复制。

| 配置 | 默认值 | 23 组专项 | 每版 26 组基础 |
| --- | --- | --- | --- |
| IP 滚动账号上限 | 5 | 64 | 100 |
| 每分钟尝试次数 | 20 | 200 | 1000 |
| 报告超时 | 20 秒 | 20 秒 | 基线 4 秒；命令门禁 10 秒 |
| VM 动作 | DENY | DENY | 基线 ALERT；VM 与 VBS 场景 DENY |
| 拒绝后的处分 | BAN | 指定 KICK 对照后恢复 BAN | BAN |
| 同 IP 在线人数 | 3 | 3 | 基线 3；最后指定场景 2 |

专项始终保留其余 11 个默认键值，KICK 对照除外；每阶段检查全部 13 个键与最终配置字节。两类夹具均要求伴侣报告和设备 ID，同 IP 同设备最多一个在线账号。基础夹具最后保留 2 人上限、4 秒超时与 VM ALERT，报告对此有明确记录。本次不证明未调整的 5 个滚动账号和每分钟 20 次限制，也不把基础检查中的短时间获准连接表述为 20 秒以上存活。

原日志完整保留以下非致命问题：1.20.1 的 Purpur spark 下载超时；1.21.1 协议库在注册表/组件解码中的 `PartialReadError`；专项世界生成器的 `No key layers in MapLike[{}]`；离线模式、旧插件 `api-version`、终端/SIMD和重复断开告警。实际准入、封禁、命令与正常停止断言仍通过；专项不依赖矿石或平坦世界生成，亦不声称协议库所有包都能正确解码。

这些是 loopback TCP 与合成自报测试，不是渲染客户端、真实虚拟机、真实作弊执行、硬件证明或性能测试。设备码仍属于客户端自报。旧 Bukkit 0.1.1 的 [42 组 Paper 集成证据](legacy-paper-integration-validation.md)使用另一份 E119 成品，未计入本页 75 组，也未转用为新成品的 Grim 或 Anti-Xray 通过证明。
