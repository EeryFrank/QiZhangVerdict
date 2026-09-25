#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Windows production-client QA for the separately pinned 1.19.2/1.20.4 candidates.

stage-base only prepares verified files. install-client and run are explicit, separate
Java actions; neither is performed implicitly by preparation or argument inspection.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
CACHE = Path('E:/CodexTemp/QiZhangVerdict/next-platforms')
JAVA17 = Path('E:/CodexTemp/mods-danzi/java/jdk-17.0.20.1+1-jre/bin/java.exe')
JAVA21 = Path('D:/Java/jdk-21/bin/java.exe')
PROFILES = ('fabric-1.19.2', 'forge-1.19.2', 'fabric-1.20.4', 'forge-1.20.4', 'neoforge-1.20.4')
PORTS = dict(zip(PROFILES, (25711, 25712, 25713, 25714, 25715)))
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def sha(path, algorithm='sha256'):
    return hashlib.new(algorithm, Path(path).read_bytes()).hexdigest()


def record(path):
    path = Path(path)
    return {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size}


def save_new(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, ensure_ascii=False, indent=2); output.write('\n')


def safe_name(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,80}', value):
        raise ValueError('Use a short plain fixture name')
    return value


def base_directory(profile, name):
    return CACHE / profile.split('-', 1)[1] / 'future-client-fixtures' / profile / safe_name(name)


