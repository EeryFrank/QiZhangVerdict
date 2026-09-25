# 七章的裁决：本次安全审查

审查日期：2026-09-25。审查对象为本仓库当前 Java 8 核心、Bukkit 适配器、共用客户端报告器，以及 1.20.1 / 1.21.1 模组适配源码。本文件区分核心回归、源码与字节码核验、真实服务端测试，不能代替完整兼容性或渗透测试报告。

## 已验证的核心行为

本次实际执行 `javac --release 8` 编译核心及 `SecurityRegressionTest`，进程退出码 0，55 项安全回归全部通过。测试可通过 `:core:securityTest` 重跑；临时数据在 `E:/CodexTemp/QiZhangGuard/core-tests`，不读取或修改现有服务器数据。

| 关注点 | 当前处理与证据 |
| --- | --- |
| IP 解析与身份别名 | 不调用 DNS；拒绝主机名、缩写/歧义 IPv4、IPv6 zone；IPv4-mapped IPv6 归一化。`literalValidation`、`mappedIdentity`、`ipv6Identity`、`cidrPolicy`、`mappedCidr` 覆盖。 |
| IP 与账号并发配额 | `openSession` 在同一锁内预留，只有 `confirmSession` 写滚动历史。64 个并发请求不能突破配额；未确认预留 30 秒过期。`concurrentAccounts`、`concurrentOnline`、`unconfirmedNotPersisted`、`reservationExpiry` 覆盖。 |
| 同 IP 与设备在线数 | 默认同 IP 3 个账号、同 IP + 同设备 1 个。设备验证与占位原子完成；重新验证不释放旧占位，退出才释放。`sameIpDevice`、`differentDevices`、`differentIps`、`concurrentDevice`、`twoPerDevice` 覆盖。 |
| 报告大小与解析 | 协议 v2、30,000 字节上限、严格 UTF-8、列表数量/字段长度/设备摘要校验、拒绝尾随数据。`wireBounds`、`wireEncoding`、`deviceWire` 覆盖。 |
| nonce 与报告时限 | 256 位随机 nonce；未知 nonce 或畸形报告消耗当前挑战。最近一条旧 nonce 最多容忍两次，仅返回拒绝状态 `STALE_REPORT`，不消费新挑战、不放行、不延长时限。`nonceReplay`、`nonceMismatch`、`challengeDeadline`、`staleReport`、`staleReportLimit` 覆盖。 |
| 稳定服务器作用域 | `server-id.txt` 随服务器保留，公开随机作用域随挑战发送；改域名/IP/端口不会让原版配套客户端生成另一个设备码。坏文件拒绝启动，不静默换身份。`stableScope`、`corruptScope` 覆盖。 |
| 黑白名单与模糊规则 | 精确匹配不误封 `antixray`、`schematica`、`lunatriuscore`；GLOB 仅支持 `*`、`?`，不执行用户正则。每份报告共享一百万步预算，超预算只拒绝，绝不永久封号。`exactBlacklist`、`managedRules`、`ruleBudget` 覆盖。 |
| 规则变更事务 | 配置、默认黑名单、管理规则一起验证后生效；管理规则原子保存后才替换内存。坏规则保留之前政策。`transactionalReload`、`blacklistTransaction`、`managedPersistence` 覆盖。 |
| 账号和设备关联封禁 | 仅明确黑名单/已知 VM DENY 在默认 BAN 策略下触发关联封禁；IP 限制、频率、并发、缺失/坏报告不永久封号。白名单不能绕过持久禁令；账号和设备独立解封。`linkedBans`、`whiteCannotBypassBan`、`independentUnban`、`kickOnly`、`missingDevice` 覆盖。 |
| 在线关联账号 | `bannedSessions()` 返回仍在线的已禁账号/设备，不自行删除会话，适配器每秒断线并清理。`onlineBans` 覆盖。 |
| 保存与损坏恢复 | 账号/IP、设备关联、封禁同一份 v2 状态原子替换，兼容读取 v1；损坏文件明确失败。后台保存与管理 ban/unban 不发生锁倒序死锁。`corruptState`、`saveConcurrency`、`banSaveConcurrency` 覆盖。 |
| VM 未知与物理机 VBS | 默认 DENY 只拒绝已知虚拟硬件类别；unknown、探测失败、HypervisorPresent 单项仅告警。`vmRequiresCompanion`、`vmEvidence` 覆盖。 |

## 适配器审查与本次修复

