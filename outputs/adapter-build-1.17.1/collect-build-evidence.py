# SPDX-License-Identifier: GPL-3.0-only
"""Read-only 1.17.1 artifact/evidence collection; never invokes Java."""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
from collections import Counter
import hashlib, json, re, zipfile, struct, importlib.util, tomllib
ROOT=Path(r'E:\Codex_work\QiZhangVerdict')
CACHE=Path(r'E:\CodexTemp\QiZhangVerdict\compat-1.17.1')
HERE=CACHE/'build-report-01'
OUT=ROOT/'outputs/adapter-build-1.17.1'
REPORT=ROOT/'outputs/adapter-build-1.17.1.json'
MAPPINGS=Path(r'E:\CodexTemp\Gradle\QiZhang_Games\caches\fabric-loom\1.17.1')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def obj(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,v):
 with Path(p).open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
def pin(p):
 p=Path(p);return {'path':p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p),'sha256':sha(p),'bytes':p.stat().st_size}
def utf_constants(data):
 assert data[:4]==b'\xca\xfe\xba\xbe';count=struct.unpack_from('>H',data,8)[0];i=1;pos=10;strings=[]
 while i<count:
  tag=data[pos];pos+=1
  if tag==1:
   length=struct.unpack_from('>H',data,pos)[0];pos+=2;strings.append(data[pos:pos+length].decode('utf8',errors='replace'));pos+=length
  elif tag in (3,4):pos+=4
  elif tag in (5,6):pos+=8;i+=1
  elif tag in (7,8,16,19,20):pos+=2
  elif tag in (9,10,11,12,17,18):pos+=4
  elif tag==15:pos+=3
  else:raise ValueError('Unknown constant-pool tag '+str(tag))
  i+=1
 return strings

def source_mapping_proof(loader,dev,final,roots):
 source={f.relative_to(r).as_posix():f for r in roots for f in r.rglob('*.java')}
 names={n for n in dev.namelist() if n.endswith('.java')}
 assert names==set(source)=={n for n in final.namelist() if n.endswith('.java')}
 mp=MAPPINGS/('loom.mappings.1_17_1.layered+hash.40545-v2/mappings.tiny' if loader=='fabric' else 'loom.mappings.1_17_1.layered+hash.40545-v2-forge-1.17.1-37.1.1/mappings-srg.tiny')
 lines=mp.read_text(encoding='utf8').splitlines();spaces=lines[0].split('\t')[3:];si=spaces.index('named');di=spaces.index('intermediary' if loader=='fabric' else 'srg');pairs=set();classpairs={}
 for line in lines[1:]:
  parts=line.lstrip('\t').split('\t')
  if parts[0]=='c':
   ns=parts[1:];a=ns[si].replace('/','.').replace('$','.');b=ns[di].replace('/','.').replace('$','.');classpairs[b]=a;pairs.add((a.rsplit('.',1)[-1],b.rsplit('.',1)[-1]))
  elif parts[0] in ('m','f'):
   ns=parts[2:];pairs.add((ns[si],ns[di]))
 pat=re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_$][A-Za-z0-9_$]*|\d+(?:\.\d+)?|[^\s]')
 def tokens(text,remap=False):
  text=re.sub(r'^\s*import [^\n]+\n','',text,flags=re.M)
  if remap:
   for b,a in sorted(classpairs.items(),key=lambda x:len(x[0]),reverse=True):
    if b in text:text=text.replace(b,a)
  return [x for x in pat.findall(text) if not x.startswith(('//','/*'))]
 rows=[]
 for name in sorted(names):
  original=source[name].read_bytes();dv=dev.read(name);fv=final.read(name)
  assert dv==original,('named source mismatch',loader,name)
  aa=tokens(dv.decode('utf8'));bb=tokens(fv.decode('utf8'),True)
  assert len(aa)==len(bb),(loader,name,'token count')
  assert all(a==b or (a,b) in pairs for a,b in zip(aa,bb)),(loader,name,'unexpected remapping change')
  rows.append({'entry':name,'source':source[name].relative_to(ROOT).as_posix(),'sourceSha256':hashlib.sha256(original).hexdigest(),'namedSourceJarEntryExact':True,'finalSourceJarEntrySha256':hashlib.sha256(fv).hexdigest(),'finalEntryByteIdentical':fv==original,'nonImportTokensEquivalentUnderBuildMappings':True})
 return {'sourceFileCount':len(rows),'namedSourcesExactToBuildInputs':True,'finalByteIdenticalCount':sum(r['finalEntryByteIdentical'] for r in rows),'finalRemappedFileCount':sum(not r['finalEntryByteIdentical'] for r in rows),'finalCoreAndClientCommonByteIdentical':all(r['finalEntryByteIdentical'] for r in rows if '/core/' in r['entry'] or '/client/' in r['entry']),'allNonImportTokensMatchExactOrBuildMappingPairs':True,'mappingInput':pin(mp),'mappingBytesPublished':False,'comparisonBoundary':'Named source JAR entries match original/generated inputs byte for byte. Final remapped source tokens match after official build-name mappings, excluding imports/comments. This is static source provenance, not recompilation.','entries':rows}

