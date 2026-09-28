# Fabric 1.17.1 GUI 初始化故障：只读调查

结论：尚未确立根因。首轮 Guard GUI 失败必须保留；无 Guard 对照及相同成品复测通过也分别保留。

| 尝试 | reload→连接 | reload→blocks atlas | modelGroups 空指针 | 结果 |
|---|---:|---:|---:|---|
| candidate-44-01 | 0.191s | 6.040s | 7 次 | client -1 / server0 |
| no-guard-01 | 0.158s | 3.918s | 0 次 | 对照观察90.0227s，双0 |
| candidate-44-02 | 0.170s | 3.486s | 0 次 | 原13策略/44规则，报告后60.2047s，双0 |

首异常发生在22:40:20.422：ClientboundSectionBlocksUpdatePacket 更新触发 ModelManager.requiresRender，而 modelGroups 尚为null。随后22:40:23.357才出现 Indigo model=null 崩溃；崩溃记录initial reload Finished: No。因此不能只把最后一层Indigo栈当作根因。

三轮都用--server在资源初载开始后约0.16–0.19秒自动连接。失败轮atlas较慢；对照与相同产品复测均成功，支持“初始化时序窗口相关”的判断，但不足以证明Guard是或不是诱因。Guard未打包渲染资源，唯一Mixin为命令门禁；客户端入口不调用模型或reload写API。不过服务端严格隔离确会设置旁观者并逐tick发送位置包，可能改变早期PLAY时序，不能凭没有Guard栈就排除影响。

日志没有失败轮challenge/send/accept/model-apply完成的精确时间点。失败脚本未确认设备关联不等同于报告从未发送。三轮共同的offline auth401不能解释差异。随机出生点/调度也未完全一致。candidate02原始formalAcceptancePassed仍为false，人工画面审阅由父任务单独记录，此诊断不改原报告。

若将来复发，可在独立诊断中保留同一JAR与默认策略，先等正常主菜单/初始资源重载完成再连接，并仅记录握手阶段元数据时间戳；不收集payload、设备值或scope。这是区分启动时序的实验，不会使旧失败变成成功。

investigation.json包含原文件哈希、逐事件时序、精确官方mapping依据及源码哈希。未启动Java，未读state/GUID/scope，未修改仓库或原夹具。
