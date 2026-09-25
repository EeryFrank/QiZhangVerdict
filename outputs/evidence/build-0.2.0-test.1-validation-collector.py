#!/usr/bin/env python3
"""Collect immutable build receipts and exact-JAR tests; never runs a build or Minecraft."""
import argparse, collections, datetime, hashlib, json, re, shutil, struct, tomllib, zipfile
from pathlib import Path

ROOT=Path('E:/Codex_work/QiZhangVerdict')
BASE=Path('E:/CodexTemp/QiZhangVerdict/release-0.2.0-test.1')
VERSION='0.2.0-test.1'
TARGETS=['root','1.20.1','1.21.1','1.19.4','1.18.2','1.16.5','1.12.2','1.8.9']
PUBLISHED={
 'bukkit':('0.1.1','e1194b8b694763afbc431e22799f40d357dd80493d194f680edfb219afe94845'),
 'fabric-1.20.1':('0.1.1','befb27baf8e567f0802bcc4372916dd45ee16052f18080d7829f4fff02add6c1'),
 'forge-1.20.1':('0.1.1','96c5dd4ea030f9c18f6db140a12f98ad7d8a391bf5c8092ce86a070afea8dee8'),
 'fabric-1.21.1':('0.1.1','f16ccdf24296b58fe6593b99617e87b10a9a72c476909d9c8de5cc0cf3f8f989'),
 'neoforge-1.21.1':('0.1.1','de6d25ccff28dcc94e705f4531d6e7ac9e11805e27fbf0c9af174624cd6a0602'),
 'fabric-1.19.4':('0.2.0-dev','c626ba359aa3a79c3e5215b590f990a6134b0de2060251701bec3eeae999a21f'),
 'forge-1.19.4':('0.2.0-dev','b4e724bb64514ce75263e9c92f2ebbb9a2b95a90c11855708e76d64cc234d154'),
 'fabric-1.18.2':('0.2.0-dev','65ad6fafe4eee0f326d3eebe67465e30022972e800fd1d93ac7c068cf6d613c5'),
 'forge-1.18.2':('0.2.0-dev','c2823b070719ace443fca7ad48ae58a13f6b70d575dafbeaeb0f676aa682e4ff'),
 'fabric-1.16.5':('0.2.0-dev','d9bb0837f97ccf30c4b0f19a5cd8b65197eab4b2c5137b246b0e56c94fe6aae6'),
 'forge-1.16.5':('0.2.0-dev','52e68051478f7e9b257432e895d81f48b54a8974f2a2a03d5f9af14d59e15779'),
 'forge-1.12.2':('0.2.0-dev','7ee00ced99919281e2d6851e123c6bcb2d8ddd3e46338870b2034d5a5dcf0966'),
 'forge-1.8.9':('0.2.0-dev','f00943b06e87dbfc04e88336134ab4ae1a571a6e9b53924ab6bc06b311918424'),
}
def digest(data): return hashlib.sha256(data).hexdigest()
def sha(path): return digest(Path(path).read_bytes())
def read(path): return json.loads(Path(path).read_text('utf-8'))
def save(path,value): Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def identity(path):
    name=Path(path).name
    return name[len('qizhangverdict-'):-len('-'+VERSION+'.jar')] if name.startswith('qizhangverdict-') and name.endswith('-'+VERSION+'.jar') else None

