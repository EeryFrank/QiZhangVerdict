# 1.12.2 Forge 专服开发版验收

本记录验证 GPL-3.0-only `0.2.0-dev`，不是已发布 `0.1.1` 的组成部分。最终成品 `qizhangverdict-forge-1.12.2-0.2.0-dev.jar` 的 SHA-256 为 `7ee00ced99919281e2d6851e123c6bcb2d8ddd3e46338870b2034d5a5dcf0966`。

官方 Forge `14.23.5.2864` 安装器通过官方 `.sha1` 及固定 SHA-256 校验，Mojang 原版服务端通过官方版本元数据的 SHA-1/大小校验。Temurin JDK `8u504-b01`、最大堆 `1536M`，全新隔离目录只监听 `127.0.0.1:25641`。安装器、专服及协议测试全部正常退出 `0`，专服进程和监听端口已释放。完整机器可读摘要及官方来源见 [验收 JSON](../outputs/legacy-mod-validation-1.12.2-gpl.json)，[原始专服日志](../outputs/evidence/legacy-112-gpl-console.log) 与 [协议结果](../outputs/evidence/legacy-112-gpl-protocol-result.json) 保留原始字节。

严格默认策略保持不变：报告必需、设备必需、VM `DENY`，同 IP 最多 3 个在线账号、同 IP 同设备最多 1 个、滚动账号数 5、报告超时 20 秒；生成配置的运行前后 SHA-256 一致。本轮 13 项真实 TCP 验收通过：原生 `QZGuard` / `REGISTER` 双向报告、合法账号报告后持续在线 **22.072 秒**且控制台仍显示严格会话、默认并发配额与退出释放、缺设备/异常报文拒绝且不永久封号、无报告 **20.393 秒**后断线且可重新登录。

等待报告时，真实获授 OP 的测试账号发送 `/say QZ112_PRE_GATE` 未执行；正确报告后 `/say QZ112_POST_GATE` 出现在专服日志。此版使用 Forge `CommandEvent` 门禁，没有 Mixin。所有账号、UUID 和设备摘要来自合成测试数据，未运行操作系统硬件探测。

本次记录不证明真实图形客户端、虚拟机识别准确率、作弊对抗、旧存档、整合包、战斗或性能。未安装第三方 Grim/AntiXray。原日志保留 8 行 WARN 和 1 行 ERROR：官方安装出的 Forge 输出 `FML appears to be missing any signature data`。因此本记录不声称“零错误日志”；专服启动、Guard 生命周期与 13 项协议断言确实完成。没有隐藏失败、重新归类告警或修改历史现代版本证据。

复现使用独立脚本 [legacy112_mod_smoke.py](../scripts/legacy112_mod_smoke.py)，依次执行 `stage <全新目录>`、`install <目录> --accept-eula`、`run <目录> --protocol`。该脚本不会修改冻结的现代协议夹具，安装/运行前要求至少 4 GiB 空闲物理内存。所有原始运行目录和准确脚本、JDK、成品及证据 SHA 均列在验收 JSON 中。