assert not OUT.exists() and not REPORT.exists()
build=obj(CACHE/'builds/build-01/result.json');configure=obj(CACHE/'builds/configure-01/result.json');review=obj(CACHE/'source-review-01/result.json')
assert build['exitCode']==configure['exitCode']==0
assert configure['configureOnly'] and configure['artifacts']==[] and configure['command'][-1]=='help'
assert not build['configureOnly'] and build['sourcesUnchanged'] and build['previousArtifactsUnchanged']
for attempt,result in [('configure-01',configure),('build-01',build)]:assert sha(CACHE/'builds'/attempt/'console.log')==result['logSha256']
for path,expected in build['sourceSha256'].items():assert sha(ROOT/path)==expected,('Source drift',path)
for row in build['previousArtifacts']:assert pin(ROOT/row['path'])==row
assert len(build['previousArtifacts'])==23
assert not review['blockingFindings'] and not review['actionableFindings'] and not review['sourceFreeze']['drift']
assert sha(Path(review['sourceFreeze']['path']))==review['sourceFreeze']['sha256']
for path,row in review['files'].items():assert sha(ROOT/path)==row['sha256']
log=(CACHE/'builds/build-01/console.log').read_text(encoding='utf8')
assert '29 actionable tasks: 29 executed' in log and 'BUILD SUCCESSFUL' in log
for loader in ('fabric','forge'):
 assert re.findall(r'^PASS '+loader+r'-connection-dispatch (\d+):',log,re.M)==[str(x) for x in range(1,16)]
 assert log.count('PASS '+loader+'-connection-dispatch total=15')==1
 assert '> Task :'+loader+':commandParserSmoke\n' in log
 assert '> Task :'+loader+':connectionDispatchSmoke\n' in log
