#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Production Forge 1.8.9 QA; isolated files and native Java 8 only."""
from __future__ import annotations
import argparse
import concurrent.futures
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import struct
import sys
import time
import uuid
import zipfile
import zlib

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'platforms/client-matrix-smoke.py'
SPEC = importlib.util.spec_from_file_location('verdict189_helpers', HELPER)
matrix = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(matrix)
CACHE = Path(r'E:\CodexTemp\QiZhangVerdict\legacy-client-matrix\forge-1.8.9')
FIXTURE = Path(r'E:\CodexTemp\QiZhangVerdict\legacy-runtime\forge-1.8.9-guard-01')
JAVA = Path(r'E:\CodexTemp\QiZhangVerdict\toolchains\jdk8\jdk8u504-b01\bin\java.exe')
INSTALLER = FIXTURE.parent / 'downloads/forge-1.8.9-11.15.1.2318-1.8.9-installer.jar'
INSTALLER_SHA = 'f9fdf4945ca02d73ec6cc46300942f4e199e4add068877d517157b3677563656'
GUARD = ROOT / 'platforms/1.8.9/forge/build/libs/qizhangverdict-forge-1.8.9-0.2.0-dev.jar'
GUARD_SHA = 'f00943b06e87dbfc04e88336134ab4ae1a571a6e9b53924ab6bc06b311918424'
BUKKIT = ROOT / 'bukkit/build/libs/qizhangverdict-bukkit-0.1.1.jar'
BUKKIT_SHA = 'e1194b8b694763afbc431e22799f40d357dd80493d194f680edfb219afe94845'
PAPER_FIXTURE = FIXTURE.parent / 'paper-1.8.8-20260925-152413'
PAPER_SHA = '7ff6d2cec671ef0d95b3723b5c92890118fb882d73b7f8fa0a2cd31d97c55f86'
PORT = 25661
MINECRAFT = '1.8.9'
FORGE = '11.15.1.2318-1.8.9'
INSTALLER_URL = ('https://maven.minecraftforge.net/net/minecraftforge/forge/1.8.9-' + FORGE +
                 '/forge-1.8.9-' + FORGE + '-installer.jar')
NAME = 'VerdictClient'
identity = bytearray(hashlib.md5(('OfflinePlayer:' + NAME).encode()).digest())
identity[6] = (identity[6] & 15) | 48
identity[8] = (identity[8] & 63) | 128
PLAYER_UUID = str(uuid.UUID(bytes=bytes(identity)))