def memory_gate(minimum):
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
            (key, ctypes.c_ulonglong) for key in ('totalPhysical', 'availablePhysical', 'totalPageFile',
                                                 'availablePageFile', 'totalVirtual', 'availableVirtual', 'extended')]
    memory = Memory(); memory.length = ctypes.sizeof(memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise RuntimeError('Cannot inspect available physical memory')
    free = memory.availablePhysical / 1024**3
    if free < minimum:
        raise RuntimeError(f'Memory gate requires {minimum} GiB, observed {free:.3f} GiB; no Java started')
    return free


def environment(directory):
    temp = Path(directory) / 'tmp'; temp.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    for key in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS'):
        env.pop(key, None)
    env.update(TEMP=str(temp), TMP=str(temp))
    return env


def fetch_verified(target, url, expected_sha1, expected_size=None, candidates=()):
    target = Path(target)
    if not re.fullmatch('[0-9a-f]{40}', expected_sha1):
        raise ValueError('Official SHA-1 required for every downloadable file')
    def valid(path):
        return path.is_file() and (expected_size is None or path.stat().st_size == expected_size) and sha(path, 'sha1') == expected_sha1
    if target.exists():
        if not valid(target):
            raise ValueError('Existing immutable cache file fails official hash: ' + str(target))
        return 'verified-existing'
    target.parent.mkdir(parents=True, exist_ok=True)
    for candidate in candidates:
        candidate = Path(candidate)
        if valid(candidate):
            shutil.copyfile(candidate, target)
            if not valid(target): raise ValueError('Copy failed official hash')
            return 'reused:' + str(candidate)
    request = urllib.request.Request(url, headers={'User-Agent': 'QiZhangVerdict-next-client-QA/1'})
    with urllib.request.urlopen(request, timeout=60) as response: raw = response.read()
    if hashlib.sha1(raw).hexdigest() != expected_sha1 or (expected_size is not None and len(raw) != expected_size):
        raise ValueError('Official download hash/size mismatch: ' + url)
    with target.open('xb') as output: output.write(raw)
    return 'downloaded'


def verified_copy(source, target, expected):
    source, target = Path(source), Path(target)
    if sha(source) != expected: raise ValueError('Pinned source changed: ' + str(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if sha(target) != expected: raise ValueError('Existing target differs: ' + str(target))
    else:
        shutil.copyfile(source, target)
    if sha(target) != expected: raise ValueError('Copied file differs')
    return target


def allowed(entry):
    rules = entry.get('rules')
    if not rules: return True
    result = False
    for rule in rules:
        if any(value is not False for value in rule.get('features', {}).values()): continue
        platform = rule.get('os', {})
        if platform.get('name', 'windows') != 'windows': continue
        if platform.get('arch', 'amd64') not in ('amd64', 'x86_64'): continue
        if 'version' in platform and not re.match(platform['version'], '10.0'): continue
        result = rule['action'] == 'allow'
    return result


def coordinate(entry):
    bits = entry['name'].split('@', 1)[0].split(':')
    group, name, version = bits[:3]
    classifier = bits[3] if len(bits) > 3 else ''
    relative = '/'.join([group.replace('.', '/'), name, version, name + '-' + version + ('-' + classifier if classifier else '') + '.jar'])
    return ':'.join((group, name, classifier)), relative


def inputs_for(profile):
    plan_path = CACHE / 'client-base-preparation-plan.json'
    plan = read(plan_path)
    receipt_path = Path(plan['inputReceipt'])
    if sha(receipt_path) != plan['inputReceiptSha256']: raise ValueError('Reviewed runtime inputs receipt changed')
    receipt = read(receipt_path)
    for item in receipt['preparedInputs']:
        if sha(item['path']) != item['sha256']: raise ValueError('Per-version input index changed')
    proposed = next(item for item in plan['profiles'] if item['id'] == profile)
    installed = next(item for item in receipt['profiles'] if item['id'] == profile)
    for item in (proposed['officialMinecraftMetadata'], proposed['vanillaClient'], proposed['officialLoaderProfile'], installed['installer']):
        if sha(item['path']) != item['sha256']: raise ValueError('Reviewed official input changed')
    return proposed, installed, receipt, record(plan_path)


def pin_guard(profile, build_receipt=None):
    loader, mc = profile.split('-', 1)
    receipt = Path(build_receipt).resolve() if build_receipt else CACHE / mc / 'builds' / ('02' if mc == '1.19.2' else '01') / 'result.json'
    receipt.resolve().relative_to((CACHE / mc / 'builds').resolve())
    built = read(receipt)
    if not built['buildSuccessful'] or built['target'] != mc or built['version'] != '0.3.0-dev':
        raise ValueError('No successful version-matched pinned build receipt')
    expected = f'platforms/{mc}/{loader}/build/libs/qizhangverdict-{profile}-0.3.0-dev.jar'
    item = next(item for item in built['artifacts'] if item['path'] == expected)
    if sha(ROOT / expected) != item['sha256']: raise ValueError('Candidate differs from the reviewed build receipt')
    return {**record(ROOT / expected), 'buildReceipt': record(receipt)}


def asset_roots():
    roots = [Path('E:/CodexTemp/mods-danzi/minecraft/assets/objects'),
             Path('E:/CodexTemp/QiZhangGuard/client-release-smoke/assets/objects'),
             Path('E:/CodexTemp/Gradle/XiuXianZhuan/caches/neoformruntime/assets/objects')]
    for folder in ('client-matrix', 'legacy-client-matrix'):
        roots.extend(Path('E:/CodexTemp/QiZhangVerdict', folder).glob('*/client/assets/objects'))
    return [path for path in roots if path.is_dir()]


def prepare_assets(metadata):
    assets = CACHE / 'client-assets'
    item = metadata['assetIndex']; index = assets / 'indexes' / (item['id'] + '.json')
    candidates = [root.parent / 'indexes' / index.name for root in asset_roots()]
    fetch_verified(index, item['url'], item['sha1'], item['size'], candidates)
    objects = read(index)['objects']; unique = {x['hash']: x['size'] for x in objects.values()}
    prior = asset_roots()
    def one(item):
        hash_value, size = item; relative = Path(hash_value[:2]) / hash_value
        origin = fetch_verified(assets / 'objects' / relative, 'https://resources.download.minecraft.net/' + relative.as_posix(), hash_value, size,
                                [root / relative for root in prior])
        return origin.split(':', 1)[0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: origins = list(pool.map(one, unique.items()))
    return {'root': str(assets), 'index': record(index), 'id': item['id'], 'logicalObjects': len(objects), 'uniqueObjects': len(unique),
            'allObjectsOfficialSha1AndSizeVerified': True, 'origins': {name: origins.count(name) for name in set(origins)}, 'totalUniqueBytes': sum(unique.values())}


def stage_base(profile, name, build_receipt=None):
    directory = base_directory(profile, name)
    if directory.exists(): raise ValueError('Preparation attempts require a new base name; preserve earlier files')
    directory.mkdir(parents=True)
    result = {'profile': profile, 'baseName': name, 'prepared': False, 'javaInvoked': False, 'runtimeVerified': False, 'helper': record(__file__)}
    try:
        proposed, installed, receipt, design = inputs_for(profile)
        loader, mc = profile.split('-', 1); metadata = read(proposed['officialMinecraftMetadata']['path'])
        profile_json = read(proposed['officialLoaderProfile']['path'])
        if metadata['javaVersion']['majorVersion'] != 17: raise ValueError('Unexpected official Java version')
        result.update(minecraft=mc, loader=loader, loaderVersion=installed['loaderVersion'], design=design,
                      installer=installed['installer'], guard=pin_guard(profile, build_receipt), java=str(JAVA17), javaMajor=17,
                      serverFixtureSource=str(CACHE / mc / 'servers' / (loader + ('-02' if profile == 'forge-1.20.4' else '-01'))))
        vanilla = directory / 'versions' / mc
        verified_copy(proposed['officialMinecraftMetadata']['path'], vanilla / (mc + '.json'), proposed['officialMinecraftMetadata']['sha256'])
        client = verified_copy(proposed['vanillaClient']['path'], vanilla / (mc + '.jar'), proposed['vanillaClient']['sha256'])
        verified_copy(proposed['officialLoaderProfile']['path'], directory / 'loader-profile.json', proposed['officialLoaderProfile']['sha256'])
        input_root = Path(proposed['verifiedLibraryInputRoot'])
        index = {str(Path(item['path']).resolve()).lower(): item for item in receipt['records']}
        # Seed only the checksum-reviewed immutable input libraries; the installer
        # may later generate additional files, which never become a wildcard classpath.
        seeded = []
        for item in receipt['records']:
            source = Path(item['path'])
            try: relative = source.relative_to(input_root)
            except ValueError: continue
            target = verified_copy(source, directory / 'libraries' / relative, item['sha256']); seeded.append(record(target))
        libraries = {}; pending = []
        for item in metadata['libraries'] + profile_json['libraries']:
            if not allowed(item): continue
            key, relative = coordinate(item)
            detail = item.get('downloads', {}).get('artifact', {})
            relative = detail.get('path', relative)
            source = input_root / relative; target = directory / 'libraries' / relative
            source_ref = index.get(str(source.resolve()).lower())
            if source_ref:
                verified_copy(source, target, source_ref['sha256'])
            elif detail.get('sha1') and detail.get('url') == '':
                pending.append({'name': item['name'], 'path': str(target), 'sha1': detail['sha1'], 'bytes': detail.get('size')})
            else:
                raise ValueError('Library is not in the reviewed input manifest: ' + relative)
            if target.exists() and detail.get('sha1') and sha(target, 'sha1') != detail['sha1']:
                raise ValueError('Profile library official SHA-1 mismatch: ' + relative)
            libraries[key] = {'name': item['name'], 'path': str(target), 'sha1': detail.get('sha1'), 'sha256': sha(target) if target.exists() else None}
        natives = directory / 'natives'; natives.mkdir()
        for item in libraries.values():
            library = Path(item['path'])
            if 'natives-windows' not in library.name or any(arch in library.name for arch in ('natives-windows-arm64', 'natives-windows-x86')): continue
            with zipfile.ZipFile(library) as archive:
                if archive.testzip() is not None: raise ValueError('Native archive CRC failure')
                for member in archive.namelist():
                    if member.endswith('.dll'): (natives / Path(member).name).write_bytes(archive.read(member))
        assets = prepare_assets(metadata)
        logging = metadata['logging']['client']; logging_path = Path(assets['root']) / 'log_configs' / logging['file']['id']
        fetch_verified(logging_path, logging['file']['url'], logging['file']['sha1'], logging['file']['size'])
        if loader != 'fabric' and profile != 'forge-1.20.4':
            client = verified_copy(client, directory / 'versions' / profile_json['id'] / (profile_json['id'] + '.jar'), proposed['vanillaClient']['sha256'])
        classpath = list(libraries.values())
        # Forge49 explicitly supplies the patched full client library; adding the
        # vanilla JAR again would create duplicate Minecraft packages.
        if profile != 'forge-1.20.4': classpath.append({**record(client), 'name': 'official-vanilla-client'})
        if proposed['fabricApi']:
            if sha(proposed['fabricApi']['path']) != proposed['fabricApi']['sha256']: raise ValueError('Pinned Fabric API changed')
        result.update(prepared=True, mainClass=profile_json['mainClass'], loaderId=profile_json['id'],
                      loaderArguments=profile_json.get('arguments', {}), libraries=str(directory / 'libraries'), classpath=classpath,
                      pendingInstallerGeneratedLibraries=pending, seededLibraryCount=len(seeded), seededLibraries=seeded,
                      nativeFiles=[record(path) for path in sorted(natives.iterdir())], natives=str(natives), assets=assets,
                      vanillaClient=proposed['vanillaClient'], fabricApi=proposed['fabricApi'], logging=record(logging_path),
                      loggingArgument=logging['argument'].replace('${path}', str(logging_path)), needsClientInstaller=loader != 'fabric')
        save_new(directory / 'base-plan.json', result)
        print(json.dumps({'profile': profile, 'prepared': True, 'assets': assets, 'pendingGeneratedLibraries': len(pending), 'javaInvoked': False}), flush=True)
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error); raise
    finally:
        save_new(directory / 'preparation-result.json', result)


def install_client(profile, name):
    directory = base_directory(profile, name); plan = read(directory / 'base-plan.json')
    if not plan['prepared']: raise ValueError('Base preparation failed')
    if (directory / 'client-install-result.json').exists(): raise ValueError('Never overwrite an installation attempt')
    if not plan['needsClientInstaller']:
        save_new(directory / 'client-install-result.json', {'exitCode': 0, 'installerRequired': False, 'javaInvoked': False})
        return
    installer = Path(plan['installer']['path'])
    if sha(installer) != plan['installer']['sha256']: raise ValueError('Installer changed')
    free = memory_gate(3.5)
    save_new(directory / 'launcher_profiles.json', {'profiles': {}})
    temp = directory / 'tmp'; temp.mkdir(exist_ok=True)
    command = [str(JAVA21), '-Xmx768M', '-Djava.awt.headless=true', '-Djava.io.tmpdir=' + str(temp),
               '-Djavax.net.ssl.trustStoreType=Windows-ROOT', '-Djavax.net.ssl.trustStore=NONE', '-jar', str(installer), '--installClient', str(directory)]
    result = {'profile': profile, 'command': command, 'availablePhysicalGiB': free, 'minimumFreeGiB': 3.5,
              'installer': record(installer), 'helper': record(__file__), 'javaInvoked': True, 'runtimeVerified': False, 'exitCode': None}
    console = directory / 'install-console.log'
    try:
        with console.open('xb') as output:
            process = subprocess.run(command, cwd=directory, env=environment(directory), stdout=output, stderr=subprocess.STDOUT, timeout=900, creationflags=NO_WINDOW)
        result['exitCode'] = process.returncode
        if process.returncode != 0: raise RuntimeError('Official client installer failed')
        for item in plan['pendingInstallerGeneratedLibraries']:
            path = Path(item['path'])
            if not path.is_file() or sha(path, 'sha1') != item['sha1']: raise ValueError('Generated client library official SHA-1 mismatch')
        profile_path = directory / 'versions' / plan['loaderId'] / (plan['loaderId'] + '.json')
        if not profile_path.is_file() or read(profile_path) != read(directory / 'loader-profile.json'):
            raise ValueError('Installed loader profile differs from the reviewed official profile')
        result['generatedLibrariesVerified'] = True
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error); raise
    finally:
        if console.exists(): result['console'] = record(console)
        save_new(directory / 'client-install-result.json', result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage-base', 'install-client', 'run'))
    parser.add_argument('profile', choices=PROFILES)
    parser.add_argument('--base-name', default='base-01')
    parser.add_argument('--run-name', default='candidate-0.3.0-dev-01')
    parser.add_argument('--port', type=int)
    parser.add_argument('--build-receipt', type=Path, help='stage-base only: explicit successful receipt under this version cache builds directory')
    args = parser.parse_args()
    if args.build_receipt and args.action != 'stage-base': parser.error('--build-receipt is only accepted for stage-base')
    if args.action == 'stage-base': stage_base(args.profile, args.base_name, args.build_receipt)
    elif args.action == 'install-client': install_client(args.profile, args.base_name)
    else:
        from next_client_runtime import run
        run(args.profile, args.base_name, safe_name(args.run_name), args.port or PORTS[args.profile])


if __name__ == '__main__':
    main()
