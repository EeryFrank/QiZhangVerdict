# SPDX-License-Identifier: GPL-3.0-only
"""Bounded offline log/source comparison. Never reads private state or runs Java."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,re,hashlib,zipfile
BASE=Path(r'E:\CodexTemp\QiZhangVerdict\compat-1.17.1')
RUNS=BASE/'client-fixtures/fabric-1.17.1/runs'
ROOT=Path(r'E:\Codex_work\QiZhangVerdict')
OUT=BASE/'fabric-gui-investigation-01';OUT.mkdir(exist_ok=False)
TZ=timezone(timedelta(hours=9))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pin(p):return {'path':str(p),'sha256':sha(p),'bytes':Path(p).stat().st_size}
def save(name,data):
 with (OUT/name).open('x',encoding='utf8',newline='\n') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
def scrub(s):
 s=re.sub(r'(?i)\b[0-9a-f]{32,}\b','<opaque-hex-redacted>',s)
 return re.sub(r'(?i)\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b','<uuid-redacted>',s)
def parse_events(text):
 events=[]
 for match in re.finditer(r'<log4j:Event\b([^>]+)>(.*?)</log4j:Event>',text,re.S):
  attrs=dict(re.findall(r'(\w+)="([^"]+)"',match.group(1)));body=match.group(2)
  msg=re.search(r'<log4j:Message><!\[CDATA\[(.*?)\]\]></log4j:Message>',body,re.S)
  throwable=re.search(r'<log4j:Throwable><!\[CDATA\[(.*?)\]\]></log4j:Throwable>',body,re.S)
  ms=int(attrs['timestamp'])
  events.append({'epochMillis':ms,'localTime':datetime.fromtimestamp(ms/1000,TZ).isoformat(),'level':attrs['level'],'logger':attrs['logger'],'thread':attrs['thread'],'message':msg.group(1) if msg else '', 'throwable':throwable.group(1) if throwable else '', 'sourceLine':text[:match.start()].count('\n')+1})
 return events
cases=[];raw={};first_stack=None
for attempt in ('candidate-44-01','no-guard-01','candidate-44-02'):
 p=RUNS/attempt;result=json.loads((p/'result.json').read_text(encoding='utf8'));raw[attempt]=result
 text=(p/'client-console.log').read_text(encoding='utf8',errors='replace');events=parse_events(text)
 reload=next(e for e in events if e['message'].startswith('Reloading ResourceManager:'))
 connect=next(e for e in events if e['message'].startswith('Connecting to'))
 blocks=next(e for e in events if 'blocks.png-atlas' in e['message'])
 particles=next(e for e in events if 'particles.png-atlas' in e['message'])
 model=[e for e in events if 'this.field_20278' in e['throwable']]
 indigo=[e for e in events if 'Tesselating block in world - Indigo Renderer' in e['throwable']]
 if model and first_stack is None:first_stack={'attempt':attempt,'time':model[0]['localTime'],'sourceLine':model[0]['sourceLine'],'throwable':scrub(model[0]['throwable'])}
 selected=[]
 for e in events:
  if e in [reload,connect,blocks,particles] or e in model or e in indigo or e['message']=='Stopping!' or e['message']=='Failed to verify authentication':
   label=('initial-resource-reload' if e==reload else 'automatic-connect' if e==connect else 'blocks-atlas-created' if e==blocks else 'particles-atlas-created' if e==particles else 'model-groups-null' if e in model else 'indigo-model-null' if e in indigo else 'normal-stop-request' if e['message']=='Stopping!' else 'offline-authentication-401')
   selected.append({k:e[k] for k in ('epochMillis','localTime','level','logger','thread','sourceLine')}|{'event':label,'secondsFromInitialReload':(e['epochMillis']-reload['epochMillis'])/1000})
 server=(p/'server-console.log').read_text(encoding='utf8',errors='replace');server_events=[]
 for i,line in enumerate(server.splitlines(),1):
  if any(x in line for x in ('logged in with entity id','joined the game','lost connection:','left the game','QiZhangVerdict sessions=')):
   server_events.append({'sourceLine':i,'line':scrub(line)})
 case={'attempt':attempt,'role':'no-Guard diagnostic control' if attempt.startswith('no-guard') else 'candidate GUI attempt','inputs':[pin(p/x) for x in ('result.json','client-console.log','server-console.log')],'result':{'passed':result['passed'],'formalAcceptancePassed':result.get('formalAcceptancePassed'),'clientExitCode':result['clientExitCode'],'serverExitCode':result['serverExitCode'],'elapsedSeconds':result['elapsedSeconds'],'onlineObservationSeconds':result.get('onlineObservationSeconds'),'baselineObservationSeconds':result.get('observedSeconds'),'strict13DefaultsUnchanged':result.get('strict13DefaultsUnchanged'),'defaultCatalogRulesUnchanged':result.get('defaultCatalogRulesUnchanged'),'exactSyntheticUUIDAndScopedDeviceAssociation':result.get('exactSyntheticUUIDAndScopedDeviceAssociation'),'survivalModeConfirmed':result.get('survivalModeConfirmed'),'exactCandidateBytesUnchanged':result.get('exactCandidateBytesUnchanged')},'timeline':selected,'serverTimeline':server_events,'reloadToConnectSeconds':(connect['epochMillis']-reload['epochMillis'])/1000,'reloadToBlocksAtlasSeconds':(blocks['epochMillis']-reload['epochMillis'])/1000,'reloadToParticlesAtlasSeconds':(particles['epochMillis']-reload['epochMillis'])/1000,'modelGroupNullCount':len(model),'indigoCrashEventCount':len(indigo),'authentication401Count':sum('Status: 401' in e['throwable'] for e in events),'firstNullBeforeBlocksAtlasSeconds':(blocks['epochMillis']-model[0]['epochMillis'])/1000 if model else None,'crashReportedInitialReloadUnfinished':'\tFinished: No' in text}
 cases.append(case)
# Explicit control-comparability checks, not a claim that all runtime timing/world state is identical.
helpers=['legacy117_client_runtime.py','legacy117_client_smoke.py','legacy117_mod_smoke.py','next_client_runtime.py','next_client_smoke.py']
helper_equal={name:len({sha(RUNS/a/name) for a in raw})==1 for name in helpers}
assert all(helper_equal.values())
assert raw['candidate-44-01']['basePlan']==raw['candidate-44-02']['basePlan']==raw['no-guard-01']['basePlan']
for flag in ('strict13DefaultsUnchanged','defaultCatalogRulesUnchanged','exactSyntheticUUIDAndScopedDeviceAssociation','survivalModeConfirmed','exactCandidateBytesUnchanged'):assert raw['candidate-44-02'][flag] is True
assert raw['candidate-44-02']['onlineObservationSeconds']>=60
assert raw['candidate-44-01']['formalAcceptancePassed'] is False and raw['candidate-44-02']['formalAcceptancePassed'] is False
jar=ROOT/'platforms/1.17.1/fabric/build/libs/qizhangverdict-fabric-1.17.1-0.6.0-dev.jar'
assert sha(jar)=='bda006d24663acb3698c8fb76d06d14220dfca18422c8eb9177499f5c498e497'
with zipfile.ZipFile(jar) as z:
 rendering_resources=[n for n in z.namelist() if n.startswith(('assets/','data/'))]
 mixins=json.loads(z.read('qizhangverdict.mixins.json'))['mixins']
assert not rendering_resources and mixins==['CommandGate117Mixin']
mapfile=Path(r'E:\CodexTemp\Gradle\QiZhang_Games\caches\fabric-loom\1.17.1\loom.mappings.1_17_1.layered+hash.40545-v2\mappings.tiny')
want={'field_20278','class_1092','class_1087','class_2637','method_21611','method_21596','method_30621','method_4708'}
mapping_lines=[];owner=''
for line in mapfile.read_text(encoding='utf8').splitlines()[1:]:
 if line.startswith('c\t'):owner=line
 if any('\t'+w+'\t' in line for w in want):mapping_lines.append({'owner':owner,'mapping':line})
source_files=['platforms/1.17.1/fabric/src/main/java/cn/qizhang/guard/fabric/GuardFabricClient.java','platforms/1.17.1/fabric/src/main/java/cn/qizhang/guard/fabric/GuardFabric.java','platforms/shared/src/main/java/cn/qizhang/guard/minecraft/MinecraftGuard.java','client-common/src/main/java/cn/qizhang/guard/client/ClientReporter.java']
sources=[pin(ROOT/n) for n in source_files]
report={'schemaVersion':1,'investigationCompletedUtc':datetime.now(timezone.utc).isoformat(),'scope':'Read-only existing XML/server logs and exact product/official mappings. No Java, no state/GUID/scope reads, no product/helper/fixture edits.','rootCauseEstablished':False,'candidateArtifact':pin(jar),'comparability':{'sameBasePlanRecord':True,'executedHelpersByteIdentical':helper_equal,'sameProductAcrossCandidateAttempts':True,'sameSelectedGraphicsOptions':True,'sameServerSeedViewDistanceAndGamemode':True,'spawnPositionsDiffer':True,'freshRunWorldAndSchedulingStateNotByteIdentical':True},'cases':cases,'firstInitializationException':first_stack,'mappingEvidence':{'mappingInput':pin(mapfile),'specificMappings':mapping_lines,'completeMappingsCopied':False},'sourceEvidence':{'files':sources,'renderAssetsOrModelsBundled':False,'onlyProductMixin':mixins,'directModelOrResourceReloadMutationFound':False,'clientEntryBehavior':'Copies a bounded challenge, queues an owner/PLAY-checked callback, reads mod IDs and selected-pack IDs, delegates asynchronous report probing, then sends only if original live connection still matches.','reportWorkerBehavior':'Runs probe/device calculation on a dedicated worker; response send is scheduled back to the client thread. No model/reload API is called.','serverIsolationBehavior':'JOIN sets SPECTATOR while required report is pending; END_SERVER_TICK resets camera and sends teleport each tick until acceptance/disconnect. These are real changes to PLAY traffic/timing, so Guard cannot be exonerated solely from an Indigo stack.'},'findings':[{'confidence':'observed','text':'The first failure is seven ModelManager.modelGroups null dereferences while applying ClientboundSectionBlocksUpdatePacket, not the later Indigo renderer model-null crash.'},{'confidence':'observed','text':'Failed attempt starts networking 0.191 seconds after initial reload, then the first modelGroups error occurs 4.888 seconds after reload and 1.152 seconds before the first blocks-atlas creation log; crash report says initial reload Finished: No.'},{'confidence':'observed','text':'The baseline and unchanged-product retry also auto-connect during initial reload. They create blocks atlases sooner (3.918 and 3.486 seconds after reload versus 6.040) and have no modelGroups/Indigo failures.'},{'confidence':'observed','text':'Offline authentication 401 occurs in all three and is not a distinguishing failure.'},{'confidence':'inference-not-root-cause','text':'The correlated evidence points to PLAY updates arriving while render models are still uninitialized. It does not determine why the first reload was slower or whether Guard isolation/reporting changes contributed to the timing window.'},{'confidence':'evidence-limit','text':'Failure logs have no explicit challenge-dispatch, client-report-send, acceptance, or model-apply completion timestamps. Absence of an association success in the failed helper result does not prove the report was never sent.'},{'confidence':'evidence-limit','text':'One no-Guard pass and one unchanged-product pass establish a successful control and successful retry; they do not erase the initial product-installed failure or establish a purely upstream root cause.'}],'suggestedNextStepIfFailureRecurs':'Preserve the same JAR/default policy and use a separate diagnostic run that opens the client normally, waits for initial resource loading/main-menu readiness, then connects. Record load, connect, challenge/send/accept metadata timestamps without payload/device/scope values. Such a run diagnoses launch timing; it does not replace or relabel the failed automatic-connect evidence.','privacy':{'privateStateFilesRead':False,'machineGuidRead':False,'scopeFilesRead':False,'deviceValuesGeneratedOrPrinted':False,'resultAssociationInspectedAsBooleansOnly':True},'javaInvoked':False,'repositoryWritten':False,'existingEvidenceOverwritten':False}
save('investigation.json',report)
md='''# Fabric 1.17.1 GUI 初始化故障：只读调查

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
'''
(OUT/'investigation.md').write_text(md,encoding='utf8')
print(json.dumps({'report':str(OUT/'investigation.json'),'sha256':sha(OUT/'investigation.json'),'bytes':(OUT/'investigation.json').stat().st_size,'rootCauseEstablished':False,'cases':len(cases),'javaInvoked':False},indent=2))