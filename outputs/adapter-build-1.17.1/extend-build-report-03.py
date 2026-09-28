# SPDX-License-Identifier: GPL-3.0-only
"""Append the authorized Forge repair evidence; preserve every initial public byte."""
from pathlib import Path
import ast, copy, hashlib, json, re, sys, zipfile
from datetime import datetime, timezone
sys.dont_write_bytecode = True
ROOT = Path('E:/Codex_work/QiZhangVerdict')
CACHE = Path('E:/CodexTemp/QiZhangVerdict/compat-1.17.1')
HERE = CACHE/'build-report-03'
REPORT = ROOT/'outputs/adapter-build-1.17.1.json'
OUT = ROOT/'outputs/adapter-build-1.17.1'
INITIAL = 'f54deb4efa7f4abc4be32df7927f035345b0ef9f94dbc844ed1afe584913c005'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def obj(p): return json.loads(Path(p).read_text(encoding='utf8'))
def save(p, value):
    with Path(p).open('x',encoding='utf8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')

assert sha(REPORT)==INITIAL
initial_bytes=REPORT.read_bytes(); initial=obj(REPORT)
assert len(initial['publicEvidence'])==60
for row in initial['publicEvidence']:
    p=ROOT/row['publicFile']; assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
assert {p.name for p in OUT.iterdir()}=={Path(r['file']).name for r in initial['publicEvidence']}
assert not (OUT/'build-02-report.json').exists()

old_build=obj(CACHE/'builds/build-02/result.json')
first_build=obj(CACHE/'builds/build-01/result.json')
new_build=obj(CACHE/'builds/build-03/result.json')
assert new_build['exitCode']==0 and new_build['sourcesUnchanged'] and new_build['previousArtifactsUnchanged']
assert new_build['target']=='forge' and not new_build['configureOnly']
assert sha(CACHE/'builds/build-03/console.log')==new_build['logSha256']
for name,expected in new_build['sourceSha256'].items(): assert sha(ROOT/name)==expected
changes=[{'path':name,'initialSha256':old_build['sourceSha256'].get(name),'finalSha256':value}
         for name,value in new_build['sourceSha256'].items() if old_build['sourceSha256'].get(name)!=value]
assert {r['path'] for r in changes}=={'platforms/1.17.1/build.gradle','platforms/1.17.1/forge/src/main/java/cn/qizhang/guard/forge/GuardForge.java'}
for row in new_build['previousArtifacts']:
    p=ROOT/row['path']; assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
assert len(new_build['previousArtifacts'])==23
log=(CACHE/'builds/build-03/console.log').read_text(encoding='utf8')
assert 'BUILD SUCCESSFUL' in log and '15 actionable tasks: 13 executed, 2 from cache' in log
cached=re.findall(r'^> Task (\S+) FROM-CACHE$',log,re.M)
assert cached==[':forge:compileSmokeJava',':forge:compileTestJava']
for task in ('commandParserSmoke','connectionDispatchSmoke','legacyPayloadSmoke','test'):
    assert log.splitlines().count('> Task :forge:'+task)==1
assert re.findall(r'^PASS forge-connection-dispatch (\d+):',log,re.M)==[str(i) for i in range(1,16)]
assert log.count('PASS forge-connection-dispatch total=15')==1
assert log.count('PASS: production command tree accepts unquoted device digests and legacy rule IDs, glob spaces and ban reasons; rejects non-admin access and invalid pages')==1
assert log.count('PASS: eight actual legacy custom-payload writes, 30000-byte bounds, readable slice and defensive ownership')==1

# Reuse the actual initial static checker definitions/loop, without its writes or
# stale initial-source checks. This second execution targets the frozen final pins.
source=(CACHE/'build-report-01/collect-build-evidence.py').read_text(encoding='utf8')
tree=ast.parse(source)
definitions=[]
for node in tree.body:
    if isinstance(node,ast.Assert): break
    definitions.append(node)