def class_annotations(data):
    """Read class-level annotation values directly from a classfile, without loading it."""
    class Reader:
        def __init__(self,data): self.data=data;self.pos=0
        def take(self,n):
            assert self.pos+n<=len(self.data)
            v=self.data[self.pos:self.pos+n];self.pos+=n;return v
        def number(self,n): return int.from_bytes(self.take(n),'big')
        def u1(self): return self.number(1)
        def u2(self): return self.number(2)
        def u4(self): return self.number(4)
    r=Reader(data);assert r.u4()==0xcafebabe;r.take(4)
    cp=[None]*r.u2();i=1
    while i<len(cp):
        tag=r.u1()
        if tag==1: cp[i]=r.take(r.u2()).decode('utf-8',errors='replace')
        elif tag in (3,4): cp[i]=r.u4()
        elif tag in (5,6): r.take(8);i+=1
        elif tag in (7,8,16,19,20): r.take(2)
        elif tag in (9,10,11,12,17,18): r.take(4)
        elif tag==15:r.take(3)
        else:raise AssertionError('Unexpected class constant tag '+str(tag))
        i+=1
    def annotation(a):
        kind=cp[a.u2()];values={}
        for _ in range(a.u2()):
            key=cp[a.u2()];values[key]=value(a)
        return {'type':kind,'values':values}
    def value(a):
        tag=chr(a.u1())
        if tag in 'BCDFIJSZs':return cp[a.u2()]
        if tag=='e':return {'enumType':cp[a.u2()],'enumValue':cp[a.u2()]}
        if tag=='c':return {'class':cp[a.u2()]}
        if tag=='@':return annotation(a)
        if tag=='[':return [value(a) for _ in range(a.u2())]
        raise AssertionError('Unexpected annotation tag '+tag)
    r.take(6);r.take(r.u2()*2)
    for _ in range(2):
        for _ in range(r.u2()):
            r.take(6)
            for _ in range(r.u2()):r.take(2);r.take(r.u4())
    result=[]
    for _ in range(r.u2()):
        name=cp[r.u2()];payload=r.take(r.u4())
        if name in ('RuntimeVisibleAnnotations','RuntimeInvisibleAnnotations'):
            a=Reader(payload);result.extend(annotation(a) for _ in range(a.u2()));assert a.pos==len(payload)
    assert r.pos==len(data)
    return result

COPIES={}
def evidence(source,label):
    source=Path(source); data=source.read_bytes()
    destination='outputs/evidence/'+label
    ref={'publicFile':destination,'sha256':digest(data),'bytes':len(data),'originalPath':str(source),'copyMode':'raw-byte-identical'}
    if destination in COPIES: assert COPIES[destination][1]==ref
    else: COPIES[destination]=(source,ref)
    return ref

