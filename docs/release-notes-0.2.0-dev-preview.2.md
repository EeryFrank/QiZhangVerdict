# 七章的裁决 0.2.0-dev-preview.2

- 新增 Forge 1.8.9 客户端/专服模组；原 preview.1 的七个旧版模组及 Bukkit 0.1.1 插件保持原字节，共九个 JAR，不重构建或改写内部版本。
- 1.8.9 Forge→Forge、Forge→Paper 1.8.8 两轮分别在报告获准后在线 65.157 / 65.213 秒，严格默认策略、设备关联、正常图形和双方退出码 0 通过。两轮本机隔离客户端设置 `config/splash.properties` 的 `enabled=false`；初始图形失败和两次无 Verdict 对照完整保留。
- 这是 1.8.9 客户端连接 Paper 1.8.8 的实测，不是原生 Forge 1.8.8 模组交付。
- 附旧版第三方依赖候选及输入验证，尚无这些旧版组合的运行、防透视启用或检测效果验收。
- 附 Grim 实际触发→Verdict 设备联动的最终第三次 run36120803733 报告：两版现代插件服 trigger/restart 共 24 组通过；前两次夹具失败保留。只有应用并验证联动配置后才有该行为，默认单独安装 Grim 不会自动执行 Verdict 封禁，结论不扩展到旧版候选。

安装及边界见 [preview.2 说明](preview-0.2.0-dev-preview.2.md)。1.20.1 / 1.21.1 继续优先使用 [GitHub 0.1.1-test.1](https://github.com/EeryFrank/QiZhangVerdict/releases/tag/v0.1.1-test.1) 或 [GitLab 0.1.1-test.1](https://gitlab.com/EeryFrank/QiZhangVerdict/-/releases/v0.1.1-test.1) 对应模组。本包的旧版开发预览不替换它们。

许可 GPL-3.0-only。设备/VM 信息属于客户端自报，不能保证封锁所有外挂、透视或虚拟机。31 ID 扩展目录仍是可选规则，不会默认全量导入。原 preview.1、0.1.1 标签和附件保持不变。

详细证据见 [1.8.9 正式客户端报告](../outputs/legacy-client-matrix/1.8.9-0.2.0-dev-gpl/acceptance.json)与 [Grim 实际联动报告](../outputs/grim-linked-ban-validation.json)。安装包的 `preview-manifest.json`、`packaging-summary.json` 和 `SHA256SUMS.txt` 分别记录明确文件白名单、最终完整源码提交与文件校验值；对应源码 ZIP 保留相同提交。
