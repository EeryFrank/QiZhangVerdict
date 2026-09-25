# 待证作弊客户端与透视资源包标识复核（2026-09-25）

本轮复核现有目录的 8 个待证项目，**8 个均继续待证，不新增封禁规则**。另找到可交由维护者审核的 Wurst+3 精确 ID `wurstplusthree`。现有目录仍为 37 个 ID（33 DENY、4 ALERT），本轮没有修改目录、默认规则或已发布制品。

[机器可读报告](../outputs/catalog-pending-research-20260925.json) 保存逐项结论、官方 URL、固定提交、实际下载文本 SHA-256、访问失败以及证据边界。缓存只含公开文本与元数据，位于 `E:\CodexTemp\QiZhangVerdict\catalog\next-pending-audit`；缓存路径不是唯一来源依据。没有下载或运行作弊二进制，没有镜像整个源码仓库，也没有绕过访问限制。

| 项目 | 本轮核验到的官方材料 | 不生成规则的原因 |
| --- | --- | --- |
| Impact | [官网](https://impactclient.net/)及[功能页](https://impactclient.net/features)；固定 [Installer 源码](https://github.com/ImpactDevelopment/Installer/tree/acda0df9f296c59d1959380a1fc4d7f44e3ee323) | `net.impactclient.Impact` 是安装器生成的启动配置/组件身份，未证明是 Forge mod ID 或实际 brand；捆绑 Baritone 也不是其唯一身份。 |
| Inertia | [官网](https://inertiaclient.com/)与[FAQ](https://inertiaclient.com/faq)明确闭源；固定[旧问题库 README](https://github.com/THEREALWWEFAN231/Inertia-Issues/blob/d639b634fd4a1ab0eea1fcf7046b6abcae5c8b45/README.md) | 旧库只有说明及问题模板，链接的新仓库本次返回 404；未得到客户端描述符。 |
| Aristois | [已验证官网域名的 GitHub 组织](https://github.com/Aristois)；固定[网站源码](https://github.com/Aristois/aristois.github.io/blob/f19ae9db94783cf92d227730197f95ad3f9fa7af/index.html) | 官网本次读取失败；公开组织只有网站与 ForgeGradle 派生仓库。EMC 框架、构建工具和 Aristois 产品名都不能直接证明客户端唯一 ID。 |
| Future Client | [官方主页](https://www.futureclient.net/)公开战斗模块和版本平台表 | 功能及发行平台可确认，但本轮没有公开客户端描述符或实际发送 brand 的源码。没有登录用户区或下载付费制品。 |
| RusherHack | [官网](https://rusherhack.org/)；固定[示例插件描述符](https://github.com/RusherDevelopment/example-plugin/blob/986db6c411a4f2312672cbd3e8f790050c83d38f/src/main/resources/rusherhack-plugin.json)及[核心插件描述符](https://github.com/RusherDevelopment/example-core-plugin/blob/ea3b04c7161f334ac09c108b6bea5d9c22b4365d/src/main/resources/rusherhack-plugin.json) | `rusherhack-plugin.json` 是客户端内部扩展的元数据，不是宿主 Fabric/Forge 描述符，也不是玩家携带的服务端 Bukkit 插件；占位名称、Java 包名不能充当宿主 ID。 |
| CatLean | 原作者固定 [ThunderHack Recode README](https://github.com/Pan4ur/ThunderHack-Recode/blob/49c76bcc5a5e4fbd12b06305c09f0c8fb76c510b/README.md)介绍闭源后继 | 前作的 `thunderhack` 描述符只能证明前作，不能继承给 CatLean；后继的版本、ID 和许可均不能照搬。 |
| Raven b+ | [官方仓库 API](https://api.github.com/repos/kopamed/Raven-bPLUS)返回 HTTP 451，指向[固定公开 DMCA 通知](https://github.com/github/dmca/blob/e1a1b681152e64b28f2d2615bab87865f53e78aa/2025/07/2025-07-15-raven-b4.md) | 未绕道分叉、镜像或旧缓存取得受限源码。其它 Raven 分支的 `keystrokesmod` 不能据此认定为 b+ 的 ID；公开通知是权利主张及平台处理记录，不是本报告作出的侵权裁判。 |
| Xray Ultimate | 作者 Filmjolk 的[CurseForge 项目页](https://www.curseforge.com/minecraft/texture-packs/xray-ultimate-1-11-compatible)明确资源包用途和保留权利声明 | 项目号 `226375` 不是客户端上报的 pack ID；展示名和版本 ZIP 文件名可变，未证明跨版本稳定、唯一的已选资源包标识。未下载资源包。 |

版本与许可必须对应材料本身。Impact 官网列举 1.11.2 至 1.16.5 的若干具体版本；其安装器文件头声明 LGPL 2.1，不能据此给客户端本体定许可。Inertia 官网的 3.1.3 旧档列举 1.12.2、1.13.2、1.14.4、1.15.2、1.16.5，但描述符未核验。Future 官网对 1.20.1 等版本列出 Fabric，对 1.19.4 标注经 ViaFabric 使用，不能写成已证明原生 1.19.4 客户端。RusherHack 官网的 1.12.2–1.21.11 宣传范围也不证明所有中间版本均有原生构建；公开例子的许可证保留全部权利，公开 API 不等于客户端开源。逐项版本与来源见 JSON。

资源包还存在单独的上报边界。本项目现代 Fabric 客户端读取已选 pack 的 `getId()`，旧 1.8.9 客户端读取 `getResourcePackName()`；没有直接上报 CurseForge 项目号。即使以后取得官方资源包的 `pack.mcmeta`，也需另证其中的信息与实际上报值的对应关系，不能直接把下载文件名加入精确规则。相关本项目源文件及其哈希已记入报告。

**额外候选：Wurst+3 / `wurstplusthree`。** 官方仓库固定提交为 `4eca774c0998dfc06d2f378bf0d939b8ad59318c`，源码目标为 Forge 1.12.2。以下两个独立位置一致：

| 证据 | 固定文件 SHA-256 |
| --- | --- |
| [`mcmod.info` 的 `/0/modid`](https://github.com/WurstPlus/wurst-plus-three/blob/4eca774c0998dfc06d2f378bf0d939b8ad59318c/src/main/resources/mcmod.info) = `wurstplusthree`，版本 `0.7.0` | `daea23ca4c25a8bc92b4ca5ea079d7b74d38ca0cf0aa15517da8ab5626e58d6f` |
| [Forge `@Mod` 入口与 `MODID` 常量](https://github.com/WurstPlus/wurst-plus-three/blob/4eca774c0998dfc06d2f378bf0d939b8ad59318c/src/main/java/me/travis/wurstplusthree/WurstplusThree.java) | `3eb6160c48bcfc6821874976471f2200c42d0b56d7d307afaf1ca1107afdf9fb` |
| [KillAura 的目标选择与攻击调用](https://github.com/WurstPlus/wurst-plus-three/blob/4eca774c0998dfc06d2f378bf0d939b8ad59318c/src/main/java/me/travis/wurstplusthree/hack/hacks/combat/KillAura.java) | `fb0d39d5fd95ce917da26451044e7a57de184402bcec51d2f4dd22f07009f030` |
| [AGPL-3.0 许可证文本](https://github.com/WurstPlus/wurst-plus-three/blob/4eca774c0998dfc06d2f378bf0d939b8ad59318c/LICENSE.md) | `8486a10c4393cee1c25392769ddd3b2d6c242d6ec7928e1414efff7dfb2f07ef` |

该候选建议 `mod / wurstplusthree / DENY`，尚未导入。它不同于已收录 Wurst+2 的 `wurstplus`，精确匹配不会自动覆盖它。官方仓库已归档；本报告仅核验历史源码身份与功能，没有构建、执行、客户端联机或识别成功率测试，也没有把 AGPL 实现复制进产品。

现有待证条目的 `BRAND` 只是调查分类，不代表已经证明存在同名 `MC|Brand` / `minecraft:brand` 值。闭源也不能反推出“纯注入”实现方式。源码 ID 可被修改，不能据此承诺覆盖所有衍生作弊客户端或穷尽市场。本轮没有发现相关既有规则需要立即删除的证据，亦未重审全部 37 个已收录 ID。

Future 与 CurseForge 的公开页面可由浏览器读取，但本地普通 HTTP 请求返回 403。报告明确区分浏览器观察与错误响应哈希，未虚构页面原始字节哈希。Raven 的原始缓存回执因响应 JSON 缺少状态字段记为 0，报告依据同时保存的 `gh` 标准错误明确解释为 HTTP 451，保留原回执不改写。
