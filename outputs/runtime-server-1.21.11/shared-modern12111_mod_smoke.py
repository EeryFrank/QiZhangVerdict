#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Fresh 1.21.11 dedicated fixtures: stage (files), install (Java), run (Java/TCP).

Startup validates the unmodified 13-key policy and all 39 catalog rows. The
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
CACHE = Path('E:/CodexTemp/QiZhangVerdict/compat-1.21.11')
INPUTS = CACHE / 'runtime-inputs-01'
FIXTURES = CACHE / 'servers'
MARKER = '.qizhang-modern12111-smoke.json'
RECEIPT_SHA256 = 'd524e9e812891c4fccf6fa7a09ec1eb4d119361d2b5adac474800e5d8c1709ad'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
PINS = {'fabric': '0.19.5', 'neoforge': '21.11.45'}
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
    if len(rows) != 39 or any(len(row) != 4 for row in rows) or len({tuple(row[:2]) for row in rows}) != 39:
        raise ValueError('Expected exactly 39 distinct catalog rows')
    if sum(row[2] == 'DENY' for row in rows) != 35 or sum(row[2] == 'ALERT' for row in rows) != 4:
        raise ValueError('Expected 35 DENY and 4 ALERT catalog rows')
    return sorted(rows)


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
    if digest(path) != sha256.lower():
        raise ValueError('Candidate SHA256 mismatch')
    if path.name != 'qizhangverdict-' + loader + '-1.21.11-0.4.0-dev.jar':
        raise ValueError('Unexpected exact candidate filename')
    with zipfile.ZipFile(path) as jar:
        if jar.testzip() is not None:
            raise ValueError('Candidate ZIP CRC error')
        for name in ('LICENSE', 'NOTICE'):
            if jar.read(name) != (ROOT / name).read_bytes():
                raise ValueError('Candidate license resource mismatch')
        mixin = json.loads(jar.read('qizhangverdict.mixins.json'))
        if mixin.get('required') is not True or mixin.get('mixins') != ['CommandGate12111Mixin'] or mixin.get('injectors', {}).get('defaultRequire') != 1:
            raise ValueError('Required command gate missing')
        if loader == 'fabric':
            meta = json.loads(jar.read('fabric.mod.json'))
            if (meta.get('id'), meta.get('version'), meta.get('depends', {}).get('minecraft')) != ('qizhangverdict', '0.4.0-dev', '1.21.11'):
                raise ValueError('Candidate Fabric metadata mismatch')
        else:
            import tomllib
            meta = tomllib.loads(jar.read('META-INF/neoforge.mods.toml').decode())
            if (meta.get('license'), meta['mods'][0]['modId'], meta['mods'][0]['version']) != ('GPL-3.0-only', 'qizhangverdict', '0.4.0-dev'):
                raise ValueError('Candidate NeoForge metadata mismatch')
    return record(path)


