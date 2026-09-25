# CI 构建范围

GitHub Actions 与 GitLab CI 都在 Linux 上分三个任务执行：核心+Bukkit、MC 1.20.1 的 Fabric+Forge、MC 1.21.1 的 Fabric+NeoForge。最后收集且必须恰好得到五个正式 JAR 和 SHA256SUMS；不收集 sources/dev JAR。流水线只保存构建产物和日志，不创建 release、不推送代码、不使用发布凭证。

三个工程都使用仓库现有的 Gradle Wrapper 8.14.1。Gradle 本身在 JDK 21 上运行；额外安装 JDK 17 供 1.20.1 工具链使用。每次调用通过 `-Porg.gradle.java.installations.paths` 显式传入 Linux JDK 目录，并关闭工具链自动探测/下载，覆盖本地 `gradle.properties` 中的 Windows 路径。`JAVA_TOOL_OPTIONS` 将核心测试的临时目录指向 runner 工作区。GitHub 使用固定提交 SHA 的官方 actions；GitLab 使用 Temurin 21 Noble 镜像和 Ubuntu 的 OpenJDK 17 包。

必须执行根工程 `build :core:securityTest`、两版工程各自的 `build :fabric:commandParserSmoke`，以及 Python 安装安全和运行证据解析回归。`build` 仍会执行全部子工程的 `check`；显式的 Fabric parser 任务运行两个 Minecraft 版本共用的真实生产命令树，和本地已验收的 parser 入口一致。没有 `-x test`、`-x check` 或忽略失败设置；`pipefail` 确保记录日志不会吞掉失败退出码。`CI=true` 供 Loom 在 CI 中减少开发依赖源码重映射，不跳过产物 remap 或检查。

上述构建 CI 是重新构建和静态/逻辑回归，不会自动接受 Minecraft EULA、启动游戏服务端或图形客户端，也不会覆盖 `outputs/validation.json` 的既有 Windows 实测证据。新构建字节不应被当作已通过本地联机验收的旧散列；测试版 release 的已验收产物由独立发布流程处理。

GitHub 的 `qizhangverdict-five-jars-<commit>`、GitLab 的 `collect` job artifacts 为五 JAR 汇总，保留 30 天；中间构建与日志保留 14 天。GitLab 项目需要可用的 Linux Docker runner，并允许下载 Maven/Gradle/Minecraft 依赖及 Ubuntu 软件包。

0.1.1 起额外执行扩展目录的 25 项 Python 回归，以及 Java 生产解析器对 31 条导出规则的兼容检查。GitLab 镜像改用 Temurin 21 Noble（Ubuntu 24.04），以满足标准库 `tomllib` 所需的 Python 3.11+；原 Jammy 默认 Python 3.10 不满足该工具要求。

## 旧版开发构建

独立的 GitHub `legacy-build.yml` 与 GitLab `legacy-build` 矩阵检查 1.8.9、1.12.2、1.16.5、1.18.2、1.19.4，共八个开发 JAR。两站共用 `scripts/ci_legacy_build.sh`，不会把开发成品混入五 JAR 的 0.1.1 汇总，也不会自动发布测试版。

1.12.2 用 JDK 8 运行官方 MDK 对应的 Gradle 5.6.4 / ForgeGradle 3；其他三版用 JDK 21 运行 Gradle 8.14.1，再以 JDK 17 编译。1.16.5 以 `--release 8` 编译并在真实 Java 8 上执行核心、报告器及两端命令解析检查；1.18.2 / 1.19.4 的命令检查使用 Java 17。所有必需检查都由各自 `build → check` 依赖执行。CI 安装三个完整 JDK，并关闭 Gradle 工具链的隐式下载。

1.8.9 另用原生 JDK 8 + 固定 ForgeGradle 2.1 + Gradle 2.7，执行 `setupCIWorkspace build` 和五项必需 Java 检查。旧 MDK wrapper 不支持分发 SHA256 校验，CI 会先校验官方 ZIP 的固定 SHA256，再解压到全新目录运行。不得用仅添加 wrapper 属性代替校验。损坏缓存拒绝、新目录隔离及 GitLab 官方 YAML lint 的证据见 [1.8.9 CI 预检](../outputs/legacy-ci-preflight-1.8.9.json)；预检不等于新增目标的远端构建已通过。

