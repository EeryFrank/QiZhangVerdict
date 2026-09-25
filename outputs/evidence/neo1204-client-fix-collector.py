from pathlib import Path
import hashlib, json, re, shutil, sys

ROOT = Path('E:/Codex_work/QiZhangVerdict')
BASE = Path('E:/CodexTemp/QiZhangVerdict/next-platforms/1.20.4')
FIX = BASE/'neoforge-client-fix'
BUILD = BASE/'builds/02-neoforge-client-fix'
WORK = BASE/'builds/03-javaexec-workdirs'
CORE = FIX/'artifact-core-01'
OLD = BASE/'future-client-fixtures/neoforge-1.20.4/runs/candidate-0.3.0-dev-01'
CLIENT = BASE/'future-client-fixtures/neoforge-1.20.4/runs/candidate-0.3.0-dev-02'
SERVER = BASE/'servers/neoforge-02'
PREFIX = 'neo1204-client-fix-'
def read(path): return json.loads(path.read_text('utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def ref(path): return {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size}
def save(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as out: json.dump(value, out, indent=2, ensure_ascii=False); out.write('\n')

build, work, core = read(BUILD/'result.json'), read(WORK/'result.json'), read(CORE/'result.json')
client, old, visual = read(CLIENT/'result.json'), read(OLD/'result.json'), read(CLIENT/'visual-review-mods.json')
server, protocol = read(SERVER/'smoke-result.json'), read(SERVER/'protocol-result.json')
assert build['buildSuccessful'] and build['oldArtifactsUnchanged'] and build['sourceUnchanged']
assert work['buildSuccessful'] and work['oldArtifactsUnchanged'] and work['sourceUnchanged']
artifact = build['artifacts'][0]
assert artifact['sha256'] == '1552dabe78c522daf615922a0644e357884f6909a8925f94c6a8b16618f5132b'
assert sha(ROOT/artifact['path']) == artifact['sha256'] and artifact['bytes'] == 95633
assert core['passed'] and core['artifactUnchanged'] and core['sha256'] == artifact['sha256']
security = (CORE/'security.log').read_text()
catalog = (CORE/'catalog.log').read_text()
assert [int(x) for x in re.findall(r'^PASS (\d+):', security, re.M)] == list(range(1,58))
assert [int(x) for x in re.findall(r'^PASS rule (\d+):', catalog, re.M)] == list(range(1,38))
assert [int(x) for x in re.findall(r'^PASS control (\d+):', catalog, re.M)] == list(range(1,4))
for folder in (BUILD, WORK):
    log = (folder/'gradle.log').read_text()
    assert [int(x) for x in re.findall(r'^PASS client-dispatch (\d+):', log, re.M)] == list(range(1,10))
    assert ':neoforge:payloadCodecSmoke' in log
assert ':neoforge:commandParserSmoke' in (BUILD/'gradle.log').read_text()
assert protocol['passed'] == len(protocol['cases']) == 26 and server['exit_code'] == 0 and server['protocol_exit_code'] == 0
assert server['guard_sha256'] == artifact['sha256'] and server['all_requested_checks_passed']
assert client['automatedPassed'] and client['strict13DefaultsUnchanged'] and client['default37RulesUnchanged']
assert client['candidate']['sha256'] == artifact['sha256'] and client['onlineObservationSeconds'] >= 60
assert client['clientExitCode'] == client['serverExitCode'] == 0 and client['normalClientExit'] and client['normalServerExit']
assert client['exactSyntheticUUIDAndScopedDeviceAssociation'] and client['survivalModeConfirmed']
assert visual['visualPassed'] and visual['png']['sha256'] == client['pngs'][0]['sha256'] and sha(Path(client['pngs'][0]['path'])) == visual['png']['sha256']
assert not old['passed'] and old['candidate']['sha256'] == 'c3e742892ef723d035b81e165eed3ef4a560aa249349183298dd0f9b45e48f66'

whitelist = [
 ('diagnosis.json', FIX/'source-race-diagnosis.json'), ('jar-delta.json', FIX/'jar-static-delta.json'),
 ('pin-review.json', FIX/'pin-override-review.json'), ('build-helper.py', FIX/'build-neoforge.py'),
 ('workdir-helper.py', FIX/'rerun-javaexec.py'), ('collector.py', Path(__file__)),
 ('build-plan.json', BUILD/'plan.json'), ('build-result.json', BUILD/'result.json'), ('build.log', BUILD/'gradle.log'),
 ('workdir-plan.json', WORK/'plan.json'), ('workdir-result.json', WORK/'result.json'), ('workdir.log', WORK/'gradle.log'),
 ('core-result.json', CORE/'result.json'), ('core-helper.py', ROOT/'scripts/artifact_core_checks.py'),
 ('old-client-result.json', OLD/'result.json'), ('client-result.json', CLIENT/'result.json'),
 ('client-visual-review.json', CLIENT/'visual-review-mods.json'), ('server-result.json', SERVER/'smoke-result.json'),
 ('protocol-result.json', SERVER/'protocol-result.json'),
 ('initial-GuardNeoForge.java', FIX/'initial-candidate/GuardNeoForge.java'),
 ('initial-GuardNeoForgeClient.java', FIX/'initial-candidate/GuardNeoForgeClient.java'),
 ('working-directory-build.gradle', ROOT/'platforms/1.20.4/build.gradle'),
 ('working-directory-neoforge.gradle', ROOT/'platforms/1.20.4/neoforge/build.gradle'),
]
for name in ('java-version','compile-runners','artifact-origin','security','catalog'):
    whitelist.append(('core-'+name+'.log', CORE/(name+'.log')))
for name in ('GuardNeoForge','GuardNeoForgeClient','ClientChallengeDispatch'):
    path = ROOT/f'platforms/1.20.4/neoforge/src/main/java/cn/qizhang/guard/neoforge/{name}.java'
    assert sha(path) == build['sourceSha256'][path.relative_to(ROOT).as_posix()]
    whitelist.append((name+'.java', path))
test = ROOT/'platforms/1.20.4/neoforge/src/test/java/cn/qizhang/guard/neoforge/ClientChallengeDispatchSmoke.java'
assert sha(test) == build['sourceSha256'][test.relative_to(ROOT).as_posix()]
whitelist.append(('ClientChallengeDispatchSmoke.java', test))
for source in core['sourceFiles']:
    path = ROOT/source['path']; assert sha(path) == source['sha256']; whitelist.append((path.name,path))
assert sha(ROOT/'scripts/artifact_core_checks.py') == core['toolSha256']
for name in ('debug.log','latest.log'):
    whitelist.append(('payload-workdir-'+name,WORK/'runtime/neoforge-payload/logs'/name))

# Private inputs are compared in memory only; none are included in the whitelist.
private_values = set()
for directory in (OLD/'server', CLIENT/'server', SERVER):
    config = directory/'config/qizhangverdict'
    if (config/'server-id.txt').exists(): private_values.add((config/'server-id.txt').read_text().strip().lower())
    if (config/'accounts.state').exists():
        for line in (config/'accounts.state').read_text().splitlines():
            fields=line.split('\t')
            if fields[0]=='D' and len(fields)==3: private_values.add(fields[2].lower())
sys.path.insert(0,str(ROOT/'scripts'))
import next_client_runtime
raw_id=next_client_runtime.windows_installation_id()
if raw_id: private_values.add(raw_id.lower())
for run in (OLD,CLIENT):
    fallback=run/'client-game/config/qizhangverdict/installation-id.txt'
    if fallback.exists(): private_values.add(fallback.read_text().strip().lower())
private_values.discard('')
for _,source in whitelist:
    raw=source.read_bytes().lower()
    assert all(value.encode() not in raw for value in private_values), 'Private identifier present in '+source.name

evidence=[]
for label,source in whitelist:
    target=ROOT/'outputs/evidence'/(PREFIX+label)
    with source.open('rb') as inp,target.open('xb') as out: shutil.copyfileobj(inp,out)
    assert source.read_bytes()==target.read_bytes()
    evidence.append({'file':target.relative_to(ROOT/'outputs').as_posix(),'publicFile':target.relative_to(ROOT).as_posix(),
                     'sha256':sha(target),'bytes':target.stat().st_size,'originalPath':str(source),'rawBytesPreserved':True})
refs={label:{'publicFile':'outputs/evidence/'+PREFIX+label,'sha256':sha(source),'bytes':source.stat().st_size} for label,source in whitelist}
aggregates=[]
for filename in ('next-platform-server-validation.json','next-platform-client-validation.json'):
    path=ROOT/'outputs'/filename; assert path.exists() and artifact['sha256'] in path.read_text()
    aggregates.append({'publicFile':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'bytes':path.stat().st_size})
report={'schemaVersion':1,'profile':'neoforge-1.20.4','loaderVersion':'20.4.251','version':'0.3.0-dev','passed':True,
 'artifact':artifact,'oldCandidate':ref(FIX/'initial-candidate'/Path(artifact['path']).name),
 'initialFailure':{'passed':False,'kind':'real-client-required-report-timeout','originalOptionalValueObserved':False,
                   'uniqueOriginalFailureCauseEstablished':False,'result':refs['old-client-result.json']},
 'repair':{'productionScope':'NeoForge 1.20.4 adapter only; shared core and other adapters unchanged',
           'description':'Clientbound handling no longer depends on a network-time Optional player snapshot. It queues processing, checks the original live channel, and rechecks the same live connection before sending the asynchronous report.',
           'serverboundOwnershipPreserved':True,'strictPolicyRelaxed':False,'diagnosis':refs['diagnosis.json'],
           'officialSourceURL':'https://maven.neoforged.net/releases/net/neoforged/neoforge/20.4.251/neoforge-20.4.251-sources.jar',
           'oldFailureBoundary':'Official source and queued-event negative control establish a reproducible race consistent with the timeout; the original Optional value was not captured.'},
 'build':{'passed':True,'reportedGradleSeconds':32,'dispatchAssertions':9,'parserAndPayloadTasksPassed':True,
          'otherArtifactHashesUnchanged':True,'result':refs['build-result.json'],'log':refs['build.log']},
 'packagedCore':{'passed':True,'runtimeJavaMajor':17,'securityAssertions':57,'catalogAssertions':37,'controls':3,'total':97,'result':refs['core-result.json']},
 'jarStaticAudit':{'passed':True,'result':refs['jar-delta.json'],'rootLicenseAndNoticeExact':True,'license':'GPL-3.0-only','classMajor':61},
 'dedicatedRuntime':{'passed':True,'protocolAssertions':26,'serverExitCode':0,'protocolExitCode':0,'result':refs['server-result.json'],'protocol':refs['protocol-result.json'],
                     'boundary':'This synthetic TCP suite deliberately changes isolated policy branches. Default-policy proof comes from the separate real client fixture.'},
 'realClient':{'passed':True,'strictDefaultSettingCount':13,'strict13DefaultsUnchanged':True,'defaultRuleCount':37,'default37RulesUnchanged':True,
               'independentActualScopedDeviceMatch':True,'onlineObservationSeconds':client['onlineObservationSeconds'],'survivalModeConfirmed':True,
               'clientExitCode':0,'serverExitCode':0,'normalClientExit':True,'normalServerExit':True,'visualPassed':True,
               'pngSha256':client['pngs'][0]['sha256'],'result':refs['client-result.json'],'visualReview':refs['client-visual-review.json'],
               'boundary':'Loopback synthetic offline authentication; self-reported device identity is not trusted hardware attestation.'},
 'workingDirectoryAppendix':{'passed':True,'tasks':[':neoforge:payloadCodecSmoke',':neoforge:clientChallengeDispatchSmoke'],
              'reportedGradleSeconds':17,'jarRebuilt':False,'allJarHashesUnchanged':True,'result':refs['workdir-result.json'],
              'payloadLogsUnderCodexTemp':True,'dispatchWorkingDirectoryUnderCodexTemp':True,
              'configurationTiming':'Working-directory-only Gradle edits followed the successful candidate build and runtime. The final sources are pinned by this separate receipt; no product Java or JAR bytes changed.'},
 'runtimeAggregates':aggregates,'privacy':{'explicitFileWhitelist':True,'rawStateOrIdentifierFilesPublished':False,'privateValueMatches':0,
       'fullMinecraftDisassemblyPublished':False,'privateLaunchPlanPublished':False},'publicEvidence':evidence,
 'publicEvidenceCount':len(evidence),'publicEvidenceBytes':sum(x['bytes'] for x in evidence),'noCommitOrPushPerformedByCollector':True}
path=ROOT/'outputs/neoforge-1.20.4-client-fix-validation.json';save(path,report)
print(json.dumps({'report':str(path),'sha256':sha(path),'evidenceFiles':len(evidence),'evidenceBytes':report['publicEvidenceBytes'],'passed':True}))