def prepare():
    """Official files only; no installer, Java process or game starts here."""
    directory = CACHE / 'client'
    directory.mkdir(parents=True, exist_ok=True)
    if matrix.digest(INSTALLER) != INSTALLER_SHA:
        raise ValueError('Official installer hash mismatch')
    installer_sha1 = matrix.fetch(INSTALLER_URL + '.sha1').decode('ascii').split()[0].lower()
    if not re.fullmatch(r'[0-9a-f]{40}', installer_sha1) or matrix.digest(INSTALLER, 'sha1') != installer_sha1:
        raise ValueError('Official installer SHA-1 mismatch')
    official_manifest = json.loads(matrix.fetch('https://piston-meta.mojang.com/mc/game/version_manifest_v2.json'))
    version_reference = next(item for item in official_manifest['versions'] if item['id'] == MINECRAFT)
    version_bytes = matrix.fetch(version_reference['url'])
    if hashlib.sha1(version_bytes).hexdigest() != version_reference['sha1']:
        raise ValueError('Official Mojang metadata hash mismatch')
    metadata = json.loads(version_bytes)
    vanilla = directory / 'versions/1.8.9'
    vanilla.mkdir(parents=True, exist_ok=True)
    (vanilla / '1.8.9.json').write_bytes(version_bytes)
    matrix.save(directory / 'official-version-reference.json', version_reference)
    client = matrix.artifact(vanilla / '1.8.9.jar', metadata['downloads']['client'])
    with zipfile.ZipFile(INSTALLER) as archive:
        if archive.testzip() is not None:
            raise ValueError('Official installer ZIP CRC failure')
        install_profile_bytes = archive.read('install_profile.json')
        install_profile = json.loads(install_profile_bytes)
        profile = install_profile['versionInfo']
        universal_bytes = archive.read(install_profile['install']['filePath'])
    if (profile['inheritsFrom'] != MINECRAFT or profile['mainClass'] != 'net.minecraft.launchwrapper.Launch'
            or install_profile['install']['minecraft'] != MINECRAFT):
        raise ValueError('Unexpected official Forge profile')
    (directory / 'install-profile.json').write_bytes(install_profile_bytes)
    matrix.save(directory / 'loader-profile.json', profile)
    matrix.save(directory / 'versions' / profile['id'] / (profile['id'] + '.json'), profile)
    priors = [FIXTURE / 'libraries', matrix.PRIOR_FORGE / 'libraries']
    priors.extend(CACHE.parent / version / 'client/libraries' for version in
                  ('forge-1.12.2', 'forge-1.16.5', 'forge-1.18.2', 'forge-1.19.4'))
    natives = directory / 'natives'
    natives.mkdir(exist_ok=True)
    libraries = {}
    library_records = []
    native_records = []

    def get_checked_library(entry):
        group, name, version, *classifier = entry['name'].split(':')
        relative = (group.replace('.', '/') + '/' + name + '/' + version + '/' + name + '-' + version +
                    ('-' + classifier[0] if classifier else '') + '.jar')
        if entry['name'] == install_profile['install']['path']:
            path = directory / 'libraries' / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(universal_bytes)
            detail = {'path': relative, 'sha1': hashlib.sha1(universal_bytes).hexdigest(),
                      'url': INSTALLER_URL + '!/' + install_profile['install']['filePath'],
                      'verification': 'Embedded bytes of official SHA-1/SHA-256 verified installer'}
        else:
            detail = dict(entry.get('downloads', {}).get('artifact') or {})
            if not detail:
                url = entry.get('url', 'https://libraries.minecraft.net/').rstrip('/') + '/' + relative
                official_checksums = entry.get('checksums', [])
                cached = [directory / 'libraries' / relative] + [prior / relative for prior in priors]
                matching = next((p for p in cached if p.is_file() and matrix.digest(p, 'sha1') in official_checksums), None)
                if matching:
                    detail = {'path': relative, 'url': url, 'sha1': matrix.digest(matching, 'sha1'),
                              'verification': 'Checksum in the verified official Forge install profile'}
                else:
                    failures = []
                    for repository in (entry.get('url', 'https://libraries.minecraft.net/'),
                                       'https://repo.maven.apache.org/maven2/'):
                        candidate_url = repository.rstrip('/') + '/' + relative
                        try:
                            sidecar = matrix.fetch(candidate_url + '.sha1').decode('ascii').split()[0].lower()
                            if not re.fullmatch(r'[0-9a-f]{40}', sidecar):
                                raise ValueError('Malformed official SHA-1')
                            if official_checksums and sidecar not in official_checksums:
                                raise ValueError('Repository SHA-1 differs from verified Forge profile')
                            detail = {'path': relative, 'url': candidate_url, 'sha1': sidecar,
                                      'verification': 'Official publisher repository SHA-1 sidecar',
                                      'prior_repository_failures': failures}
                            # A SHA-1 sidecar existing does not guarantee the JAR URL remains live.
                            matrix.artifact(directory / 'libraries' / relative, detail, cached)
                            break
                        except Exception as error:
                            failures.append({'url': candidate_url, 'error': type(error).__name__ + ': ' + str(error)})
                    else:
                        raise ValueError('Official library unavailable: ' + entry['name'] + ': ' + str(failures))
            if not re.fullmatch(r'[0-9a-f]{40}', detail.get('sha1', '')):
                raise ValueError('Missing official library checksum: ' + entry['name'])
            path = matrix.artifact(directory / 'libraries' / detail['path'], detail,
                                   [prior / detail['path'] for prior in priors])
        if matrix.digest(path, 'sha1') != detail['sha1'] or ('size' in detail and path.stat().st_size != detail['size']):
            raise ValueError('Official library bytes/hash mismatch: ' + entry['name'])
        library_records.append({**matrix.artifact_record(path), 'coordinate': entry['name'],
                                'official_sha1': detail['sha1'], 'source': detail['url'],
                                'prior_repository_failures': detail.get('prior_repository_failures', []),
                                'verification': detail.get('verification', 'Official Mojang metadata SHA-1/size')})
        return path

    def add(entry):
        path = get_checked_library(entry)
        parts = entry['name'].split(':')
        libraries[':'.join(parts[:2]) + (':' + parts[3] if len(parts) > 3 else '')] = str(path)

    for entry in metadata['libraries'] + profile['libraries']:
        if not matrix.allowed(entry) or entry.get('clientreq') is False:
            continue
        # Some old metadata entries contain only native classifiers, no classpath JAR.
        if entry.get('downloads', {}).get('artifact') or entry in profile['libraries']:
            add(entry)
        classifier = entry.get('natives', {}).get('windows', '').replace('${arch}', '64')
        detail = entry.get('downloads', {}).get('classifiers', {}).get(classifier)
        if detail:
            path = get_checked_library({'name': entry['name'] + ':' + classifier,
                                        'downloads': {'artifact': detail}})
            with zipfile.ZipFile(path) as archive:
                if archive.testzip() is not None:
                    raise ValueError('Native library archive CRC failure')
                for member in archive.namelist():
                    if member.endswith('.dll'):
                        extracted = natives / Path(member).name
                        extracted.write_bytes(archive.read(member))
                        native_records.append({**matrix.artifact_record(extracted),
                                               'archive_sha256': matrix.digest(path), 'member': member})
    index_entry = metadata['assetIndex']
    index_id = index_entry['id']
    asset_root = directory / 'assets'
    index = matrix.artifact(asset_root / 'indexes' / (index_id + '.json'), index_entry)
    objects = matrix.read(index)['objects']
    asset_priors = [CACHE.parent / version / 'client/assets/objects' for version in
                    ('forge-1.12.2', 'forge-1.16.5', 'forge-1.18.2', 'forge-1.19.4')]
    asset_priors.append(matrix.PRIOR_FORGE / 'assets/objects')
    def prepare_asset(item):
        relative = Path(item['hash'][:2]) / item['hash']
        path = matrix.artifact(asset_root / 'objects' / relative,
                               {'url': 'https://resources.download.minecraft.net/' + relative.as_posix(),
                                'sha1': item['hash']}, [prior / relative for prior in asset_priors])
        if path.stat().st_size != item['size']:
            raise ValueError('Official asset size mismatch')
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(prepare_asset, {item['hash']: item for item in objects.values()}.values()))
    objects = matrix.read(directory / 'assets/indexes' / (index_id + '.json'))['objects']
    for item in objects.values():
        path = directory / 'assets/objects' / item['hash'][:2] / item['hash']
        if path.stat().st_size != item['size'] or matrix.digest(path, 'sha1') != item['hash']:
            raise ValueError('Asset bytes/hash mismatch')
    logging = metadata['logging']['client']
    logging_file = matrix.artifact(directory / 'assets/log_configs' / logging['file']['id'], logging['file'])
    game = directory / 'game'
    (game / 'mods').mkdir(parents=True, exist_ok=True)
    if matrix.digest(GUARD) != GUARD_SHA:
        raise ValueError('Pinned product changed')
    shutil.copy2(GUARD, game / 'mods' / GUARD.name)
    (game / 'options.txt').write_text('fullscreen:false\nrenderDistance:2\nmaxFps:30\npauseOnLostFocus:false\n', encoding='ascii')
    plan = {'minecraft': '1.8.9', 'loader_version': '11.15.1.2318-1.8.9', 'main': profile['mainClass'],
            'loader_id': profile['id'], 'classpath': list(libraries.values()) + [str(client)],
            'loader_arguments': profile['minecraftArguments'], 'game': str(game), 'assets': str(directory / 'assets'),
            'asset_index': index_id, 'natives': str(natives), 'vanilla_client_sha1': matrix.digest(client, 'sha1'),
            'client_logging': matrix.artifact_record(logging_file),
            'logging_argument': logging['argument'].replace('${path}', str(logging_file)),
            'installer_sha256': INSTALLER_SHA, 'installer_official_sha1': installer_sha1,
            'metadata_reference': version_reference, 'library_artifacts': library_records, 'native_files': native_records,
            'asset_index_sha1': matrix.digest(index, 'sha1'),
            'asset_objects_verified': len({v['hash'] for v in objects.values()}),
            'guard_source': str(GUARD), 'guard_sha256': GUARD_SHA,
            'targets': [{'kind': 'forge', 'server_minecraft': '1.8.9', 'port': PORT},
                        {'kind': 'bukkit', 'server_minecraft': '1.8.8', 'port': PORT}],
            'compatibility_claim': 'Prepared only; no live client/server compatibility conclusion. This is not a native Forge 1.8.8 adapter.',
            'java_executed': False, 'helper_sha256': matrix.digest(HELPER), 'harness_sha256': matrix.digest(Path(__file__))}
    matrix.save(directory / 'base-plan.json', plan)
    print(json.dumps({'prepared': True, 'java_executed': False, 'assets': plan['asset_objects_verified']}), flush=True)


