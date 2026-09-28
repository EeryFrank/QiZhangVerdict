#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Fresh 1.17.1 dedicated fixtures: stage (files), install (Java), run (Java/TCP).

Startup validates the unmodified 13-key policy and every pinned catalog row. The
optional existing TCP suite then uses explicitly acknowledged synthetic-report
policy overrides; it does not validate a rendered companion or real hardware.
"""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import sys
import time
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
CACHE = Path('E:/CodexTemp/QiZhangVerdict/compat-1.17.1')
INPUTS = CACHE / 'runtime-inputs-01'
CLIENT_INPUTS = CACHE / 'client-inputs-01'
CLIENT_RECEIPT_SHA256 = '87e84a9b1486da6893e9f16571a8471f560901326f601e8d69bab21a48acef06'
FIXTURES = CACHE / 'servers'
MARKER = '.qizhang-legacy117-smoke.json'
RECEIPT_SHA256 = '3aee72affa901e35c8b701a0ea5631032a158a1ef6a3c7ae6814e126c40c65e5'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
PINS = {'fabric': '0.19.5', 'forge': '37.1.1'}
DEFAULTS = {'limits.max-online-per-ip': '3', 'limits.max-online-per-ip-device': '1',
    'limits.max-accounts-per-ip': '5', 'limits.account-window-hours': '720',
    'limits.attempts-per-minute': '20', 'ip.allow': '', 'ip.deny': '',
    'companion.required': 'true', 'companion.timeout-seconds': '20', 'device.required': 'true',
    'vm.action': 'DENY', 'blacklist.action': 'DENY', 'sanctions.on-deny': 'BAN'}
PROTOCOL_SOURCES = ('protocol_smoke.cjs', 'protocol_disconnect_observer.cjs', 'protocol_player_loaded.cjs')
QA_OVERRIDES = {'limits.max-accounts-per-ip': '100', 'limits.attempts-per-minute': '1000',
    'companion.timeout-seconds': '4 (10 for the operator gate)', 'vm.action': 'ALERT initially; DENY in VM cases',
    'ip.deny': '127.0.0.0/8 in CIDR case', 'limits.max-online-per-ip': '2 in final quota cases'}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def record(path):
    path = Path(path).resolve()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def write_json(path, value, exclusive=False):
    with Path(path).open('x' if exclusive else 'w', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def no_reparse(path):
    for part in [Path(path), *Path(path).parents]:
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if part.is_symlink() or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ValueError('Reparse/symlink path is not allowed: ' + str(part))


def fixture_path(path):
    raw = Path(path)
    if '..' in raw.parts:
        raise ValueError('Parent traversal is not allowed')
    no_reparse(raw.absolute())
    result = raw.resolve()
    relative = result.relative_to(FIXTURES.resolve())
    if not relative.parts:
        raise ValueError('Expected a new child fixture, not the cache root')
    return result


def under(directory, relative):
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('Unsafe relative input path')
    path = directory / rel
    no_reparse(path)
    path.resolve().relative_to(directory.resolve())
    return path


def verified_copy(source, expected, target):
    source = Path(source); no_reparse(source)
    if not re.fullmatch('[a-fA-F0-9]{64}', expected) or digest(source) != expected.lower():
        raise ValueError('Input SHA256 mismatch: ' + source.name)
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as inp, target.open('xb') as out:
        shutil.copyfileobj(inp, out)
    if digest(source) != expected.lower() or digest(target) != expected.lower():
        raise ValueError('Input changed while copying')
    return record(target)


def catalog_rows(path):
    rows = [line.split('\t') for line in Path(path).read_text('utf-8').splitlines() if line.strip() and not line.startswith('#')]
    if not rows or any(len(row) != 4 for row in rows):
        raise ValueError('Expected nonempty four-column catalog rows')
    if len({row[1] for row in rows}) != len(rows):
        raise ValueError('Duplicate catalog identity, including across mod/automation kinds')
    for kind, identifier, action, source in rows:
        if (kind not in ('mod', 'automation') or action not in ('DENY', 'ALERT')
                or not re.fullmatch(r'[a-z][a-z0-9_.-]{1,127}', identifier)
                or not re.fullmatch(r'https://raw\.githubusercontent\.com/[^/]+/[^/]+/[0-9a-f]{40}/.+', source)):
            raise ValueError('Invalid exact catalog row or unpinned source')
    return sorted(rows)


def verify_input_indexes(inputs):
    receipt_path = inputs / 'prepared-inputs.json'
    if digest(receipt_path) != RECEIPT_SHA256:
        raise ValueError('Reviewed installer/FAPI input receipt changed')
    receipt = json.loads(receipt_path.read_text('utf-8'))
    if receipt.get('minecraft') != '1.17.1' or receipt.get('passed') is not True:
        raise ValueError('Unexpected installer input receipt')
    for entry in receipt['records'] + receipt['artifacts']:
        path = under(inputs, entry['relative'])
        if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            raise ValueError('Reviewed installer input changed: ' + entry['relative'])
    artifacts = {entry['role']: dict(entry, localPath=under(inputs, entry['relative'])) for entry in receipt['artifacts']}
    if set(artifacts) != {'fabric-api-full-distribution', 'fabric-installer', 'forge-installer'}:
        raise ValueError('Expected the three pinned installer/FAPI artifacts')
    for entry in artifacts.values():
        if entry.get('officialHashesVerified') is not True:
            raise ValueError('Installer/API lacks its original official digest verification')
        raw = entry['localPath'].read_bytes()
        for algorithm, expected in entry['officialHashes'].items():
            if hashlib.new(algorithm, raw).hexdigest() != expected:
                raise ValueError('Official installer/API digest mismatch')
        with zipfile.ZipFile(entry['localPath']) as archive:
            if archive.testzip() is not None:
                raise ValueError('Official input ZIP CRC mismatch')
    with zipfile.ZipFile(artifacts['forge-installer']['localPath']) as archive:
        for name in ('install_profile.json', 'version.json'):
            if archive.read(name) != (inputs / 'metadata' / ('forge-' + name)).read_bytes():
                raise ValueError('Forge metadata differs from fixed official installer')
    api = artifacts['fabric-api-full-distribution']
    with zipfile.ZipFile(api['localPath']) as archive:
        descriptor = json.loads(archive.read('fabric.mod.json'))
        if descriptor['id'] != 'fabric' or descriptor['version'] != '0.46.1+1.17' or len(descriptor.get('jars', [])) != 46:
            raise ValueError('Expected complete official FAPI distribution, not Maven aggregate shell')
        if any(member['file'] not in archive.namelist() for member in descriptor['jars']):
            raise ValueError('Missing bundled FAPI module')
    return artifacts


def verify_client_inputs():
    if not CLIENT_RECEIPT_SHA256:
        raise ValueError('Official client-input receipt has not been frozen; do not stage yet')
    receipt_path = CLIENT_INPUTS / 'prepared-inputs.json'
    if digest(receipt_path) != CLIENT_RECEIPT_SHA256:
        raise ValueError('Reviewed Mojang/loader-library receipt changed')
    receipt = json.loads(receipt_path.read_text('utf-8'))
    if receipt.get('minecraft') != '1.17.1' or receipt.get('passed') is not True:
        raise ValueError('Official base preparation did not pass')
    # Client-only assets are not copied into a dedicated-server fixture.
    selected = [r for r in receipt['records'] if r['role'] in ('mojang-server', 'fabric-server-profile') or r['relative'].startswith('libraries/')]
    by_path = {}
    for row in selected:
        path = under(CLIENT_INPUTS, row['relative'])
        if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise ValueError('Selected official base file changed: ' + row['relative'])
        if row['relative'] in by_path and by_path[row['relative']]['sha256'] != row['sha256']:
            raise ValueError('Conflicting official library bytes')
        by_path[row['relative']] = dict(row, localPath=path)
    selected = list(by_path.values())
    for role in ('mojang-server', 'fabric-server-profile'):
        if sum(row['role'] == role for row in selected) != 1:
            raise ValueError('Expected one pinned ' + role)
    return selected


def java16_record(java):
    java = Path(java).resolve()
    release = java.parent.parent / 'release'
    if not re.search(r'^JAVA_VERSION="16(?:\.|\")', release.read_text('utf-8'), re.M):
        raise ValueError('This fixture requires the reviewed Java 16 toolchain')
    javap = java.with_name('javap.exe' if os.name == 'nt' else 'javap')
    if not javap.is_file():
        raise ValueError('A complete Java16 JDK is required for actual Mixin inspection')
    return record(java), record(release), record(javap)


def maven_relative(coordinate):
    coordinate = coordinate.strip('[]')
    coordinate, sep, extension = coordinate.partition('@')
    pieces = coordinate.split(':')
    if len(pieces) not in (3, 4) or any(not re.fullmatch(r'[A-Za-z0-9_.+-]+', value) for value in pieces):
        raise ValueError('Invalid official Maven coordinate')
    group, artifact, version = pieces[:3]
    classifier = '-' + pieces[3] if len(pieces) == 4 else ''
    extension = extension if sep else 'jar'
    if extension not in ('jar', 'txt', 'zip'):
        raise ValueError('Unexpected official Maven extension')
    return group.replace('.', '/') + '/' + artifact + '/' + version + '/' + artifact + '-' + version + classifier + '.' + extension



def properties(path):
    result = {}
    for line in Path(path).read_text('utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith(('#', '!')):
            continue
        key, separator, value = line.partition('=')
        if not separator or key in result:
            raise ValueError('Malformed/duplicate property: ' + key)
        result[key] = value
    return result


def validate_jar(path, sha256, loader):
    path = Path(path); no_reparse(path)
    if not re.fullmatch('[a-fA-F0-9]{64}', sha256) or digest(path) != sha256.lower():
        raise ValueError('Candidate SHA256 mismatch')
    if path.name != 'qizhangverdict-' + loader + '-1.17.1-0.6.0-dev.jar':
        raise ValueError('Unexpected exact candidate filename')
    with zipfile.ZipFile(path) as jar:
        if jar.testzip() is not None:
            raise ValueError('Candidate ZIP CRC error')
        for name in ('LICENSE', 'NOTICE'):
            if jar.read(name) != (ROOT / name).read_bytes():
                raise ValueError('Candidate license resource mismatch')
        mixin = json.loads(jar.read('qizhangverdict.mixins.json'))
        if (mixin.get('required') is not True or mixin.get('mixins') != ['CommandGate117Mixin']
                or mixin.get('compatibilityLevel') != 'JAVA_16' or mixin.get('injectors', {}).get('defaultRequire') != 1):
            raise ValueError('Required Java16 command gate missing')
        refmap = mixin.get('refmap')
        if refmap != 'qizhangverdict.refmap.json' or not json.loads(jar.read(refmap)).get('mappings'):
            raise ValueError('Mapped legacy command gate refmap missing')
        classes = [name for name in jar.namelist() if name.startswith('cn/qizhang/') and name.endswith('.class')]
        if not classes or any(int.from_bytes(jar.read(name)[6:8], 'big') > 60 for name in classes):
            raise ValueError('Candidate contains bytecode newer than Java16')
        if loader == 'fabric':
            meta = json.loads(jar.read('fabric.mod.json'))
            if (meta.get('id'), meta.get('version'), meta.get('license'), meta.get('depends', {}).get('minecraft')) != ('qizhangverdict', '0.6.0-dev', 'GPL-3.0-only', '1.17.1'):
                raise ValueError('Candidate Fabric metadata mismatch')
            if meta['depends'].get('fabric') != '>=0.46.1' or meta['depends'].get('java') != '>=16':
                raise ValueError('Candidate Fabric API/Java dependency mismatch')
        elif loader == 'forge':
            import tomllib
            meta = tomllib.loads(jar.read('META-INF/mods.toml').decode())
            if (meta.get('license'), meta.get('modLoader'), meta['mods'][0]['modId'], meta['mods'][0]['version']) != ('GPL-3.0-only', 'javafml', 'qizhangverdict', '0.6.0-dev'):
                raise ValueError('Candidate Forge metadata mismatch')
            dependencies = {item['modId']: item for item in meta['dependencies']['qizhangverdict']}
            if (meta.get('loaderVersion'), dependencies['minecraft']['versionRange'], dependencies['forge']['versionRange']) != ('[37,38)', '[1.17.1]', '[37.1.1,38)'):
                raise ValueError('Candidate Forge target range mismatch')
            if 'MixinConfigs: qizhangverdict.mixins.json' not in jar.read('META-INF/MANIFEST.MF').decode():
                raise ValueError('Forge required Mixin manifest missing')
        else:
            raise ValueError('Unsupported candidate loader')
    return record(path)



def read_marker(path):
    directory = fixture_path(path)
    metadata = json.loads((directory / MARKER).read_text('utf-8'))
    if metadata.get('fixtureTool') != 'legacy117_mod_smoke' or metadata.get('loader') not in PINS:
        raise ValueError('Not this helper\'s fixture')
    if metadata['minecraft'] != '1.17.1' or metadata['loaderVersion'] != PINS[metadata['loader']]:
        raise ValueError('Fixture pin mismatch')
    if digest(__file__) != metadata['helper']['sha256']:
        raise ValueError('Helper changed since stage; create a new attempt')
    for entry in metadata.get('helperDependencies', []):
        if digest(entry['path']) != entry['sha256']:
            raise ValueError('Helper dependency changed since stage; create a new attempt')
    return directory, metadata


def memory_gate():
    if os.name == 'nt':
        class Mem(ctypes.Structure):
            _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(name, ctypes.c_ulonglong) for name in ('totalPhysical', 'availablePhysical', 'totalPageFile', 'availablePageFile', 'totalVirtual', 'availableVirtual', 'availableExtendedVirtual')]
        mem = Mem(); mem.length = ctypes.sizeof(mem)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
            raise OSError('Cannot read free physical memory')
        free = mem.availablePhysical / 1024 ** 3
    else:
        match = re.search(r'^MemAvailable:\s+(\d+) kB', Path('/proc/meminfo').read_text(), re.M)
        if not match:
            raise OSError('Cannot read free physical memory')
        free = int(match[1]) / 1024 ** 2
    if free < 5:
        raise RuntimeError('Need 5 GiB available before Java; actual %.3f' % free)
    return free


def environment(temp):
    env = dict(os.environ)
    for name in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS'):
        env.pop(name, None)
    env.update(TEMP=str(temp), TMP=str(temp))
    return env


def stage(args):
    directory = fixture_path(args.directory)
    if directory.exists():
        raise ValueError('Stage requires an entirely new fixture')
    if not args.accept_eula:
        raise ValueError('Explicit --accept-eula is required; stage never assumes acceptance')
    artifacts = verify_input_indexes(INPUTS)
    base = verify_client_inputs()
    expected_rows = catalog_rows(args.catalog)
    guard = validate_jar(args.guard_jar, args.guard_sha256, args.loader)
    java, release, javap = java16_record(args.java)
    if not 1024 <= args.port <= 65535:
        raise ValueError('Use an unprivileged explicit port')
    directory.mkdir(parents=True)
    (directory / 'mods').mkdir(); (directory / 'qa').mkdir()
    verified_copy(__file__, digest(__file__), directory / 'qa' / Path(__file__).name)
    verified_copy(args.catalog, digest(args.catalog), directory / 'qa/catalog.tsv')
    snapshots = [verified_copy(ROOT / 'scripts' / name, digest(ROOT / 'scripts' / name), directory / 'qa' / name) for name in PROTOCOL_SOURCES]
    snapshots.append(verified_copy(ROOT / 'scripts/protocol-qa/package-lock.json', digest(ROOT / 'scripts/protocol-qa/package-lock.json'), directory / 'qa/package-lock.json'))
    copy = lambda entry, target: verified_copy(entry['localPath'], entry['sha256'], target)
    server = next(row for row in base if row['role'] == 'mojang-server')
    official = {'server':copy(server, directory / 'server.jar'),
        'installer':copy(artifacts[args.loader + '-installer'], directory / 'loader-installer.jar')}
    if args.loader == 'fabric':
        official['fabricApi'] = copy(artifacts['fabric-api-full-distribution'], directory / 'mods/fabric-api-0.46.1+1.17.jar')
        profile = next(row for row in base if row['role'] == 'fabric-server-profile')
        official['profile'] = copy(profile, directory / 'qa/official-server-profile.json')
    else:
        profile = INPUTS / 'metadata/forge-install_profile.json'
        official['profile'] = verified_copy(profile, digest(profile), directory / 'qa/official-install-profile.json')
        meta = json.loads(profile.read_text('utf-8'))
        if (meta['minecraft'], meta['version'], meta['serverJarPath']) != ('1.17.1', '1.17.1-forge-37.1.1', '{LIBRARY_DIR}/net/minecraft/server/{MINECRAFT_VERSION}/server-{MINECRAFT_VERSION}.jar'):
            raise ValueError('Unexpected Forge37 install profile/server path')
        official['installerServerInput'] = copy(server, directory / 'libraries/net/minecraft/server/1.17.1/server-1.17.1.jar')
    libraries = [row for row in base if row['relative'].startswith('libraries/')]
    copied = [copy(row, under(directory, row['relative'])) for row in libraries]
    target = verified_copy(args.guard_jar, args.guard_sha256, directory / 'mods' / Path(args.guard_jar).name)
    (directory / 'eula.txt').write_text('eula=true\n', encoding='ascii')
    (directory / 'server.properties').write_text(
        'server-ip=127.0.0.1\nserver-port=' + str(args.port) + '\nonline-mode=' + ('false' if args.mode == 'tcp' else 'true') + '\n'
        'view-distance=2\nmax-players=20\nspawn-protection=0\nallow-flight=false\nenable-rcon=false\nenable-query=false\n'
        'level-name=world\nlevel-seed=12955\ndifficulty=peaceful\ngenerate-structures=false\nlevel-type=flat\n'
        'generator-settings={"layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:dirt","height":2},{"block":"minecraft:grass_block","height":1}],"biome":"minecraft:plains"}\n', encoding='ascii')
    metadata = {'fixtureTool':'legacy117_mod_smoke', 'profile':args.loader + '-1.17.1', 'loader':args.loader,
        'minecraft':'1.17.1', 'loaderVersion':PINS[args.loader], 'mode':args.mode, 'port':args.port,
        'prepared':False, 'java':str(Path(args.java).resolve()), 'javaRecord':java, 'javaRelease':release, 'javapRecord':javap,
        'guardRecord':target, 'guardSource':guard, 'officialInputRecords':official, 'helper':record(__file__), 'protocolSnapshots':snapshots,
        'catalog':record(directory / 'qa/catalog.tsv'), 'expectedRuleCount':len(expected_rows),
        'expectedCatalogActions':{action:sum(row[2] == action for row in expected_rows) for action in ('DENY', 'ALERT')},
        'serverProperties':record(directory / 'server.properties'), 'eula':record(directory / 'eula.txt'),
        'officialReceiptSha256':RECEIPT_SHA256, 'baseReceiptSha256':CLIENT_RECEIPT_SHA256,
        'helperDependencies':[], 'copiedLibraryCount':len(copied), 'copiedLibraryRecords':copied, 'javaStarted':False}
    write_json(directory / MARKER, metadata, True)
    print(json.dumps({'staged':str(directory), 'profile':metadata['profile'], 'javaStarted':False}))
    return 0



def validate_staged(directory, metadata):
    for row in [metadata['javaRecord'], metadata['javaRelease'], metadata['javapRecord'], metadata['guardRecord'], *metadata['officialInputRecords'].values(),
                metadata['serverProperties'], metadata['eula'], metadata['catalog'], *metadata['protocolSnapshots'],
                *metadata.get('copiedLibraryRecords', [])]:
        if digest(row['path']) != row['sha256']:
            raise ValueError('Staged input drift: ' + row['path'])
    rows = catalog_rows(directory / 'qa/catalog.tsv')
    actions = {action:sum(row[2] == action for row in rows) for action in ('DENY', 'ALERT')}
    if len(rows) != metadata['expectedRuleCount'] or actions != metadata['expectedCatalogActions']:
        raise ValueError('Pinned catalog counts changed since stage')


def install(args):
    directory, metadata = read_marker(args.directory)
    if metadata['prepared'] or (directory / 'install-result.json').exists() or (directory / 'install-console.log').exists():
        raise ValueError('Install attempts require a new staged fixture')
    validate_staged(directory, metadata)
    free = memory_gate()
    temp = directory / 'install-temp'; temp.mkdir()
    loader_args = ['server', '-mcversion', '1.17.1', '-loader', PINS['fabric'], '-dir', str(directory)] if metadata['loader'] == 'fabric' else ['--installServer', str(directory)]
    command = [metadata['java'], '-Xmx1536M', '-Djava.awt.headless=true', '-Djava.io.tmpdir=' + str(temp)]
    if os.name == 'nt':
        command += ['-Djavax.net.ssl.trustStoreType=Windows-ROOT', '-Djavax.net.ssl.trustStore=NONE']
    command += ['-jar', str(directory / 'loader-installer.jar'), *loader_args]
    result = {'command':command, 'availablePhysicalGiB':free, 'installerSha256':digest(directory / 'loader-installer.jar'),
        'installerExitCode':None, 'gameStarted':False, 'installedOutputsVerified':False}
    with (directory / 'install-console.log').open('xb') as log:
        try:
            completed = subprocess.run(command, cwd=directory, env=environment(temp), stdout=log, stderr=subprocess.STDOUT,
                timeout=args.timeout, creationflags=NO_WINDOW)
            result['installerExitCode'] = completed.returncode
        except subprocess.TimeoutExpired:
            result['timedOut'] = True
    result['console'] = record(directory / 'install-console.log')
    try:
        if result['installerExitCode'] != 0:
            raise RuntimeError('Installer failed; preserve this directory and use a new attempt')
        if metadata['loader'] == 'fabric':
            entry = directory / 'fabric-server-launch.jar'
            with zipfile.ZipFile(entry) as archive:
                if archive.testzip() is not None:
                    raise ValueError('Generated Fabric launcher CRC mismatch')
                manifest = archive.read('META-INF/MANIFEST.MF').decode().replace('\r\n ', '')
                if 'Main-Class: net.fabricmc.loader.impl.launch.server.FabricServerLauncher' not in manifest:
                    raise ValueError('Unexpected generated Fabric server main class')
            runtime_args = ['-jar', str(entry), 'nogui']
        else:
            entry = directory / 'libraries/net/minecraftforge/forge/1.17.1-37.1.1' / ('win_args.txt' if os.name == 'nt' else 'unix_args.txt')
            with zipfile.ZipFile(directory / 'loader-installer.jar') as archive:
                if entry.read_bytes() != archive.read('data/' + entry.name):
                    raise ValueError('Forge server arguments differ from fixed official installer')
            generated = verify_generated_forge(directory)
            metadata['generatedServerLibraries'] = generated
            metadata['patchedServer'] = next(row for row in generated if row['role'] == 'PATCHED')
            metadata['patchedServerVerification'] = 'Successful fixed official installer plus original PATCHED_SHA, MC_SLIM_SHA and MC_EXTRA_SHA SHA-1 checks; MC_SRG has local digest/CRC only.'
            runtime_args = ['@' + str(entry.relative_to(directory)), 'nogui']
        # The official installer must not replace any staged pinned library.
        for row in metadata['copiedLibraryRecords']:
            if digest(row['path']) != row['sha256']:
                raise ValueError('Installer changed a pinned library')
        metadata.update(prepared=True, runtimeArgs=runtime_args, serverEntry=record(entry))
        result['installedOutputsVerified'] = True
        write_json(directory / MARKER, metadata)
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    write_json(directory / 'install-result.json', result, True)
    if not result['installedOutputsVerified']:
        raise RuntimeError(result.get('error', 'Installation failed'))
    print(json.dumps({'installed':metadata['profile'], 'installerExitCode':0, 'gameStarted':False}))
    return 0


def verify_generated_forge(directory):
    profile = json.loads((directory / 'qa/official-install-profile.json').read_text('utf-8'))
    found = []
    for role in ('PATCHED', 'MC_SLIM', 'MC_EXTRA', 'MC_SRG'):
        path = under(directory / 'libraries', maven_relative(profile['data'][role]['server']))
        raw = path.read_bytes()
        expected = profile['data'].get(role + '_SHA', {}).get('server')
        if expected is not None:
            expected = expected.strip("'")
            if not re.fullmatch('[0-9a-f]{40}', expected) or hashlib.sha1(raw).hexdigest() != expected:
                raise ValueError('Official generated ' + role + ' digest mismatch')
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError('Generated Forge jar CRC mismatch: ' + role)
        found.append(dict(record(path), role=role, upstreamExpectedSha1=expected,
            upstreamSha1Verified=expected is not None, zipCrcVerified=True))
    return found


def audit_mixin(directory, metadata, temp):
    target = 'net/minecraft/class_2170' if metadata['loader'] == 'fabric' else 'net/minecraft/commands/Commands'
    export = under(directory / '.mixin.out/class', target + '.class')
    if not export.is_file():
        raise ValueError('Required transformed command dispatcher was not exported')
    # Full Minecraft disassembly stays in the private runtime cache, never public evidence.
    output = directory / 'private-mixin-javap.txt'
    with output.open('xb') as stream:
        completed = subprocess.run([metadata['javapRecord']['path'], '-p', '-c', str(export)], cwd=directory,
            env=environment(temp), stdout=stream, stderr=subprocess.STDOUT, timeout=30, creationflags=NO_WINDOW)
    text = output.read_text('utf-8', errors='replace')
    calls = mixin_call_chain(text)
    result = {'scope':'Actual runtime-transformed dispatcher inspected with the pinned Java16 javap; full disassembly remains private.',
        'target':target, 'export':record(export), 'privateDisassembly':record(output), 'javapExitCode':completed.returncode,
        **calls, 'passed':completed.returncode == 0 and all(calls.values())}
    if not result['passed']:
        raise ValueError('Actual transformed command gate call chain was not verified')
    return result


def mixin_call_chain(text):
    """Require the invocation in the real two-argument dispatcher, not any method."""
    methods = re.split(r'(?m)(?=^  (?:public|private|protected|static) )', text)
    handlers = [method for method in methods if re.match(r'^  private void [^\s(]*qizhangverdict\$denyPendingCommand\(', method)]
    dispatchers = [method for method in methods if re.match(
        r'^  public int \S+\((?:net\.minecraft\.commands\.CommandSourceStack|net\.minecraft\.class_2168), java\.lang\.String\);', method)]
    if len(handlers) != 1 or len(dispatchers) != 1:
        return dict(dispatchCallsInjectedHandler=False, handlerCallsGuardWaiting=False, handlerCancelsCommand=False)
    handler = handlers[0]
    name = re.match(r'^  private void ([^\s(]+)\(', handler).group(1)
    return {
        'dispatchCallsInjectedHandler':bool(re.search(r'invoke(?:special|virtual).*Method ' + re.escape(name) + r':', dispatchers[0])),
        'handlerCallsGuardWaiting':bool(re.search(r'invokestatic.*cn/qizhang/guard/minecraft/MinecraftGuard\.isWaiting:', handler)),
        'handlerCancelsCommand':bool(re.search(r'invokevirtual.*CallbackInfoReturnable\.setReturnValue:', handler))}



def protocol_support(modules):
    modules = Path(modules).resolve()
    protocol = modules / 'minecraft-protocol'
    data = modules / 'minecraft-data'
    versions = (protocol / 'src/version.js').read_text()
    if "'1.17.1'" not in versions.split('supportedVersions:', 1)[1]:
        raise ValueError('Installed minecraft-protocol does not list 1.17.1')
    paths = json.loads((data / 'minecraft-data/data/dataPaths.json').read_text())['pc']['1.17.1']
    version_file = data / 'minecraft-data/data' / paths['version'] / 'version.json'
    version = json.loads(version_file.read_text())
    schema = data / 'minecraft-data/data' / paths['protocol'] / 'protocol.json'
    parsed = json.loads(schema.read_text())
    if version['version'] != 756 or version['minecraftVersion'] != '1.17.1' or 'packet_player_loaded' in parsed['play']['toServer']['types'] or parsed['play']['toServer']['types'].get('packet_custom_payload') != ['container', [{'name': 'channel', 'type': 'string'}, {'name': 'data', 'type': 'restBuffer'}]]:
        raise ValueError('Installed protocol schema is not the inspected 1.17.1 protocol 756')
    return {'minecraftProtocolVersion':json.loads((protocol / 'package.json').read_text())['version'],
        'minecraftDataVersion':json.loads((data / 'package.json').read_text())['version'], 'protocol':756,
        'versionMetadata':record(version_file), 'schema':record(schema), 'versionList':record(protocol / 'src/version.js'),
        'scope':'Static package support and schema inspection; TCP success is a separate run result'}


def send(server, text):
    server.stdin.write((text + '\n').encode()); server.stdin.flush()


def wait_status(server, console, timeout=20, command='qzverdict status'):
    offset = console.stat().st_size
    send(server, command)
    end = time.monotonic() + timeout
    while server.poll() is None and time.monotonic() < end:
        with console.open('rb') as stream:
            stream.seek(offset); text = stream.read().decode('utf-8', errors='replace')
        responses = [line for line in text.splitlines() if 'QiZhangVerdict sessions=' in line and 'started:' not in line]
        if responses:
            return responses[-1]
        time.sleep(0.25)
    raise RuntimeError('No fresh console status response')


def run_protocol(args, directory, metadata, server, result, temp):
    if not args.protocol_node or not args.allow_synthetic_policy_overrides:
        raise ValueError('TCP mode requires --protocol-node and --allow-synthetic-policy-overrides')
    result['protocolSupport'] = protocol_support(args.protocol_node_modules)
    env = environment(temp)
    env.update(NODE_PATH=str(Path(args.protocol_node_modules).resolve()), QV_DATA_DIR=str(directory / 'config/qizhangverdict'),
        QV_TEST_COMMAND_GATE='1', QV_TEST_ANTIXRAY='0')
    queue = directory / 'commands.queue'; queue.touch(exist_ok=False)
    result['syntheticPolicyOverrides'] = QA_OVERRIDES
    script = directory / 'qa/protocol_smoke.cjs'
    result['executedProtocol'] = record(script)
    forwarded = 0; begin = time.monotonic()
    with (directory / 'protocol-console.log').open('xb') as log:
        bot = subprocess.Popen([args.protocol_node, str(script), '1.17.1', str(metadata['port']), str(directory)],
            cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
        try:
            while bot.poll() is None and server.poll() is None and time.monotonic() - begin < args.protocol_timeout:
                lines = queue.read_text('utf-8').splitlines(keepends=True)
                for line in [line for line in lines if line.endswith('\n')][forwarded:]:
                    send(server, line.rstrip('\r\n')); forwarded += 1
                time.sleep(0.1)
        finally:
            if bot.poll() is None:
                result['protocolForcedTermination'] = True; bot.kill()
            bot.wait(timeout=20)
    result.update(protocolExitCode=bot.returncode, protocolElapsedSeconds=round(time.monotonic() - begin, 3), forwardedCommands=forwarded)
    result_file = directory / 'protocol-result.json'
    if result_file.exists():
        protocol = json.loads(result_file.read_text('utf-8'))
        result['protocolResult'] = protocol
        result['protocolResultRecord'] = record(result_file)
        result['protocolPassed'] = (bot.returncode == 0 and not result.get('protocolForcedTermination', False)
            and protocol.get('version') == '1.17.1' and protocol.get('passed') == 26
            and len(protocol.get('cases', [])) == 26 and len(set(protocol['cases'])) == 26)
    else:
        result['protocolPassed'] = False


def run(args):
    directory, metadata = read_marker(args.directory)
    if not metadata['prepared'] or (directory / 'smoke-result.json').exists() or (directory / 'console.log').exists():
        raise ValueError('Run requires an installed fixture that has never run')
    if (directory / 'world').exists() or (directory / 'config/qizhangverdict').exists():
        raise ValueError('World/guard state must be entirely fresh')
    validate_staged(directory, metadata)
    for key in ('serverEntry', 'patchedServer', 'rootShim'):
        if key in metadata and digest(metadata[key]['path']) != metadata[key]['sha256']:
            raise ValueError('Installed server entry changed')
    for entry in metadata.get('installedLibraries', []) + metadata.get('generatedServerLibraries', []):
        if digest(entry['path']) != entry['sha256']:
            raise ValueError('Installed Forge server library changed')
    if metadata['mode'] == 'tcp':
        if not args.protocol_node or not args.allow_synthetic_policy_overrides:
            raise ValueError('TCP requires explicit synthetic-policy acknowledgement')
        protocol_support(args.protocol_node_modules)
    free = memory_gate()
    with socket.socket() as test:
        test.bind(('127.0.0.1', metadata['port']))
    temp = directory / 'runtime-temp'; temp.mkdir()
    command = [metadata['java'], '-Xms512M', '-Xmx1536M', '-Djava.awt.headless=true', '-Dfile.encoding=UTF-8',
        '-Djava.io.tmpdir=' + str(temp), '-Dmixin.debug.verbose=true', '-Dmixin.debug.export=true',
        '-Dmixin.debug.countInjections=true', *metadata['runtimeArgs']]
    result = {'profile':metadata['profile'], 'guard':metadata['guardRecord'], 'mode':metadata['mode'], 'command':command,
        'scope':'Dedicated startup/status/required command Mixin and clean stop; optional real TCP synthetic reports, not rendered companion/hardware evidence',
        'availablePhysicalGiB':free, 'started':False, 'normalStop':False, 'serverExitCode':None, 'protocolPassed':False,
        'defaultPolicyVerified':False, 'defaultCatalogVerified':False, 'requiredMixinObserved':False, 'helper':record(__file__)}
    console = directory / 'console.log'; server = None; begin = time.monotonic(); baseline = None
    with console.open('xb') as log:
        try:
            server = subprocess.Popen(command, cwd=directory, env=environment(temp), stdin=subprocess.PIPE,
                stdout=log, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
            result['serverPid'] = server.pid
            while server.poll() is None and time.monotonic() - begin < args.timeout:
                text = console.read_text('utf-8', errors='replace')
                if re.search(r'Done \([\d.,]+s\)! For help', text):
                    result['started'] = True; break
                time.sleep(0.5)
            if not result['started']:
                raise RuntimeError('Server did not reach Done')
            policy = directory / 'config/qizhangverdict/guard.properties'
            blacklist = directory / 'config/qizhangverdict/blacklist.tsv'
            baseline = policy.read_bytes()
            if properties(policy) != DEFAULTS:
                raise ValueError('Fresh guard policy is not all 13 strict defaults')
            result['defaultPolicyVerified'] = True
            if catalog_rows(blacklist) != catalog_rows(directory / 'qa/catalog.tsv'):
                raise ValueError('Fresh catalog differs from the complete pinned catalog')
            result['defaultCatalogVerified'] = True
            result['expectedRuleCount'] = metadata['expectedRuleCount']
            result['expectedCatalogActions'] = metadata['expectedCatalogActions']
            verified_copy(policy, digest(policy), directory / 'guard-default.properties')
            verified_copy(blacklist, digest(blacklist), directory / 'blacklist-default.tsv')
            result['freshStatus'] = wait_status(server, console)
            if not all(token in result['freshStatus'] for token in (', rules=' + str(metadata['expectedRuleCount']) + ',', ', companion=required,', ', vm=DENY,', ', deviceRequired=true')):
                raise ValueError('Fresh status differs from strict policy and pinned catalog count')
            text = console.read_text('utf-8', errors='replace')
            result['mixinLines'] = [line for line in text.splitlines() if 'CommandGate117Mixin' in line]
            result['requiredMixinObserved'] = any('Mixing CommandGate117Mixin from qizhangverdict.mixins.json into ' in line for line in result['mixinLines'])
            if not result['requiredMixinObserved']:
                raise ValueError('Required command gate Mixin application not observed')
            result['mixinAudit'] = audit_mixin(directory, metadata, temp)
            if metadata['mode'] == 'tcp':
                run_protocol(args, directory, metadata, server, result, temp)
        except Exception as error:
            result['error'] = type(error).__name__ + ': ' + str(error)
        finally:
            if server is not None and server.poll() is None:
                try:
                    if baseline is not None:
                        policy = directory / 'config/qizhangverdict/guard.properties'
                        result['policyBeforeRestore'] = properties(policy)
                        policy.write_bytes(baseline)
                        # The reload runs asynchronously. Wait for its own success
                        # callback before asking status, rather than accepting an
                        # old live policy while only the disk file was restored.
                        result['restoreReloadStatus'] = wait_status(server, console, command='qzverdict reload')
                        result['restoredStatus'] = wait_status(server, console)
                        strict = (', companion=required,', ', vm=DENY,', ', blacklist=DENY,', ', deviceRequired=true')
                        result['strictPolicyRestored'] = (policy.read_bytes() == baseline and properties(policy) == DEFAULTS
                            and all(token in result[field] for field in ('restoreReloadStatus', 'restoredStatus') for token in strict))
                    send(server, 'stop')
                    server.wait(timeout=90)
                    result['normalStop'] = server.returncode == 0
                except Exception as error:
                    result['stopError'] = type(error).__name__ + ': ' + str(error)
                finally:
                    if server.poll() is None:
                        result['forcedServerTermination'] = True; server.kill(); server.wait(timeout=30)
            result['serverExitCode'] = server.returncode if server is not None else None
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', metadata['port'])); result['portReleased'] = True
        except OSError:
            result['portReleased'] = False
    result['elapsedSeconds'] = round(time.monotonic() - begin, 3)
    result['console'] = record(console)
    text = console.read_text('utf-8', errors='replace')
    result['warningAndErrorLines'] = [line for line in text.splitlines() if any(token in line for token in ('WARN', 'ERROR', 'Exception'))]
    if (directory / 'protocol-console.log').exists():
        raw = (directory / 'protocol-console.log').read_text('utf-8', errors='replace')
        result['protocolDecoderErrors'] = [line for line in raw.splitlines() if line.startswith('PartialReadError:')]
        result['protocolConsole'] = record(directory / 'protocol-console.log')
    result['passed'] = (result['started'] and result['defaultPolicyVerified'] and result['defaultCatalogVerified']
        and result['requiredMixinObserved'] and result.get('mixinAudit', {}).get('passed') is True and result['normalStop'] and result.get('strictPolicyRestored', False)
        and result['portReleased'] and not result.get('forcedServerTermination', False)
        and 'error' not in result and 'stopError' not in result
        and (metadata['mode'] != 'tcp' or result['protocolPassed']))
    write_json(directory / 'smoke-result.json', result, True)
    print(json.dumps({key:result[key] for key in ('profile', 'started', 'passed', 'serverExitCode', 'normalStop', 'elapsedSeconds')}))
    return 0 if result['passed'] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    p = commands.add_parser('stage'); p.add_argument('--loader', choices=PINS, required=True)
    for key in ('directory', 'guard-jar', 'guard-sha256'):
        p.add_argument('--' + key, required=True)
    p.add_argument('--catalog', default=str(ROOT / 'catalog/blacklist-extension.tsv'))
    p.add_argument('--java', default='E:/CodexTemp/QiZhangVerdict/toolchains/jdk16/installation-01/extracted/jdk-16.0.2+7/bin/java.exe')
    p.add_argument('--port', type=int, required=True); p.add_argument('--mode', choices=('startup', 'tcp'), default='tcp')
    p.add_argument('--accept-eula', action='store_true'); p.set_defaults(func=stage)
    p = commands.add_parser('install'); p.add_argument('--directory', required=True)
    p.add_argument('--timeout', type=int, default=900); p.set_defaults(func=install)
    p = commands.add_parser('run'); p.add_argument('--directory', required=True)
    p.add_argument('--timeout', type=int, default=300); p.add_argument('--protocol-timeout', type=int, default=360)
    p.add_argument('--protocol-node'); p.add_argument('--protocol-node-modules', default='E:/CodexTemp/QiZhangGuard/bot/node_modules')
    p.add_argument('--allow-synthetic-policy-overrides', action='store_true'); p.set_defaults(func=run)
    p = commands.add_parser('inspect-protocol'); p.add_argument('--protocol-node-modules', default='E:/CodexTemp/QiZhangGuard/bot/node_modules')
    p.set_defaults(func=lambda args: print(json.dumps(protocol_support(args.protocol_node_modules), indent=2)) or 0)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