GitHub 使用固定 SHA 的官方 actions；GitLab 开发任务使用[官方 Temurin 8 Noble 镜像](https://github.com/adoptium/containers/blob/main/8/jdk/ubuntu/noble/Dockerfile)，另安装 Ubuntu 24.04 的 JDK 17 / 21。独立任务保留日志及带 SHA256 的开发产物 14 天。CI 构建成功仍不能替代指定 Windows 成品的专服或客户端实测。

0.1.1 发布提交 `d485e597827dd8544fc8cc183df19389a1db06e1` 的 [GitHub tag 构建](https://github.com/EeryFrank/QiZhangVerdict/actions/runs/36106352623)四个任务全部通过；同提交 [GitLab pipeline](https://gitlab.com/EeryFrank/QiZhangVerdict/-/pipelines/2881378657) 因 `ci_quota_exceeded` 未执行。新加入的旧版流水线结果须按新提交单独核验，不能借用此历史结果。

开发提交 `34e323b656af4f7a49edcf646e0d5b8d62ebb919` 的[旧版四任务](https://github.com/EeryFrank/QiZhangVerdict/actions/runs/36111380288)与[现代版四任务](https://github.com/EeryFrank/QiZhangVerdict/actions/runs/36111380421)均通过。已实际下载七个旧版 CI JAR，核对校验和、内置 GPL / NOTICE、Manifest 和 class 版本；见[独立 CI 记录](../outputs/legacy-ci-validation-0.2.0-dev.json)。首轮 1.19.4 因未使用仓库共享 wrapper 而失败，原运行保留，修正仅涉及 CI 路径。同提交 GitLab 的八个任务仍因额度不足未执行。

配置依据：[setup-java](https://github.com/actions/setup-java)、[Gradle setup action](https://github.com/gradle/actions/blob/main/setup-gradle/README.md)、[GitLab CI YAML](https://docs.gitlab.com/ci/yaml/)。首次远端 pipeline 的执行结果应单独核验；仅完成配置静态校验不等于 CI 已通过。

`v0.2.0-dev-preview.1` 的固定提交 `0f5335649573a2cb3f0ee4c11d264cd17a116c6e` 已完成 [GitHub 旧版四任务](https://github.com/EeryFrank/QiZhangVerdict/actions/runs/36115223222)和[现代四任务](https://github.com/EeryFrank/QiZhangVerdict/actions/runs/36115223292)，全部通过。同提交 [GitLab tag pipeline](https://gitlab.com/EeryFrank/QiZhangVerdict/-/pipelines/2881654692) 的八任务均为 `ci_quota_exceeded`，未执行。发布成品另经本机运行和两站下载校验，见 [预览回执](../outputs/publish-receipt-0.2.0-dev-preview.1.json)。

加入 1.8.9 后，提交 `281fa7a` 的首次远程构建因官方 Gradle 2.7 启动脚本被 `sh` 执行而失败。保持分发校验和必需检查不变，仅该目标改用 Bash 后，提交 `ba7c919ef48298b15fe41fff8bfc222524961291` 的旧版五任务与现代四任务全部通过；GitLab 九任务仍因额度不足未执行。见[故障复现](../outputs/legacy-ci-diagnosis-1.8.9.json)与[远程结果](../outputs/legacy-ci-validation-1.8.9.json)。

## 手动 Grim 联动运行测试

`grim-link-qa.yml` 仅通过 `workflow_dispatch` 启动，在临时的 Linux runner 上创建绑定 `127.0.0.1` 的两个独立测试服。它下载并校验已发布 GPL Bukkit 0.1.1、固定 Purpur 与 Grim，接受该隔离夹具的 Minecraft EULA，实际启动 JVM；不会连接现存服务器。测试使用原样处罚模板的 `120:0` 阈值，通过重复物品栏槽位包触发 Grim 检查，验证关联账号/设备封禁、重启持久化和管理员解封。Node 22 依赖通过固定 npm lock 安装。只有该运行的实际日志和结果可证明通过；配置存在不代表测试已执行。上传路径明确限定为夹具元数据、日志与结果，不上传世界、Minecraft JAR 或账号状态文件。
