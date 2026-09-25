#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Read-only production/input inspection and explicit text-evidence export; no Java."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import struct
import tomllib
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = Path('E:/CodexTemp/QiZhangVerdict/next-platforms/1.20.4')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text('utf-8'))


def dump(path, value):
    with Path(path).open('x', encoding='utf-8') as f:
        f.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def copy_text(source, name):
    source = Path(source); raw = source.read_bytes(); raw.decode('utf-8')
    assert source.suffix.lower() not in ('.jar', '.zip', '.class')
    assert 'mappings' not in source.name.lower()
    target = OUT / name
    if target.exists():
        assert target.read_bytes() == raw
    else:
        with target.open('xb') as f:
            f.write(raw)
    return {'path': target.relative_to(ROOT).as_posix(), 'sha256': sha(target), 'bytes': len(raw),
            'originalPath': str(source), 'rawBytesPreserved': True}


class ClassFile:
    """Minimal JVM classfile/annotation reader. Does not load or execute bytecode."""
    def __init__(self, raw):
        self.raw = raw; self.pos = 0
        assert self.take(4) == b'\xca\xfe\xba\xbe'
        self.minor = self.u2(); self.major = self.u2()
        self.cp = [None] * self.u2(); i = 1
        while i < len(self.cp):
            tag = self.u1()
            if tag == 1: value = self.take(self.u2()).decode('utf-8', errors='replace')
            elif tag == 3: value = struct.unpack('>i', self.take(4))[0]
            elif tag == 4: value = self.take(4).hex()
            elif tag in (5, 6): value = self.take(8).hex()
            elif tag in (7, 8, 16, 19, 20): value = self.u2()
            elif tag in (9, 10, 11, 12, 17, 18): value = [self.u2(), self.u2()]
            elif tag == 15: value = [self.u1(), self.u2()]
            else: raise ValueError('Unknown constant-pool tag ' + str(tag))
            self.cp[i] = (tag, value); i += 2 if tag in (5, 6) else 1
        self.access = self.u2(); self.this = self.utf(self.cp[self.u2()][1]); self.super = self.u2()
        for _ in range(self.u2()): self.u2()
        self.fields = self.members(); self.methods = self.members(); self.attributes = self.attributes_read()
        assert self.pos == len(raw)

    def take(self, n):
        out = self.raw[self.pos:self.pos+n]; assert len(out) == n; self.pos += n; return out
    def u1(self): return self.take(1)[0]
    def u2(self): return int.from_bytes(self.take(2), 'big')
    def u4(self): return int.from_bytes(self.take(4), 'big')
    def utf(self, index):
        tag, value = self.cp[index]; assert tag == 1; return value
    def attributes_read(self):
        result = {}
        for _ in range(self.u2()):
            name = self.utf(self.u2()); raw = self.take(self.u4())
            if name in ('RuntimeVisibleAnnotations', 'RuntimeInvisibleAnnotations'):
                result[name] = self.annotations(raw)
        return result
    def members(self):
        result = []
        for _ in range(self.u2()):
            access = self.u2(); name = self.utf(self.u2()); desc = self.utf(self.u2())
            result.append({'name': name, 'descriptor': desc, 'access': access, 'attributes': self.attributes_read()})
        return result
    def annotations(self, data):
        pos = 0
        def u2():
            nonlocal pos
            value = int.from_bytes(data[pos:pos+2], 'big'); pos += 2; return value
        def value():
            nonlocal pos
            tag = chr(data[pos]); pos += 1
            if tag in 'BCDFIJSZs':
                result = self.cp[u2()][1]
                return bool(result) if tag == 'Z' else result
            if tag == 'c': return {'class': self.utf(u2())}
            if tag == 'e': return {'enum': self.utf(u2()), 'value': self.utf(u2())}
            if tag == '@': return annotation()
            if tag == '[': return [value() for _ in range(u2())]
            raise ValueError('Unknown annotation element ' + tag)
        def annotation():
            typ = self.utf(u2()); fields = {}
            for _ in range(u2()):
                key = self.utf(u2()); fields[key] = value()
            return {'type': typ, 'values': fields}
        result = [annotation() for _ in range(u2())]; assert pos == len(data); return result


def all_annotations(attributes):
    return [a for values in attributes.values() for a in values]


