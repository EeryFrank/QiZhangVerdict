# 1.17.1 开发提交 CI 验证

提交 `22549cbc1334990801ec1cb87bd3cb395d624ff8` 的 `main / push` 开发 CI 已完成：GitHub **14 个任务全部成功**；GitLab **14 个任务均因配额不足未启动**。GitLab 不计为构建通过，本报告也不代表最终发布标签的 CI。

| 平台 | 固定运行 | 结果 |
| --- | --- | --- |
| GitHub 现代构建 | [36435367558](https://github.com/EeryFrank/QiZhangVerdict/actions/runs/36435367558) | 8 个构建任务及 `Collect seventeen modern JARs`，共 9 项成功 |
| GitHub 旧版构建 | [36435367429](https://github.com/EeryFrank/QiZhangVerdict/actions/runs/36435367429) | 1.8.9、1.12.2、1.16.5、1.18.2、1.19.4 共 5 项成功 |
| GitLab | [2889898639](https://gitlab.com/EeryFrank/QiZhangVerdict/-/pipelines/2889898639) | 14 项均为 `ci_quota_exceeded`，全部 `started_at=null` |

1.17.1 任务的原始日志记录了 29 个实际执行的 Gradle 任务：Fabric 与 Forge 各 15 项连接归属检查、两端生产命令解析检查，以及 Forge 的 8 次实际旧协议载荷写入检查。两端标准 `test` 任务执行成功，但没有仅凭任务状态推断 JUnit 用例数量。根工程原始日志另有逐项 1–57 的安全回归通过记录。

现代任务汇总的 17 个 JAR 已独立下载检查：GitHub API 的 ZIP SHA-256 和字节数、ZIP/JAR CRC、精确文件集合、`SHA256SUMS`、组件版本描述及提交中的 GPL-3.0-only `LICENSE`/`NOTICE` 均匹配。两个 1.17.1 CI JAR 分别与本地冻结成品 `bda006d2…`、`a71d6bb2…` 字节相同。这批 CI 重编文件不替换已冻结或已发布的本地制品；其他旧版任务的成功状态也不等于本报告逐包审计了其 8 个 JAR。

完整机器可读结果及 21 份明确列举的原字节附件见 [CI 报告](../outputs/ci-development-1.17.1.json)，包含 14 份官方任务日志、[终态 API 白名单快照](../outputs/ci-development-1.17.1/terminal-snapshot.json)、收集器结果与实际工具源码。公开前已检查凭据形态、邮箱、带签名的 URL 和本机主机名；没有复制账户状态、设备标识、原始 API 作者对象或下载的 CI 二进制 ZIP。

监看始终绑定上述两个 GitHub 运行和一个 GitLab 流水线。一轮列表筛选曾暂时返回空结果，随后直接查询最初的运行 ID；未重跑、取消或替换任务。

游戏兼容结论以独立的 [本地构建及包内核心报告](../outputs/adapter-build-1.17.1.json)、[专服与协议报告](../outputs/runtime-server-1.17.1.json) 和 [真实图形客户端报告](../outputs/runtime-client-1.17.1.json) 为准。本轮没有在本机启动 Java 或游戏，也没有执行发布操作。