assert log.count('PASS: production command tree accepts unquoted device digests and legacy rule IDs, glob spaces and ban reasons; rejects non-admin access and invalid pages')==2
assert '> Task :forge:legacyPayloadSmoke\n' in log
assert log.count('PASS: eight actual legacy custom-payload writes, 30000-byte bounds, readable slice and defensive ownership')==1
catalog=ROOT/'catalog/blacklist-extension.tsv';catalog_rows=[s for s in catalog.read_text(encoding='utf8').splitlines() if s and not s.startswith('#')]
assert len(catalog_rows)==44
spec=importlib.util.spec_from_file_location('artifactcheck',ROOT/'scripts/artifact_core_checks.py');checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)
artifacts=[];core_reports={};audit=[]
for loader in ('fabric','forge'):
 binary=next(r for r in build['artifacts'] if '/'+loader+'/' in r['path'] and not r['path'].endswith('-sources.jar'))
 source=next(r for r in build['artifacts'] if '/'+loader+'/' in r['path'] and r['path'].endswith('-sources.jar'))
 for row in (binary,source):assert pin(ROOT/row['path'])==row
 p=ROOT/'platforms/1.17.1'/loader
 with zipfile.ZipFile(ROOT/binary['path']) as bz,zipfile.ZipFile(ROOT/source['path']) as sz,zipfile.ZipFile(p/'build/devlibs'/f'qizhangverdict-{loader}-1.17.1-0.6.0-dev-sources.jar') as dz:
  for z in (bz,sz,dz):
   assert z.testzip() is None
   assert len(z.namelist())==len(set(n.casefold() for n in z.namelist()))
   for n in z.namelist():assert not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts and '\\' not in n and ':' not in n
   for license_file in ('LICENSE','NOTICE'):assert z.read(license_file)==(ROOT/license_file).read_bytes()
   assert 'License: GPL-3.0-only' in z.read('META-INF/MANIFEST.MF').decode('utf8')
  classes=[n for n in bz.namelist() if n.endswith('.class')]
  assert all(n.startswith('cn/qizhang/guard/') for n in classes)
  assert all(not any(s in n.lower() for s in ('smoke','regressiontest','compatibilitytest','artifactorigincheck')) for n in classes)
  assert not any(n.endswith('.jar') for n in bz.namelist())
  majors={struct.unpack_from('>H',bz.read(n),6)[0] for n in classes};assert majors=={60}
  assert not any(n.endswith('.class') for n in sz.namelist())
  defaults=[x for x in utf_constants(bz.read('cn/qizhang/guard/core/Blacklist.class')) if x.startswith('# kind<TAB>')]
  assert len(defaults)==1
  embedded=[x for x in defaults[0].splitlines() if x and not x.startswith('#')];assert embedded==catalog_rows
  mix=json.loads(bz.read('qizhangverdict.mixins.json'));assert mix['required'] is True and mix['injectors']['defaultRequire']==1 and mix['compatibilityLevel']=='JAVA_16' and mix['mixins']==['CommandGate117Mixin']
  ref=json.loads(bz.read(mix['refmap']));target=ref['mappings']['cn/qizhang/guard/minecraft/mixin/CommandGate117Mixin']['performCommand(Lnet/minecraft/commands/CommandSourceStack;Ljava/lang/String;)I']
  expected='Lnet/minecraft/class_2170;method_9249(Lnet/minecraft/class_2168;Ljava/lang/String;)I' if loader=='fabric' else 'Lnet/minecraft/commands/Commands;m_82117_(Lnet/minecraft/commands/CommandSourceStack;Ljava/lang/String;)I'
  assert target==expected
  mixcp=utf_constants(bz.read('cn/qizhang/guard/minecraft/mixin/CommandGate117Mixin.class'))
  assert 'HEAD' in mixcp and 'require' in mixcp and 'cancellable' in mixcp and 'Lorg/spongepowered/asm/mixin/injection/Inject;' in mixcp
  if loader=='fabric':
   desc=json.loads(bz.read('fabric.mod.json'));assert desc['id']=='qizhangverdict' and desc['version']=='0.6.0-dev' and desc['license']=='GPL-3.0-only'
   assert desc['depends']=={'fabricloader':'>=0.19.5','fabric':'>=0.46.1','minecraft':'1.17.1','java':'>=16'}
  else:
   desc=tomllib.loads(bz.read('META-INF/mods.toml').decode('utf8'));assert desc['modLoader']=='javafml' and desc['loaderVersion']=='[37,38)' and desc['license']=='GPL-3.0-only'
   assert desc['mods'][0]['modId']=='qizhangverdict' and desc['mods'][0]['version']=='0.6.0-dev'
   deps={d['modId']:d['versionRange'] for d in desc['dependencies']['qizhangverdict']};assert deps=={'minecraft':'[1.17.1]','forge':'[37.1.1,38)'}
   assert 'MixinConfigs: qizhangverdict.mixins.json' in bz.read('META-INF/MANIFEST.MF').decode('utf8')
  source_roots=[ROOT/'core/src/main/java',ROOT/'client-common/src/main/java',ROOT/'platforms/1.17.1/src/main/java',p/'src/main/java',p/'build/generated/sources/shared1171/main']
  proof=source_mapping_proof(loader,dz,sz,source_roots)
  # Check the adapter's generated source against the exact three configured API substitutions.
  for shared in (ROOT/'platforms/shared/src/main/java').rglob('*.java'):
   rel=shared.relative_to(ROOT/'platforms/shared/src/main/java').as_posix()
   if '/mixin/' in rel:continue
   adapted=shared.read_text(encoding='utf8').replace('.serverLevel()', '.getLevel()').replace('sendSuccess(() -> ', 'sendSuccess(').replace('Component.literal(', 'new net.minecraft.network.chat.TextComponent(')
   generated=p/'build/generated/sources/shared1171/main'/rel
   assert generated.read_text(encoding='utf8')==adapted,rel
  core_path=CACHE/'core-checks'/f'{loader}-44-01';cr=obj(core_path/'result.json');assert cr['passed'] and cr['artifactUnchanged'] and cr['sha256']==binary['sha256'] and cr['bytes']==binary['bytes'];assert cr['toolSha256']==sha(ROOT/'scripts/artifact_core_checks.py')
  for c in cr['checks']:
   assert c['passed'] and c['exitCode']==0 and sha(core_path/c['log'])==c['sha256'] and (core_path/c['log']).stat().st_size==c['bytes']
  security=(core_path/'security.log').read_text(encoding='utf8');assert re.findall(r'^PASS (\d+):',security,re.M)==[str(i) for i in range(1,58)] and security.rstrip().endswith('PASS: 57 security regression tests')
  cv=checks.validate_catalog_log((core_path/'catalog.log').read_text(encoding='utf8'),catalog);assert cv['rules']==44 and cv['deny']==40 and cv['alert']==4 and cv['controls']==3
  assert '16.0.2' in (core_path/'java-version.log').read_text(encoding='utf8')
  core_reports[loader]=cr
  entry={'loader':loader,'artifact':binary,'sourceJar':source,'classCount':len(classes),'classMajor':60,'zipCrcPassed':True,'embeddedLicenseNoticeExact':True,'onlyFirstPartyClasses':True,'noNestedThirdPartyOrTestClasses':True,'descriptor':desc,'embeddedDefaults':{'rules':44,'deny':40,'alert':4,'exactTsvRowsAndSourcesMatched':True},'requiredMixin':{'name':'CommandGate117Mixin','required':True,'defaultRequire':1,'mappedTarget':target,'refmapNonemptyAndTargetVerified':True,'productionRuntimeInjectionClaimed':False},'exactJarCoreChecks':{'securityCases':57,'catalogRules':44,'catalogControls':3,'totalChecks':104,'passed':True,'javaMajorUsed':16,'guardServiceCodeSourcePinnedToArtifact':True,'report':f'adapter-build-1.17.1/core-{loader}-result.json'},'sourceProvenance':proof}
  artifacts.append(entry)
  audit.append({'loader':loader,'binary':binary,'sources':source,'classCount':len(classes),'classMajor':60,'zipCrcPassed':True,'licenseNoticeMatched':True,'descriptorVersion':'0.6.0-dev','requiredMixin':entry['requiredMixin'],'sourceProvenance':proof})