def inspect(loader, artifact):
    jar = ROOT / artifact['path']; assert sha(jar) == artifact['sha256']; assert jar.stat().st_size == artifact['bytes']
    with zipfile.ZipFile(jar) as z:
        assert z.testzip() is None
        names = z.namelist(); assert len(names) == len(set(names))
        license_hashes = {}
        for filename in ('LICENSE', 'NOTICE'):
            assert z.read(filename) == (ROOT / filename).read_bytes()
            license_hashes[filename] = hashlib.sha256(z.read(filename)).hexdigest()
        manifest = z.read('META-INF/MANIFEST.MF').decode()
        assert 'License: GPL-3.0-only' in manifest
        class_names = [n for n in names if n.endswith('.class')]
        assert class_names and all(n.startswith('cn/qizhang/guard/') for n in class_names)
        assert not any(n.endswith('.jar') for n in names)
        classes = {n: ClassFile(z.read(n)) for n in class_names}
        assert set(c.major for c in classes.values()) == {61}
        mixin = json.loads(z.read('qizhangverdict.mixins.json'))
        assert mixin['required'] is True and mixin['injectors']['defaultRequire'] == 1
        assert mixin['mixins'] == ['CommandGate1204Mixin'] and mixin['compatibilityLevel'] == 'JAVA_17'
        gate_name = 'cn/qizhang/guard/minecraft/mixin/CommandGate1204Mixin.class'
        gate = classes[gate_name]
        annotation = next(a for a in all_annotations(gate.attributes) if a['type'].endswith('/Mixin;'))
        handler = next(m for m in gate.methods if m['name'] == 'qizhangverdict$denyPendingCommand')
        inject = next(a['values'] for a in all_annotations(handler['attributes']) if a['type'].endswith('/Inject;'))
        target = 'performCommand(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)V'
        assert inject['method'] == [target] and inject['cancellable'] is True and inject['require'] == 1
        assert inject['at'][0]['values']['value'] == 'HEAD'
        assert 'CallbackInfo;' in handler['descriptor'] and 'CallbackInfoReturnable' not in handler['descriptor']
        refmap = None
        if loader == 'neoforge':
            assert 'refmap' not in mixin and not any(n.endswith('refmap.json') for n in names)
            assert annotation['values']['value'] == [{'class':'Lnet/minecraft/commands/Commands;'}]
        else:
            assert mixin['refmap'] == 'qizhangverdict.refmap.json'
            refmap = json.loads(z.read(mixin['refmap']))['mappings'][gate_name[:-6]]
            expected = 'Lnet/minecraft/class_2170;method_9249' if loader == 'fabric' else 'Lnet/minecraft/commands/Commands;m_242674_'
            assert refmap[target] == expected + '(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)V'
        if loader == 'fabric':
            descriptor = json.loads(z.read('fabric.mod.json'))
            assert descriptor['id'] == 'qizhangverdict' and descriptor['version'] == '0.3.0-dev'
            assert descriptor['license'] == 'GPL-3.0-only' and descriptor['depends']['minecraft'] == '1.20.4'
        else:
            descriptor = tomllib.loads(z.read('META-INF/mods.toml').decode())
            assert descriptor['mods'][0]['modId'] == 'qizhangverdict' and descriptor['mods'][0]['version'] == '0.3.0-dev'
            assert descriptor['license'] == 'GPL-3.0-only' and 'MixinConfigs: qizhangverdict.mixins.json' in manifest
            assert json.loads(z.read('pack.mcmeta'))['pack']['pack_format'] == 22
        core_classes = {n: hashlib.sha256(z.read(n)).hexdigest() for n in names if n.startswith('cn/qizhang/guard/core/') and n.endswith('.class')}
        return {'artifact':artifact, 'loader':loader, 'zipCrcPassed':True, 'embeddedLicenseNoticeExact':True,
                'licenseSha256':license_hashes, 'manifestSpdx':'GPL-3.0-only', 'descriptor':descriptor,
                'classCount':len(classes), 'classMajor':61, 'allClassNamesFirstParty':True, 'nestedJars':0,
                'thirdPartyMinecraftClassesBundled':False, 'coreClassSha256':core_classes,
                'mixin':{'configuration':mixin, 'classAnnotation':annotation, 'handlerDescriptor':handler['descriptor'],
                         'compiledInjectAnnotation':inject, 'refmap':refmap,
                         'refmapNote':'No refmap in NeoForge named-mapping artifact; required injection still needs runtime proof.' if loader == 'neoforge' else 'Actual packaged refmap matches the void target descriptor.',
                         'runtimeInjectionVerified':False}}