`bukkit/.../QiZhangVerdictPlugin.java` 的初始化失败路径现在保留监听器并拒绝后续登录；加入确认异常会清理并踢出，避免异常后留下未管理的玩家。等待报告期间拦截移动、交互、破坏/放置、背包点击和拖拽、拾取/丢弃、桶操作、指令、受伤和玩家/投射物伤害。重载先完成核心事务，再逐个复查在线 IP、账号、设备和已保存品牌，最后发新挑战；不再把重验异常误报成整个配置事务回滚。收到 `STALE_REPORT` 时保持等待状态。

此失败关闭路径已有真实 TCP 验证：使用最终 Bukkit JAR，SHA-256 为 `b752cac809c9247c7f8fc14560d1f06236b12f627cb6342e6afa684712362141`，在全新仅监听 `127.0.0.1:25589` 的 Purpur 1.21.1 测试服写入非法配置 `limits.max-online-per-ip=-1`。服务器达到 Done，插件仍可响应管理命令并记录 `ALL LOGINS BLOCKED`；真实 minecraft-protocol 客户端收到 `unavailable` 踢出文本，未进入 PLAY，正常 stop 后进程退出 0。完整证据：`E:/CodexTemp/QiZhangGuard/runtime/failclosed-1.21.1-20260925-141039/result.json`、同目录 `console.log` 和 `client-result.json`。可用 `scripts/failclosed_smoke.py` 重现，此脚本仅创建新的隔离测试目录。

配套客户端到插件服也已有最终成品的真实渲染客户端验证：正式 Fabric 1.21.1 成品 JAR `c878c510bfb0c0cc1815f34ef327b73cb4ce45eddeeb2d9e7bcac1b476fda182`，Fabric Loader 0.16.14 / Fabric API 0.116.15，连接最终 Bukkit 插件 B752 的独立严格默认测试服。14:34:40 加入，14:35:36 仍在有效会话中且为生存模式，已超过 20 秒必需报告窗口；有效格式的服务器作用域设备关联已持久保存，无账号/设备禁令。相同客户端在此 Bukkit 服与独立 Fabric 服生成不同设备摘要，证据仅保存比较结果，不包含原始安装标识。14:35:54 客户端正常断线，客户端与服务端均正常退出 0。证据：`E:/CodexTemp/QiZhangGuard/runtime/client-companion-bukkit-20260925-143045/companion-observation.json`、`result.json` 和 `console.log`；客户端日志在 `E:/CodexTemp/QiZhangGuard/client-release-smoke/evidence-bukkit-final`。这是实际客户端报告和联机证据，仍不证明真实 VM 拒绝、所有作弊识别或手动游戏体验。

`platforms/shared/.../MinecraftGuard.java` 已用连接对象身份防止旧连接退出事件清除新连接的会话。成功报告、正常退出、拒绝/超时断线及停服路径都会尝试恢复记录的游戏模式；加入初始化异常会清理并断线。等待期间使用旁观模式并每 tick 固定位置和观察目标。仅靠旁观模式不能拦截模组或原版指令，因此本次新增了版本明确的必需 Mixin：

- 1.20.1：`CommandGate120Mixin` 拦截 `Commands.performCommand(ParseResults, String): int`。
- 1.21.1：`CommandGate121Mixin` 拦截 `Commands.performCommand(ParseResults, String): void`。
- 两者都在 HEAD 取消等待玩家的执行；`required=true`、`require=1`，没有用 `require=0` 隐藏映射失败。
- 本次对缓存的 Mojang 映射 JAR 实际运行 `javap`，核对了两版不同返回类型，并核对 1.21.1 的 signed 与 unsigned 网络命令分支均调用该入口；1.20.1 的网络命令也调用对应入口。

最终 Fabric 1.21.1 成品 `c878c510bfb0c0cc1815f34ef327b73cb4ce45eddeeb2d9e7bcac1b476fda182` 已完成真实网络命令门禁验证：具有 OP 权限的测试账号在报告前发送 `/say` 唯一标记不执行，合法报告后发送的标记正常执行。同轮 26 项协议用例覆盖设备配额、账号与设备解封、带冒号的默认规则删除/恢复、白名单与 VM 策略，测试与服务端均退出 0。证据为 `E:/CodexTemp/QiZhangGuard/runtime-smoke/fabric-1.21.1-final-06/smoke-result.json`、`protocol-result.json` 和 `console.log`。这些客户端通过真实 TCP 连接，但报告为测试程序合成，不代表真实 VM 或作弊客户端穿透测试。其他三个模组平台的命令门禁目前仅有源码、映射、产物和启动核验，不能从此用例外推为已验证。