save(HERE/'artifact-audit.json',{'passed':True,'artifacts':audit,'javaInvokedByCollector':False})
save(HERE/'source-hashes.json',{'buildInputs':build['sourceSha256'],'allCurrentBytesMatch':True,'independentSourceReviewInputs':len(review['files']),'reviewFreezeMatched':True,'generatedSharedBridgeOnlyThreeExpectedSubstitutions':True})
save(HERE/'previous-artifacts-verification.json',{'count':23,'allRehashedUnchanged':True,'rebuiltOrRetested':False,'artifacts':build['previousArtifacts']})
# Explicit public attachment whitelist only. No recursive cache copying.
files=[]
def include(path,name,derived=False):files.append((Path(path),name,derived))
for attempt in ('configure-01','build-01'):
 for name in ('result.json','plan.json','console.log','daemon-java-version.log','target-java-version.log'):
  include(CACHE/'builds'/attempt/name,attempt+'-'+name)
include(CACHE/'builds/build-01/executed-build_target.py','executed-build_target.py')
assert (CACHE/'builds/configure-01/executed-build_target.py').read_bytes()==(CACHE/'builds/build-01/executed-build_target.py').read_bytes()
for loader in ('fabric','forge'):
 for name in ('result.json','artifact-origin.log','catalog.log','compile-runners.log','java-version.log','security.log'):
  include(CACHE/'core-checks'/f'{loader}-44-01'/name,'core-'+loader+'-'+name)