def main():
    receipt = read(BASE / 'builds/01/result.json')
    logpath = BASE / 'builds/01/gradle.log'; log = logpath.read_text('utf-8')
    assert receipt['exitCode'] == 0 and receipt['buildSuccessful'] and receipt['sourceUnchanged'] and receipt['oldArtifactsUnchanged']
    assert sha(logpath) == receipt['logSha256'] and 'BUILD SUCCESSFUL' in log
    changed_sources = [p for p, h in receipt['sourceSha256'].items() if sha(ROOT / p) != h]
    unchanged_old = [p for p, h in receipt['oldArtifactSha256'].items() if sha(ROOT / p) == h]
    assert len(unchanged_old) == len(receipt['oldArtifactSha256'])
    artifacts = []
    for artifact in receipt['artifacts']:
        loader = artifact['path'].split('/')[2]
        item = inspect(loader, artifact)
        checks = {}
        for task, marker in [('commandParserSmoke','PASS: production command tree'),('payloadCodecSmoke','PASS: raw wire round trips')]:
            match = re.search(r'> Task :' + loader + ':' + task + r'\s*\n(.*?)(?=\n> Task|\Z)', log, re.S)
            assert match and marker in match[1], (loader,task)
            checks[task] = {'passed':True,'evidence':'build-01-gradle.log.txt','scope':'Gradle source/test runtime classpath, not standalone packaged-core execution'}
        item['gradleChecks'] = checks
        core = read(BASE / 'artifact-core/01' / loader / 'result.json')
        assert core['passed'] and core['artifactUnchanged'] and core['sha256'] == artifact['sha256']
        assert (core['securityCount'],core['catalogRuleCount'],core['catalogControlCount']) == (57,37,3)
        item['exactJarCoreChecks'] = {'passed':True,'security':57,'catalogRules':37,'catalogControls':3,'java':core['java'],'report':'outputs/adapter-build-1.20.4/core-'+loader+'-result.json'}
        artifacts.append(item)
    assert artifacts[0]['coreClassSha256'] == artifacts[1]['coreClassSha256'] == artifacts[2]['coreClassSha256']

    inputs = read(BASE.parent / 'runtime-input-preparation.json')
    selected = [r for r in inputs['records'] if r['minecraft'] == '1.20.4' and r['role'] in
                ('vanilla-server','vanilla-client','vanilla-server_mappings','vanilla-client_mappings','official-loader-installer','fabric-api-full-distribution')]
    for r in selected:
        assert sha(r['path']) == r['sha256'] and r['officialHashVerified']
    mapping = next(r for r in selected if r['role'] == 'vanilla-server_mappings')
    assert 'void performCommand(com.mojang.brigadier.ParseResults,java.lang.String)' in Path(mapping['path']).read_text('utf-8')
    forge_input = read(BASE / 'forge-research/official-inputs.json')
    forge_checked = []
    for rec in forge_input['files']:
        if rec.get('status') != 200: continue
        path = BASE / 'forge-research' / rec['file']
        assert sha(path) == rec['sha256']
        if rec.get('officialSha1'):assert hashlib.sha1(path.read_bytes()).hexdigest() == rec['officialSha1']
        forge_checked.append(rec)
    neo_jar = BASE / 'upstream/neoforge-20.4.251-sources.jar'
    neo_url = 'https://maven.neoforged.net/releases/net/neoforged/neoforge/20.4.251/neoforge-20.4.251-sources.jar'
    with urllib.request.urlopen(neo_url+'.sha1',timeout=30) as response: neo_sha_raw = response.read()
    neo_sha = neo_sha_raw.decode('ascii').strip().split()[0]
    assert hashlib.sha1(neo_jar.read_bytes()).hexdigest() == neo_sha
    sidecar = OUT / 'neoforge-sources.jar.sha1.txt'
    if sidecar.exists(): assert sidecar.read_bytes() == neo_sha_raw
    else:
        with sidecar.open('xb') as f: f.write(neo_sha_raw)
    with zipfile.ZipFile(neo_jar) as z:
        names = z.namelist()
        neo_api = [n for n in names if n.endswith(('RegisterPayloadHandlerEvent.java','IPayloadRegistrar.java','PlayPayloadContext.java'))]
        assert any(n.endswith('RegisterPayloadHandlerEvent.java') for n in neo_api)
        neo_source = {'url':neo_url,'sha1':neo_sha,'sha256':sha(neo_jar),'bytes':neo_jar.stat().st_size,
                      'officialSha1Url':neo_url+'.sha1','officialSha1Verified':True,
                      'selectedMembers':[{'name':n,'sha256':hashlib.sha256(z.read(n)).hexdigest()} for n in neo_api],
                      'archivePublished':False}

    evidence = []
    for source,name in [(BASE/'builds/01/plan.json','build-01-plan.json'),
                        (BASE/'builds/01/result.json','build-01-result.json'),
                        (logpath,'build-01-gradle.log.txt'),
                        (BASE/'upstream/pins-research.json','upstream-pins-research.json'),
                        (BASE/'forge-research/official-inputs.json','forge-official-inputs.json'),
                        (BASE/'forge-research/source-readiness.json','forge-source-readiness.json'),
                        (BASE/'runtime-inputs/prepared-inputs.json','prepared-runtime-inputs.json'),
                        (BASE/'artifact-core/01/summary.json','core-summary.json')]:
        evidence.append(copy_text(source,name))
    for loader in ('fabric','forge','neoforge'):
        source = BASE / 'artifact-core/01' / loader
        for name in ('result.json','java-version.log','compile-runners.log','artifact-origin.log','security.log','catalog.log','ArtifactOriginCheck.java'):
            public_name = 'core-'+loader+'-'+name+('.txt' if name.endswith('.log') else '')
            evidence.append(copy_text(source/name,public_name))
    for path in (sidecar,OUT/'run-exact-jar-checks.py',Path(__file__)):
        evidence.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'bytes':path.stat().st_size,'rawBytesPreserved':True})
    core_summary = read(BASE / 'artifact-core/01/summary.json')
    assert core_summary['runnerSha256'] == sha(OUT/'run-exact-jar-checks.py')
    report = {'schemaVersion':1,'minecraft':'1.20.4','version':'0.3.0-dev',
       'generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'stage':'BUILD_STATIC_AND_EXACT_JAR_CORE_PASSED_RUNTIME_NOT_RUN',
       'passed':True,'passedScope':'Three production JAR builds, 3 command-parser + 3 payload-codec checks, static packaging/compiled-Mixin inspection, and 291 exact-JAR core checks only.',
       'buildSuccessful':True,'formalAcceptancePassed':False,'minecraftRuntimeExecuted':False,'runtimeAcceptancePassed':False,
       'versions':{'minecraft':'1.20.4','javaMajor':17,'fabricLoader':'0.16.14','fabricApi':'0.97.3+1.20.4','forge':'49.2.9','neoforge':'20.4.251','gradle':'8.14.1','architecturyLoom':'1.11.456'},
       'build':{'attempt':'01','exitCode':0,'startedUtc':receipt['startedUtc'],'finishedUtc':receipt['finishedUtc'],
                'availablePhysicalGiB':receipt['availablePhysicalGiB'],'minimumFreeGiB':receipt['minimumFreeGiB'],
                'sourceUnchangedDuringBuild':receipt['sourceUnchanged'],'sourceFilesChangedSinceBuild':changed_sources,
                'oldArtifactCountRehashed':len(unchanged_old),'oldArtifactsUnchanged':True,
                'sourceClasspathCoreTestsExecuted':False,'commandParserChecks':3,'payloadCodecChecks':3},
       'artifacts':artifacts,'exactJarCore':{'passed':True,'javaMajor':17,'perJar':{'security':57,'catalogRules':37,'catalogControls':3},'totalChecks':291,
                   'originCheckedFromExactJar':True,'productionSourcesCompiledByRunner':False,
                   'publicSummary':'outputs/adapter-build-1.20.4/core-summary.json'},
       'officialInputs':{'selectedRuntimeInputs':selected,'forgeVerifiedTextOrArchiveInputs':forge_checked,'neoForgeSource':neo_source,
                         'fabricApiDescriptor':next(x for x in inputs['fabricApi'] if x['minecraft']=='1.20.4'),
                         'officialVoidCommandSignatureVerifiedInCachedMapping':True,'minecraftMappingsPublished':False,'thirdPartyBinariesPublished':False},
       'warningsPreserved':['Architectury Loom beta notice.','Gradle deprecated features warning for Gradle9.'],
       'limits':['No dedicated server startup, actual Mixin injection, protocol client, rendered client, behavior detection, VM classification or anti-xray effectiveness test is part of this report.',
                 'NeoForge production artifact has no refmap and retains named Commands.performCommand(...):void; required injection must be checked in an actual NeoForge runtime.',
                 'All three Gradle check tasks run parser and codec smoke only; standalone exact-JAR tests separately prove the embedded core regressions.',
                 'Official cached metadata/API declarations and binary packaging do not demonstrate interoperability; no previous-version acceptance has been reused.',
                 'No Minecraft/Forge/NeoForge/Fabric binaries, mapping files, private state, credentials or test-data folders are included as public evidence.'],
       'evidence':evidence,'staticAuditorSha256':sha(__file__)}
    dump(ROOT/'outputs/adapter-build-1.20.4.json',report)
    print(json.dumps({'report':'outputs/adapter-build-1.20.4.json','sha256':sha(ROOT/'outputs/adapter-build-1.20.4.json'),
                      'artifacts':len(artifacts),'exactJarChecks':291,'evidenceFiles':len(evidence),
                      'sourceFilesChangedSinceBuild':changed_sources,'minecraftRuntimeExecuted':False}))


if __name__ == '__main__':
    main()
