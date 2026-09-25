# 1.21.11 Fabric / NeoForge 静态制品审查

未发现制品或39规则动态日志判据的阻断问题。

| 成品 | SHA256 | 字节 |
| --- | --- | --- |
| Fabric | `732ba77c6978785a8969c6f92476b8c57009be464b9210bfef2c9bb19c0d6ce5` | 97169 |
| NeoForge | `47dc8edff5faeb9c41ce19575bd37f49a2205877d99f814aa7acc33c0440d789` | 95394 |

两端binary和sources JAR的ZIP CRC、LICENSE/NOTICE及版本均通过；各29个首方类均major65，无测试类、Minecraft类或第三方嵌套JAR。Fabric描述符精确MC1.21.11/Java>=21；Neo声明MC[1.21.11]和Neo[21.11.45,21.12)，没有单独javaVersion字段，实际最低Java21由class65与JAVA_21 mixin确立。两端已编译的39行默认与TSV完全相同。

Fabric refmap 的 Commands.performCommand → ee.a → class_2170.method_9249 完整签名经官方SHA校验映射和真实server类文件确认；Neo具名目标亦存在于官方映射及Neo开发类文件。两端编译注解保留HEAD/cancellable/require1，配置required/defaultRequire1；Neo没有refmap，未把静态验证冒称运行时注入/玩家隔离成功。

构建编排：Fabric独立smoke源集挂3项JavaExec；Neo通过官方unitTest.enable/testedMod + JUnit5.13.4执行命令与codec的2项测试，dispatch9项仍JavaExec；没有放宽标准Test任务。最终06-combined源码稳定、旧18制品和两端binary/sources哈希不变、exit0；Fabric3组重新执行。Neo test在06为FROM-CACHE，实际FML引导与2项JUnit零失败零跳过证据保留在05。

日志检查从传入TSV动态计数、完整逐行序号/ID/action/控制项/唯一末汇总，且必须进程exit0。已存9项纯Python回归与当前脚本SHA一致。exact-JAR核心99另由主任务验证，不能与这三组构建检查混为一谈。

审查初次遇到根构建脚本调整及06构建中sources.jar短暂输出，均保留为审查窗口记录；最终只接受06退出后的固定字节。缓存布局的旧观察已通知根任务迁移，未进入制品。完整来源、编译注解、SHA及日志索引见 [result.json](result.json)。本审查未运行Java/Gradle/MC，也未修改源码、历史证据或发布包。