ns={'__file__':str(HERE/'extend-build-report.py')}
exec(compile(ast.Module(body=definitions,type_ignores=[]),'<preserved-first-static-checker-definitions>','exec'),ns)
final_build=copy.deepcopy(new_build)
final_build['artifacts']=[r for r in first_build['artifacts'] if '/fabric/' in r['path']]+new_build['artifacts']
ns['build']=final_build
audit_loop=source[source.index("catalog=ROOT/'catalog/blacklist-extension.tsv'"):source.index("save(HERE/'artifact-audit.json'")]
audit_loop=audit_loop.replace("f'{loader}-44-01'","(f'{loader}-44-03' if loader=='forge' else f'{loader}-44-01')")
audit_loop=audit_loop.replace("   generated=p/'build/generated/sources/shared1171/main'/rel", "   if loader=='forge':adapted=adapted.replace('org.slf4j.Logger;', 'org.apache.logging.log4j.Logger;').replace('org.slf4j.LoggerFactory;', 'org.apache.logging.log4j.LogManager;').replace('LoggerFactory.getLogger(', 'LogManager.getLogger(')\n   generated=p/'build/generated/sources/shared1171/main'/rel")
exec(compile(audit_loop,'<final-four-artifact-static-checks>','exec'),ns)
artifacts=ns['artifacts']
for artifact in artifacts:
    artifact['buildAttempt']='build-03' if artifact['loader']=='forge' else 'build-01'
    if artifact['loader']=='forge': artifact['exactJarCoreChecks']['report']='adapter-build-1.17.1/core-forge-03-result.json'

frozen=obj(CACHE/'frozen-candidate-03/artifacts.json')
assert len(frozen)==4
for entry in frozen:
    p=CACHE/'frozen-candidate-03'/entry['name']
    assert sha(p)==entry['sha256'] and p.stat().st_size==entry['bytes']
    match=[r for r in final_build['artifacts'] if Path(r['path']).name==entry['name']]
    assert len(match)==1 and match[0]['sha256']==entry['sha256'] and match[0]['bytes']==entry['bytes']
old_forge=next(a for a in initial['artifacts'] if a['loader']=='forge')
superseded=CACHE/'frozen-candidate-02'/Path(old_forge['artifact']['path']).name
assert sha(superseded)==old_forge['artifact']['sha256']
superseded_source=CACHE/'frozen-candidate-02'/Path(old_forge['sourceJar']['path']).name
assert sha(superseded_source)==old_forge['sourceJar']['sha256']
new_forge=next(a for a in artifacts if a['loader']=='forge')
with zipfile.ZipFile(superseded) as before,zipfile.ZipFile(ROOT/new_forge['artifact']['path']) as after:
    assert before.testzip() is None
    assert set(before.namelist())==set(after.namelist())
    changed_classes=[n for n in before.namelist() if n.endswith('.class') and before.read(n)!=after.read(n)]
    assert changed_classes==['cn/qizhang/guard/forge/GuardForge.class','cn/qizhang/guard/minecraft/MinecraftGuard.class']
    cp=ns['utf_constants']
    all_classes=[n for n in after.namelist() if n.endswith('.class')]
    slf_before=[n for n in all_classes if any('org/slf4j/' in s or 'org.slf4j.' in s for s in cp(before.read(n)))]
    slf_after=[n for n in all_classes if any('org/slf4j/' in s or 'org.slf4j.' in s for s in cp(after.read(n)))]
    assert slf_before==changed_classes and slf_after==[]
    for name in changed_classes: assert any('org/apache/logging/log4j/' in s for s in cp(after.read(name)))
    availability=cp(after.read('cn/qizhang/guard/forge/GuardForge$1.class'))
    assert 'isRemotePresent' not in availability and 'm_129536_' in availability and 'm_129538_' in availability
guard_source=ROOT/'platforms/1.17.1/forge/src/main/java/cn/qizhang/guard/forge/GuardForge.java'
guard_text=guard_source.read_text(encoding='utf8')
assert 'return origin.isConnected() && origin.getPacketListener() == player.connection;' in guard_text
assert not re.search(r'\bCHANNEL\.isRemotePresent\s*\(',guard_text)

audit={'passed':True,'currentFinalArtifacts':artifacts,'frozenManifestVerified':True,
       'javaInvokedByCollector':False,'allFourArchivesCrcLicenseMetadataClassAndSourceChecksPassed':True}
