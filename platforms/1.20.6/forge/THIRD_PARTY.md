# 第三方构建材料

`gradlew`、`gradlew.bat`、`gradle/wrapper/gradle-wrapper.jar` 从固定的 [Forge 1.20.6-50.2.0 官方 MDK](https://maven.minecraftforge.net/net/minecraftforge/forge/1.20.6-50.2.0/forge-1.20.6-50.2.0-mdk.zip) 原字节提取；下载文件的官方 SHA-1 与 ZIP CRC 已核验。

- MDK SHA-256：`de036a47e541d309a8158449ffdf846039ee79852fcf52e2af969cc591295683`。
- wrapper 使用 Apache-2.0；[许可原文](third-party/gradle-wrapper-LICENSE.txt)直接提取自 wrapper JAR 的 `META-INF/LICENSE`，脚本内的版权头保留。
- 保留 MDK 的 [原 LICENSE 告示](third-party/forge-mdk-LICENSE.txt)与[原 CREDITS](third-party/forge-mdk-CREDITS.txt)，不将这些第三方材料改标 GPL。
- `gradle-wrapper.properties` 沿用官方 MDK 的 Gradle 8.12.1 地址，并新增官方发行 ZIP 的 SHA-256 固定值 `8d97a97984f6cbd2b85fe4c60a743440a347544bf18818048e611f5288d46c94`。

Forge/FML/ForgeGradle 实现只作为依赖及缓存中的官方 API 核查来源，没有复制到首方生产源码或打入模组 JAR。首方适配实现继续使用仓库明确的 GPL-3.0-only。