def install():
    directory = CACHE / 'client'
    plan = matrix.read(directory / 'base-plan.json')
    if matrix.digest(GUARD) != GUARD_SHA or matrix.digest(INSTALLER) != INSTALLER_SHA:
        raise ValueError('Pinned product or installer changed')
    result_path = directory / 'client-install-result.json'
    if not result_path.exists():
        matrix.save(directory / 'launcher_profiles.json', {'profiles': {}})
        shutil.copytree(FIXTURE / 'libraries', directory / 'libraries', dirs_exist_ok=True)
        log = directory / 'install-console.log'
        with log.open('xb') as output:
            process = subprocess.run([str(JAVA), '-Xmx1G', '-Djava.awt.headless=true', '-jar', str(INSTALLER),
                                      '--installClient', str(directory)], cwd=directory, stdout=output,
                                     stderr=subprocess.STDOUT, timeout=900, creationflags=matrix.NO_WINDOW,
                                     env=matrix.runtime_environment(directory))
        matrix.save(result_path, {'exit_code': process.returncode, 'installer_sha256': INSTALLER_SHA,
                                 'console': matrix.artifact_record(log)})
    if matrix.read(result_path)['exit_code'] != 0:
        raise RuntimeError('Retained client installer failure; investigate before creating a new attempt')
    verify_prepared_inputs(plan)
    shutil.copy2(GUARD, Path(plan['game']) / 'mods' / GUARD.name)
    plan.update({'guard_sha256': GUARD_SHA, 'guard_source': str(GUARD)})
    matrix.save(directory / 'launch-plan.json', plan)
    print('Official client installer passed; candidate staged', flush=True)