save(HERE/'final-artifact-audit.json',audit)
change_report={'passed':True,'sourceChanges':changes,'sourceFilesCompared':len(new_build['sourceSha256']),
    'changedBinaryClasses':changed_classes,'otherProductionClassesByteIdentical':True,
    'previousAvailabilityFixUnchanged':True,'livePlayConnectionGateRetained':True,
    'strictPolicyAndEmbedded44DefaultsUnchanged':True,
    'previousProductSlF4jReferenceClasses':slf_before,'finalProductSlf4jReferenceClasses':slf_after,
    'finalForgeUsesExistingLog4jBackend':True,'loggingImplementationBundled':False,
    'fabricBinaryAndSourceJarUnchanged':True,
    'reason':'Forge 37 provided no SLF4J provider for these first-party log calls. Forge-only generated MinecraftGuard imports/factory and GuardForge startup logging now use the existing Log4j backend, so decision/save-error logging does not depend on an absent SLF4J provider. Fabric sources and artifacts are unchanged.',
    'boundary':'Static change and build/core checks only. A production TCP or graphical-client result is not inferred here.'}
save(HERE/'forge-logging-fix-review.json',change_report)

files=[(REPORT,'build-02-report.json',False)]
for name in ('result.json','plan.json','console.log','daemon-java-version.log','target-java-version.log','executed-build_target.py'):
    files.append((CACHE/'builds/build-03'/name,'build-03-'+name,False))
for name in ('result.json','artifact-origin.log','catalog.log','compile-runners.log','java-version.log','security.log'):
    files.append((CACHE/'core-checks/forge-44-03'/name,'core-forge-03-'+name,False))
files.extend([(CACHE/'frozen-candidate-03/artifacts.json','frozen-candidate-03-artifacts.json',False),
              (HERE/'final-artifact-audit.json','build-03-artifact-audit.json',True),
              (HERE/'forge-logging-fix-review.json','forge-logging-fix-review.json',True),
              (guard_source,'build-03-GuardForge.java',False),
              (ROOT/'platforms/1.17.1/build.gradle','build-03-parent-build.gradle',False),
              (ROOT/'platforms/1.17.1/forge/build/generated/sources/shared1171/main/cn/qizhang/guard/minecraft/MinecraftGuard.java','build-03-generated-MinecraftGuard.java',False),
              (Path(__file__),'extend-build-report-03.py',False)])
patterns=[rb'(?i)(?:ghp_|gho_|github_pat_|glpat-)[A-Za-z0-9_\-]{16,}',
          rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'(?i)Authorization\s*:\s*Bearer\s+\S+']
for path,name,_ in files:
    assert not (OUT/name).exists()
    assert not any(re.search(p,path.read_bytes()) for p in patterns),name
assert len(files)==len(set(name for _,name,_ in files))

report=copy.deepcopy(initial)
report['generatedAtUtc']=datetime.now(timezone.utc).isoformat()
report['scope']='Compilation, platform API smoke checks, static artifact/source provenance and core checks from the final Fabric build-01 and repaired Forge build-03 JARs. Earlier successful build/core evidence remains historical; no server/TCP/GUI acceptance is included.'
report['previousIncrementalBuildReport']={'file':'adapter-build-1.17.1/build-02-report.json',
    'sha256':INITIAL,'bytes':len(initial_bytes),'rawBytesPreserved':True,
    'attachmentsCount':60,'allPreviousAttachmentsUnchanged':True}
report['attempts'][2]['supersededForgeArtifacts']=True
report['attempts'].append({'attempt':'build-03','target':'forge','configureOnly':False,'exitCode':0,
    'elapsedSeconds':new_build['elapsedSeconds'],'productArtifactCount':1,'sourceArtifactCount':1,
    'result':'adapter-build-1.17.1/build-03-result.json','console':'adapter-build-1.17.1/build-03-console.log',
    'reason':'Use the existing Log4j backend in Forge entry and Forge-only generated shared logging; retain strict policy and availability fix.'})
report['finalBuild']={'artifactOrigins':{'fabric':'build-01','forge':'build-03'},'latestAttempt':'build-03',
    'exitCode':0,'elapsedSeconds':new_build['elapsedSeconds'],'actionableTasks':15,'tasksExecuted':13,
    'tasksFromCache':2,'cachedTasks':cached,'realSmokeTasksExecuted':[':forge:commandParserSmoke',':forge:connectionDispatchSmoke',':forge:legacyPayloadSmoke'],
    'standardTestTaskExecuted':True,'sourceFileCount':len(new_build['sourceSha256']),
    'sourceFilesStillMatch':True,'sourceChangeSinceBuild02Count':2,
    'previousArtifactsRehashed':23,'previousArtifactsUnchanged':True,'previousArtifactsRebuiltOrRetested':False}