def static_artifact(item):
    path=ROOT/item['path']; key=identity(item['path']); assert key in PUBLISHED
    assert sha(path)==item['sha256'] and path.stat().st_size==item['bytes']
    old_version,old_hash=PUBLISHED[key]
    old=path.with_name(path.name.replace(VERSION,old_version)); assert sha(old)==old_hash
    expected=65 if '1.21.1' in key else 61 if any(v in key for v in ('1.18.2','1.19.4','1.20.1')) else 52
    with zipfile.ZipFile(path) as z,zipfile.ZipFile(old) as previous:
        assert z.testzip() is None and previous.testzip() is None
        names=z.namelist(); assert len(names)==len(set(names))
        assert all(not n.startswith('/') and '..' not in n.split('/') for n in names)
        license_checks={}
        for name in ('LICENSE','NOTICE'):
            data=z.read(name); assert data==(ROOT/name).read_bytes()
            license_checks[name]={'entry':name,'sha256':digest(data),'bytes':len(data),'matchesRepositoryRootBytes':True}
        manifest=z.read('META-INF/MANIFEST.MF').decode('utf-8').replace('\r\n ','')
        attributes=dict(line.split(': ',1) for line in manifest.splitlines() if ': ' in line)
        assert attributes['License']=='GPL-3.0-only'
        assert attributes['Bundle-License']=='https://www.gnu.org/licenses/gpl-3.0.html'
        if key=='bukkit':
            descriptor_path='plugin.yml'; descriptor=z.read(descriptor_path).decode('utf-8')
            m=re.search(r'^version:\s*[\'\"]?([^\s\'\"]+)',descriptor,re.M); assert m
            version=m.group(1); descriptor_license=None
        elif key.startswith('fabric-'):
            descriptor_path='fabric.mod.json'; descriptor=json.loads(z.read(descriptor_path))
            assert descriptor['id']=='qizhangverdict';version=descriptor['version'];descriptor_license=descriptor['license']
        elif any(v in key for v in ('1.8.9','1.12.2')):
            descriptor_path='mcmod.info'; descriptor=json.loads(z.read(descriptor_path))[0]
            assert descriptor['modid']=='qizhangverdict';version=descriptor['version'];descriptor_license=descriptor['license']
        else:
            descriptor_path='META-INF/neoforge.mods.toml' if key.startswith('neoforge-') else 'META-INF/mods.toml'
            descriptor=tomllib.loads(z.read(descriptor_path).decode('utf-8'))
            mods=[m for m in descriptor['mods'] if m['modId']=='qizhangverdict'];assert len(mods)==1
            version=mods[0]['version'];descriptor_license=descriptor['license']
        assert version==VERSION
        assert descriptor_license is None or descriptor_license=='GPL-3.0-only'
        legacy_annotation=None
        if key in ('forge-1.8.9','forge-1.12.2'):
            suffix='189' if key=='forge-1.8.9' else '112'
            entry='cn/qizhang/guard/forge'+suffix+'/GuardForge'+suffix+'.class'
            annotations=[a for a in class_annotations(z.read(entry)) if a['type']=='Lnet/minecraftforge/fml/common/Mod;']
            assert len(annotations)==1
            values=annotations[0]['values']
            assert values['modid']=='qizhangverdict' and values['version']==VERSION,(key,'legacy Forge @Mod version',values.get('version'))
            legacy_annotation={'entry':entry,'annotationType':annotations[0]['type'],'version':values['version'],
                               'modid':values['modid'],'matchesDescriptor':True,'readFromPackagedClassBytes':True}
        classes={n:z.read(n) for n in names if n.endswith('.class')}
        old_classes={n:previous.read(n) for n in previous.namelist() if n.endswith('.class')}
        assert classes and all(v[:4]==b'\xca\xfe\xba\xbe' for v in classes.values())
        majors=collections.Counter(struct.unpack('>H',v[6:8])[0] for v in classes.values())
        assert max(majors)==expected and all(45<=major<=expected for major in majors)
        noncore={n:v for n,v in classes.items() if not n.startswith('cn/qizhang/guard/core/')}
        old_noncore={n:v for n,v in old_classes.items() if not n.startswith('cn/qizhang/guard/core/')}
        comparison=[]
        for name in sorted(noncore.keys()|old_noncore.keys()):
            before=old_noncore.get(name);after=noncore.get(name)
            delta={'class':name,'oldSha256':digest(before) if before is not None else None,'newSha256':digest(after) if after is not None else None,'identical':before is not None and before==after}
            if before is not None and after is not None and before!=after and legacy_annotation and name==legacy_annotation['entry']:
                old_constant=b'\x01'+len(old_version).to_bytes(2,'big')+old_version.encode('ascii')
                new_constant=b'\x01'+len(VERSION).to_bytes(2,'big')+VERSION.encode('ascii')
                delta['onlyVersionUtf8ConstantChanged']=after.count(new_constant)==1 and after.replace(new_constant,old_constant)==before
            comparison.append(delta)
        changed=[x['class'] for x in comparison if not x['identical']]
        core_changed=[n for n in sorted(classes.keys()|old_classes.keys()) if n.startswith('cn/qizhang/guard/core/') and classes.get(n)!=old_classes.get(n)]
        return {'id':key,'artifact':item,'passed':True,'zipCrcPassed':True,'duplicateEntries':False,
                'rootLicenseAndNotice':license_checks,'manifestLicense':attributes['License'],'bundleLicense':attributes['Bundle-License'],
                'descriptor':{'entry':descriptor_path,'sha256':digest(z.read(descriptor_path)),'version':version,'license':descriptor_license,
                              'bukkitLicenseLocation':'JAR manifest and root LICENSE; plugin.yml has no standard license key' if key=='bukkit' else None},
                'legacyForgeModAnnotation':legacy_annotation,
                'classMajor':{'expectedMaximum':expected,'counts':dict(sorted(majors.items())),'allWithinTarget':True},
                'embeddedCoreClassCount':len(classes)-len(noncore),
                'publishedComparison':{'oldArtifact':{'path':old.relative_to(ROOT).as_posix(),'version':old_version,'sha256':old_hash,'bytes':old.stat().st_size},
                    'nonCoreDefinition':'Every .class outside cn/qizhang/guard/core/, including platform, client reporter and mixin classes.',
                    'oldNonCoreClassCount':len(old_noncore),'newNonCoreClassCount':len(noncore),'allNonCoreClassBytesIdentical':not changed,
                    'changedAddedOrRemovedNonCoreClasses':changed,'nonCoreClasses':comparison,'changedCoreClasses':core_changed,
                    'interpretation':'Byte identity is a static bridge for unchanged platform classes only; this does not transfer prior Minecraft runtime acceptance to the new artifact.'}}