include(CACHE/'core-checks/fabric-44-01/ArtifactOriginCheck.java','ArtifactOriginCheck.java')
assert (CACHE/'core-checks/fabric-44-01/ArtifactOriginCheck.java').read_bytes()==(CACHE/'core-checks/forge-44-01/ArtifactOriginCheck.java').read_bytes()
include(CACHE/'source-review-01/result.json','source-review-result.json')
include(ROOT/'scripts/artifact_core_checks.py','artifact_core_checks.py')
for name in ('SecurityRegressionTest.java','CatalogCompatibilityTest.java'):include(ROOT/'core/src/test/java/cn/qizhang/guard/core'/name,name)
include(catalog,'catalog-44.tsv')
include(ROOT/'platforms/shared/src/test/java/cn/qizhang/guard/minecraft/CommandParserSmoke.java','CommandParserSmoke.java')
for loader in ('fabric','forge'):include(ROOT/'platforms/1.17.1'/loader/'src/smoke/java/cn/qizhang/guard'/loader/'ConnectionDispatchSmoke.java',loader+'-ConnectionDispatchSmoke.java')
include(ROOT/'platforms/1.17.1/forge/src/smoke/java/cn/qizhang/guard/forge/LegacyPayloadSmoke.java','LegacyPayloadSmoke.java')
include(ROOT/'platforms/1.17.1/gradle/wrapper/gradle-wrapper.properties','gradle-wrapper.properties')
for name in ('LICENSE','NOTICE'):include(ROOT/name,name)
include(CACHE.parent/'toolchains/jdk16/installation-01/installation.json','jdk16-official-installation.json')
include(CACHE.parent/'toolchains/jdk16/installation-01/official-sha256.txt','jdk16-official-sha256.txt')
for name in ('artifact-audit.json','source-hashes.json','previous-artifacts-verification.json'):include(HERE/name,name,True)
include(Path(__file__),'collect-build-evidence.py')
# Source-controlled test data is synthetic; this task does not read any GUI/server state.
credential_patterns=[rb'(?i)(?:ghp_|gho_|github_pat_|glpat-)[A-Za-z0-9_\-]{16,}',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'(?i)Authorization\s*:\s*Bearer\s+\S+']
for path,name,_ in files:
 assert path.suffix.lower() not in ('.jar','.zip','.class','.exe','.dll')
 data=path.read_bytes()
 assert not any(re.search(pattern,data) for pattern in credential_patterns),('Credential-shaped content',name)
 assert '\n' not in name and '/' not in name and '\\' not in name
assert len(files)==len({name.casefold() for _,name,_ in files})
OUT.mkdir(exist_ok=False);evidence=[]
for path,name,derived in files:
 data=path.read_bytes();destination=OUT/name
 with destination.open('xb') as f:f.write(data)
 assert sha(destination)==sha(path)
 evidence.append({'file':'adapter-build-1.17.1/'+name,'publicFile':'outputs/adapter-build-1.17.1/'+name,'source':str(path),'sha256':sha(path),'bytes':len(data),'rawBytesPreserved':not derived,'derivedSummary':derived})