def read_marker(path):
    directory = fixture_path(path)
    metadata = json.loads((directory / MARKER).read_text('utf-8'))
    if metadata.get('fixtureTool') != 'modern12111_mod_smoke' or metadata.get('loader') not in PINS:
        raise ValueError('Not this helper\'s fixture')
    if metadata['minecraft'] != '1.21.11' or metadata['loaderVersion'] != PINS[metadata['loader']]:
        raise ValueError('Fixture pin mismatch')
    if digest(__file__) != metadata['helper']['sha256']:
        raise ValueError('Helper changed since stage; create a new attempt')
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
    inputs = INPUTS
    if digest(inputs / 'preparation-receipt.json') != RECEIPT_SHA256:
        raise ValueError('Reviewed official input receipt changed')
    receipt = json.loads((inputs / 'preparation-receipt.json').read_text())
    for entry in receipt['records'] + receipt['metadata']:
        if digest(under(inputs, entry['file'])) != entry['sha256']:
            raise ValueError('Reviewed input index changed')
    catalog_rows(args.catalog)
    guard = validate_jar(args.guard_jar, args.guard_sha256, args.loader)
    java = record(args.java)
    if not 1024 <= args.port <= 65535:
        raise ValueError('Use an unprivileged explicit port')
    directory.mkdir(parents=True)
    (directory / 'mods').mkdir(); (directory / 'qa').mkdir()
    verified_copy(__file__, digest(__file__), directory / 'qa' / Path(__file__).name)
    verified_copy(args.catalog, digest(args.catalog), directory / 'qa/catalog.tsv')
    snapshots = []
    for name in PROTOCOL_SOURCES:
        snapshots.append(verified_copy(ROOT / 'scripts' / name, digest(ROOT / 'scripts' / name), directory / 'qa' / name))
    snapshots.append(verified_copy(ROOT / 'scripts/protocol-qa/package-lock.json', digest(ROOT / 'scripts/protocol-qa/package-lock.json'), directory / 'qa/package-lock.json'))
    records = json.loads((inputs / 'binary-inputs.json').read_text())
    by_role = {entry['role']: entry for entry in records}
    copy = lambda entry, target: verified_copy(under(inputs, entry['file']), entry['sha256'], target)
    official = {'server': copy(by_role['mojang-server'], directory / 'server.jar'),
                'installer': copy(by_role[args.loader + '-installer'], directory / 'loader-installer.jar')}
    if args.loader == 'fabric':
        official['fabricApi'] = copy(by_role['fabric-api-complete-distribution'], directory / 'mods/fabric-api-0.141.6+1.21.11.jar')
        profile = inputs / 'metadata/fabric-loader-0.19.5-server.json'
        official['profile'] = verified_copy(profile, digest(profile), directory / 'qa/official-server-profile.json')
    else:
        profile = inputs / 'metadata/neoforge-install_profile.json'
        official['profile'] = verified_copy(profile, digest(profile), directory / 'qa/official-install-profile.json')
        install_meta = json.loads(profile.read_text())
        if install_meta['minecraft'] != '1.21.11' or install_meta['version'] != 'neoforge-21.11.45':
            raise ValueError('Unexpected NeoForge install profile')
        server_path = install_meta['serverJarPath']
        if server_path != '{LIBRARY_DIR}/net/minecraft/server/{MINECRAFT_VERSION}/server-{MINECRAFT_VERSION}.jar':
            raise ValueError('Unexpected NeoForge bundled-server path')
        server_relative = server_path.replace('{LIBRARY_DIR}', 'libraries').replace('{MINECRAFT_VERSION}', '1.21.11')
        copy(by_role['mojang-server'], under(directory, server_relative))
    libs = {}
    for index in ('client-libraries-files.json', args.loader + '-loader-libraries-files.json'):
        for entry in json.loads((inputs / index).read_text()):
            if entry['file'] in libs and libs[entry['file']]['sha256'] != entry['sha256']:
                raise ValueError('Conflicting official library')
            libs[entry['file']] = entry
    for entry in libs.values():
        copy(entry, under(directory, entry['file']))
    guard_target = verified_copy(args.guard_jar, args.guard_sha256, directory / 'mods' / Path(args.guard_jar).name)
    (directory / 'eula.txt').write_text('eula=true\n', encoding='ascii')
    (directory / 'server.properties').write_text(
        'server-ip=127.0.0.1\nserver-port=' + str(args.port) + '\nonline-mode=' + ('false' if args.mode == 'tcp' else 'true') + '\n'
        'enforce-secure-profile=false\nview-distance=2\nsimulation-distance=2\nmax-players=20\nspawn-protection=0\n'
        'allow-flight=false\nenable-rcon=false\nenable-query=false\nlevel-name=world\nlevel-seed=12955\n'
        'difficulty=peaceful\ngenerate-structures=false\nlevel-type=minecraft:flat\n'
        'generator-settings={"layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:dirt","height":2},{"block":"minecraft:grass_block","height":1}],"biome":"minecraft:plains"}\n', encoding='ascii')
    metadata = {'fixtureTool':'modern12111_mod_smoke', 'profile':args.loader + '-1.21.11', 'loader':args.loader,
        'minecraft':'1.21.11', 'loaderVersion':PINS[args.loader], 'mode':args.mode, 'port':args.port,
        'prepared':False, 'java':str(Path(args.java).resolve()), 'javaRecord':java, 'guardRecord':guard_target,
        'guardSource':guard, 'officialInputRecords':official, 'helper':record(__file__), 'protocolSnapshots':snapshots,
        'catalog':record(directory / 'qa/catalog.tsv'), 'expectedRuleCount':39,
        'serverProperties':record(directory / 'server.properties'), 'eula':record(directory / 'eula.txt'),
        'officialReceiptSha256':RECEIPT_SHA256, 'copiedLibraryCount':len(libs), 'javaStarted':False}
    write_json(directory / MARKER, metadata, True)
    print(json.dumps({'staged':str(directory), 'profile':metadata['profile'], 'javaStarted':False}))
    return 0


