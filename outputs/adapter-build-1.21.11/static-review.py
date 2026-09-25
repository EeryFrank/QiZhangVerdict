from pathlib import Path
import collections,datetime,hashlib,io,json,re,struct,sys,urllib.request,zipfile
ROOT=Path(r'E:/Codex_work/QiZhangVerdict');CACHE=Path(__file__).resolve().parent
class Reader:
 def __init__(self,b):self.b=b;self.i=0
 def raw(self,n):v=self.b[self.i:self.i+n];assert len(v)==n;self.i+=n;return v
 def u1(self):return self.raw(1)[0]
 def u2(self):return int.from_bytes(self.raw(2),'big')
 def u4(self):return int.from_bytes(self.raw(4),'big')
def cls(raw):
 r=Reader(raw);assert r.u4()==0xcafebabe;minor=r.u2();major=r.u2();cp=[None]*r.u2();i=1
 while i<len(cp):
  t=r.u1()
  if t==1:cp[i]=r.raw(r.u2()).decode('utf-8',errors='replace')
  elif t==3:cp[i]=int.from_bytes(r.raw(4),'big',signed=True)
  elif t in (4,5,6):cp[i]=r.raw(8 if t in (5,6) else 4);i+=int(t in (5,6))
  elif t in (7,8,16,19,20):cp[i]=(t,r.u2())
  elif t in (9,10,11,12,17,18):cp[i]=(t,r.u2(),r.u2())
  elif t==15:cp[i]=(t,r.u1(),r.u2())
  else:raise AssertionError(t)
  i+=1
 def ann(q):
  a={'type':cp[q.u2()],'values':{}}
  for _ in range(q.u2()):
   name=cp[q.u2()];a['values'][name]=element(q)
  return a
 def element(q):
  t=chr(q.u1())
  if t in 'BCDFIJSZsc':return cp[q.u2()]
  if t=='e':return [cp[q.u2()],cp[q.u2()]]
  if t=='@':return ann(q)
  if t=='[':return [element(q) for _ in range(q.u2())]
  raise AssertionError(t)
 def attrs():
  out={}
  for _ in range(r.u2()):
   name=cp[r.u2()];b=r.raw(r.u4())
   if name in ('RuntimeVisibleAnnotations','RuntimeInvisibleAnnotations'):
    q=Reader(b);out[name]=[ann(q) for _ in range(q.u2())];assert q.i==len(b)
   elif name=='ConstantValue':
    value=cp[int.from_bytes(b,'big')];out[name]=cp[value[1]] if isinstance(value,tuple) and value[0]==8 else value
  return out
 access=r.u2();this=r.u2();superclass=r.u2();r.raw(2*r.u2())
 groups=[]
 for group in range(2):
  members=[]
  for _ in range(r.u2()):
   access=r.u2();name=cp[r.u2()];desc=cp[r.u2()];members.append({'name':name,'descriptor':desc,'access':access,'attributes':attrs()})
  groups.append(members)
 annotations=attrs();assert r.i==len(raw)
 return {'major':major,'class':cp[cp[this][1]],'fields':groups[0],'methods':groups[1],'attributes':annotations}
