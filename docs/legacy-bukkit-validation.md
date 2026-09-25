# 旧版 Bukkit 独立运行验证

## 0.1.1 新构建：五版各 12 项通过

2026-09-25 对 `qizhangverdict-bukkit-0.1.1.jar` 再次逐版串行启动，SHA-256 为 `5688683392ff59aee0bfbbe3f1f41ca056cebc06a063afad608714848d7d7639`。五个版本全部通过 12 项真实 TCP 检查，服务端均正常 `stop`、退出 0。每台服务使用最多 1 GiB 堆；原 `v0.1.0-test.1` 产物及历史 JSON 保持不变。

新增第 12 项独立检查：合法报告之后等待至少 22 秒，客户端仍连接；随后实际执行 `qzverdict status`，验证服务端仍有一个有效会话，且 `companion=required`、`deviceRequired=true`、`vm=DENY`。这避免只凭短时在线或客户端“已经发送”判断报告通过。同时继续保留无响应账号在默认 20 秒后被踢出的检查，测试前后 `guard.properties` 的散列一致。

| Minecraft / Paper | 合法报告后持续在线 | 无报告踢出时间 | TCP 用例 | 进程退出 |
| --- | --- | --- | --- | --- |
| 1.8.8 / 445 | 22.130 秒 | 20.686 秒 | 12 / 12 | 0 |
| 1.12.2 / 1620 | 22.072 秒 | 20.911 秒 | 12 / 12 | 0 |
| 1.16.5 / 794 | 22.190 秒 | 20.890 秒 | 12 / 12 | 0 |
| 1.18.2 / 388 | 22.139 秒 | 20.861 秒 | 12 / 12 | 0 |
| 1.19.4 / 550 | 22.065 秒 | 20.552 秒 | 12 / 12 | 0 |

独立机器可读证据：[legacy-bukkit-validation-0.1.1.json](../outputs/legacy-bukkit-validation-0.1.1.json)，保存成品散列、后验状态行、原始日志及结果散列。合计 60 项是五版各 12 项网络断言，不是核心单元测试数量。Java 与 Paper 构建与下面的历史矩阵一致。1.16.5 仍记录一条超平坦 structures 配置回退 ERROR，1.18.2 记录旧 Bukkit material 初始化提示；实际启动、准入与退出结果均单独检查，没有把 PASS 解释成无错误日志。

新版脚本可显式指定并校验待测成品：

```powershell
python scripts/legacy_bukkit_smoke.py run 1.16.5 1.18.2 1.19.4 1.12.2 1.8.8 --guard-jar bukkit/build/libs/qizhangverdict-bukkit-0.1.1.jar --expected-guard-sha256 5688683392ff59aee0bfbbe3f1f41ca056cebc06a063afad608714848d7d7639
```

本轮依旧使用合成客户端报告，没有把这些版本的真实配套客户端、VM 探测或外部防作弊兼容性列为通过。

## 0.1.0 已发布产物的历史验证

验证日期：2026-09-25。本节历史测试对象是公开测试版 `v0.1.0-test.1` 的同一份 Bukkit 插件，SHA-256 为 `b752cac809c9247c7f8fc14560d1f06236b12f627cb6342e6afa684712362141`。没有修改、重建或覆盖该发布产物。

以下五个官方 Paper 构建均完成实际启动、`qzverdict status` 响应、11 项真实 TCP 检查及正常 `stop`，服务端退出码全部为 0。**这证明所列插件准入行为在这些具体构建上运行，不代表旧版配套客户端模组已经交付，也不代表全部主流版本完整兼容。**

| Minecraft | Paper 构建 | 实测 Java | 消息频道 | TCP 用例 | 默认超时实测 |
| --- | --- | --- | --- | --- | --- |
| 1.8.8 | 445 | Temurin 8u504-b01 | `QZGuard` / `REGISTER` | 11 / 11 | 20.556 秒 |
| 1.12.2 | 1620 | Temurin 8u504-b01 | `QZGuard` / `REGISTER` | 11 / 11 | 20.203 秒 |
| 1.16.5 | 794 | Temurin 8u504-b01 | `qzguard:main` / `minecraft:register` | 11 / 11 | 20.622 秒 |
| 1.18.2 | 388 | Temurin 17.0.20.1+1 | `qzguard:main` / `minecraft:register` | 11 / 11 | 20.118 秒 |
| 1.19.4 | 550 | Temurin 17.0.20.1+1 | `qzguard:main` / `minecraft:register` | 11 / 11 | 20.195 秒 |

所有运行都保留插件首次生成的 `guard.properties`，测试前后校验其 SHA-256 一致：同 IP 最多 3 个在线账号、同 IP 与同设备最多 1 个、滚动账号上限 5、客户端报告和设备码必需、已知 VM 默认 DENY、报告期限 20 秒。未关闭设备验证，也未把超时缩短后冒充默认行为。为了可重复地使用合成账号，服务器仅监听 `127.0.0.1`，在隔离目录中采用离线模式；这不是对生产服关闭认证的建议。

