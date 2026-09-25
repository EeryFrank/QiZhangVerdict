"""Independent read-only 0.2.0-test.1 audit; only writes the requested audit JSON."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import io
import json
import os
import posixpath
import re
import stat
import subprocess
import struct
import tomllib
import zipfile
import zlib
from urllib.parse import unquote, urlsplit

ROOT = Path('E:/Codex_work/QiZhangVerdict')
NAME = 'QiZhangVerdict-0.2.0-test.1'
PINS = {'bukkit/build/libs/qizhangverdict-bukkit-0.2.0-test.1.jar': ('1e54c48f744b61cc23efe28b8516132d13dba601d9b36beab88c1da3a849f1b7', 73684), 'platforms/1.20.1/fabric/build/libs/qizhangverdict-fabric-1.20.1-0.2.0-test.1.jar': ('cbeb929c831ff5ea7728c3cf844a21e9b90e1dc883ffac97c864953717309a89', 92584), 'platforms/1.20.1/forge/build/libs/qizhangverdict-forge-1.20.1-0.2.0-test.1.jar': ('1b4d684960466146da6ba10986490a51dccfb8160f51ac4f8f9dc803b4b490e1', 93651), 'platforms/1.21.1/fabric/build/libs/qizhangverdict-fabric-1.21.1-0.2.0-test.1.jar': ('fca097330af917758d956a355f213863b9dfd4b627b0785562ad2b2bb7a4280b', 94214), 'platforms/1.21.1/neoforge/build/libs/qizhangverdict-neoforge-1.21.1-0.2.0-test.1.jar': ('9b540c55cb395a4df129e6ecf4ba82b373def9c3115fe253779980f7f06e62ce', 94155), 'platforms/1.19.4/fabric/build/libs/qizhangverdict-fabric-1.19.4-0.2.0-test.1.jar': ('b4181ebbc96e8483a9a780e71d1bf0339b834a8b90351a03b06372a54f0c3365', 92461), 'platforms/1.19.4/forge/build/libs/qizhangverdict-forge-1.19.4-0.2.0-test.1.jar': ('db1c774e45894208178b317ed68b76c8def76974edfce28135000525dc7b6c88', 93517), 'platforms/1.18.2/fabric/build/libs/qizhangverdict-fabric-1.18.2-0.2.0-test.1.jar': ('b801c4a3ba1c192d8436a8c8870306646f48fb5baf413ab7811085df2ef32760', 92231), 'platforms/1.18.2/forge/build/libs/qizhangverdict-forge-1.18.2-0.2.0-test.1.jar': ('f3502b4d38abe80c1fa1b08e197d90335c6056b4b8ac0bb0303b92dc446d2c01', 93425), 'platforms/1.16.5/fabric/build/libs/qizhangverdict-fabric-1.16.5-0.2.0-test.1.jar': ('75969bc1d4afdf983cd42dc472f5e3b2d8c525f7e6e5fe387192d33fd86904d9', 92743), 'platforms/1.16.5/forge/build/libs/qizhangverdict-forge-1.16.5-0.2.0-test.1.jar': ('583997a92114de525007096f550ec979df07e6a73bebe10ea599e717200fdbcc', 94002), 'platforms/1.12.2/forge/build/libs/qizhangverdict-forge-1.12.2-0.2.0-test.1.jar': ('dcd20d9e5dbad6bee8fea53b4295bc6824c6c2acf7c72e1c9b9dc0131d6c211a', 94545), 'platforms/1.8.9/forge/build/libs/qizhangverdict-forge-1.8.9-0.2.0-test.1.jar': ('59ed17d9df197f6057a9709519fc3a3d33404cf92c783f176d2b6a3e7ff1b226', 95454)}
BASE = Path('E:/CodexTemp/QiZhangVerdict/release-0.2.0-test.1')
PRIVATE_NAMES = {'accounts.state', 'server-id.txt', 'installation-id.txt', 'usercache.json',
                 'ops.json', 'banned-players.json', 'banned-ips.json'}
FORBIDDEN_DIRS = {'.git', '.gradle', '__pycache__', 'build', 'runtime', 'cache',
                  'world', 'worlds', 'playerdata', 'logs', 'run'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args, data=None):
    p = subprocess.run(['git', '-C', str(ROOT), *args], input=data, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=120,
                       env=dict(os.environ, GIT_NO_REPLACE_OBJECTS='1', GIT_TERMINAL_PROMPT='0'))
    if p.returncode:
        raise ValueError('Read-only Git operation failed')
    return p.stdout


def safe_relative(name, source=True):
    assert isinstance(name, str) and name and '\\' not in name and ':' not in name
    parts = name.split('/')
    assert all(p not in ('', '.', '..') and p.rstrip(' .') == p for p in parts)
    assert not PurePosixPath(name).is_absolute() and not any(ord(c) < 32 for c in name)
    if source:
        assert not (set(p.casefold() for p in parts[:-1]) & FORBIDDEN_DIRS), name
        assert parts[-1].casefold() not in PRIVATE_NAMES and not parts[-1].startswith('.env'), name
        assert not name.endswith(('.class', '.pyc', '.pyo')), name


def no_links(path):
    for p in [path, *path.parents]:
        if p.exists():
            s = p.lstat()
            assert not stat.S_ISLNK(s.st_mode) and not getattr(s, 'st_file_attributes', 0) & 0x400


def reference(item, data):
    assert type(item['bytes']) is int and len(data) == item['bytes']
    assert re.fullmatch('[0-9a-f]{64}', item['sha256']) and sha(data) == item['sha256']


def tracked_blobs(commit):
    assert re.fullmatch('[0-9a-f]{40}', commit)
    assert git('rev-parse', '--verify', commit + '^{commit}').decode().strip() == commit
    tree = {}
    for row in git('ls-tree', '-r', '-z', '--full-tree', commit).split(b'\0'):
        if not row:
            continue
        meta, raw_name = row.split(b'\t', 1)
        mode, kind, oid = meta.decode('ascii').split()
        name = raw_name.decode('utf-8')
        safe_relative(name)
        assert mode in ('100644', '100755') and kind == 'blob'
        assert name.casefold() not in {x.casefold() for x in tree}
        tree[name] = (mode, oid)
    stream = io.BytesIO(git('cat-file', '--batch', data=''.join(v[1] + '\n' for v in tree.values()).encode()))
    blobs = {}
    for name, (_, expected_oid) in tree.items():
        oid, kind, size = stream.readline().decode().strip().split()
        assert oid == expected_oid and kind == 'blob'
        b = stream.read(int(size)); assert len(b) == int(size) and stream.read(1) == b'\n'
        blobs[name] = b
    assert stream.read() == b''
    return tree, blobs


def jar_audit(data, license_bytes, notice_bytes, product=True, name=None):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist(); assert len(names) == len(set(names)) and z.testzip() is None
        assert not any(n.startswith(('net/minecraft/', 'com/mojang/', 'assets/minecraft/')) for n in names)
        if not product:
            return
        assert z.read('LICENSE') == license_bytes and z.read('NOTICE') == notice_bytes
        assert b'GPL-3.0-only' in z.read('META-INF/MANIFEST.MF')
        classes = [n for n in names if n.endswith('.class')]
        assert classes and all(n.startswith('cn/qizhang/') for n in classes)
        assert not any(n.endswith('.jar') for n in names)
        major=65 if '1.21.1' in name else 61 if any(x in name for x in ('1.18.2','1.19.4','1.20.1')) else 52
        assert max(int.from_bytes(z.read(n)[6:8],'big') for n in classes)==major
        assert all(z.read(n)[:4]==b'\xca\xfe\xba\xbe' and 45<=int.from_bytes(z.read(n)[6:8],'big')<=major for n in classes)
        if 'bukkit' in name:
            assert re.search(rb'(?m)^version:\s*[\'\"]?0\.2\.0-test\.1[\'\"]?\s*$',z.read('plugin.yml'))
        elif 'fabric-' in name:
            descriptor=json.loads(z.read('fabric.mod.json'));assert descriptor['version']=='0.2.0-test.1' and descriptor['id']=='qizhangverdict'
        elif any(x in name for x in ('1.8.9','1.12.2')):
            descriptor=json.loads(z.read('mcmod.info'))[0];assert descriptor['version']=='0.2.0-test.1' and descriptor['modid']=='qizhangverdict'
            suffix='189' if '1.8.9' in name else '112'
            entry=z.read('cn/qizhang/guard/forge'+suffix+'/GuardForge'+suffix+'.class')
            # These whole JAR bytes are also hard-pinned to the independently audited class-annotation report.
            assert b'\x01\x00\x0c0.2.0-test.1' in entry and b'\x01\x00\x090.2.0-dev' not in entry
        else:
            descriptor=tomllib.loads(z.read('META-INF/neoforge.mods.toml' if 'neoforge-' in name else 'META-INF/mods.toml').decode())
            mods=[m for m in descriptor['mods'] if m['modId']=='qizhangverdict'];assert len(mods)==1 and mods[0]['version']=='0.2.0-test.1'


def local_markdown_links(payloads):
    links = []
    for name, b in payloads.items():
        if not name.endswith('.md'):
            continue
        text=b.decode('utf-8-sig')
        raw_links=[m[1] for m in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)',text)]
        raw_links += [m[1] for m in re.finditer(r'^\s{0,3}\[[^\]]+\]:\s*(<[^>]+>|\S+)',text,re.M)]
        for raw_link in raw_links:
            link = raw_link.strip().split(' "', 1)[0].strip('<>')
            if urlsplit(link).scheme or link.startswith(('#', '//')):
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(link.split('#', 1)[0])))
            assert target in payloads, (name, link, target)
            links.append({'document': name, 'target': target})
    return links


def private_device_tokens():
    # Read only locally retained real rendered-client state. Never emit any values.
    tokens = set()
    roots=[Path('E:/CodexTemp/QiZhangVerdict')/name for name in ('legacy-client-matrix','client-matrix','release-0.2.0-test.1/client-runs')]
    for cache in roots:
        for path in cache.rglob('accounts.state'):
            for line in path.read_text('utf-8').splitlines():
                if re.fullmatch(r'D\t[0-9a-f-]{36}\t[0-9a-f]{64}', line):
                    tokens.add(line.split('\t')[2].encode())
    return tokens


def privacy_audit(payloads, devices):
    for name, data in payloads.items():
        if name.endswith(('.jar', '.png')):
            continue
        assert all(token not in data for token in devices), 'Private device digest in ' + name
        assert not re.search(rb'(?m)^D\t[0-9a-f-]{36}\t[0-9a-f]{64}', data), name
        assert not re.search(rb'(?i)(?:MachineGuid|machine-id|device_hash)\s*["\s:=]+[a-f0-9]{32,64}\b', data), name
        assert not re.search(rb'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|glpat-[A-Za-z0-9_-]{15,}|-----BEGIN [A-Z ]*PRIVATE KEY-----', data), name
        # A complete javap listing includes a class declaration and Code sections.
        assert not (re.search(rb'(?m)^public .*net\.minecraft\..*\{\r?$', data)
                    and re.search(rb'(?m)^\s+Code:\r?$', data)), name


def evidence_reference_closure(payloads):
    """Only explicit public references count; private cache paths are not package requirements."""
    checked=set()
    def walk(value,owner):
        if isinstance(value,dict):
            target=value.get('publicFile')
            if target is None:
                candidate=value.get('file')
                if isinstance(candidate,str) and candidate.startswith(('outputs/','evidence/','legacy-client-matrix/','client-matrix/')):
                    target=candidate if candidate.startswith('outputs/') else 'outputs/'+candidate
            if isinstance(target,str) and 'sha256' in value and 'bytes' in value:
                safe_relative(target);assert target in payloads,('Missing explicit public evidence',owner,target)
                reference(value,payloads[target]);checked.add((owner,target))
            for child in value.values():walk(child,owner)
        elif isinstance(value,list):
            for child in value:walk(child,owner)
    for name,data in payloads.items():
        if name.endswith('.json') and name.startswith('outputs/'):
            walk(json.loads(data),name)
    return len(checked)


def png_bytes_check(data):
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    pos=8;idat=[];ended=False;width=height=None
    while pos<len(data):
        length=struct.unpack('>I',data[pos:pos+4])[0];kind=data[pos+4:pos+8]
        body=data[pos+8:pos+8+length];crc=struct.unpack('>I',data[pos+8+length:pos+12+length])[0]
        assert len(body)==length and zlib.crc32(kind+body)&0xffffffff==crc
        if kind==b'IHDR':width,height,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',body)
        elif kind==b'IDAT':idat.append(body)
        elif kind==b'IEND':ended=True;pos+=length+12;break
        pos+=length+12
    assert ended and pos==len(data) and width and height and idat
    assert depth==8 and color in (2,6) and compression==filtering==interlace==0
    pixels=zlib.decompress(b''.join(idat));stride=1+width*(3 if color==2 else 4)
    assert len(pixels)==height*stride and all(pixels[y*stride]<=4 for y in range(height))
    return width,height


def exact_new_runtime_gate(payloads,client_report):
    build_path='outputs/build-validation-0.2.0-test.1.json'
    core_path='outputs/artifact-core-validation-0.2.0-test.1.json'
    bukkit_path='outputs/bukkit-validation-0.2.0-test.1.json'
    for name in (build_path,core_path,bukkit_path,client_report):assert name in payloads,name
    build=json.loads(payloads[build_path]);core=json.loads(payloads[core_path]);bukkit=json.loads(payloads[bukkit_path])
    assert build['allBuildsPassed'] and build['allStaticArtifactChecksPassed'] and build['productArtifactCount']==13
    assert build['oldArtifactsUnchanged'] and core['allPassed'] and core['artifactCount']==13 and core['totalExecutedCaseGroups']==1261
    assert {x['artifact']['path']:(x['artifact']['sha256'],x['artifact']['bytes']) for x in build['artifacts']}==PINS
    assert {x['artifact']['path']:(x['artifact']['sha256'],x['artifact']['bytes']) for x in core['cases']}==PINS
    assert bukkit['passed'] and bukkit['artifactVersion']=='0.2.0-test.1' and bukkit['assertionGroups']==75
    item=bukkit['artifact'];assert PINS[item['path']]==(item['sha256'],item['bytes'])
    report=json.loads(payloads[client_report])
    assert report.get('passed') is True or report.get('allPassed') is True,'Final client report requires explicit pass'
    assert 'IN_PROGRESS' not in report.get('scope','').upper() and not report.get('pendingCases')
    wanted={PurePosixPath(p).name.removeprefix('qizhangverdict-').removesuffix('-0.2.0-test.1.jar') for p in PINS if '/bukkit/' not in '/'+p}
    wanted|={'forge-1.12.2-paper','forge-1.8.9-paper'}
    cases=report['cases'];assert len(cases)==14 and {c['id'] for c in cases}==wanted
    by_hash={h:path for path,(h,_) in PINS.items()};assert len(by_hash)==13
    by_id={PurePosixPath(path).name.removeprefix('qizhangverdict-').removesuffix('-0.2.0-test.1.jar'):path for path in PINS}
    covered=set();png_count=0
    for case in cases:
        assert case['passed'] is True and case['clientExitCode']==case['serverExitCode']==0
        assert case['strict13DefaultsUnchanged'] and case['default37RulesMatchCatalog'] and case['exactSyntheticUUIDAndScopedDeviceAssociation']
        assert case['strictDefaultSettingCount']==13 and case['defaultRuleCount']==37
        assert case['strictPolicySha256']=='47310c31b47287ab805bfdbf8ddddf80e8169385bd9c862239a0a0075644da4e'
        assert case['onlineObservationSeconds']>=60 and case['pngs']
        client=case['clientGuardSha256'];server=case['serverGuardSha256']
        assert client in by_hash and server in by_hash,('Old artifact cannot count as new runtime',case['id'])
        assert by_hash[client]==by_id[case['id'].removesuffix('-paper')]
        if case['id'].endswith('-paper'):
            assert case['kind']=='bukkit-interoperability' and by_hash[server]==by_id['bukkit']
        else:
            assert case['kind']=='matching-mod-server' and client==server
        covered.update((by_hash[client],by_hash[server]))
        for png in case['pngs']:
            name=png['publicFile']
            assert name in payloads and sha(payloads[name])==png['sha256']
            assert len(payloads[name])==png['bytes'] and png['zlibAndScanlinesValid']
            assert png_bytes_check(payloads[name])==(png['width'],png['height']);png_count+=1
            assert png['sha256'] in json.dumps(case['visualReview']),'Missing hash-bound manual visual-review record'
    assert covered==set(PINS),'All 13 new SHA-pinned products require evidence coverage'
    return {'clientReport':client_report,'newRuntimeCases':len(cases),'newArtifactHashesCovered':len(covered),
            'bukkitProtocolAssertionGroups':75,'pngBytesVerified':png_count,
            'historicalReportsCountedAsNewRuntime':0,
            'selectionPolicy':'Only the explicitly named new client report and new Bukkit runtime report count. Historical integration, old acceptance and source-test reports remain supporting history; never inferred as new runtime from passed=true.',
            'limits':'PNG decoding proves file integrity, not visual correctness; visual review and exact on-machine device checks remain in the separately reviewed runtime reports.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--commit', required=True)
    p.add_argument('--receipt', type=Path, required=True)
    p.add_argument('--manifest',required=True,help='Exact committed repository-relative manifest path')
    p.add_argument('--client-report',required=True,help='Explicit new-version final 14-case rendered-client report; history is never auto-selected')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    assert args.output.resolve().is_relative_to(BASE),'Audit outputs must remain in the assigned cache directory'
    safe_relative(args.manifest);safe_relative(args.client_report)
    no_links(args.receipt); no_links(args.output)
    assert not args.output.exists(), 'Refuse replacing an earlier audit'
    tree, blobs = tracked_blobs(args.commit)
    summary = json.loads(args.receipt.read_bytes())
    assert summary['sourceCommit'] == args.commit and summary['sourceTrackedFiles'] == len(tree)
    assert summary['packageName'] == NAME and summary['manifestPath'] == args.manifest
    assert sha(blobs[args.manifest]) == summary['manifestSha256']
    manifest = json.loads(blobs[args.manifest])
    assert set(manifest) == {'schemaVersion', 'packageName', 'artifacts', 'documents', 'evidence'}
    assert type(manifest['schemaVersion']) is int and manifest['schemaVersion'] == 1 and manifest['packageName'] == NAME
    assert len(manifest['artifacts']) == len(PINS) == 13
    assert {r['path']: (r['sha256'], r['bytes']) for r in manifest['artifacts']} == PINS
    assert b'GNU GENERAL PUBLIC LICENSE' in blobs['LICENSE'] and b'Version 3,' in blobs['LICENSE']
    expected = {}
    for role in ('documents', 'evidence'):
        for row in manifest[role]:
            assert set(row) == {'path', 'sha256', 'bytes'}
            name = row['path']; safe_relative(name); data = blobs[name]; reference(row, data)
            assert name not in expected; expected[name] = data
    assert {'LICENSE','NOTICE','docs/release-0.2.0-test.1.md','docs/privacy-and-limits.md',
            'docs/catalog.md','integrations/README.md'} <= set(expected)
    for row in manifest['artifacts']:
        safe_relative(row['path'], source=False)
        path = ROOT / row['path']; no_links(path); data = path.read_bytes(); reference(row, data)
        jar_audit(data, blobs['LICENSE'], blobs['NOTICE'],name=path.name)
        name = PurePosixPath(row['path']).name; assert name not in expected; expected[name] = data
    expected['preview-manifest.json'] = blobs[args.manifest]
    assert {r['file'] for r in summary['binaryFiles']} == set(expected)
    assert len(summary['binaryFiles']) == len(expected)
    for row in summary['binaryFiles']:
        reference(row, expected[row['file']])
    expected['packaging-summary.json'] = (json.dumps({k:v for k,v in summary.items() if k != 'archives'}, indent=2) + '\n').encode()
    expected['SHA256SUMS.txt'] = ''.join(sha(b) + '  ' + n + '\n' for n,b in sorted(expected.items())).encode()
    explicit_refs=evidence_reference_closure(expected)
    runtime_gate=exact_new_runtime_gate(expected,args.client_report)
    devices = private_device_tokens()
    archives = []
    assert {r['file'] for r in summary['archives']} == {NAME + '.zip', NAME + '-sources.zip'}
    for row in summary['archives']:
        path = args.receipt.parent / row['file']; no_links(path); data = path.read_bytes(); reference(row, data)
        source = row['file'].endswith('-sources.zip'); wanted = blobs if source else expected
        prefix = NAME + ('-sources/' if source else '/')
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = z.namelist(); assert len(names) == len(set(names)) == len({n.casefold() for n in names})
            assert z.testzip() is None and set(names) == {prefix+n for n in wanted}
            payloads = {}
            for name, b in wanted.items():
                actual = z.read(prefix + name); assert actual == b, name; payloads[name] = actual
                info = z.getinfo(prefix + name); mode = info.external_attr >> 16
                assert stat.S_ISREG(mode) and not stat.S_ISLNK(mode)
                assert info.date_time==(1980,1,1,0,0,0) and info.compress_type==zipfile.ZIP_DEFLATED
                if source:
                    assert mode & 0o777 == (0o755 if tree[name][0] == '100755' else 0o644)
            jars = [n for n in payloads if n.endswith('.jar')]
            if source:
                assert all(n == 'gradle/wrapper/gradle-wrapper.jar' or n.endswith('/gradle/wrapper/gradle-wrapper.jar') for n in jars)
                for n in jars: jar_audit(payloads[n], b'', b'', product=False)
                assert 'platforms/1.8.9/forge/build.gradle' in payloads
            else:
                assert len(jars) == 13 and all(n.startswith('qizhangverdict-') and n.endswith('-0.2.0-test.1.jar') and '/' not in n for n in jars)
            links = local_markdown_links(payloads)
            privacy_audit(payloads, devices)
            archives.append({**row, 'crc':'PASS', 'entries':len(names), 'allEntriesByteEqualToExpected':True,
                             'expectedBasis':f'{len(blobs)} fixed-commit Git blobs' if source else 'Committed explicit manifest plus thirteen pinned runtime JARs',
                             'markdownLocalLinksVerified':len(links), 'missingMarkdownLinks':0, 'jarFiles':jars,
                             'privateStateAndIdentifierPatterns':0, 'minecraftDistributionClassesOrJarsIncluded':False})
    release = args.receipt.parent / NAME
    no_links(release)
    if release.exists():
        actual = {p.relative_to(release).as_posix():p for p in release.rglob('*') if p.is_file()}
        assert set(actual) == set(expected)
        for name, path in actual.items(): no_links(path); assert path.read_bytes() == expected[name]
    result = {'passed':True, 'sourceCommit':args.commit, 'manifestSha256':summary['manifestSha256'],
              'packagingReceipt':{'file':args.receipt.name,'sha256':sha(args.receipt.read_bytes())},
              'artifactCount':13,'allArtifactsMatchReviewedNewVersionPins':True,
              'newRuntimeEvidenceGate':runtime_gate,'explicitPublicEvidenceReferencesVerified':explicit_refs,
              'sourceTrackedFiles':len(blobs), 'archives':archives, 'privateClientDeviceDigestsChecked':len(devices),
              'knownPrivateDeviceDigestLeaks':0, 'expandedPackageDirectoryByteEqual':release.exists(),
              'auditScriptSha256':sha(Path(__file__).read_bytes()),
              'method':'Independent Git cat-file, ZIP CRC/entry/byte/mode, manifest and receipt, GPL/NOTICE, thirteen pinned original JARs, descriptor/class-major, Markdown link and bounded privacy audit. No Java, build, repackage or publishing.',
              'limits':'Pattern and known-private-token scans do not prove absence of every possible secret format. This archive audit does not expand runtime or gameplay acceptance.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f: json.dump(result, f, indent=2); f.write('\n')
    print(json.dumps({'passed':True,'report':str(args.output),'sha256':sha(args.output.read_bytes()),'archives':archives}))


if __name__ == '__main__':
    main()
