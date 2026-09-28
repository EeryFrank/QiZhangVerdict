# SPDX-License-Identifier: GPL-3.0-only
"""Append the authorized Forge repair evidence; preserve every initial public byte."""
from pathlib import Path
import ast, copy, hashlib, json, re, sys, zipfile
from datetime import datetime, timezone
sys.dont_write_bytecode = True
ROOT = Path('E:/Codex_work/QiZhangVerdict')
CACHE = Path('E:/CodexTemp/QiZhangVerdict/compat-1.17.1')
HERE = CACHE/'build-report-02'
REPORT = ROOT/'outputs/adapter-build-1.17.1.json'
OUT = ROOT/'outputs/adapter-build-1.17.1'
INITIAL = 'b2fd1942c8e4200fef26d495eeb77a0c77c9d2005a954d4e33ccfda4c3150bc9'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def obj(p): return json.loads(Path(p).read_text(encoding='utf8'))
def save(p, value):
    with Path(p).open('x',encoding='utf8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')

assert sha(REPORT)==INITIAL
initial_bytes=REPORT.read_bytes(); initial=obj(REPORT)
assert len(initial['publicEvidence'])==42
for row in initial['publicEvidence']:
    p=ROOT/row['publicFile']; assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
assert {p.name for p in OUT.iterdir()}=={Path(r['file']).name for r in initial['publicEvidence']}
assert not (OUT/'initial-build-report.json').exists()

old_build=obj(CACHE/'builds/build-01/result.json')
new_build=obj(CACHE/'builds/build-02/result.json')
assert new_build['exitCode']==0 and new_build['sourcesUnchanged'] and new_build['previousArtifactsUnchanged']
assert new_build['target']=='forge' and not new_build['configureOnly']
assert sha(CACHE/'builds/build-02/console.log')==new_build['logSha256']
for name,expected in new_build['sourceSha256'].items(): assert sha(ROOT/name)==expected
changes=[{'path':name,'initialSha256':old_build['sourceSha256'].get(name),'finalSha256':value}
         for name,value in new_build['sourceSha256'].items() if old_build['sourceSha256'].get(name)!=value]
assert len(changes)==1 and changes[0]['path']=='platforms/1.17.1/forge/src/main/java/cn/qizhang/guard/forge/GuardForge.java'
for row in new_build['previousArtifacts']:
    p=ROOT/row['path']; assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
assert len(new_build['previousArtifacts'])==23
log=(CACHE/'builds/build-02/console.log').read_text(encoding='utf8')
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
final_build['artifacts']=[r for r in old_build['artifacts'] if '/fabric/' in r['path']]+new_build['artifacts']
ns['build']=final_build
audit_loop=source[source.index("catalog=ROOT/'catalog/blacklist-extension.tsv'"):source.index("save(HERE/'artifact-audit.json'")]
audit_loop=audit_loop.replace("f'{loader}-44-01'","(f'{loader}-44-02' if loader=='forge' else f'{loader}-44-01')")
exec(compile(audit_loop,'<final-four-artifact-static-checks>','exec'),ns)
artifacts=ns['artifacts']
for artifact in artifacts:
    artifact['buildAttempt']='build-02' if artifact['loader']=='forge' else 'build-01'
    if artifact['loader']=='forge': artifact['exactJarCoreChecks']['report']='adapter-build-1.17.1/core-forge-02-result.json'

frozen=obj(CACHE/'frozen-candidate-02/artifacts.json')
assert len(frozen)==4
for entry in frozen:
    p=CACHE/'frozen-candidate-02'/entry['name']
    assert sha(p)==entry['sha256'] and p.stat().st_size==entry['bytes']
    match=[r for r in final_build['artifacts'] if Path(r['path']).name==entry['name']]
    assert len(match)==1 and match[0]['sha256']==entry['sha256'] and match[0]['bytes']==entry['bytes']
