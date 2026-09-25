# 开发预览包的明确清单打包

[package_preview.py](../scripts/package_preview.py) 为旧版 `0.2.0-dev` 预览包提供独立入口，不改动既有发行脚本，不上传或创建 GitHub/GitLab Release。`verify` 只校验；`package` 在新目录中生成安装 ZIP、源码 ZIP、清单与哈希。

## 清单格式

清单须先提交到仓库。顶层恰好包含 `schemaVersion`、`packageName`、`artifacts`、`documents`、`evidence` 五个字段；每项文件引用恰好包含 `path`、`sha256`、`bytes`。`schemaVersion` 为 `1`。`packageName` 以 `QiZhangVerdict-` 开头，例如 `QiZhangVerdict-0.2.0-dev-preview.1`。

| 数组 | path 内容 | 安装包位置 | 校验来源 |
| --- | --- | --- | --- |
| artifacts | `platforms/.../build/libs/*.jar` 或 `bukkit/build/libs/*.jar` 原始构建产物 | JAR 原文件名 | 实际文件 SHA-256、大小、ZIP CRC 与嵌入许可 |
| documents | 明确列出的 README、说明、目录表等仓库路径 | 保留仓库路径 | 指定提交的 Git blob |
| evidence | 明确列出的 `outputs/...` 公开结果、日志、PNG | 保留仓库路径 | 指定提交的 Git blob，工作区须逐字节一致 |

`documents` 必须显式列出 `LICENSE`、`NOTICE`。不支持通配符、目录整体复制、绝对文件引用、反斜杠、`..`、重复输入、重名包内文件。SHA-256 必须是 64 位小写十六进制，`bytes` 为非负整数。草稿状态、发布说明、尚缺证据等备注放在清单之外；重复 JSON 键也会被拒绝。

全部清单引用都验证 SHA/大小。工具只收集清单明确列出的文件，不追随报告正文中的原始缓存路径；报告内的公开附件也应展开到 `evidence` 数组。制作清单时先做公开附件及 Markdown 链接闭包审核，避免漏收附件。账号状态、世界、设备安装标识以及完整 Minecraft 类反汇编不应进入公开清单。

## 固定提交与许可

执行时提供完整的小写 Git commit 对象 ID，禁止 `HEAD`、分支名、标签或缩写。清单、文档和证据必须在该提交中，工作区内容须与其对应。文档和清单允许仅 CRLF/LF 差异，实际打包始终使用提交中的字节；证据不允许任何字节差异。因此文档 SHA/大小应由将要提交的 Git blob 计算，证据使用原始文件字节。

每个运行 JAR 必须包含至少一个 class，ZIP CRC 正常，无重复/越界 ZIP 条目，`LICENSE`、`NOTICE` 必须与指定提交完全一致，JAR manifest 的 `License` 必须为 `GPL-3.0-only`。这里验证交付字节及许可标识；运行验收由列入清单的真实证据提供，打包本身不产生兼容性或可复现构建结论。

源码 ZIP 由该提交的全部已跟踪 blob 生成，保留可执行文件标记；不会读取未跟踪源目录或当前工作区中的改动。提交中的符号链接、子模块、已知缓存/运行目录及账号状态文件会被拒绝。源码 ZIP 与安装包的明确文件清单分别处理：源码快照可以保留该提交已有的公开历史证据。

## 使用

在仓库根目录运行，替换下面的清单路径、完整提交号与新输出目录：

```powershell
python scripts/package_preview.py verify --manifest outputs/preview-manifest.json --commit FULL_REVIEWED_COMMIT --output-root outputs/preview-packages
python scripts/package_preview.py package --manifest outputs/preview-manifest.json --commit FULL_REVIEWED_COMMIT --output-root outputs/preview-packages
```

也可通过 `--repository` 指定另一个仓库根目录。工具只运行本地 Git 读取与 Python 文件/ZIP 操作，不启动 Java、构建或网络发布。

输出包括：

- `<packageName>/`：明确列出的文件、`preview-manifest.json`、`packaging-summary.json`、`SHA256SUMS.txt`。
- `<packageName>.zip`：安装包。
- `<packageName>-sources.zip`：指定提交的源码快照。
- `<packageName>-packaging.json`：完整提交号、输入清单 SHA、收集文件与两个 ZIP 的 SHA/大小。

任意同名目录（包括空目录）、ZIP 或打包记录已存在就拒绝，工具不会覆盖或删除。输入路径及输出路径的已存在祖先会检查符号链接和 Windows 重解析点。校验完成后的字节快照用于打包，避免读取过程中源文件变化造成混包。若过程中发生 I/O 失败，留下的部分输出应保留供检查，重新尝试时使用新的包名/目录。

## 本次工具验证

[工具验收记录](../outputs/package-preview-tool-validation.json) 记录 24 项隔离样例检查：文档/清单/证据/构建产物漂移，证据换行漂移，越界路径，错误 SHA/大小，重名产物，未提交证据，错误 GPL 文件，非法 JAR，真实 Windows junction，已有空目录/ZIP，重复打包和已跟踪账号状态拒绝，顶层非对象及布尔 schemaVersion 拒绝，以及固定提交源码与二进制白名单的正向校验。

样例仓库、测试脚本和合成 ZIP 全部位于 `E:\CodexTemp\QiZhangVerdict\preview-packaging-tests`。没有使用产品 JAR 生成正式预览包，没有发布，也没有启动 Java。记录中的源码提交和 JAR 是专门的合成夹具。