每版实际检查：

1. 在正确的新/旧插件频道发送完整协议 v2 报告后正常加入。
2. 同 IP、同设备的第二个账号被拒绝。
3. 同 IP 的第二个不同设备被允许。
4. 同 IP 的第三个不同设备被允许。
5. 同 IP 的第四个并发账号被拒绝。
6. 退出后释放 IP 与设备并发名额。
7. 缺失设备码被严格默认策略拒绝。
8. 畸形报告被拒绝。
9. 畸形报告未产生永久封号，正确重连可成功。
10. 不响应挑战的账号在默认 20 秒期限后被断开。
11. 超时未产生永久封号且清理会话，正确重连可成功。

这 55 项是五个版本各 11 项实际网络断言，与核心模块的 55 项 Java 回归是不同证据，不能混为同一组测试。

## 来源与证据

服务端来自 [Paper 官方下载 API](https://fill.papermc.io/v3/projects/paper)，逐个核验其官方 SHA-256 和文件长度。构建选择结果已固定在本地下载收据，不在重跑时自动更换版本。Java 8 来自 [Adoptium 官方 API](https://api.adoptium.net/v3/assets/latest/8/hotspot?architecture=x64&image_type=jre&os=windows&vendor=eclipse)，使用 Temurin 8u504-b01 Windows x64 JRE ZIP，官方 SHA-256 为 `82e2cdc6693737c5998445b31f69668fa0da77c7705121053f6508ac84961123`。没有使用重新打包的第三方服务器镜像。

| 版本 | 官方 Paper JAR SHA-256 |
| --- | --- |
| 1.8.8 | `7ff6d2cec671ef0d95b3723b5c92890118fb882d73b7f8fa0a2cd31d97c55f86` |
| 1.12.2 | `3a2041807f492dcdc34ebb324a287414946e3e05ec3df6fd03f5b5f7d9afc210` |
| 1.16.5 | `e67da4851d08cde378ab2b89be58849238c303351ed2482181a99c2c2b489276` |
| 1.18.2 | `0578f18f4d632b494b468ec56b3b414b5b56fea087ee7d39cf6dcdf4c9d01f05` |
| 1.19.4 | `e587d78cba3e99ef8c4bc24cf20cc3bdbbe89e33b0b572070446af4eb6be5ccf` |

机器可读结果：[legacy-bukkit-validation.json](../outputs/legacy-bukkit-validation.json)。它记录每个具体服务端来源、构建、插件散列、Java 版本、策略、日志与结果文件散列，以及原始证据位置；不包含玩家状态文件、服务器作用域、设备摘要或世界数据。原始隔离运行记录保留在 `E:/CodexTemp/QiZhangVerdict/legacy-runtime`，没有加入项目源码或安装包。

复现入口：[legacy_bukkit_smoke.py](https://github.com/EeryFrank/QiZhangVerdict/blob/v0.1.1-test.1/scripts/legacy_bukkit_smoke.py)。脚本是 Windows 本机验证工具，使用其中明确配置的 Node、`minecraft-protocol` 1.66.2 及 Java 17 路径；Java 8 会从官方来源下载并验证。它只创建新的隔离目录，不接管已有服务器。

```powershell
python scripts/legacy_bukkit_smoke.py prepare 1.16.5 1.18.2 1.19.4 1.12.2 1.8.8
python scripts/legacy_bukkit_smoke.py run 1.16.5 1.18.2 1.19.4 1.12.2 1.8.8
```

## 已保留的日志现象与边界

旧版 Paper 在部分有意踢出路径打印 `handleDisconnection() called twice`，现代 Paper 因插件兼容旧 Bukkit API 而打印 legacy material/API-version 提示；这些日志没有被删去。1.16.5 的旧 Paper 检查器对 Java 8 主版本发出通用弃用提示，本次实际使用的是更新的 Temurin 8u504。首次现代版测试夹具没有填写超平坦生成层，Paper 输出生成配置回退错误后继续启动并完成所有测试；复现脚本随后补上明确生成层。PASS 不等于日志没有 WARN/ERROR。

1.8.8 / 1.12.2 的第一次预备运行因旧 Paper 不接受 `--nogui` 提前退出；改为 `nogui` 后重新在全新目录完成全部测试。这属于验证脚本启动参数问题，不是插件运行失败；失败记录仍保留在机器可读报告中。

本轮客户端通过真实 TCP 连接，但设备与模组信息由测试程序合成。尚未验证这些版本的图形配套客户端、真实 VM 拒绝、防篡改设备身份、Grim/AntiXray、指令隔离、完整玩法、性能、代理、混合端和 Folia。不能将此报告外推为所有中间版本或老版本自身安全性的保证。默认严格策略依赖匹配版本的配套客户端，只有插件通过旧版测试并不使现有 1.20.1 / 1.21.1 客户端模组自动兼容旧游戏版本。