def verify_prepared_inputs(plan):
    for item in plan['library_artifacts'] + plan['native_files']:
        path = Path(item['path'])
        if matrix.digest(path) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('Prepared official library/native changed: ' + path.name)
    client = CACHE / 'client/versions/1.8.9/1.8.9.jar'
    if matrix.digest(client, 'sha1') != plan['vanilla_client_sha1']:
        raise ValueError('Prepared official Minecraft client changed')
    if matrix.digest(Path(plan['client_logging']['path'])) != plan['client_logging']['sha256']:
        raise ValueError('Prepared official logging configuration changed')


def stage():
    """Old Forge has no --installClient CLI; use its verified production profile directly."""
    directory = CACHE / 'client'
    plan = matrix.read(directory / 'base-plan.json')
    verify_prepared_inputs(plan)
    if matrix.digest(GUARD) != GUARD_SHA or matrix.digest(INSTALLER) != INSTALLER_SHA:
        raise ValueError('Pinned product or official installer changed')
    if plan['main'] != 'net.minecraft.launchwrapper.Launch':
        raise ValueError('Unexpected official production entry point')
    shutil.copy2(GUARD, Path(plan['game']) / 'mods' / GUARD.name)
    # The embedded universal Forge JAR is used unmodified. No dev classes,
    # generated Minecraft classes, library patches or authentication changes.
    plan.update({'guard_sha256': GUARD_SHA, 'guard_source': str(GUARD),
                 'launch_method': 'Official install_profile versionInfo and unmodified embedded universal JAR',
                 'staging_harness_sha256': matrix.digest(Path(__file__))})
    matrix.save(directory / 'launch-plan.json', plan)
    failed = directory / 'client-install-result.json'
    matrix.save(directory / 'client-stage-result.json', {
        'prepared': True, 'java_executed': False, 'runtime_acceptance': False,
        'guard_sha256': GUARD_SHA, 'installer_sha256': INSTALLER_SHA,
        'launch_method': plan['launch_method'],
        'legacy_installer_cli_boundary': 'This official SimpleInstaller does not implement --installClient; retained attempt is not a product/runtime failure.',
        'retained_installer_attempt': matrix.artifact_record(failed) if failed.exists() else None,
        'harness_sha256': plan['staging_harness_sha256']})
    print('Verified official production profile staged without executing Java', flush=True)