report={'schemaVersion':1,'generatedAtUtc':datetime.now(timezone.utc).isoformat(),'minecraft':'1.17.1','version':'0.6.0-dev','status':'LOCAL_BUILD_AND_EXACT_JAR_CHECKS_PASSED','passed':True,'scope':'Compilation, platform API smoke checks, static artifact/source provenance and core checks from two exact final packaged JARs. No production server/TCP/GUI result is included.','toolchain':{'gradle':'8.14.1','architecturyPlugin':'3.4.164','architecturyLoom':'1.11.456','gradleDaemonJava':'21.0.8','compileAndPlatformSmokeJava':'Temurin16.0.2+7','targetClassMajor':60,'compilerRelease':16,'exactJarCoreJava':'Temurin16.0.2+7','coreRunnerCompilerJava':'21.0.8 --release 8','forgeGradleFallbackUsed':False,'fabricLoader':'0.19.5','fabricApi':'0.46.1+1.17','forge':'37.1.1','jdk16OfficialArchiveSha256':'40191ffbafd8a6f9559352d8de31e8d22a56822fb41bbcf45f34e3fd3afa5f9e','jdk16Receipt':'adapter-build-1.17.1/jdk16-official-installation.json'},'attempts':[{'attempt':'configure-01','configureOnly':True,'task':'help','exitCode':0,'elapsedSeconds':configure['elapsedSeconds'],'producedProductArtifacts':False,'artifactCount':0,'result':'adapter-build-1.17.1/configure-01-result.json','console':'adapter-build-1.17.1/configure-01-console.log'},{'attempt':'build-01','configureOnly':False,'exitCode':0,'elapsedSeconds':build['elapsedSeconds'],'productArtifactCount':2,'sourceArtifactCount':2,'result':'adapter-build-1.17.1/build-01-result.json','console':'adapter-build-1.17.1/build-01-console.log'}],'finalBuild':{'attempt':'build-01','exitCode':0,'elapsedSeconds':build['elapsedSeconds'],'actionableTasks':29,'tasksExecuted':29,'sourceFileCount':len(build['sourceSha256']),'sourceFilesStillMatch':True,'previousArtifactsRehashed':23,'previousArtifactsUnchanged':True,'previousArtifactsRebuiltOrRetested':False},'artifacts':artifacts,'coreChecks':{'uniqueCheckDefinitions':104,'securityCases':57,'catalogRules':44,'catalogControls':3,'exactFinalArtifacts':2,'exactJarCheckExecutions':208,'countingBoundary':'104 checks = 57 security cases + 44 exact catalog-rule checks + 3 preservation/ordinary-ID controls. Repeating on two JARs yields 208 executions, not 208 different cases or primitive assertions.','sourceCoreExecutionIncluded':False,'ruleActions':{'DENY':40,'ALERT':4},'catalogSnapshot':'adapter-build-1.17.1/catalog-44.tsv','catalogSha256':sha(catalog)},'platformChecks':{'fabric':{'connectionDispatchChecks':15,'commandParserSmokeExecuted':True,'commandParserScenarioCount':7,'actualJava16':True},'forge':{'connectionDispatchChecks':15,'commandParserSmokeExecuted':True,'commandParserScenarioCount':7,'actualVanillaPacketWriteCombinations':8,'packetWriteLengths':[0,1,127,30000],'packetWriteDirections':['clientbound','serverbound'],'boundsReadableSliceDefensiveCopyControlsPassed':True,'actualJava16':True},'addedToCoreCheckCount':False,'networkSocketOrPlayerRuntimeClaimed':False,'dispatchBoundary':'Production dispatcher invoked with controlled object identities and queues; this does not establish a real login or timing result.','parserBoundary':'Production command registration/arguments/permissions are exercised; Mixin runtime interception is not part of this build report.'},'securityReview':{'readOnly':True,'newAdapterBlockingFindings':0,'javaRunByReviewer':False,'matchingSourceInputs':review['sourceFreeze']['matchingInputs'],'sourceFreezeMatched':True,'report':'adapter-build-1.17.1/source-review-result.json','clientReportedDeviceSignalsAreForgeableNotHardwareAttestation':True},'publicEvidence':evidence,'publicEvidenceCount':len(evidence),'publicEvidenceBytes':sum(r['bytes'] for r in evidence),'privacy':{'explicitFileAllowlist':True,'credentialPatternScanPassed':True,'serverOrGuiPrivateStateReadOrCopied':False,'excluded':['Minecraft/game libraries and full mappings or third-party source archives','JDK archives/binaries','Worlds, account/device state, installation identifiers and server scopes','Build caches and compiled test runners']},'warningsPreserved':['Architectury Loom beta notice','Official Mojang mapping license notice','Deprecated Gradle features not compatible with Gradle9'], 'limitations':['This report does not include dedicated-server startup, actual Mixin execution, TCP admission or graphical-client acceptance.','Successful configure/help is preserved separately and is not product-build acceptance.','Source JAR resource descriptors retain ${version} templates; binary descriptors are expanded to0.6.0-dev.','The 23 previous published JARs were rehashed unchanged, not rebuilt or retested in this task.','The exact catalog does not cover all cheat tools and self-reported IDs/device/VM signals can be falsified.'],'collectorInvokedJava':False,'repositoryChangesRestrictedToNewReportAndAttachments':True}
save(REPORT,report)
for row in evidence:assert sha(ROOT/row['publicFile'])==row['sha256']
save(HERE/'collection-result.json',{'passed':True,'report':pin(REPORT),'evidenceFiles':len(evidence),'evidenceBytes':sum(r['bytes'] for r in evidence),'binaryArtifacts':2,'sourceArtifacts':2,'exactJarCheckExecutions':208,'javaInvokedByCollector':False})
print(json.dumps(obj(HERE/'collection-result.json'),indent=2))