四端最终产物的 Mixin 必需配置、正确版本类、Fabric/Forge 非空 refmap 与 NeoForge 生产命名声明已经逐 JAR 核验，记录在 `E:/CodexTemp/QiZhangGuard/mixin-artifact-review.json`。两版真实 Brigadier 生产命令树回归通过，覆盖不加引号的 `device:<摘要>` 和 `legacy:mod:<ID>`、空格 GLOB、封禁原因、非管理员拒绝和无效页码；构建记录见 `outputs/evidence/mods-1.20.1-build-parser.log` 和 `mods-1.21.1-build-parser.log`。

最终 C878 成品也完成真实渲染 Fabric 客户端到同成品专服的验证：14:32:14 加入，14:32:52 仍处于严格策略下的有效会话，超过 20 秒报告期限，并实际读取到 `playerGameType=0`，证明已经恢复生存模式；设备关联已保存且没有新增禁令。14:33:29 客户端正常断线，客户端与专服均退出 0。证据在 `E:/CodexTemp/QiZhangGuard/runtime-smoke/fabric-1.21.1-realclient-final-02/companion-observation.json` 和同目录服务端日志、结果；客户端日志在 `E:/CodexTemp/QiZhangGuard/client-release-smoke/evidence-fabric-final`。同一最终客户端还完成 101.3 秒单人启动、报告通过、正常存档并退出 0，证据在 `evidence-singleplayer-final`。这验证了集成服务器 owner 的本地连接地址处理，不会将远程无效 IP 归一化为可信回环地址。

`client-common/.../ClientReporter.java` 本次审查发现并推动修复了两个竞态：原先三秒内丢弃新挑战会让快速重连/管理重载误超时；旧探测回调晚于新挑战会发旧 nonce。现实现每个报告器最多一个活动探测任务和一个待处理的最新请求，相同 nonce + scope 不重复探测，在真正回到客户端线程发送时再次核对 generation。适配器同时绑定原连接/原玩家，防止切服后旧包被迟到任务错误关联到新连接。探测不在游戏线程等待外部进程，Windows 查询设置超时；原始安装 ID 不进入报告。

物理服务端方面，Fabric 将客户端入口单独声明；Forge/NeoForge 只在物理客户端判断之后调用独立客户端类，共用服务器逻辑和命令 Mixin 不导入 `net.minecraft.client`。这项源码检查可以排除明显的直接客户端类引用，但实际物理专服加载仍须逐平台启动验证。

## 仍然存在的信任与运维边界

1. 客户端报告不是可信证明。修改客户端可以隐藏模组、伪造资源包清单、清空 VM 指标、替换或复制设备摘要。黑名单只有本次实际核验的精确规则，不能宣称覆盖全部市售作弊，更不能检测服务端自身安装的恶意插件。
2. 设备码是系统安装标识或本地随机安装标识的服务器作用域 SHA-256 摘要，不是不可更改硬件码。换系统、修改客户端、修改本地标识仍能改变它。管理员若删除/更换 `server-id.txt`，原设备禁令就失去对应关系。复制同一服务器配置时应保留该文件，独立服务器应各自创建作用域。该作用域是公开值，恶意服务器可以复制其他服务器的作用域，不能据此宣称对恶意服务器也不可跨服关联。
3. 共享设备会关联多个账号；伪造/复制摘要也可能错误关联账号。因此自动封禁不是可靠作弊证据，管理员必须保留复核和分别解封账号/设备的流程。首次品牌命中且从未收到设备报告时，服务器只能封已知账号。
4. 在线模式之外，服务器必须另行认证 UUID/账号归属。当前通用适配器的“成功加入”指 Minecraft 服务器 JOIN，不是 AuthMe 或其他登录插件的认证完成事件；没有声称集成这些认证插件。未受保护的代理转发同样不能作为可信 IP。
5. 精确 IP 配额不能阻止换代理/IPv6 地址；共享公网 IP 也不等于同一人。瞬时限速表有 LRU 容量，分布式 IP 轮换可能淘汰旧桶，不能代替网络层抗 DDoS。
6. 服务器里的其他插件/模组属于可信计算环境。它们能覆盖游戏模式、取消踢出、直接修改存档或绕开正常指令入口；本项目不提供插件之间的安全沙箱。强制结束服务器进程时，内存中的暂存游戏模式也无法完成退出恢复。
7. 自动封禁等待适配器后台保存；进程在保存前异常终止可能丢失最近几秒变更。正常关服主动刷盘。磁盘错误会保留 dirty 状态并报错重试，不能把失败写入当作已经持久化。状态文件、设备关联和禁令需要管理员备份、权限限制和保留期管理。
8. 动作预测/战斗判定依靠另行安装且真正验证过的反作弊引擎；透视防护依靠服务端区块混淆。报告黑名单和登录限制不能替代这两类运行机制。Folia、历史版本、混合端、大型整合包、旧存档与真实 VM/物理机矩阵需各自验证。