def client_command(plan):
    # LaunchWrapper requires the Forge tweaker from this exact official profile.
    expected = '--tweakClass net.minecraftforge.fml.common.launcher.FMLTweaker'
    if expected not in plan['loader_arguments']:
        raise ValueError('Unexpected Forge 1.8.9 launch profile')
    return [str(JAVA), '-Xms256M', '-Xmx2G', '-Dfile.encoding=UTF-8', plan['logging_argument'],
            '-Djava.library.path=' + plan['natives'], '-cp', os.pathsep.join(plan['classpath']), plan['main'],
            '--username', NAME, '--version', plan['loader_id'], '--gameDir', plan['game'], '--assetsDir', plan['assets'],
            '--assetIndex', plan['asset_index'], '--uuid', PLAYER_UUID, '--accessToken', '0', '--userType', 'legacy',
            '--userProperties', '{}',
            '--tweakClass', 'net.minecraftforge.fml.common.launcher.FMLTweaker', '--versionType', 'Forge',
            '--width', '640', '--height', '360', '--server', '127.0.0.1', '--port', str(PORT)]


def prepare_server(run_name, kind):
    if not re.fullmatch(r'[a-zA-Z0-9._-]+', run_name) or run_name in ('.', '..'):
        raise ValueError('Run name must be a simple child name')
    target = CACHE / run_name / 'server'
    target.mkdir(parents=True, exist_ok=False)
    source = FIXTURE if kind == 'forge' else PAPER_FIXTURE
    for child in source.iterdir():
        if child.name in ('libraries', 'cache') and child.is_dir():
            shutil.copytree(child, target / child.name)
        elif child.is_file() and child.suffix == '.jar':
            shutil.copy2(child, target / child.name)
    if kind == 'forge':
        (target / 'mods').mkdir()
        shutil.copy2(GUARD, target / 'mods' / GUARD.name)
    else:
        if matrix.digest(BUKKIT) != BUKKIT_SHA or matrix.digest(source / 'server.jar') != PAPER_SHA:
            raise ValueError('Pinned Paper/plugin mismatch')
        (target / 'plugins').mkdir()
        shutil.copy2(BUKKIT, target / 'plugins' / BUKKIT.name)
    (target / 'eula.txt').write_text('eula=true\n', encoding='ascii')
    (target / 'server.properties').write_text(
        f'server-ip=127.0.0.1\nserver-port={PORT}\nonline-mode=false\nlevel-name=world\nlevel-type=FLAT\n'
        'generator-settings=3;minecraft:bedrock,2*minecraft:dirt,minecraft:grass;1;\n'
        'spawn-protection=0\nview-distance=2\nmax-players=5\ndifficulty=0\ngamemode=0\nenable-rcon=false\n'
        'enable-query=false\ngenerate-structures=false\nnetwork-compression-threshold=256\n', encoding='ascii')
    return target, matrix.read(FIXTURE / '.qizhang-189-basic.json')['serverEntry'] if kind == 'forge' else 'server.jar'


