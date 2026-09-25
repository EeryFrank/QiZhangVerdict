import datetime,hashlib,json,re,shutil
from pathlib import Path
ROOT=Path('E:/Codex_work/QiZhangVerdict');BASE=Path('E:/CodexTemp/QiZhangVerdict/next-platforms/1.19.2')
DEST=ROOT/'outputs/adapter-build-1.19.2';SUMMARY=ROOT/'outputs/adapter-build-1.19.2.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf-8'))
def ref(p):return {'path':Path(p).relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':Path(p).stat().st_size}
assert not DEST.exists();DEST.mkdir()
shutil.copyfile(SUMMARY,BASE/'source-preparation-report.json')
public=[]
def copy(source,name):
 source=Path(source);target=DEST/name;target.parent.mkdir(parents=True,exist_ok=True)
 assert not target.exists();shutil.copyfile(source,target);assert source.read_bytes()==target.read_bytes()
 item=ref(target);item.update(originalPath=str(source),rawBytesPreserved=True);public.append(item);return item
attempts=[]
for folder in sorted((BASE/'builds').iterdir()):
 result=read(folder/'result.json')
 refs={n:copy(folder/n,'build-'+folder.name+'-'+n+('.txt' if n.endswith('.log') else '')) for n in ['plan.json','result.json','gradle.log','build-attempt.py']}
 attempts.append({'attempt':folder.name,'exitCode':result['exitCode'],'buildSuccessful':result['buildSuccessful'],'elapsedSeconds':result['elapsedSeconds'],'oldArtifactsUnchanged':result['oldArtifactsUnchanged'],'availablePhysicalGiB':result['availablePhysicalGiB'],'minimumFreeGiB':result['minimumFreeGiB'],'artifacts':result['artifacts'],'evidence':refs})
assert len(attempts)==2 and attempts[0]['exitCode']==1 and attempts[-1]['buildSuccessful']
audit=read(BASE/'artifact-audit.json');assert audit['passed'] and len(audit['artifacts'])==2
log=(BASE/'builds/02/gradle.log').read_text('utf-8',errors='replace')
def task_text(loader,name):
 m=re.search(r'^> Task :'+loader+':'+name+r'\s*\n(.*?)(?=^> Task|\Z)',log,re.M|re.S);assert m,(loader,name);return m.group(1)
for artifact in audit['artifacts']:
 loader=artifact['loader'];folder=BASE/'artifact-core'/loader
 sec=task_text(loader,'securityTest');cat=task_text(loader,'catalogCompatibilityTest')
 assert list(map(int,re.findall(r'^PASS (\d+):',sec,re.M)))==list(range(1,58))
 assert list(map(int,re.findall(r'^PASS rule (\d+):',cat,re.M)))==list(range(1,38))
 assert list(map(int,re.findall(r'^PASS control (\d+):',cat,re.M)))==[1,2,3]
 assert 'PASS: production command tree' in task_text(loader,'commandParserSmoke')
 assert 'PASS: stable scoped digest' in task_text(loader,'clientReporterSmoke')
 artifact['gradleSourceClasspathChecks']={'security':57,'catalogRules':37,'catalogControls':3,'commandParserSmokePassed':True,'clientReporterSmokePassed':True,'javaToolchain':17}
 artifact['publicCoreEvidence']={}
 for name in ['result.json','java-version.log','compile-runners.log','artifact-origin.log','security.log','catalog.log','ArtifactOriginCheck.java']:
  artifact['publicCoreEvidence'][name]=copy(folder/name,'core-'+loader+'-'+name+('.txt' if name.endswith('.log') else ''))
 copy(BASE/('artifact-core-'+loader+'.log'),'core-'+loader+'-driver-console.log.txt')
assert all(sha(ROOT/a['artifact']['path'])==a['artifact']['sha256'] for a in audit['artifacts'])
copy(BASE/'artifact-audit.json','artifact-audit.json')
copy(BASE/'audit-artifacts.py','audit-artifacts.py')
copy(BASE/'collect-build-evidence.py','collect-build-evidence.py')
copy(BASE/'source-preparation-report.json','source-preparation-report.json')
copy(ROOT/'scripts/artifact_core_checks.py','artifact_core_checks.py')
for p in [ROOT/'core/src/test/java/cn/qizhang/guard/core/SecurityRegressionTest.java',ROOT/'core/src/test/java/cn/qizhang/guard/core/CatalogCompatibilityTest.java',ROOT/'client-common/src/test/java/cn/qizhang/guard/client/ClientReporterSmoke.java',ROOT/'platforms/shared/src/test/java/cn/qizhang/guard/minecraft/CommandParserSmoke.java']:
 copy(p,p.name)
published=read(ROOT/'outputs/build-validation-0.2.0-test.1.json')['artifacts'];assert len(published)==13
old_unchanged=all(sha(ROOT/a['artifact']['path'])==a['artifact']['sha256'] for a in published);assert old_unchanged
# Public attachment selection is an explicit list. No generated state or private probe files are copied.
for p in public:
 name=Path(p['path']).name.lower();assert not any(x in name for x in ['accounts.state','server-id','machine-id','installation-id'])
 data=(ROOT/p['path']).read_bytes().decode('utf-8',errors='replace')
 assert not re.search(r'(gh[pousr]_[A-Za-z0-9]{20,}|glpat-[A-Za-z0-9_-]{15,}|Bearer\s+[A-Za-z0-9._-]{20,})',data)
summary={'schemaVersion':1,'minecraft':'1.19.2','version':'0.3.0-dev','stage':'BUILD_AND_STATIC_CORE_PASSED_RUNTIME_NOT_RUN','prepared':True,'buildExecuted':True,'buildSuccessful':True,'passed':True,'passedScope':'Two production remapped JAR builds, per-loader Gradle checks, static packaging, and exact-JAR core regressions under Java17 only.','formalAcceptancePassed':False,'minecraftRuntimeExecuted':False,'runtimeAcceptancePassed':False,'allAttemptsSuccessful':False,'failedBuildAttemptCount':1,'failureHistory':[{'attempt':'01','phase':'Gradle project configuration before compilation','reason':'New Forge child project omitted loom.platform=forge; dependencies.forge configuration was unavailable.','fixedInAttempt':'02','productArtifactsProduced':False}], 'warningsPreserved':['Architectury Loom reports beta status.','Forge emits one ResourceLocation(String,String) removal/deprecation warning.','Gradle reports deprecated features incompatible with Gradle9.','Forge access-transformer step reports overwriting its cached intermediate output JAR, not a project or released artifact.'],'versions':read(ROOT/'platforms/1.19.2/api-evidence.json')['versions'],'officialApiEvidence':ref(ROOT/'platforms/1.19.2/api-evidence.json'),'buildAttempts':attempts,'artifacts':audit['artifacts'],'packagedCoreRegressionCount':194,'packagedCoreRegressionPerJar':{'security':57,'catalogRules':37,'catalogControls':3},'published020ArtifactsChecked':13,'published020ArtifactsUnchanged':old_unchanged,'allPriorArtifactHashesUnchanged':all(a['oldArtifactsUnchanged'] for a in attempts),'minecraftOrClientProcessStarted':False,'sharedOrReleasedSourceModifiedByThisTask':False,'runtimeBoundaries':['No Fabric or Forge dedicated server startup yet.','No actual command-gate injection, wire login, post-report online duration, or real graphical client validation yet.','Other Minecraft versions and historical results do not satisfy this candidate acceptance.'],'buildStorage':{'gradleUserHome':'E:/CodexTemp/Gradle/QiZhang_Games','attemptRoot':str(BASE/'builds'),'projectCacheAndJavaTmpPerAttempt':True,'heapMaxMiB':1536,'workers':1,'ciEnvironment':'true','gradleLauncherJava':21,'compilationAndTestJava':17},'publicEvidence':public,'publicEvidenceCount':len(public),'publicEvidenceBytes':sum(p['bytes'] for p in public),'privacyBoundary':'Explicit raw-file whitelist only; no account/device state, installation IDs, scoped actual device digests, whole Minecraft mappings/JARs or decompiled classes are copied. Log extension .log.txt retains original bytes.','apiEvidenceTiming':'api-evidence.json and source-preparation-report.json are frozen preparation-stage observations; this report records the later real build and checks.'}
SUMMARY.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'report':str(SUMMARY),'sha256':sha(SUMMARY),'publicEvidenceCount':len(public),'publicEvidenceBytes':sum(p['bytes'] for p in public),'artifacts':[{k:a['artifact'][k] for k in ('path','sha256','bytes')} for a in audit['artifacts']],'minecraftRuntimeExecuted':False}))
