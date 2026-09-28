# Forge 1.20.6 独立构建工程

本目录固定 Forge `50.2.0`、ForgeGradle `6.0.54`、Gradle `8.12.1` 和 Java 21，组件版本为 `0.5.0-dev`。它是独立 Gradle 工程，不能加入上一层 Gradle 9.2.1 的 `settings.gradle`，也不能通过该父 wrapper 或 `includeBuild` 调用。

源码引用仓库的 `core`、`client-common` 和 `platforms/1.20.6/common`；不复制它们，也不改变已验证的 Fabric/NeoForge 模块。遵循固定官方 MDK 的 `reobf=false`，保留每个 sourceSet 合并 classes/resources 输出。生产 Mixin 使用官方方法名称，`required=true`、`defaultRequire=1`，不混入 Fabric refmap。

首方代码与成品为 GPL-3.0-only，二进制和源码 JAR 均通过仓库现有许可脚本包含根目录 `LICENSE`、`NOTICE`。Gradle wrapper 和官方 MDK 告示的第三方许可见 [THIRD_PARTY.md](THIRD_PARTY.md)。

在此目录使用自己的 wrapper 构建，先把进程的 `JAVA_HOME` 指向 Java 21，并将 `GRADLE_USER_HOME`、`TEMP`、`TMP`、`JAVA_TOOL_OPTIONS` 中的 `java.io.tmpdir` 指向 `E:/CodexTemp` 内的独立缓存。例：

```powershell
.\gradlew.bat --no-daemon --max-workers=1 --console=plain --stacktrace `
  --project-cache-dir E:/CodexTemp/QiZhangVerdict/compat-1.20.6/forge-build/project-cache `
  -PqzRuntimeRoot=E:/CodexTemp/QiZhangVerdict/compat-1.20.6/forge-build/runtime build
```

`check` 强制依赖四个真实实现检查：

- `connectionDispatchSmoke` 调用生产连接门禁 helper，覆盖 15 项排队登录、切服、监听器替换、关闭连接、阶段切换和身份比较断言。
- `payloadCodecSmoke` 使用实际 Forge `EventNetworkChannel.encode` 与生产 `ForgeWire`，检查原始字节、不额外加长度前缀、30,000 字节边界、非零读指针和数组/缓冲区所有权。
- `commandParserSmoke` 复用公共生产命令树和实际 Brigadier，覆盖设备解封、默认规则 ID、模糊资源包参数、封禁原因与管理员权限。
- `mixinCompatibilitySmoke` 直接读取本次构建 JAR 的配置和 Mixin class，用固定 Mixin 0.8.5 的真实兼容级别枚举、LanguageFeatures 扫描和实际 ASM 版本检查配置、字节码特征及必需隔离声明。

Forge 50 固定的 Mixin 0.8.5 不认识 `JAVA_21` 配置值，因此此模块声明 `JAVA_17` 兼容特征集；主运行及 javac 仍为 Java 21，class major 仍为 65。Mixin 官方实现允许较新编译器生成、但未使用超出声明特征集的类，同时要求实际 ASM 能解析其 class 版本。构建检查不替代专服中必需 Mixin 的真实注入验收。

主函数检查位于独立 smoke 源集，不伪装成 JUnit。Forge 原始事件传输不使用 Fabric/Neo 的 typed payload，因此改用专属 raw-payload 检查，未删除 payload 检查门槛。首次构建若暴露 Forge 初始化要求，应修正真实引导流程并保留失败，不能跳过检查。

网络回调只接受原入站 PLAY 阶段，捕获原 Connection 和 PacketListener，在逻辑主线程重新核对身份及存活。客户端桥由仅限物理客户端的 FML 事件订阅器注册；异步探测完成后再次核对本地监听器与传输监听器，没有把 Forge 远端模组列表当作可信设备证明。共享 pending 隔离、nonce、设备策略和命令门禁保持原实现。

本文件说明实现和构建入口，不表示已经编译或通过游戏验收。实际产物哈希、构建日志、专服与客户端结果须由后续独立记录证明。