def policy(directory, kind):
    folder = directory / ('config/qizhangverdict' if kind == 'forge' else 'plugins/QiZhangVerdict')
    path = folder / 'guard.properties'
    values = dict(line.split('=', 1) for line in path.read_text('utf-8').splitlines() if line and not line.startswith('#'))
    return {**matrix.artifact_record(path), 'values': values, 'matches_strict_defaults': values == matrix.EXPECTED_POLICY}


def has_association(directory, kind):
    path = directory / ('config/qizhangverdict' if kind == 'forge' else 'plugins/QiZhangVerdict') / 'accounts.state'
    return path.exists() and any(re.fullmatch(r'D\t' + re.escape(PLAYER_UUID) + r'\t[0-9a-f]{64}', line)
                                 for line in path.read_text('utf-8').splitlines())


def png_verified(path):
    raw = path.read_bytes()
    if raw[:8] != b'\x89PNG\r\n\x1a\n':
        return False
    offset, compressed, dimensions = 8, bytearray(), None
    while offset < len(raw):
        size = struct.unpack('>I', raw[offset:offset + 4])[0]
        kind = raw[offset + 4:offset + 8]
        payload = raw[offset + 8:offset + 8 + size]
        crc = struct.unpack('>I', raw[offset + 8 + size:offset + 12 + size])[0]
        if zlib.crc32(kind + payload) & 0xffffffff != crc:
            return False
        if kind == b'IHDR': dimensions = struct.unpack('>II', payload[:8])
        if kind == b'IDAT': compressed.extend(payload)
        offset += 12 + size
        if kind == b'IEND': break
    return dimensions == (640, 360) and len(zlib.decompress(compressed)) > 640 * 360 * 3


def close_legacy_client(pid):
    # LWJGL 2 WindowsDisplay requests shutdown on WM_SYSCOMMAND / SC_CLOSE.
    # WM_CLOSE alone can destroy the native window without setting its Java flag.
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def callback(handle, unused):
        owner = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(owner))
        if owner.value == pid:
            user32.PostMessageW(handle, 0x0112, 0xF060, 0)
        return True
    user32.EnumWindows(callback_type(callback), 0)


