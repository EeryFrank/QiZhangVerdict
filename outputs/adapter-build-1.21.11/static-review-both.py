from pathlib import Path
import json,runpy,tomllib,xml.etree.ElementTree as ET,zipfile,re
CACHE=Path(__file__).resolve().parent
g=runpy.run_path(str(CACHE/'review.py'));ROOT=g['ROOT'];cls=g['cls'];sha=g['sha'];pin=g['pin'];j=g['j']
report=j(CACHE/'result.json');neo=ROOT/'platforms/1.21.11/neoforge/build/libs/qizhangverdict-neoforge-1.21.11-0.4.0-dev.jar';build=CACHE.parent/'builds/05-neoforge-junit';receipt=j(build/'result.json');log=(build/'console.log').read_bytes()
assert receipt['exitCode']==0 and receipt['logSha256']==sha(log)
a=next(x for x in receipt['artifacts'] if x['path']==neo.relative_to(ROOT).as_posix());assert a['sha256']==sha(neo.read_bytes()) and a['bytes']==neo.stat().st_size
with zipfile.ZipFile(neo) as z:
 assert z.testzip() is None;names=z.namelist();assert len(names)==len(set(names))
 desc=tomllib.loads(z.read('META-INF/neoforge.mods.toml').decode());assert desc['license']=='GPL-3.0-only'
 assert desc['mods'][0]['modId']=='qizhangverdict' and desc['mods'][0]['version']=='0.4.0-dev'
 deps={d['modId']:d for d in desc['dependencies']['qizhangverdict']};assert deps['minecraft']['versionRange']=='[1.21.11]' and deps['neoforge']['versionRange']=='[21.11.45,21.12)'
 assert all(d['side']=='BOTH' and d['type']=='required' for d in deps.values())
 for n in ('LICENSE','NOTICE'):assert z.read(n)==(ROOT/n).read_bytes()
 assert 'License: GPL-3.0-only' in z.read('META-INF/MANIFEST.MF').decode()
 classes={n:cls(z.read(n)) for n in names if n.endswith('.class')};assert len(classes)==29 and {c['major'] for c in classes.values()}=={65}
 assert all(n.startswith('cn/qizhang/guard/') for n in classes) and not any('Smoke' in n or 'Test' in n or n.endswith('.jar') for n in names)
 mix=json.loads(z.read('qizhangverdict.mixins.json'));assert mix['required'] is True and mix['injectors']['defaultRequire']==1 and mix['compatibilityLevel']=='JAVA_21'
 assert mix['mixins']==['CommandGate12111Mixin'];assert not any('refmap' in n for n in names) and 'refmap' not in mix
 mc=classes['cn/qizhang/guard/minecraft/mixin/CommandGate12111Mixin.class'];anns=sum([v for k,v in mc['attributes'].items() if k.endswith('Annotations')],[]);ma=next(a for a in anns if a['type']=='Lorg/spongepowered/asm/mixin/Mixin;');assert ma['values']['value']==['Lnet/minecraft/commands/Commands;']
 handler=next(m for m in mc['methods'] if m['name']=='qizhangverdict$denyPendingCommand');anns=sum([v for k,v in handler['attributes'].items() if k.endswith('Annotations')],[]);inject=next(a for a in anns if a['type']=='Lorg/spongepowered/asm/mixin/injection/Inject;');v=inject['values'];assert v['method']==['performCommand(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)V'] and v['require']==1 and v['cancellable']==1 and v['at'][0]['values']['value']=='HEAD'
 defaults=next(f['attributes']['ConstantValue'] for f in classes['cn/qizhang/guard/core/Blacklist.class']['fields'] if f['name']=='DEFAULTS');rows=[x for x in defaults.splitlines() if x and not x.startswith('#')];assert rows==g['source_rows']
 dev=ROOT/'platforms/1.21.11/neoforge/build/moddev/artifacts/neoforge-21.11.45.jar'
 with zipfile.ZipFile(dev) as d:
  actual=cls(d.read('net/minecraft/commands/Commands.class'));method=next(m for m in actual['methods'] if m['name']=='performCommand' and m['descriptor']=='(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)V');assert method['access']&1