old_forge=next(a for a in initial['artifacts'] if a['loader']=='forge')
superseded=CACHE/'superseded-build-01/artifacts'/Path(old_forge['artifact']['path']).name
assert sha(superseded)==old_forge['artifact']['sha256']
new_forge=next(a for a in artifacts if a['loader']=='forge')
with zipfile.ZipFile(superseded) as before,zipfile.ZipFile(ROOT/new_forge['artifact']['path']) as after:
    assert before.testzip() is None
    assert set(before.namelist())==set(after.namelist())
    changed_classes=[n for n in before.namelist() if n.endswith('.class') and before.read(n)!=after.read(n)]
    assert changed_classes==['cn/qizhang/guard/forge/GuardForge$1.class','cn/qizhang/guard/forge/GuardForge.class']
    cp=ns['utf_constants']
    assert 'isRemotePresent' in cp(before.read(changed_classes[0]))
    assert 'isRemotePresent' not in cp(after.read(changed_classes[0]))
    assert 'm_129536_' in cp(after.read(changed_classes[0])) and 'm_129538_' in cp(after.read(changed_classes[0]))
guard_source=ROOT/changes[0]['path']
guard_text=guard_source.read_text(encoding='utf8')
assert 'return origin.isConnected() && origin.getPacketListener() == player.connection;' in guard_text
assert not re.search(r'\bCHANNEL\.isRemotePresent\s*\(',guard_text)

audit={'passed':True,'currentFinalArtifacts':artifacts,'frozenManifestVerified':True,
       'javaInvokedByCollector':False,'allFourArchivesCrcLicenseMetadataClassAndSourceChecksPassed':True}
save(HERE/'final-artifact-audit.json',audit)
change_report={'passed':True,'sourceChanges':changes,'sourceFilesCompared':len(new_build['sourceSha256']),
    'changedBinaryClasses':changed_classes,'otherProductionClassesByteIdentical':True,
    'binaryAvailabilityGateNoLongerCallsFmlIsRemotePresent':True,'livePlayConnectionGateRetained':True,
    'strictPolicyAndEmbedded44DefaultsUnchanged':True,
    'reason':'Forge 37 isRemotePresent describes FML negotiation. This transport also accepts vanilla protocol peers reporting through the QZGuard channel. Availability now requires the same live PLAY connection/listener identity without requiring FML-only remote-presence metadata.',
    'boundary':'Static change and build/core checks only. A production TCP or graphical-client result is not inferred here.'}
save(HERE/'forge-channel-fix-review.json',change_report)

files=[(REPORT,'initial-build-report.json',False)]
for name in ('result.json','plan.json','console.log','daemon-java-version.log','target-java-version.log','executed-build_target.py'):
    files.append((CACHE/'builds/build-02'/name,'build-02-'+name,False))
for name in ('result.json','artifact-origin.log','catalog.log','compile-runners.log','java-version.log','security.log'):
    files.append((CACHE/'core-checks/forge-44-02'/name,'core-forge-02-'+name,False))
files.extend([(CACHE/'frozen-candidate-02/artifacts.json','frozen-candidate-02-artifacts.json',False),
              (HERE/'final-artifact-audit.json','final-artifact-audit.json',True),
              (HERE/'forge-channel-fix-review.json','forge-channel-fix-review.json',True),
              (guard_source,'final-GuardForge.java',False),
              (Path(__file__),'extend-build-report.py',False)])
patterns=[rb'(?i)(?:ghp_|gho_|github_pat_|glpat-)[A-Za-z0-9_\-]{16,}',
          rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'(?i)Authorization\s*:\s*Bearer\s+\S+']
for path,name,_ in files:
    assert not (OUT/name).exists()
    assert not any(re.search(p,path.read_bytes()) for p in patterns),name
assert len(files)==len(set(name for _,name,_ in files))

report=copy.deepcopy(initial)
report['generatedAtUtc']=datetime.now(timezone.utc).isoformat()
report['scope']='Compilation, platform API smoke checks, static artifact/source provenance and core checks from the final Fabric build-01 and repaired Forge build-02 JARs. Earlier successful build/core evidence remains historical; no server/TCP/GUI acceptance is included.'
report['initialBuildReport']={'file':'adapter-build-1.17.1/initial-build-report.json',
    'sha256':INITIAL,'bytes':len(initial_bytes),'rawBytesPreserved':True,
    'initialAttachmentsCount':42,'allInitialAttachmentsUnchanged':True}
report['attempts'][1]['supersededForgeArtifacts']=True
report['attempts'][1]['fabricRemainsFinal']=True
report['attempts'].append({'attempt':'build-02','target':'forge','configureOnly':False,'exitCode':0,
    'elapsedSeconds':new_build['elapsedSeconds'],'productArtifactCount':1,'sourceArtifactCount':1,
    'result':'adapter-build-1.17.1/build-02-result.json','console':'adapter-build-1.17.1/build-02-console.log',
    'reason':'Remove FML-only remote-presence predicate while retaining live PLAY connection/listener ownership.'})