def run(run_name, kind):
    with socket.socket() as port:
        port.bind(('127.0.0.1', PORT))
    plan = matrix.read(CACHE / 'client/launch-plan.json')
    verify_prepared_inputs(plan)
    if matrix.digest(GUARD) != GUARD_SHA or matrix.digest(Path(plan['game']) / 'mods' / GUARD.name) != GUARD_SHA:
        raise ValueError('Pinned candidate changed')
    server_dir, entry = prepare_server(run_name, kind)
    directory = server_dir.parent
    server_log, client_log = directory / 'server-console.log', directory / 'client-console.log'
    result = {'minecraft': '1.8.9', 'loader': 'Forge 11.15.1.2318-1.8.9', 'guard_sha256': GUARD_SHA,
              'scope': 'Production rendered Forge client and ' + kind + ' server, offline-auth loopback only',
              'server_minecraft': '1.8.9' if kind == 'forge' else '1.8.8',
              'native_forge_1_8_8_adapter_claimed': False,
              'server_kind': kind, 'server_guard_sha256': GUARD_SHA if kind == 'forge' else BUKKIT_SHA,
              'vanilla_client_sha1': plan['vanilla_client_sha1'], 'java': str(JAVA),
              'launch_method': plan.get('launch_method', 'Official Forge profile'),
              'harness_sha256': matrix.digest(Path(__file__)), 'helper_sha256': matrix.digest(HELPER),
              'client_logging': plan['client_logging'], 'passed': False}
    server = client = None
    start = time.monotonic()
    client_start = None
    try:
        with server_log.open('xb') as server_out, client_log.open('xb') as client_out:
            server = subprocess.Popen([str(JAVA), '-Xms256M', '-Xmx1536M', '-Djava.awt.headless=true',
                                       '-Dfile.encoding=UTF-8', '-jar', entry, 'nogui'], cwd=server_dir,
                                      stdin=subprocess.PIPE, stdout=server_out, stderr=subprocess.STDOUT,
                                      creationflags=matrix.NO_WINDOW, env=matrix.runtime_environment(server_dir))
            def console(value):
                if server.poll() is None:
                    server.stdin.write((value + '\n').encode()); server.stdin.flush()
            while server.poll() is None and time.monotonic() - start < 240:
                log = matrix.text_log(server_log)
                if re.search(r'Done \([\d.,]+s\)!', log) and 'deviceRequired=true' in log:
                    break
                time.sleep(.5)
            else:
                raise RuntimeError('Strict server did not become ready')
            before = policy(server_dir, kind)
            result['policy_before_client'] = before
            if not before['matches_strict_defaults']:
                raise RuntimeError('Server does not use complete strict defaults')
            console('gamerule doMobSpawning false'); console('qzverdict status')
            client_start = time.time()
            client = subprocess.Popen(client_command(plan), cwd=plan['game'], stdout=client_out, stderr=subprocess.STDOUT,
                                      creationflags=matrix.NO_WINDOW, env=matrix.runtime_environment(Path(plan['game'])))
            print('Running production Forge 1.8.9', 'server', server.pid, 'client', client.pid, flush=True)
            began = time.monotonic()
            joined = validated = last_query = None
            captured = False
            acceptance_timestamp = None
            final_live_line = None
            observed_duration = 0
            while client.poll() is None and time.monotonic() - began < 300:
                matrix.windows(client.pid)
                now = time.monotonic()
                log = matrix.text_log(server_log)
                # Old Paper logs PlayerList admission, but not the join broadcast.
                joined_line = NAME + ' joined the game' in log or (kind == 'bukkit' and
                    re.search(r'\bVerdictClient\[/127\.0\.0\.1:\d+\] logged in with entity id ', log))
                if joined is None and joined_line:
                    joined = now; print('Joined real Forge 1.8.9', flush=True)
                if joined is not None and now - joined >= 5 and (last_query is None or now - last_query >= 10):
                    console('list'); console('qzverdict status'); console('testfor @a[name=VerdictClient,m=0]')
                    last_query = now
                accepted = 'Found VerdictClient' in log and has_association(server_dir, kind)
                if validated is None and accepted:
                    validated = now; print('Required report accepted; survival confirmed', flush=True)
                    acceptance_timestamp = time.strftime('%H:%M:%S')
                if not captured and ((validated is not None and now - validated >= 30) or now - began > 100):
                    matrix.windows(client.pid, screenshot=True); captured = True
                if validated is not None and now - validated >= 65:
                    # Require a NEW server response after the observation window.
                    # Old successful queries remain in the log after disconnect.
                    final_offset = len(matrix.text_log(server_log))
                    console('list'); console('testfor @a[name=VerdictClient,m=0]')
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline and client.poll() is None:
                        suffix = matrix.text_log(server_log)[final_offset:]
                        fresh = [line for line in suffix.splitlines() if 'Found VerdictClient' in line]
                        if fresh:
                            final_live_line = fresh[-1]
                            observed_duration = time.monotonic() - validated
                            break
                        time.sleep(.1)
                    break
                if joined is not None and validated is None and now - joined > 45:
                    break
                time.sleep(.25)
            if client.poll() is None:
                close_legacy_client(client.pid); client.wait(timeout=30)
            console('stop'); server.wait(timeout=90)
        after = policy(server_dir, kind)
        log, client_text = matrix.text_log(server_log), matrix.text_log(client_log)
        modes = [line for line in log.splitlines() if 'Found VerdictClient' in line]
        duration = round(observed_duration, 3)
        association = has_association(server_dir, kind)
        strict = before['matches_strict_defaults'] and after['matches_strict_defaults'] and before['sha256'] == after['sha256']
        rendered = 'OpenAL initialized' in client_text and 'textures-atlas' in client_text
        warnings = 'Missing metadata in pack mod:qizhangverdict' in client_text or 'failed to load a valid ResourcePackInfo' in client_text
        result.update({'policy_after_client': after, 'strict_defaults': strict, 'policy_unchanged': before['sha256'] == after['sha256'],
                       'persisted_device_association': association, 'survival_mode_confirmed': bool(modes),
                       'restored_survival_from_spectator': kind == 'forge' and bool(modes),
                       'confirmed_online_seconds_after_report_evidence': duration,
                       'report_acceptance_basis': ('Exact UUID device association persisted and vanilla testfor m=0 succeeds after required-report spectator isolation; then >=65 monotonic seconds and a fresh successful query.' if kind == 'forge' else
                           'Device association persisted for this exact UUID, followed by >=65 monotonic seconds and a fresh survival/online query under the unchanged 20-second required-report deadline. Survival alone is not report proof or a mode transition.'),
                       'acceptance_observed_local_time': acceptance_timestamp,
                       'final_fresh_survival_query': final_live_line,
                       'survival_query_lines': modes, 'rendered_client_confirmed': rendered,
                       'resource_pack_metadata_warning': warnings, 'elapsed_seconds': round(time.monotonic() - start, 2)})
        result['passed'] = strict and association and rendered and not warnings and bool(final_live_line) and duration >= 65 and client.returncode == 0 and server.returncode == 0
    except Exception as error:
        # TimeoutExpired embeds the entire command line; retain a bounded summary.
        result['error'] = ('TimeoutExpired: process did not exit within ' + str(error.timeout) + ' seconds'
                           if isinstance(error, subprocess.TimeoutExpired) else type(error).__name__ + ': ' + str(error))
    finally:
        if client is not None and client.poll() is None:
            close_legacy_client(client.pid)
            try: client.wait(timeout=20)
            except subprocess.TimeoutExpired: client.terminate(); client.wait(timeout=10)
        if server is not None and server.poll() is None:
            try: server.stdin.write(b'stop\n'); server.stdin.flush(); server.wait(timeout=90)
            except (OSError, subprocess.TimeoutExpired): server.terminate(); server.wait(timeout=15)
        result['client_exit_code'] = client.returncode if client else None
        result['server_exit_code'] = server.returncode if server else None
        result['raw_evidence'] = [matrix.artifact_record(p) for p in (server_log, client_log) if p.exists()]
        valid_screenshots = 0
        if client_start:
            for path in (Path(plan['game']) / 'screenshots').glob('*.png'):
                if path.stat().st_mtime >= client_start:
                    output = directory / 'screenshots' / path.name
                    output.parent.mkdir(exist_ok=True); shutil.copy2(path, output)
                    result['raw_evidence'].append(matrix.artifact_record(output))
                    try:
                        valid_screenshots += int(png_verified(output))
                    except (ValueError, struct.error, zlib.error):
                        pass
        result['verified_current_run_pngs'] = valid_screenshots
        result['passed'] = result['passed'] and valid_screenshots > 0
        matrix.save(directory / 'result.json', result)
    print(json.dumps({'passed': result['passed'], 'result': str(directory / 'result.json'), 'error': result.get('error')}), flush=True)
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'install', 'stage', 'run'))
    parser.add_argument('--run-name', default='candidate-0.2.0-dev-gpl-01')
    parser.add_argument('--server-kind', choices=('forge', 'bukkit'), default='forge')
    args = parser.parse_args()
    if args.action == 'prepare': prepare()
    elif args.action == 'install': install()
    elif args.action == 'stage': stage()
    else: run(args.run_name, args.server_kind)