srcjar=neo.with_name(neo.stem+'-sources.jar')
with zipfile.ZipFile(srcjar) as z:
 assert z.testzip() is None
 for n in ('LICENSE','NOTICE'):assert z.read(n)==(ROOT/n).read_bytes()
 assert not any('Smoke' in n or 'Test' in n or n.endswith('.class') for n in z.namelist())
xml=ROOT/'platforms/1.21.11/neoforge/build/test-results/test/TEST-cn.qizhang.guard.neoforge.PlatformContractTest.xml';suite=ET.fromstring(xml.read_bytes());assert suite.get('tests')=='2' and all(suite.get(k)=='0' for k in ('skipped','failures','errors'))
assert {x.get('name') for x in suite.findall('testcase')}=={'administratorCommandTree()','boundedBukkitCompatiblePayload()'}
text=log.decode('utf-8',errors='replace');assert re.findall(r'^PASS client-dispatch (\d+):',text,re.M)==list(map(str,range(1,10)))
assert 'Starting FancyModLoader version 10.0.36 (DEDICATED_SERVER in DEV)' in text and 'Active FML loader' in text and 'BUILD SUCCESSFUL' in text
nb=(ROOT/'platforms/1.21.11/neoforge/build.gradle').read_text();assert 'unitTest {' in nb and 'testedMod = mods.qizhangverdict' in nb and "testImplementation platform('org.junit:junit-bom:5.13.4')" in nb and "sourceSets.test.java.srcDir rootProject.file('common/src/smoke/java')" in nb and 'useJUnitPlatform()' in nb and 'failOnNoDiscoveredTests' not in nb
relevant=['platforms/1.21.11/build.gradle','platforms/1.21.11/neoforge/build.gradle']+[p.relative_to(ROOT).as_posix() for folder in ('common','neoforge') for p in (ROOT/'platforms/1.21.11'/folder/'src').rglob('*') if p.is_file()]
assert all(sha((ROOT/p).read_bytes())==receipt['sourceSha256'][p] for p in relevant)
combined=CACHE.parent/'builds/06-combined';cr=j(combined/'result.json');clog=(combined/'console.log').read_bytes();assert cr['exitCode']==0 and sha(clog)==cr['logSha256'] and cr['sourcesUnchanged'] and cr['previousArtifactsUnchanged']
for p in (neo,srcjar,g['artifact'],g['srcjar']):
 a=next(x for x in cr['artifacts'] if x['path']==p.relative_to(ROOT).as_posix());assert a['sha256']==sha(p.read_bytes()) and a['bytes']==p.stat().st_size