def collect(complete):
    build_cases=[]; artifacts=[]; excluded=[]; old_seen={}; build_refs=[]; core_refs=[]
    completed_targets=set()
    for target in TARGETS:
        reports=sorted((BASE/'builds').glob(target+'-*/result.json'))
        if not reports: continue
        successful_reports=[p for p in reports if read(p).get('buildSuccessful') and read(p).get('exitCode')==0]
        selected=successful_reports[-1] if successful_reports else None
        for path in reports:
            receipt=read(path);assert receipt['target']==target and receipt['version']==VERSION
            folder=path.parent;label='build-0.2.0-test.1-'+folder.name+'-'
            refs=[evidence(path,label+'receipt.json'),evidence(folder/'plan.json',label+'plan.json'),evidence(folder/'gradle.log',label+'gradle.log')]
            assert refs[-1]['sha256']==receipt['logSha256']
            text=(folder/'gradle.log').read_text('utf-8',errors='replace')
            successful=receipt.get('buildSuccessful') is True and receipt['exitCode']==0 and 'BUILD SUCCESSFUL' in text
            preserved=all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in receipt['oldArtifactSha256'].items())
            assert preserved==receipt['oldArtifactsUnchanged']
            for p,h in receipt['oldArtifactSha256'].items():
                normalized=Path(p).as_posix()
                if normalized in old_seen: assert old_seen[normalized]==h
                old_seen[normalized]=h
            source_matches=all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in receipt['sourceSha256'].items())
            source_drift=[{'path':Path(p).as_posix(),'recordedSha256':h,'currentSha256':sha(ROOT/p) if (ROOT/p).is_file() else None}
                          for p,h in receipt['sourceSha256'].items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
            # Raw logs retain dependency, compiler and Gradle warnings; successful exit does not erase them.
            case={'target':target,'attempt':folder.name,'exitCode':receipt['exitCode'],'buildSuccessful':successful,
                  'oldArtifactsUnchanged':preserved,'recordedSourceFilesMatchCurrentBytes':source_matches,
                  'sourceSnapshotDrift':source_drift,'selectedForProductSet':path==selected,
                  'startedUtc':receipt['startedUtc'],'finishedUtc':receipt['finishedUtc'],'availablePhysicalGiB':receipt['availablePhysicalGiB'],
                  'gameStarted':receipt['gameStarted'],'warningLines':len(re.findall(r'^.*(?:warning|warn\]|deprecated|deprecation).*$' ,text,re.I|re.M)),
                  'rawEvidence':refs,'productArtifactPaths':[],'excludedInternalArtifactPaths':[]}
            if not successful:
                case['failureSummary']='Gradle wrapper download failed certificate-chain validation (PKIX) before compilation; no Minecraft runtime was invoked.' if 'PKIX path building failed' in text and 'GradleWrapperMain' in text else 'Build failed; see immutable full console log.'
            if folder.name=='1.12.2-02':
                candidate=BASE/'pre-annotation-fix-112/qizhangverdict-forge-1.12.2-0.2.0-test.1.jar'
                candidate_hash=sha(candidate);assert candidate_hash==receipt['artifacts'][0]['sha256']
                entry='cn/qizhang/guard/forge112/GuardForge112.class'
                with zipfile.ZipFile(candidate) as z:
                    values=[a['values'] for a in class_annotations(z.read(entry)) if a['type']=='Lnet/minecraftforge/fml/common/Mod;'][0]
                    descriptor_version=json.loads(z.read('mcmod.info'))[0]['version']
                assert values['version']=='0.2.0-dev' and descriptor_version==VERSION
                case['notSelectedReason']='Successful compilation produced mismatched legacy Forge runtime annotation version; candidate preserved as an unpublished diagnostic and replaced by attempt 03.'
                case['unpublishedCandidateInspection']={'originalPath':str(candidate),'sha256':candidate_hash,'bytes':candidate.stat().st_size,
                    'annotationEntry':entry,'annotationVersion':values['version'],'descriptorVersion':descriptor_version,'versionConsistent':False,
                    'coreRegressionRun':False,'minecraftRuntimeRun':False}
            build_refs+=refs
            for item in receipt['artifacts']:
                if identity(item['path']) not in PUBLISHED:
                    excluded.append(dict(item,reason='Internal compatibility verification output; not an installable platform distribution and not counted among 13 products.'))
                    case['excludedInternalArtifactPaths'].append(item['path']);continue
                case['productArtifactPaths'].append(item['path'])
                if successful and path==selected: artifacts.append(item)
            build_cases.append(case)
            if successful and path==selected:
                assert target not in completed_targets,'Multiple successful attempts require manual selection'
                completed_targets.add(target)
    assert len({i['path'] for i in artifacts})==len(artifacts),'Multiple successful output attempts need explicit selection'
    pending=sorted(set(PUBLISHED)-{identity(i['path']) for i in artifacts})
    if complete: assert not pending and len(artifacts)==13,pending
    static=[static_artifact(item) for item in artifacts]
    core_cases=[]
    for item in artifacts:
        key=identity(item['path']);folder=BASE/'artifact-core'/Path(item['path']).stem
        if not (folder/'result.json').is_file():
            if complete: raise AssertionError('Missing core receipt '+key)
            continue
        result=read(folder/'result.json');assert result['sha256']==item['sha256'] and result['passed'] and result['artifactUnchanged']
        assert result['toolSha256']==sha(ROOT/'scripts/artifact_core_checks.py')
        assert all(sha(ROOT/x['path'])==x['sha256'] for x in result['sourceFiles'])
        checks={c['name']:c for c in result['checks']};assert set(checks)=={'java-version','compile-runners','artifact-origin','security','catalog'}
        refs=[evidence(folder/'result.json','artifact-core-0.2.0-test.1-'+key+'-receipt.json')]
        for name,check in checks.items():
            assert check['exitCode']==0 and check['passed'] and sha(folder/check['log'])==check['sha256']
            refs.append(evidence(folder/check['log'],'artifact-core-0.2.0-test.1-'+key+'-'+name+'.log'))
        security=(folder/'security.log').read_text('utf-8');catalog=(folder/'catalog.log').read_text('utf-8')
        assert [int(v) for v in re.findall(r'^PASS (\d+):',security,re.M)]==list(range(1,58))
        assert [int(v) for v in re.findall(r'^PASS rule (\d+):',catalog,re.M)]==list(range(1,38))
        assert [int(v) for v in re.findall(r'^PASS control (\d+):',catalog,re.M)]==[1,2,3]
        assert '37 exact catalog rules (33 DENY, 4 ALERT); 3 preservation and ordinary-ID controls passed' in catalog
        assert 'PASS: production GuardService loaded from the explicitly pinned artifact' in (folder/'artifact-origin.log').read_text('utf-8')
        runtime_major=8 if key=='bukkit' or any(v in key for v in ('1.8.9','1.12.2','1.16.5')) else 21
        assert ('jdk8' in result['java'])==(runtime_major==8)
        core_cases.append({'id':key,'artifact':item,'passed':True,'productionCoreOriginVerified':True,'artifactUnchanged':True,
            'securityCasesPassed':57,'exactCatalogRulesPassed':37,'catalogDenyRules':33,'catalogAlertRules':4,'additionalControlsPassed':3,
            'coreJavaRuntimeMajor':runtime_major,'compilerReleaseForTestRunners':8,'testJvmMaximumHeapMiB':128,'testJvmMaximumMetaspaceMiB':64,
            'productionClassesCompiledByTestHarness':False,'rawEvidence':refs})
        core_refs+=refs
    history=[]
    for name in ('bukkit-01','bukkit-02'):
        folder=BASE/'artifact-core'/name;result=read(folder/'result.json')
        refs=[evidence(folder/'result.json','artifact-core-0.2.0-test.1-historical-'+name+'-receipt.json')]
        for check in result['checks']:
            assert sha(folder/check['log'])==check['sha256']
            refs.append(evidence(folder/check['log'],'artifact-core-0.2.0-test.1-historical-'+name+'-'+check['log']))
        core_refs+=refs
        history.append({'attempt':name,'passed':result['passed'],'error':result.get('error'),'artifactSha256':result['sha256'],
            'countedAmong13':False,'classification':'Harness expected META-INF/LICENSE instead of the actual root LICENSE; no core test executed.' if name=='bukkit-01' else 'Successful intermediate verification of the same Bukkit artifact, superseded only for counting by its formally named directory.',
            'originalHarnessSha256':result['toolSha256'],'rawEvidence':refs})
    common_sources=[
        (BASE/'build-matrix.py','build-0.2.0-test.1-final-build-driver-snapshot.py','build'),
        (BASE/'check-built-artifacts.py','artifact-core-0.2.0-test.1-executed-batch-driver.py','core'),
        (ROOT/'scripts/artifact_core_checks.py','artifact-core-0.2.0-test.1-executed-harness.py','core'),
        (ROOT/'core/src/test/java/cn/qizhang/guard/core/SecurityRegressionTest.java','artifact-core-0.2.0-test.1-SecurityRegressionTest.java','core'),
        (ROOT/'core/src/test/java/cn/qizhang/guard/core/CatalogCompatibilityTest.java','artifact-core-0.2.0-test.1-CatalogCompatibilityTest.java','core'),
        (ROOT/'catalog/blacklist-extension.tsv','artifact-core-0.2.0-test.1-exact-catalog.tsv','core'),
        (BASE/'artifact-core/qizhangverdict-bukkit-0.2.0-test.1/ArtifactOriginCheck.java','artifact-core-0.2.0-test.1-ArtifactOriginCheck.java','core'),
        (Path(__file__),'build-0.2.0-test.1-validation-collector.py','build'),
    ]
    for source,label,group in common_sources:
        (build_refs if group=='build' else core_refs).append(evidence(source,label))
    for source in sorted(BASE.glob('build-matrix-snapshot-*.py')):
        build_refs.append(evidence(source,'build-0.2.0-test.1-observed-'+source.name))
    first_driver=BASE/'build-matrix-first-executed.py'
    if first_driver.exists():build_refs.append(evidence(first_driver,'build-0.2.0-test.1-first-build-driver.py'))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    old_refs=[{'path':p,'sha256':h,'matchesCurrentBytes':True} for p,h in sorted(old_seen.items())]
    build={'schemaVersion':1,'version':VERSION,'generatedUtc':now,'scope':'Local builds and static inspection of exact packaged distributions. This is not Minecraft dedicated-server, graphical-client, multiplayer, performance, or broad anti-cheat effectiveness acceptance.',
        'allBuildsPassed':completed_targets==set(TARGETS),'allAttemptsSuccessful':all(c['buildSuccessful'] for c in build_cases),'failedAttemptCount':sum(not c['buildSuccessful'] for c in build_cases),
        'allStaticArtifactChecksPassed':len(static)==13 and all(c['passed'] for c in static),
        'productArtifactCount':len(static),'expectedProductArtifactCount':13,'pendingProducts':pending,'buildTargetCount':len({c['target'] for c in build_cases}),'buildAttemptCount':len(build_cases),
        'completedBuildTargets':sorted(completed_targets),'buildSuccessMeaning':'Each required target has a successful final attempt. Earlier failed attempts remain listed and are not reclassified as successes.',
        'sourceSnapshotMeaning':'Build receipts snapshot all project Java sources, including unrelated platforms. Any later source-byte differences are listed per attempt without rewriting historical receipts.',
        'buildDriverObservation':'The first and final build driver snapshots are retained. After the 1.12.2 wrapper PKIX failure, the final driver selects the existing E:/CodexTemp/Gradle/XiuXianZhuan Gradle cache for 1.12.2 and sets CI=true for later builds to avoid development source remapping. The original receipts do not record CI; no historical receipt has been backfilled. No TLS validation was disabled.',
        'oldArtifactsUnchanged':all(c['oldArtifactsUnchanged'] for c in build_cases),'oldArtifactFileCount':len(old_refs),'oldArtifacts':old_refs,
        'buildAttempts':build_cases,'artifacts':static,'excludedInternalOutputs':excluded,
        'warningsPreservedInRawLogs':True,'minecraftRuntimeAcceptanceClaimed':False,
        'platformByteComparisonIsNotRuntimeAcceptance':True,'publicEvidence':build_refs,
        'privacy':'Only explicitly listed build/test receipts, logs and our QA sources are copied. Test-data/state directories, device IDs, server scopes, credentials, Minecraft game files and decompilations are excluded.'}
    core={'schemaVersion':1,'version':VERSION,'generatedUtc':now,'scope':'Runs regression test runners against production classes loaded from each exact distributable JAR, without launching Minecraft or any loader.',
        'allPassed':len(core_cases)==13 and all(c['passed'] for c in core_cases),'artifactCount':len(core_cases),'expectedArtifactCount':13,
        'perArtifactCounts':{'securityRegressionCases':57,'exactDefaultCatalogRules':37,'additionalControls':3},
        'totalExecutedCaseGroups':len(core_cases)*97,'cases':core_cases,'historicalAttemptsNotCounted':history,'excludedInternalOutputs':excluded,
        'originIsolation':'Only test runner classes are compiled with an empty sourcepath; the runtime classpath contains those runners and one pinned production JAR. GuardService code-source URI must resolve to that JAR.',
        'runtimeBoundary':'Java 8 is used for Bukkit and 1.8.9/1.12.2/1.16.5 artifacts; Java 21 for the modern artifacts, including class-major-61 Java 17 targets. This does not claim a Minecraft runtime or Java 17 loader launch.',
        'minecraftRuntimeAcceptanceClaimed':False,'publicEvidence':core_refs,
        'privacy':'No test-data directory or generated state is published; logs contain only synthetic unit-test outcomes and local source/runtime paths.'}
    return build,core

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--publish',action='store_true');args=parser.parse_args()
    build,core=collect(args.publish)
    report_names=['build-validation-0.2.0-test.1.json','artifact-core-validation-0.2.0-test.1.json']
    if args.publish:
        assert build['allBuildsPassed'] and build['allStaticArtifactChecksPassed'] and core['allPassed']
        destinations=[ROOT/p for p in COPIES]+[ROOT/'outputs'/n for n in report_names]
        assert all(not p.exists() for p in destinations),'Never overwrite prior evidence'
        # Public inputs contain no authentication command line or generated account state.
        for source,ref in COPIES.values():
            data=source.read_bytes();assert digest(data)==ref['sha256'] and len(data)==ref['bytes']
            if source.suffix in ('.json','.log','.py','.java','.tsv'):
                text=data.decode('utf-8',errors='replace')
                assert not re.search(r'(?i)(?:ghp_|github_pat_|glpat-|sk-proj-)[A-Za-z0-9_-]{15,}',text),source
        for public,(source,ref) in COPIES.items():
            destination=ROOT/public;destination.parent.mkdir(parents=True,exist_ok=True)
            with destination.open('xb') as stream: stream.write(source.read_bytes())
            assert sha(destination)==ref['sha256']
        for name,value in zip(report_names,(build,core)): save(ROOT/'outputs'/name,value)
    else:
        for name,value in zip(report_names,(build,core)): save(BASE/('draft-'+name),value)
    print(json.dumps({'published':args.publish,'buildTargets':build['buildTargetCount'],'staticProducts':build['productArtifactCount'],'corePassedProducts':core['artifactCount'],
        'pending':build['pendingProducts'],'unchangedNonCoreProducts':sum(c['publishedComparison']['allNonCoreClassBytesIdentical'] for c in build['artifacts']),
        'publicEvidenceFiles':len(COPIES),'publicEvidenceBytes':sum(r['bytes'] for _,r in COPIES.values())}))

if __name__=='__main__': main()
