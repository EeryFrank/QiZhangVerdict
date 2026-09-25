# CI 构建范围

GitHub Actions 与 GitLab CI 都在 Linux 上分三个任务执行：核心+Bukkit、MC 1.20.1 的 Fabric+Forge、MC 1.21.1 的 Fabric+NeoForge。最后收集且必须恰好得到五个正式 JAR 和 SHA256SUMS；不收集 sources/dev JAR。流水线只保存构建产物和日志，不创建 release、不推送代码、不使用发布凭证。

三个工程都使用仓库现有的 Gradle Wrapper 8.14.1。Gradle 本身在 JDK 21 上运行；额外安装 JDK 17 供 1.20.1 工具链使用。每次调用通过 `-Porg.gradle.java.installations.paths` 显式传入 Linux JDK 目录，并关闭工具链自动探测/下载，覆盖本地 `gradle.properties` 中的 Windows 路径。`JAVA_TOOL_OPTIONS` 将核心测试的临时目录指向 runner 工作区。GitHub 使用固定提交 SHA 的官方 actions；GitLab 使用 Temurin 21 Jammy 镜像和 Ubuntu 的 OpenJDK 17 包。

必须执行根工程 `build :core:securityTest`、两版工程各自的 `build :fabric:commandParserSmoke`，以及 Python 安装安全和运行证据解析回归。`build` 仍会执行全部子工程的 `check`；显式的 Fabric parser 任务运行两个 Minecraft 版本共用的真实生产命令树，和本地已验收的 parser 入口一致。没有 `-x test`、`-x check` 或忽略失败设置；`pipefail` 确保记录日志不会吞掉失败退出码。`CI=true` 供 Loom 在 CI 中减少开发依赖源码重映射，不跳过产物 remap 或检查。

CI 是重新构建和静态/逻辑回归，不会自动接受 Minecraft EULA、启动游戏服务端或图形客户端，也不会覆盖 `outputs/validation.json` 的既有 Windows 实测证据。新构建字节不应被当作已通过本地联机验收的旧散列；测试版 release 的已验收产物由独立发布流程处理。

GitHub 的 `qizhangverdict-five-jars-<commit>`、GitLab 的 `collect` job artifacts 为五 JAR 汇总，保留 30 天；中间构建与日志保留 14 天。GitLab 项目需要可用的 Linux Docker runner，并允许下载 Maven/Gradle/Minecraft 依赖及 Ubuntu 软件包。

配置依据：[setup-java](https://github.com/actions/setup-java)、[Gradle setup action](https://github.com/gradle/actions/blob/main/setup-gradle/README.md)、[GitLab CI YAML](https://docs.gitlab.com/ci/yaml/)。首次远端 pipeline 的执行结果应单独核验；仅完成配置静态校验不等于 CI 已通过。