ct=clog.decode('utf-8',errors='replace');assert ':neoforge:test FROM-CACHE' in ct
assert re.findall(r'^PASS fabric-client-dispatch (\d+):',ct,re.M)==list(map(str,range(1,13)))
report['additionalNeoForgeReview']={'passed':True,'blockingFindings':[],'artifact':pin(neo),'sourceJar':pin(srcjar),'zipCrcValid':True,'entries':len(names),'classes':29,'classMajors':[65],'firstPartyClassesOnly':True,'embeddedLicenseAndNoticeEqualRoot':True,'descriptor':desc,'javaRequirement':{'explicitJavaDescriptorFeature':None,'classFileMinimum':21,'mixinCompatibility':'JAVA_21','note':'Neo descriptor itself has no explicit javaVersion feature; class65, JAVA_21 mixins and fixed Neo loader establish the actual Java21 minimum.'},'mixin':{'required':True,'require':1,'cancellable':True,'head':True,'compiledMixinAnnotation':ma,'compiledInjectAnnotation':inject,'refmapAbsent':True,'namespace':'Mojang named','targetPresentInOfficialMappingsAndNeoDevClass':True,'devInput':pin(dev),'runtimeGateNotTestedByThisReview':True},'embeddedDefaults':report['embeddedDefaults'],'existingBuildEvidence':{'result':pin(build/'result.json'),'log':pin(build/'console.log'),'exitCode':0,'sourceFilesStillMatch':True,'dispatchAssertions':9,'junit':{'xml':pin(xml),'tests':2,'failures':0,'errors':0,'skipped':0,'officialFMLBootObserved':True}},'scope':'Neo05 JUnit ran under actual official FML DEV bootstrap, not a real dedicated-server player session; source classes, not standalone exact-JAR runtime.'}
report['finalCombinedBuild']={'result':pin(combined/'result.json'),'log':pin(combined/'console.log'),'exitCode':0,'currentSourcesMatch':True,'bothBinaryAndSourcesJarsUnchanged':True,'previous18ArtifactsUnchanged':True,'fabricThreeSmokeGroupsReran':True,'neoJUnit':'FROM-CACHE; actual execution evidence stays in build05'}
report['scope']='Read-only Fabric+NeoForge product/source ZIP, class-file, Mixin mapping and build-source-set review; inspected final combined build06 and original actual executions03/05; no Java/Gradle/game launched by reviewer.'
report['reviewAttempts']=[pin(CACHE/'attempt-01-source-change.json'),pin(CACHE/'attempt-02-concurrent-output.json')]
report['boundaries']=['Static mapping existence and FML DEV JUnit success do not prove real-player command isolation or every production-loader route.','Exact-JAR core99 has its own parent-run evidence, not substituted by smoke/JUnit groups in this audit.','NeoJUnit actual execution is build05; build06 uses cached test result. Fabric smoke reran in build06.','No source files, historical evidence or release bytes were changed by reviewer.']
(CACHE/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(CACHE/'review.md').write_text('# 1.21.11 Fabric / NeoForge 静态制品审查\n\n未发现制品或39规则动态日志判据的阻断问题。\n\n| 成品 | SHA256 | 字节 |\n| --- | --- | --- |\n| Fabric | `'+sha(g['artifact'].read_bytes())+'` | 97169 |\n| NeoForge | `'+sha(neo.read_bytes())+'` | 95394 |\n\n两端binary和sources JAR的ZIP CRC、LICENSE/NOTICE及版本均通过；各29个首方类均major65，无测试类、Minecraft类或第三方嵌套JAR。Fabric描述符精确MC1.21.11/Java>=21；Neo声明MC[1.21.11]和Neo[21.11.45,21.12)，没有单独javaVersion字段，实际最低Java21由class65与JAVA_21 mixin确立。两端已编译的39行默认与TSV完全相同。\n\nFabric refmap 的 Commands.performCommand → ee.a → class_2170.method_9249 完整签名经官方SHA校验映射和真实server类文件确认；Neo具名目标亦存在于官方映射及Neo开发类文件。两端编译注解保留HEAD/cancellable/require1，配置required/defaultRequire1；Neo没有refmap，未把静态验证冒称运行时注入/玩家隔离成功。\n\n构建编排：Fabric独立smoke源集挂3项JavaExec；Neo通过官方unitTest.enable/testedMod + JUnit5.13.4执行命令与codec的2项测试，dispatch9项仍JavaExec；没有放宽标准Test任务。最终06-combined源码稳定、旧18制品和两端binary/sources哈希不变、exit0；Fabric3组重新执行。Neo test在06为FROM-CACHE，实际FML引导与2项JUnit零失败零跳过证据保留在05。\n\n日志检查从传入TSV动态计数、完整逐行序号/ID/action/控制项/唯一末汇总，且必须进程exit0。已存9项纯Python回归与当前脚本SHA一致。exact-JAR核心99另由主任务验证，不能与这三组构建检查混为一谈。\n\n审查初次遇到根构建脚本调整及06构建中sources.jar短暂输出，均保留为审查窗口记录；最终只接受06退出后的固定字节。缓存布局的旧观察已通知根任务迁移，未进入制品。完整来源、编译注解、SHA及日志索引见 [result.json](result.json)。本审查未运行Java/Gradle/MC，也未修改源码、历史证据或发布包。\n',encoding='utf-8')
print(json.dumps({'passed':True,'fabric':report['artifact'],'neo':report['additionalNeoForgeReview']['artifact'],'report':str(CACHE/'result.json'),'sha256':sha((CACHE/'result.json').read_bytes()),'blockingFindings':[]},indent=2))