report['artifacts']=artifacts
report['currentFinalArtifacts']=[{**row,'originBuild':'build-03' if '/forge/' in row['path'] else 'build-01',
    'frozenCopyVerified':True} for row in final_build['artifacts']]
report['historicalSupersededArtifacts']['build02']={'forgeBinary':{**old_forge['artifact'],'retainedCacheCopy':str(superseded),
    'retainedCopyRehashed':True},'forgeSourceJar':{**old_forge['sourceJar'],'retainedCacheCopy':str(superseded_source),
    'retainedCopyAvailable':True,'retainedCopyRehashed':True}}
report['coreChecks']['historicalAdditionalExactJarCheckExecutions']=208
report['coreChecks']['allRecordedExactJarCheckExecutions']=416
report['coreChecks']['countingBoundary']='104 checks = 57 security cases + 44 exact catalog-rule checks + 3 preservation/ordinary-ID controls. The two final JARs account for 208 executions; superseded Forge build-01/build-02 add 208 historical executions. None of these totals is a count of different primitive assertions.'
report['platformChecks']['fabric']['evidenceBuild']='build-01'
report['platformChecks']['forge']['evidenceBuild']='build-03'
report['platformChecks']['forge']['compileSmokeJavaFromCache']=True
report['platformChecks']['forge']['compileTestJavaFromCache']=True
report['platformChecks']['forge']['smokeJavaExecutionFromCache']=False
report['securityReview']['appliesToInitialBuild']=True
report['securityReview']['sourceFreezeMatched']='At the initial-build review; later Forge-only availability and logging changes are separately recorded.'
report['securityReview']['finalLoggingFixReview']='adapter-build-1.17.1/forge-logging-fix-review.json'
report['forgeLoggingFix']=change_report
report['repositoryChangesRestrictedToNewReportAndAttachments']=False
report['repositoryChangesRestrictedToAuthorizedIncrementalReportAndNewAttachments']=True
report['limitations'].append('Forge build-03 adds explicit Forge-only Log4j adaptation; no logging backend runtime result is inferred from static reference checks.')

new_rows=[]
for path,name,derived in files:
    data=path.read_bytes()
    new_rows.append({'file':'adapter-build-1.17.1/'+name,'publicFile':'outputs/adapter-build-1.17.1/'+name,
        'source':str(path),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
        'rawBytesPreserved':not derived,'derivedSummary':derived})
report['publicEvidence']+=new_rows
report['publicEvidenceCount']=len(report['publicEvidence'])
report['publicEvidenceBytes']=sum(r['bytes'] for r in report['publicEvidence'])
candidate=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf8')
assert not any(re.search(p,candidate) for p in patterns)
save(HERE/'final-report-candidate.json',report)

# Mutate only after every original and new input has been independently checked.
assert sha(REPORT)==INITIAL
for path,name,_ in files:
    with (OUT/name).open('xb') as f: f.write(path.read_bytes())
assert (OUT/'build-02-report.json').read_bytes()==initial_bytes
REPORT.write_bytes(candidate)
for row in report['publicEvidence']:
    p=ROOT/row['publicFile']; assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
assert {p.name for p in OUT.iterdir()}=={Path(r['file']).name for r in report['publicEvidence']}
summary={'passed':True,'report':str(REPORT),'reportSha256':sha(REPORT),'reportBytes':REPORT.stat().st_size,
    'previousReportSha256Preserved':sha(OUT/'build-02-report.json'),'previous60AttachmentsUnchanged':True,
    'newAttachments':len(files),'totalAttachments':len(report['publicEvidence']),
    'totalAttachmentBytes':report['publicEvidenceBytes'],'finalProductJars':2,'finalSourceJars':2,
    'finalExactJarCheckExecutions':208,'historicalAdditionalExactJarCheckExecutions':208,
    'javaInvoked':False,'runtimeAcceptanceClaimed':False}
save(HERE/'collection-result.json',summary)
print(json.dumps(summary,indent=2))