report['finalBuild']={'artifactOrigins':{'fabric':'build-01','forge':'build-02'},'latestAttempt':'build-02',
    'exitCode':0,'elapsedSeconds':new_build['elapsedSeconds'],'actionableTasks':15,'tasksExecuted':13,
    'tasksFromCache':2,'cachedTasks':cached,'realSmokeTasksExecuted':[':forge:commandParserSmoke',':forge:connectionDispatchSmoke',':forge:legacyPayloadSmoke'],
    'standardTestTaskExecuted':True,'sourceFileCount':len(new_build['sourceSha256']),
    'sourceFilesStillMatch':True,'sourceChangeSinceBuild01Count':1,
    'previousArtifactsRehashed':23,'previousArtifactsUnchanged':True,'previousArtifactsRebuiltOrRetested':False}
report['artifacts']=artifacts
report['currentFinalArtifacts']=[{**row,'originBuild':'build-02' if '/forge/' in row['path'] else 'build-01',
    'frozenCopyVerified':True} for row in final_build['artifacts']]
report['historicalSupersededArtifacts']={'forgeBinary':{**old_forge['artifact'],'retainedCacheCopy':str(superseded),
    'retainedCopyRehashed':True},'forgeSourceJar':{**old_forge['sourceJar'],'retainedCopyAvailable':False,
    'historicalHashEvidenceOnly':True,'boundary':'The original source JAR was overwritten by the authorized rebuild; its prior audited hash/size remain in initial report and raw build-01 receipt. This report does not claim the old source JAR is still available.'}}
report['coreChecks']['historicalAdditionalExactJarCheckExecutions']=104
report['coreChecks']['allRecordedExactJarCheckExecutions']=312
report['coreChecks']['countingBoundary']='104 checks = 57 security cases + 44 exact catalog-rule checks + 3 preservation/ordinary-ID controls. The two final JARs account for 208 executions; the superseded Forge build-01 adds 104 historical executions. None of these totals is a count of different primitive assertions.'
report['platformChecks']['fabric']['evidenceBuild']='build-01'
report['platformChecks']['forge']['evidenceBuild']='build-02'
report['platformChecks']['forge']['compileSmokeJavaFromCache']=True
report['platformChecks']['forge']['compileTestJavaFromCache']=True
report['platformChecks']['forge']['smokeJavaExecutionFromCache']=False
report['securityReview']['appliesToInitialBuild']=True
report['securityReview']['sourceFreezeMatched']='At the initial-build review; GuardForge.java changed once for build-02.'
report['securityReview']['finalChannelFixReview']='adapter-build-1.17.1/forge-channel-fix-review.json'
report['forgeChannelAvailabilityFix']=change_report
report['repositoryChangesRestrictedToNewReportAndAttachments']=False
report['repositoryChangesRestrictedToAuthorizedIncrementalReportAndNewAttachments']=True
report['limitations'].append('The source-review-01 report is preserved as the initial snapshot; only the explicit Forge availability change was added for build-02.')

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
assert (OUT/'initial-build-report.json').read_bytes()==initial_bytes
REPORT.write_bytes(candidate)
for row in report['publicEvidence']:
    p=ROOT/row['publicFile']; assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
assert {p.name for p in OUT.iterdir()}=={Path(r['file']).name for r in report['publicEvidence']}
summary={'passed':True,'report':str(REPORT),'reportSha256':sha(REPORT),'reportBytes':REPORT.stat().st_size,
    'initialReportSha256Preserved':sha(OUT/'initial-build-report.json'),'initial42AttachmentsUnchanged':True,
    'newAttachments':len(files),'totalAttachments':len(report['publicEvidence']),
    'totalAttachmentBytes':report['publicEvidenceBytes'],'finalProductJars':2,'finalSourceJars':2,
    'finalExactJarCheckExecutions':208,'historicalAdditionalExactJarCheckExecutions':104,
    'javaInvoked':False,'runtimeAcceptanceClaimed':False}
save(HERE/'collection-result.json',summary)
print(json.dumps(summary,indent=2))
