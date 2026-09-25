# Minecraft 1.12.2 Forge 开发适配

`platforms/1.12.2` 是独立的 **GPL-3.0-only、0.2.0-dev** 工程。2026-09-25 已完成正式重混淆 JAR 构建及原生 Java 8 回归；随后[独立专服通过 13 项真实 TCP 检查](legacy-mod-validation-1.12.2-gpl.md)。真实图形客户端和 Bukkit 配套联机仍须分别验证。它不属于冻结的 0.1.1 五个发布安装包。

## 构建与检查

固定 Minecraft 1.12.2、Forge 14.23.5.2864、ForgeGradle 3.0.197、Gradle 5.6.4、MCP snapshot `20171003-1.12`。采用该版本[官方 Forge MDK](https://maven.minecraftforge.net/net/minecraftforge/forge/1.12.2-14.23.5.2864/forge-1.12.2-14.23.5.2864-mdk.zip)的构建代际，不能用现代平台的 Java 21 命令直接运行。MDK 和 Forge 源包已核对官方 SHA1，Gradle 发行包固定 SHA256；依据在 `platforms/1.12.2/api-evidence.json`。

构建、编译与检查均实际使用 Temurin **JDK 8u504-b01**。检查结果：

- 55 项共享核心安全回归通过。
- 生产解析器加载 31 条可选目录规则，并保留 ALERT 和正常模组边界。
- 客户端报告器验证同服标识稳定、跨服 scope 隔离、异步探测、协议往返、旧回调抑制及 20 次快速重载合并。
- 13 项旧命令测试验证真实 `CommandBase.checkPermission` 的非管理员拒绝和管理员允许，以及冒号 ID、含空格 GLOB／理由、页数与非法参数。
- 正式 JAR 的 31 个类均为 major 52（Java 8）；无 Minecraft／Forge 类被复制打包。二进制及 sources JAR 均包含与项目根相同的 LICENSE / NOTICE。

最终产物及构建日志散列见 [Java 8 构建记录](../outputs/legacy-mod-build-1.12.2-gpl.json)。初次尝试的 Gradle 5 不支持把 `javax.net.ssl.trustStore=NONE` 作为现代 Windows trust 配置使用；之后使用此 JDK 的默认可信证书存储构建成功，没有关闭 TLS 校验。最后一次构建同时验证了开发启动所需的 classes/resources 合并配置。

```powershell
$env:JAVA_HOME = 'E:\CodexTemp\QiZhangVerdict\toolchains\jdk8\jdk8u504-b01'
$env:GRADLE_USER_HOME = 'E:\CodexTemp\QiZhangVerdict\legacy-build\1.12.2\gradle-home'
$env:JAVA_TOOL_OPTIONS = ''
.\platforms\1.12.2\gradlew.bat -p platforms/1.12.2 --no-daemon --console=plain --max-workers=1 --project-cache-dir E:\CodexTemp\QiZhangVerdict\legacy-build\1.12.2\project-cache build
```

Linux/macOS 使用自己的 JDK 8 路径；开发运行目录默认放系统临时目录，可通过 `-PqzRuntimeRoot=...` 覆盖。

## 旧接口和防护边界

策略、账号/IP 配额、名单管理、关联封禁和 wire2 直接使用共享核心。报告器与服务器生命周期逻辑通过有预期计数的源码转换生成，不修改现代端文件。Java 8 有界读取保留原 128/256/1024/4096/8192 字节上限，随机安装 ID 保留 `CREATE_NEW`，nonce、scope、任务合并及连接归属检查不变。

1.12.2 使用大小写敏感的 **`QZGuard`** 原生频道，并在客户端进入 PLAY 后声明 `REGISTER`。没有使用会添加 discriminator 的 `SimpleNetworkWrapper`。官方旧 `ClientCustomPacketEvent` 是客户端接收、`ServerCustomPacketEvent` 是服务端接收；这与现代 Forge payload 事件命名不同。网络线程复制有上限的负载后，通过旧 Forge 的游戏线程调度接口处理；客户端最终回包再次检查原连接。

此版没有 Brigadier。独立 `CommandBase` 适配调用同一核心管理操作，权限为等级 3，保留冒号设备／规则 ID 和贪婪文本。利用官方可取消的 `CommandEvent` 在分发执行前拦截待验证玩家，包括 OP；没有假设旧 Forge 会自动初始化现代 Mixin。源码事件位置核对和命令单元回归都不能代替实际玩家指令门禁验收。

报告等待期使用旁观模式、固定位置和视角对象。若其他模组在待验证期更换玩家维度，本旧版适配会断开并恢复游戏模式；不会尝试套用现代跨维度传送接口。未知 IP 不伪装成回环地址；只有原版集成服本地主连接且名字匹配服主的情形沿用共享逻辑的本地映射。

构建通过不代表旧 Forge 握手、Bukkit 配套客户端、生产认证、混合端或全部玩法已经通过。设备和 VM 信号仍为可伪造的客户端自报。本阶段没有选定或验证 1.12.2 的 Grim、AntiXray 或其他行为／矿物混淆组合。
