# 1.20.6 开发提交 CI 记录

准确提交 [`d3422484b23e3f9a48465266335b81602d208c4b`](https://github.com/EeryFrank/QiZhangVerdict/commit/d3422484b23e3f9a48465266335b81602d208c4b) 的 GitHub 自动 push CI **13/13 项成功**：现代 7 个构建任务加 1 个收集任务，旧版 5 个构建任务。GitLab 同一提交的 13 项均因 `ci_quota_exceeded` 在启动前被拒绝，`started_at` 全部为空；不能算作 GitLab 构建通过。

| 工作流 | 运行 | 结果 |
|---|---|---|
| GitHub modern | [36413926835](https://github.com/EeryFrank/QiZhangVerdict/actions/runs/36413926835) | 8/8 成功；收集器报告 14 个精确名称及校验和符合预期的 JAR |
| GitHub legacy | [36413926666](https://github.com/EeryFrank/QiZhangVerdict/actions/runs/36413926666) | 1.8.9、1.12.2、1.16.5、1.18.2、1.19.4 共 5/5 成功 |
| GitLab main | [2889229996](https://gitlab.com/EeryFrank/QiZhangVerdict/-/pipelines/2889229996) | 13 项额度拒启，没有源码编译失败或成功的执行证据 |

本报告只绑定这次 `main` 提交，不是未来发布 tag 的 CI。**该提交的 1.20.6 目标只有 Fabric 和 NeoForge，后续 Forge 1.20.6 适配不在本次范围内。** 旧 Minecraft 版本已有 Forge 目标的构建仍按原矩阵计入。

新增 1.20.6 任务使用 Java 21 / Gradle 9.2.1，原日志显示 23 个 actionable tasks 全部实际执行。Fabric 的 12 项挑战派发检查、命令 parser 和原始 payload codec 均输出通过；NeoForge 的 9 项派发检查和两个 FML 引导的 JUnit 方法实际输出 `PASSED`，不是 `FROM-CACHE`。两个方法分别覆盖管理员命令树和有界 Bukkit 兼容 payload；不把方法内部断言数另计成 JUnit 方法数。

`core-bukkit` 实际执行 57 项安全回归、42 条目录规则及 3 项控制检查、6 项 Bukkit 延迟挑战检查。其五组 Python 测试共发现 56 项，其中 **55 通过、1 跳过**：文件/路径保护 6 项中的 Windows junction 用例在 Linux 上按源码条件跳过，其余四组分别 3、25、13、9 项通过。上述是源码任务检查，与本机精确成品 JAR 的核心验证分开记录。

各任务确实恢复了依赖及工具缓存；这不等于测试结果来自缓存。13 份原日志中未观察到 Gradle `FROM-CACHE` 任务结果。`NO-SOURCE`、聚合任务 `UP-TO-DATE` 和旧构建中 `SKIPPED` 的条目均在机器报告中保留，不能仅凭 `test` 或 `check` 任务名称增加测试数量。日志中的弃用、映射及加载器告警也未删改。

本轮只读取 API 和任务日志，没有下载并独立审计 CI JAR，也没有运行 Java、服务器或客户端。因此 14 个现代与 8 个旧版预期成品只描述该 CI 源码构建范围，不证明与已冻结本机成品逐字节一致，更不替代专服、图形客户端、性能、实际 VM 或 Anti-Xray 验收。

[机器报告](../outputs/ci-development-1.20.6.json)明确列出 14 份附件、771,302 字节：13 份 GitHub 原始任务日志，以及一份去掉作者/提交者邮箱等字段的 [API 派生摘要](../outputs/ci-development-1.20.6/api-summary.json)。每项均有来源、SHA-256 和大小，原日志字节与 ANSI 保留不变；完整原始 API 仅留缓存并记录哈希。本机 MachineGuid、主机名、已知夹具 scope/设备值只在内存中比对，选定材料没有命中；账号状态、server-id、世界、启动私密参数及第三方二进制没有复制。

相关本机阶段另见[成品构建验证](adapter-1.20.6.md)和[双加载器专服 TCP 验证](runtime-server-1.20.6.md)，它们各自保留独立来源、成品哈希和验证范围。