def validate_staged(directory, metadata):
    for row in [metadata['javaRecord'], metadata['guardRecord'], *metadata['officialInputRecords'].values(),
                metadata['serverProperties'], metadata['eula'], metadata['catalog'], *metadata['protocolSnapshots']]:
        if digest(row['path']) != row['sha256']:
            raise ValueError('Staged input drift: ' + row['path'])


def install(args):
    directory, metadata = read_marker(args.directory)
    if metadata['prepared'] or (directory / 'install-result.json').exists() or (directory / 'install-console.log').exists():
        raise ValueError('Install attempts require a new staged fixture')
    validate_staged(directory, metadata)
    free = memory_gate()
    temp = directory / 'install-temp'; temp.mkdir()
    loader_args = ['server', '-mcversion', '1.21.11', '-loader', '0.19.5', '-dir', str(directory)] if metadata['loader'] == 'fabric' else ['--installServer', str(directory)]
    command = [metadata['java'], '-Xmx1536M', '-Djava.awt.headless=true', '-Djava.io.tmpdir=' + str(temp)]
    if os.name == 'nt':
        command += ['-Djavax.net.ssl.trustStoreType=Windows-ROOT', '-Djavax.net.ssl.trustStore=NONE']
    command += ['-jar', str(directory / 'loader-installer.jar'), *loader_args]
    result = {'command':command, 'availablePhysicalGiB':free, 'installerSha256':digest(directory / 'loader-installer.jar'), 'installerExitCode':None, 'gameStarted':False}
    with (directory / 'install-console.log').open('xb') as log:
        try:
            completed = subprocess.run(command, cwd=directory, env=environment(temp), stdout=log, stderr=subprocess.STDOUT,
                timeout=args.timeout, creationflags=NO_WINDOW)
            result['installerExitCode'] = completed.returncode
        except subprocess.TimeoutExpired:
            result['timedOut'] = True
    result['console'] = record(directory / 'install-console.log')
    write_json(directory / 'install-result.json', result, True)
    if result['installerExitCode'] != 0:
        raise RuntimeError('Installer failed; preserve this directory and use a new attempt')
    if metadata['loader'] == 'fabric':
        entry = directory / 'fabric-server-launch.jar'
        runtime_args = ['-jar', str(entry), 'nogui']
    else:
        entry = directory / 'libraries/net/neoforged/neoforge/21.11.45' / ('win_args.txt' if os.name == 'nt' else 'unix_args.txt')
        # FML 10 starts through this exact new official argument file, not the
        # older BootstrapLauncher/--launchTarget forge-server command.
        text = entry.read_text('utf-8')
        if 'net.neoforged.fml.startup.Server' not in text or '--fml.mcVersion 1.21.11' not in text or '--fml.neoForgeVersion 21.11.45' not in text:
            raise ValueError('Official NeoForge 1.21.11 server entry mismatch')
        patched = directory / 'libraries/net/neoforged/minecraft-server-patched/21.11.45/minecraft-server-patched-21.11.45.jar'
        if not patched.is_file():
            raise ValueError('NeoForge installer did not create the patched server')
        metadata['patchedServer'] = record(patched)
        runtime_args = ['@' + str(entry.relative_to(directory)), 'nogui']
    metadata.update(prepared=True, runtimeArgs=runtime_args, serverEntry=record(entry))
    write_json(directory / MARKER, metadata)
    print(json.dumps({'installed':metadata['profile'], 'installerExitCode':0, 'gameStarted':False}))
    return 0


