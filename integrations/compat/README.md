# 独立第三方兼容补丁

此目录的工具为明确固定的第三方发布包生成独立兼容副本。生成物不是 QiZhangVerdict 的 GPL 插件／模组，也不是上游官方更新。不要与相同模组 ID 的官方 JAR 同时安装；没有逐组合运行证据时不能宣称可用。

`patch_antixray116.py` 只接受 SHA256 `7c8d22a2e9c8d0f88a33ce76cdb7bade18c63bb2a5cc9b3a11991bd28c742f43` 的官方 `anti-xray-mc1.16.5-1.1.0.jar`。它生成 `anti-xray-mc1.16.5-1.1.0-qzcompat.1.jar`，保留 `antixray` ID，并明确更改显示名和版本。

算法和 32 个 class 的原字节均不改变。唯一逻辑修复是向 refmap 的两个命名空间补同一映射：`lambda$scheduleChunkLoad$14` → `Lnet/minecraft/class_3898;method_17256(Lnet/minecraft/class_1923;)Lcom/mojang/datafixers/util/Either;`。Mojang 1.16.5 官方 server mappings、Fabric intermediary 和实际运行时构造调用位置三者对应；原问题见[官方 issue #48](https://github.com/DrexHD/AntiXray/issues/48)，原失败记录见[本地测试报告](../../docs/legacy-fabric116-antixray110-java17.md)。

输出 ZIP 使用排序后的条目、固定 1980 时间、固定权限及无压缩存储，不依赖 zlib 版本或输入文件时间。原嵌套 JAR、Mixin 必需检查和默认配置均保留原字节。工具拒绝错误输入哈希、已存在的输出和错误输出文件名，并生成逐条目差异与 SHA256 回执。

当前工具另在写入前拒绝输出与回执的同路径及 Windows 路径别名；[5 项 CLI 检查](../../outputs/compat-patch-cli-validation.json)确认拒绝时没有残留输出，正常生成的 JAR 仍与下方历史运行版本逐字节一致。历史运行报告保存的是当时工具的原始 SHA256；后续路径预检没有改写这些记录。

示例（只运行 Python，不启动 Java）：

```powershell
python -B integrations/compat/patch_antixray116.py --input E:\CodexTemp\QiZhangVerdict\legacy-integration-research\binary-audit-01\jars\anti-xray-mc1.16.5-1.1.0.jar --output E:\CodexTemp\QiZhangVerdict\legacy-fabric-antixray\compat-artifact-01\anti-xray-mc1.16.5-1.1.0-qzcompat.1.jar --receipt E:\CodexTemp\QiZhangVerdict\legacy-fabric-antixray\compat-artifact-01\receipt.json
```

实际上游嵌入许可与[精确源提交的 LICENSE](https://github.com/DrexHD/AntiXray/blob/a113ce0b0616052de80ca8719986a09849348ce0/LICENSE)均为 MIT（SHA256 `109d6d2b31d28899e2a4e017341ab1ea5f5cf670a866e2bac538e8a5683e2f00`）。原 `fabric.mod.json` 却声明 CC0-1.0；兼容副本保留这一原始字段，在新增 `NOTICE_QIZHANG_COMPAT.txt` 中明确矛盾、真实来源、变更和非官方身份，保留原 MIT 正文。映射和元数据修改也按 MIT 提供；此 Python 工具自身遵循本仓库 GPL-3.0-only 许可。

补丁生成成功只证明输入和确定性变更检查通过，不能代替严格默认策略下的专服启动、配套报告、命令隔离、实际区块坐标混淆和正常退出测试。旧版 pins／lock 及官方缓存均不由此工具修改。

本次输出 SHA256 为 `fa72bb5e4424bc8ffb9cda83298f8c27b704dd36c3bd413660a3a58d69cc9484`。固定 Fabric 1.16.5 / Java 17 的实际结果、三轮 QA 历史与最终受控位置验收见[独立集成报告](../../docs/legacy-fabric116-antixray-qzcompat1-java17.md)。该结论只适用于报告中的版本、配置和检查范围。