def sha(b):return hashlib.sha256(b).hexdigest()
def pin(p):return {'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size}
def j(p):return json.loads(p.read_text(encoding='utf-8'))
artifact=ROOT/'platforms/1.21.11/fabric/build/libs/qizhangverdict-fabric-1.21.11-0.4.0-dev.jar'
builddir=CACHE.parent/'builds/03-fabric-smoke-source-set';receipt=j(builddir/'result.json');log=(builddir/'console.log').read_bytes()
assert receipt['exitCode']==0 and receipt['logSha256']==sha(log)
record=next(x for x in receipt['artifacts'] if x['path']==artifact.relative_to(ROOT).as_posix());assert record['sha256']==sha(artifact.read_bytes()) and record['bytes']==artifact.stat().st_size
with zipfile.ZipFile(artifact) as z:
 assert z.testzip() is None;names=z.namelist();assert len(names)==len(set(names))
 descriptor=json.loads(z.read('fabric.mod.json'));assert descriptor['version']=='0.4.0-dev' and descriptor['id']=='qizhangverdict'
 assert descriptor['name']=="QiZhang's Verdict / \u4e03\u7ae0\u7684\u88c1\u51b3"
 assert descriptor['depends']['minecraft']=='1.21.11' and descriptor['depends']['java']=='>=21'
 assert descriptor['license']=='GPL-3.0-only' and descriptor['depends']['fabricloader']=='>=0.19.5'
 assert descriptor['depends']['fabric-api']=='>=0.141.6+1.21.11'
 for n in ('LICENSE','NOTICE'):assert z.read(n)==(ROOT/n).read_bytes()
 manifest=z.read('META-INF/MANIFEST.MF').decode();assert 'License: GPL-3.0-only' in manifest and 'Fabric-Mapping-Namespace: intermediary' in manifest
 classes={n:cls(z.read(n)) for n in names if n.endswith('.class')};assert len(classes)==29
 assert {c['major'] for c in classes.values()}=={65}
 assert all(n.startswith('cn/qizhang/guard/') for n in classes)
 assert not any('Smoke' in n or 'Test' in n or n.endswith('.jar') for n in names)
 mix=json.loads(z.read('qizhangverdict.mixins.json'));ref=json.loads(z.read('qizhangverdict.refmap.json'))
 assert mix['required'] is True and mix['injectors']['defaultRequire']==1 and mix['compatibilityLevel']=='JAVA_21'
 assert mix['mixins']==['CommandGate12111Mixin'] and mix['refmap']=='qizhangverdict.refmap.json'
 key='cn/qizhang/guard/minecraft/mixin/CommandGate12111Mixin';method='performCommand(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)V';target='Lnet/minecraft/class_2170;method_9249(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)V'
 assert ref['mappings'][key][method]==target and ref['data']['named:intermediary'][key][method]==target
 mixclass=classes[key+'.class'];anns=sum([v for k,v in mixclass['attributes'].items() if k.endswith('Annotations')],[])
 ma=next(x for x in anns if x['type']=='Lorg/spongepowered/asm/mixin/Mixin;');assert ma['values']['value']==['Lnet/minecraft/class_2170;']
 handler=next(m for m in mixclass['methods'] if m['name']=='qizhangverdict$denyPendingCommand')
 anns=sum([v for k,v in handler['attributes'].items() if k.endswith('Annotations')],[])
 inject=next(a for a in anns if a['type']=='Lorg/spongepowered/asm/mixin/injection/Inject;');v=inject['values']
 assert v['method']==[method] and v['require']==1 and v['cancellable']==1 and v['at'][0]['values']['value']=='HEAD'
 defaults=next(f['attributes']['ConstantValue'] for f in classes['cn/qizhang/guard/core/Blacklist.class']['fields'] if f['name']=='DEFAULTS')
 rows=[line for line in defaults.splitlines() if line and not line.startswith('#')]
 source_rows=[line for line in (ROOT/'catalog/blacklist-extension.tsv').read_text(encoding='utf-8').splitlines() if line and not line.startswith('#')]
 assert rows==source_rows and len(rows)==39
licensefiles={n:{'sha256':sha((ROOT/n).read_bytes()),'embeddedEqualsRoot':True} for n in ('LICENSE','NOTICE')}
# Independent official-to-intermediary chain; no Java executable is involved.
inputs=CACHE.parent/'runtime-inputs-01';meta=j(inputs/'metadata/minecraft-1.21.11.json');versions=j(inputs/'metadata/mojang-version-manifest.json')
version=next(x for x in versions['versions'] if x['id']=='1.21.11');assert hashlib.sha1((inputs/'metadata/minecraft-1.21.11.json').read_bytes()).hexdigest()==version['sha1']
server=inputs/'minecraft/minecraft-1.21.11-server.jar';mappings=inputs/'minecraft/minecraft-1.21.11-server_mappings.txt'
for key,p in [('server',server),('server_mappings',mappings)]:assert hashlib.sha1(p.read_bytes()).hexdigest()==meta['downloads'][key]['sha1']
mt=mappings.read_text();part=mt.split('net.minecraft.commands.Commands -> ee:\n',1)[1].split('\nnet.',1)[0]
assert 'void performCommand(com.mojang.brigadier.ParseResults,java.lang.String) -> a' in part
inter=Path(r'E:/CodexTemp/Gradle/QiZhang_Games/caches/modules-2/files-2.1/net.fabricmc/intermediary/1.21.11/16a84fabebbbfaf4950abe072f6d3653090430a/intermediary-1.21.11-v2.jar')
url='https://maven.fabricmc.net/net/fabricmc/intermediary/1.21.11/intermediary-1.21.11-v2.jar.sha1'
raw=(CACHE/'intermediary-official-sha1.txt').read_bytes() if (CACHE/'intermediary-official-sha1.txt').exists() else urllib.request.urlopen(url,timeout=20).read(1000);assert re.fullmatch(rb'[0-9a-f]{40}\s*',raw)
(CACHE/'intermediary-official-sha1.txt').write_bytes(raw);assert hashlib.sha1(inter.read_bytes()).hexdigest()==raw.decode().strip()
with zipfile.ZipFile(inter) as z:
 tiny=z.read('mappings/mappings.tiny').decode();section=tiny.split('c\tee\tnet/minecraft/class_2170\n',1)[1].split('\nc\t',1)[0]
 assert '\tm\t(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)V\ta\tmethod_9249' in section
with zipfile.ZipFile(server) as z:
 vs=z.read('META-INF/versions.list').decode().strip().split('\t');assert len(vs)==3
 inside=z.read('META-INF/versions/'+vs[2]);assert sha(inside)==vs[0]
 with zipfile.ZipFile(io.BytesIO(inside)) as actual:
  actualclass=cls(actual.read('ee.class'));actualmethod=next(m for m in actualclass['methods'] if m['name']=='a' and m['descriptor']=='(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)V')
  assert actualmethod['access']&1
# This audit reads existing build evidence; it does not re-run any smoke program.
text=log.decode('utf-8',errors='replace');dispatch=re.findall(r'^PASS fabric-client-dispatch (\d+):',text,re.M)
assert dispatch==[str(i) for i in range(1,13)] and 'PASS fabric-client-dispatch total=12' in text
assert text.count('PASS: production command tree accepts')==1 and text.count('PASS: four raw wire round trips')==1
assert 'BUILD SUCCESSFUL' in text and '> Task :fabric:test NO-SOURCE' in text
relevant=['platforms/1.21.11/build.gradle','platforms/1.21.11/fabric/build.gradle']+[str(p.relative_to(ROOT)).replace('\\','/') for folder in ['common','fabric'] for p in (ROOT/'platforms/1.21.11'/folder/'src').rglob('*') if p.is_file()]
changed_sources=[p for p in relevant if sha((ROOT/p).read_bytes())!=receipt['sourceSha256'][p]]
assert changed_sources==['platforms/1.21.11/build.gradle']
neo_receipt=j(CACHE.parent/'builds/05-neoforge-junit/result.json')
assert all(sha((ROOT/p).read_bytes())==neo_receipt['sourceSha256'][p] for p in relevant)
rootbuild=(ROOT/'platforms/1.21.11/build.gradle').read_text();fabbuild=(ROOT/'platforms/1.21.11/fabric/build.gradle').read_text()
assert "java.srcDir rootProject.file('common/src/smoke/java')" in rootbuild and 'sourceSets.smoke.runtimeClasspath' in rootbuild and 'sourceSets.smoke.runtimeClasspath' in fabbuild
assert "tasks.named('check') { dependsOn tasks.named('commandParserSmoke'), tasks.named('payloadCodecSmoke') }" in rootbuild
assert "tasks.named('check') { dependsOn tasks.named('clientChallengeDispatchSmoke') }" in fabbuild
assert 'failOnNoDiscoveredTests' not in rootbuild+fabbuild
srcjar=artifact.with_name(artifact.stem+'-sources.jar')
with zipfile.ZipFile(srcjar) as z:
 assert z.testzip() is None
 for n in ('LICENSE','NOTICE'):assert z.read(n)==(ROOT/n).read_bytes()
 assert not any('Smoke' in n or n.endswith('.class') for n in z.namelist())
# Review only the previously completed pure-Python checker regression evidence.
qa=Path(r'E:/CodexTemp/QiZhangVerdict/catalog-next-20260925/artifact-checks-regression-01');qr=j(qa/'result.json');assert qr['passed'] and qr['exitCode']==0 and qr['tests']==9
assert all(sha((ROOT/s['file']).read_bytes())==s['sha256'] for s in qr['sourceFiles'])
report={'schemaVersion':1,'reviewedAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Read-only source/ZIP/class-file/mapping review plus prior build/Python log inspection; no Java, Gradle or game launched by reviewer.','passed':True,'blockingFindings':[],'artifact':pin(artifact),'sourceJar':pin(srcjar),'zip':{'crcValid':True,'uniqueEntries':len(names),'classCount':29,'classMajors':[65],'onlyFirstPartyClasses':True,'testClassesBundled':False,'nestedJars':False},'license':licensefiles,'descriptor':descriptor,'mixin':{'required':True,'defaultRequire':1,'compiledTargetAnnotation':ma,'compiledInjectAnnotation':inject,'namedTarget':method,'intermediaryTarget':target,'officialClass':'ee','officialMethod':'a','descriptor':'(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)V','officialMethodActuallyPresent':True,'officialMethodPublic':True,'mappingChainVerified':True,'runtimeInjectionVerifiedByThisReview':False},'mappingSources':{'mojangVersion':{'url':version['url'],'sha1':version['sha1']},'server':{**meta['downloads']['server'],'sha256':sha(server.read_bytes())},'serverMappings':{**meta['downloads']['server_mappings'],'sha256':sha(mappings.read_bytes())},'intermediary':{**pin(inter),'url':url.removesuffix('.sha1'),'officialSha1URL':url,'sha1':raw.decode().strip(),'officialSha1Matches':True}},'embeddedDefaults':{'rules':39,'deny':sum('\tDENY\t' in line for line in rows),'alert':sum('\tALERT\t' in line for line in rows),'matchesCurrentExport':True},'sourceSetsReview':{'dedicatedSmokeSourceSet':True,'commonAndPlatformSmokeSources':True,'mainOutputAndRuntimeDependenciesPresent':True,'threeJavaExecTasksRequiredByCheck':True,'standardTestRemainsStrict':True,'currentTestTask':'NO-SOURCE','noSmokeClassesInProductOrSourcesJar':True,'reviewedProductSourcesMatchFabric03Receipt':True,'buildChangesAfterFabric03':changed_sources,'currentInputsMatchNeo05Receipt':True,'buildChangeExplanation':'Parent restricted the two existing JavaExec tasks to Fabric and moved Neo contracts to official FML JUnit; Fabric product and smoke source bytes stayed unchanged.','sourceFiles':[pin(ROOT/p) for p in relevant]},'existingBuildEvidence':{'result':pin(builddir/'result.json'),'log':pin(builddir/'console.log'),'exitCode':0,'artifactMatchesReceipt':True,'groupsPassed':['clientChallengeDispatchSmoke (12 checks)','commandParserSmoke','payloadCodecSmoke'],'notIncluded':'Exact-JAR core regression, dedicated server startup, real GUI client and command-gate runtime are separate acceptance steps.'},'catalogLogCheckerReview':{'blockingFindings':[],'rulesAndCountsDerivedFromPassedTsv':True,'exactRowsAndSequenceRequired':True,'exactControlsRequiredOnce':3,'uniqueFinalSummaryRequired':True,'nonzeroExitCannotPass':True,'artifactOriginMechanismUnchanged':True,'existingPythonRegression':pin(qa/'result.json'),'existingRegressionTestsPassed':9,'noJavaExecuted':True},'nonBlockingObservations':[{'file':'platforms/1.21.11/.gradle/loom-cache','detail':'The current Loom cache is a real directory under project workspace, not an E:/CodexTemp junction. It is not inside the product JAR. Observed before combined build06 finished; parent is relocating this cache after Java stops. This observation is not a product defect.'}],'boundaries':['Compilation and mapped target existence are not proof that a live server applied the injection.','Three build smoke groups do not stand in for exact-JAR core99 or server/client interoperability.','NeoForge is covered by the separate additionalNeoForgeReview, when present.','No source files or historical evidence were modified.']}
(CACHE/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(CACHE/'review.md').write_text('# 1.21.11 Fabric 成品只读审查\n\n未发现成品或日志判据的阻断问题。\n\n- 成品 SHA256：`'+sha(artifact.read_bytes())+'`，97169 字节；与构建03回执一致。\n- ZIP CRC、GPL/NOTICE 与根文件逐字节一致；描述符精确 MC1.21.11 / Java>=21 / GPL-3.0-only。29个首方类均 class major65，没有嵌套第三方 JAR或测试类。\n- 编译后的 Mixin 保留 HEAD、cancellable=true、require=1；官方 Commands→ee.a 与 Fabric class_2170.method_9249 的完整描述符一致，且官方服务端类文件中确有该public方法。refmap双入口一致。\n- 独立 smoke sourceSet 接入 common+Fabric，check依赖三项JavaExec，默认Test仍严格；现有日志三组PASS（dispatch12项），不是本轮重新执行。\n- JAR内默认39行与当前TSV完全相同。日志判据从TSV读取数量，逐行/控制项/唯一末汇总严格匹配，退出非0不能通过；已存9项Python回归与当前脚本哈希一致。\n\n边界：尚不能由此声明游戏内Mixin应用、专服/真实客户端或exact-JAR核心99验收。另发现项目内 `.gradle/loom-cache` 是真实缓存目录，建议等当前Neo构建停后迁往Etemp或设junction；未进入成品，非制品阻断。\n\n精确来源、哈希、编译注解和已有日志索引见 [result.json](result.json)。只写缓存，无Java/Gradle/MC运行、源码或历史证据修改。\n',encoding='utf-8')
print(json.dumps({'passed':True,'artifact':report['artifact'],'report':str(CACHE/'result.json'),'reportSha256':sha((CACHE/'result.json').read_bytes()),'classCount':29,'mappedMethodFound':True,'blockingFindings':0},indent=2))