def protocol_support(modules):
    modules = Path(modules).resolve()
    protocol = modules / 'minecraft-protocol'
    data = modules / 'minecraft-data'
    versions = (protocol / 'src/version.js').read_text()
    if "'1.21.11'" not in versions.split('supportedVersions:', 1)[1]:
        raise ValueError('Installed minecraft-protocol does not list 1.21.11')
    paths = json.loads((data / 'minecraft-data/data/dataPaths.json').read_text())['pc']['1.21.11']
    version_file = data / 'minecraft-data/data' / paths['version'] / 'version.json'
    version = json.loads(version_file.read_text())
    schema = data / 'minecraft-data/data' / paths['protocol'] / 'protocol.json'
    parsed = json.loads(schema.read_text())
    if version['version'] != 774 or version['minecraftVersion'] != '1.21.11' or parsed['play']['toServer']['types']['packet_player_loaded'] != ['container', []]:
        raise ValueError('Installed protocol schema is not the inspected 1.21.11 protocol 774')
    return {'minecraftProtocolVersion':json.loads((protocol / 'package.json').read_text())['version'],
        'minecraftDataVersion':json.loads((data / 'package.json').read_text())['version'], 'protocol':774,
        'versionMetadata':record(version_file), 'schema':record(schema), 'versionList':record(protocol / 'src/version.js'),
        'scope':'Static package support and schema inspection; TCP success is a separate run result'}


def send(server, text):
    server.stdin.write((text + '\n').encode()); server.stdin.flush()


def wait_status(server, console, timeout=20):
    offset = console.stat().st_size
    send(server, 'qzverdict status')
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
        bot = subprocess.Popen([args.protocol_node, str(script), '1.21.11', str(metadata['port']), str(directory)],
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
            and protocol.get('version') == '1.21.11' and protocol.get('passed') == 26
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
    for key in ('serverEntry', 'patchedServer'):
        if key in metadata and digest(metadata[key]['path']) != metadata[key]['sha256']:
            raise ValueError('Installed server entry changed')
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
                raise ValueError('Fresh catalog differs from all 39 pinned rows')
            result['defaultCatalogVerified'] = True
            verified_copy(policy, digest(policy), directory / 'guard-default.properties')
            verified_copy(blacklist, digest(blacklist), directory / 'blacklist-default.tsv')
            result['freshStatus'] = wait_status(server, console)
            if not all(token in result['freshStatus'] for token in (', rules=39,', ', companion=required,', ', vm=DENY,', ', deviceRequired=true')):
                raise ValueError('Fresh status is not strict with 39 rules')
            text = console.read_text('utf-8', errors='replace')
            result['mixinLines'] = [line for line in text.splitlines() if 'CommandGate12111Mixin' in line]
            result['requiredMixinObserved'] = any('Mixing CommandGate12111Mixin from qizhangverdict.mixins.json into ' in line for line in result['mixinLines'])
            if not result['requiredMixinObserved']:
                raise ValueError('Required command gate Mixin application not observed')
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
                        send(server, 'qzverdict reload')
                        result['restoredStatus'] = wait_status(server, console)
                        result['strictPolicyRestored'] = policy.read_bytes() == baseline and properties(policy) == DEFAULTS
                    send(server, 'stop')
                    server.wait(timeout=90)
                    result['normalStop'] = server.returncode == 0
                except Exception as error:
                    result['stopError'] = type(error).__name__ + ': ' + str(error)
                finally:
                    if server.poll() is None:
                        result['forcedServerTermination'] = True; server.kill(); server.wait(timeout=30)
            result['serverExitCode'] = server.returncode if server is not None else None
    result['elapsedSeconds'] = round(time.monotonic() - begin, 3)
    result['console'] = record(console)
    text = console.read_text('utf-8', errors='replace')
    result['warningAndErrorLines'] = [line for line in text.splitlines() if any(token in line for token in ('WARN', 'ERROR', 'Exception'))]
    if (directory / 'protocol-console.log').exists():
        raw = (directory / 'protocol-console.log').read_text('utf-8', errors='replace')
        result['protocolDecoderErrors'] = [line for line in raw.splitlines() if line.startswith('PartialReadError:')]
        result['protocolConsole'] = record(directory / 'protocol-console.log')
    result['passed'] = (result['started'] and result['defaultPolicyVerified'] and result['defaultCatalogVerified']
        and result['requiredMixinObserved'] and result['normalStop'] and result.get('strictPolicyRestored', False)
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
    p.add_argument('--java', default='D:/Java/jdk-21/bin/java.exe')
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
