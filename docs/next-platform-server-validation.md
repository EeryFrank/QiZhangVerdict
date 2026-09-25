# 新适配专服验收

0.3.0-dev 的五个适配分别完成真实隔离专服启动、必需命令 Mixin 载入和 26 组 TCP 检查。实际本机成品 SHA、原运行日志、执行脚本快照与失败记录见[完整报告](../outputs/next-platform-server-validation.json)。这不是 CI 重编 JAR 或图形客户端验收。

| Attempt | Full TCP groups | Scope | Server / protocol exit |
| --- | ---: | --- | --- |
| 1.19.2/fabric-01 | 26 | current pinned artifact | 0 / 0 |
| 1.19.2/forge-01 | 0 (failed) | retained failure | 0 / 1 |
| 1.19.2/forge-02 | 26 | current pinned artifact | 0 / 0 |
| 1.20.4/fabric-01 | 0 (failed) | retained failure | 0 / 1 |
| 1.20.4/fabric-02 | 0 (failed) | retained failure | 0 / 1 |
| 1.20.4/forge-02 | 26 | current pinned artifact | 0 / 0 |
| 1.20.4/neoforge-01 | 26 | historical extra pass | 0 / 0 |
| 1.20.4/fabric-03 | 26 | current pinned artifact | 0 / 0 |
| 1.20.4/neoforge-02 | 26 | current pinned artifact | 0 / 0 |

保留所有失败尝试；退出 0 只说明服务端正常停机，不能把失败的协议检查计为通过。Forge 1.19.2 首次因测试频道注册缺少 NUL 而未收到挑战，原产品未改；后续格式修正运行单独记录。Fabric 1.20.4 的历史断线原因观察失败亦保留，以最终独立运行及诊断为准。

启动日志确认 companion / device 必需与 VM DENY；为批量 TCP 用例，脚本随后将历史账号上限改为 100、尝试频率改为 1000、超时改为 4 秒、VM 改为 ALERT，并在专门用例中切回 VM DENY、调整 IP 规则、超时和在线人数。不能宣称全程保持默认政策，或把合成报告当作真实 VM / 设备证明。没有安装第三方 Grim 或 Anti-Xray，没有性能或作弊检测准确率结论。

公开文件只按报告白名单复制原字节；scope、状态文件、实际设备摘要、世界和 Minecraft 二进制均不公开。日志中的上游兼容性/离线模式/资源告警仍然保留。

最终五个明确 SHA 成品各 26 组，共 **130 组**；NeoForge 1.20.4 首轮旧 `c3e742…` 的 26 组仅作为历史额外通过保存，不计入这 130 组。该旧 JAR 后续真实客户端报告超时失败，新 `1552dabe…` 成品必须并已在 `neoforge-02` 独立重测。全部材料有 9 次实际运行（6 次完整协议通过、3 次协议失败）及 1 个只准备未启动 Java 的目录。旧失败不能用服务端退出 0 改写为通过。

Fabric 1.20.4 第三轮在原成品上加入仅观察的协议 trace，真实记录了 IP 拒绝及旧封号断线原因并完成 26 项；首两轮缺少原因的根因仍未确认，不声称 trace 修复了产品。原 trace、三轮原结果和执行脚本全部保留。支持性 11 项 observer 内存测试、3 份脚本语法检查和 9 项 trace 内存测试另列，不计入 130 个真实 TCP 检查，也不证明历史失败的根因。
