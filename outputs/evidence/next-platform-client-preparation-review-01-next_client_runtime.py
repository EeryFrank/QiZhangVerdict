# SPDX-License-Identifier: GPL-3.0-only
"""Explicit runtime half of next_client_smoke; importing it starts no process."""
import ctypes
import hashlib
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import time
import uuid
import zipfile
import zlib

import next_client_smoke as qa

PLAYER = 'VerdictNextClient'
identity = bytearray(hashlib.md5(('OfflinePlayer:' + PLAYER).encode('utf-8')).digest())
identity[6] = (identity[6] & 15) | 48; identity[8] = (identity[8] & 63) | 128
PLAYER_UUID = str(uuid.UUID(bytes=bytes(identity)))
STRICT = {'limits.max-online-per-ip': '3', 'limits.max-online-per-ip-device': '1', 'limits.max-accounts-per-ip': '5',
          'limits.account-window-hours': '720', 'limits.attempts-per-minute': '20', 'ip.allow': '', 'ip.deny': '',
          'companion.required': 'true', 'companion.timeout-seconds': '20', 'vm.action': 'DENY',
          'blacklist.action': 'DENY', 'sanctions.on-deny': 'BAN', 'device.required': 'true'}


def text(path):
    return re.sub(r'\x1b\[[0-9;]*m', '', Path(path).read_text('utf-8', errors='replace')) if Path(path).exists() else ''


def policy(server):
    path = server / 'config/qizhangverdict/guard.properties'
    values = dict(line.split('=', 1) for line in path.read_text('utf-8').splitlines() if line and not line.startswith('#'))
    blacklist = path.parent / 'blacklist.tsv'
    def rows(file): return sorted(line for line in file.read_text('utf-8').splitlines() if line and not line.startswith('#'))
    catalog = qa.ROOT / 'catalog/blacklist-extension.tsv'
    expected = rows(catalog); actual = rows(blacklist)
    return {**qa.record(path), 'strictSettingCount': len(STRICT), 'exact13Defaults': values == STRICT,
            'defaultRuleCount': len(actual), 'default37RulesMatchCatalog': len(expected) == 37 and actual == expected,
            'blacklistSha256': qa.sha(blacklist), 'catalogSha256': qa.sha(catalog)}


def associated(server):
    path = server / 'config/qizhangverdict/accounts.state'
    # Never return or print a system installation ID or scoped device digest.
    return path.is_file() and any(re.fullmatch(r'D\t' + re.escape(PLAYER_UUID) + r'\t[0-9a-f]{64}', line)
                                  for line in path.read_text('utf-8').splitlines())


def windows(pid, action):
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    handles = []
    def callback(handle, unused):
        owner = ctypes.c_ulong(); user32.GetWindowThreadProcessId(handle, ctypes.byref(owner))
        if owner.value == pid:
            handles.append(int(handle))
            if action == 'screenshot':
                user32.PostMessageW(handle, 0x0100, 0x71, 0x003C0001)
                user32.PostMessageW(handle, 0x0101, 0x71, 0xC03C0001)
            elif action == 'close':
                # LWJGL3/GLFW uses the ordinary close request; this is not the
                # LWJGL2 SC_CLOSE workaround used by the separate 1.8/1.12 QA.
                user32.PostMessageW(handle, 0x0010, 0, 0)
            else: user32.ShowWindow(handle, 0)
        return True
    user32.EnumWindows(callback_type(callback), 0)
    return handles


def png_record(path):
    raw = path.read_bytes(); assert raw[:8] == b'\x89PNG\r\n\x1a\n'
    offset, compressed, header, chunks, ended = 8, bytearray(), None, 0, False
    while offset < len(raw):
        assert offset + 12 <= len(raw)
        size = struct.unpack('>I', raw[offset:offset + 4])[0]; assert offset + size + 12 <= len(raw)
        kind = raw[offset + 4:offset + 8]; payload = raw[offset + 8:offset + 8 + size]
        crc = struct.unpack('>I', raw[offset + 8 + size:offset + 12 + size])[0]
        assert zlib.crc32(kind + payload) & 0xffffffff == crc
        if kind == b'IHDR': header = struct.unpack('>IIBBBBB', payload)
        elif kind == b'IDAT': compressed.extend(payload)
        chunks += 1; offset += size + 12
        if kind == b'IEND': ended = True; break
    assert ended and offset == len(raw) and header is not None
    width, height, depth, color, compression, filtering, interlace = header
    assert (width, height) == (640, 360) and depth == 8 and color in (2, 6)
    assert (compression, filtering, interlace) == (0, 0, 0)
    scanlines = zlib.decompress(compressed); stride = width * (3 if color == 2 else 4)
    assert len(scanlines) == height * (stride + 1)
    assert all(scanlines[y * (stride + 1)] in range(5) for y in range(height))
    return {**qa.record(path), 'width': width, 'height': height, 'crcCheckedChunks': chunks,
            'zlibAndScanlinesValid': True, 'manualVisualReviewPassed': None,
            'boundary': 'Valid PNG bytes are not evidence of correct world/HUD rendering; inspect this exact hash.'}


def prepare_run(profile, base_name, run_name, port):
    if not 1024 <= port <= 65535: raise ValueError('Use an isolated nonprivileged loopback port')
    base = qa.base_directory(profile, base_name); plan = qa.read(base / 'base-plan.json')
    if plan['needsClientInstaller']:
        installed = qa.read(base / 'client-install-result.json')
        if installed.get('exitCode') != 0 or installed.get('error') or not installed.get('generatedLibrariesVerified'):
            raise ValueError('Official client installation has not passed verification')
    guard = Path(plan['guard']['path'])
    if qa.sha(guard) != plan['guard']['sha256']: raise ValueError('Prepared candidate changed')
    source = Path(plan['serverFixtureSource']); marker = qa.read(source / '.qizhang-verdict-smoke.json')
    if not marker.get('prepared') or marker.get('profile') != profile: raise ValueError('Matching server fixture is not installed')
    with socket.socket() as sock: sock.bind(('127.0.0.1', port))
    directory = base.parent / 'runs' / run_name
    directory.mkdir(parents=True, exist_ok=False)
    server, game = directory / 'server', directory / 'client-game'; server.mkdir(); (game / 'mods').mkdir(parents=True)
    for folder in ('libraries', 'versions', '.fabric'):
        if (source / folder).is_dir(): shutil.copytree(source / folder, server / folder)
    # Do not clone any world, config, mod list, account state, player or operator files.
    for file in source.glob('*.jar'):
        if file.name != 'loader-installer.jar': shutil.copyfile(file, server / file.name)
    (server / 'mods').mkdir()
    for target in (server / 'mods' / guard.name, game / 'mods' / guard.name): qa.verified_copy(guard, target, plan['guard']['sha256'])
    if plan['fabricApi']:
        api = plan['fabricApi']
        for folder in (server / 'mods', game / 'mods'): qa.verified_copy(api['path'], folder / Path(api['path']).name, api['sha256'])
    (server / 'eula.txt').write_text('eula=true\n', encoding='ascii')
    (server / 'server.properties').write_text(
        f'server-ip=127.0.0.1\nserver-port={port}\nonline-mode=false\nenforce-secure-profile=false\n'
        'view-distance=2\nsimulation-distance=2\nmax-players=5\nspawn-protection=0\nallow-flight=false\nenable-rcon=false\nenable-query=false\n'
        'level-name=world\nlevel-seed=12955\ndifficulty=peaceful\ngamemode=survival\ngenerate-structures=false\nlevel-type=minecraft:flat\n'
        'generator-settings={"layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:dirt","height":2},{"block":"minecraft:grass_block","height":1}],"biome":"minecraft:plains"}\n', encoding='ascii')
    (game / 'options.txt').write_text('fullscreen:false\nrenderDistance:2\nsimulationDistance:5\nmaxFps:30\npauseOnLostFocus:false\njoinedFirstServer:true\nskipMultiplayerWarning:true\n', encoding='ascii')
    for script in (Path(__file__), Path(qa.__file__)): shutil.copyfile(script, directory / script.name)
    return directory, server, game, plan, marker


def client_command(profile, plan, game, port):
    classpath = []
    for entry in plan['classpath']:
        path = Path(entry['path'])
        if not path.is_file(): raise ValueError('Missing exact classpath entry: ' + str(path))
        if entry.get('sha256') and qa.sha(path) != entry['sha256']: raise ValueError('Prepared library changed')
        if entry.get('sha1') and qa.sha(path, 'sha1') != entry['sha1']: raise ValueError('Official library SHA-1 mismatch')
        classpath.append(str(path))
    substitutions = {'library_directory': plan['libraries'].replace('\\', '/'), 'classpath_separator': os.pathsep,
                     'version_name': plan['loaderId'], 'natives_directory': plan['natives'], 'launcher_name': 'QiZhangVerdict-QA',
                     'launcher_version': '1', 'classpath': os.pathsep.join(classpath)}
    def expand(value):
        for key, replacement in substitutions.items(): value = value.replace('${' + key + '}', replacement)
        if '${' in value: raise ValueError('Unknown official launch placeholder: ' + value)
        return value
    def expand_args(entries):
        values = []
        for entry in entries:
            if isinstance(entry, str): values.append(expand(entry))
            elif qa.allowed(entry):
                raw = entry['value']; values.extend(expand(x) for x in (raw if isinstance(raw, list) else [raw]))
        return values
    proposed = qa.inputs_for(profile)[0]
    vanilla_jvm = qa.read(proposed['officialMinecraftMetadata']['path'])['arguments']['jvm']
    official_jvm = expand_args(vanilla_jvm) + expand_args(plan['loaderArguments'].get('jvm', []))
    temp = game / 'tmp'; temp.mkdir(exist_ok=True)
    command = [str(qa.JAVA17), '-Xms256M', '-Xmx2G', '-Dfile.encoding=UTF-8', '-Djava.io.tmpdir=' + str(temp),
               plan['loggingArgument'], *official_jvm,
               plan['mainClass'], '--username', PLAYER, '--version', plan['loaderId'], '--gameDir', str(game),
               '--assetsDir', plan['assets']['root'], '--assetIndex', plan['assets']['id'], '--uuid', PLAYER_UUID,
               '--accessToken', '0', '--userType', 'legacy', '--versionType', 'release', '--width', '640', '--height', '360']
    command += ['--server', '127.0.0.1', '--port', str(port)] if plan['minecraft'] == '1.19.2' else ['--quickPlayMultiplayer', '127.0.0.1:' + str(port)]
    command += expand_args(plan['loaderArguments'].get('game', []))
    if profile == 'forge-1.20.4':
        if plan['mainClass'] != 'net.minecraftforge.bootstrap.ForgeBootstrap' or command[command.index('--launchTarget') + 1] != 'forge_client':
            raise ValueError('Forge49 requires its own official bootstrap/launch target')
    return command


def run(profile, base_name, run_name, port):
    directory, server_dir, game, plan, marker = prepare_run(profile, base_name, run_name, port)
    server_log, client_log = directory / 'server-console.log', directory / 'client-console.log'
    result = {'profile': profile, 'candidate': plan['guard'], 'basePlan': qa.record(qa.base_directory(profile, base_name) / 'base-plan.json'),
              'helper': qa.record(__file__), 'preparationHelper': qa.record(qa.__file__), 'javaMajor': 17, 'syntheticPlayerUuid': PLAYER_UUID,
              'authentication': 'Loopback offline-mode fixture with synthetic access token 0; does not validate online account authentication.',
              'passed': False, 'automatedPassed': False, 'formalAcceptancePassed': False, 'manualVisualReviewRequired': True,
              'minimumPostReportSeconds': 60, 'minecraftRuntimeExecuted': False}
    server = client = None; client_started_wall = None; normal_client_exit = normal_server_exit = False
    begin = time.monotonic()
    try:
        result['availablePhysicalGiBBeforeServer'] = qa.memory_gate(5)
        arguments = marker['runtime_args']
        if any(x.startswith(('-Xmx', '-Xms')) for x in arguments): raise ValueError('Server fixture must not override the QA heap limit')
        temp = server_dir / 'tmp'; temp.mkdir()
        with server_log.open('xb') as server_out, client_log.open('xb') as client_out:
            server = subprocess.Popen([str(qa.JAVA17), '-Xms256M', '-Xmx1536M', '-Djava.awt.headless=true', '-Dfile.encoding=UTF-8',
                                       '-Djava.io.tmpdir=' + str(temp), *arguments], cwd=server_dir, env=qa.environment(server_dir),
                                      stdin=subprocess.PIPE, stdout=server_out, stderr=subprocess.STDOUT, creationflags=qa.NO_WINDOW)
            result.update(serverPid=server.pid, minecraftRuntimeExecuted=True)
            def console(command):
                if server.poll() is not None: raise RuntimeError('Server exited before console command')
                server.stdin.write((command + '\n').encode('utf-8')); server.stdin.flush()
            deadline = time.monotonic() + 240
            while time.monotonic() < deadline and server.poll() is None:
                log = text(server_log)
                if re.search(r'Done \([\d.,]+s\)!', log) and 'deviceRequired=true' in log: break
                time.sleep(.25)
            else: raise RuntimeError('Server did not become ready with required-device guard')
            result['policyBefore'] = before = policy(server_dir)
            if not before['exact13Defaults'] or not before['default37RulesMatchCatalog']: raise RuntimeError('Strict defaults/catalog differ before login')
            console('difficulty peaceful'); console('gamerule doMobSpawning false')
            command = client_command(profile, plan, game, port)
            qa.save_new(directory / 'private-launch-plan.json', {'command': command, 'classpathOrigin': 'Explicit official profile only; no wildcard cache enumeration'})
            result['availablePhysicalGiBBeforeClient'] = qa.memory_gate(3.5)
            client_started_wall = time.time()
            client = subprocess.Popen(command, cwd=game, env=qa.environment(game), stdout=client_out, stderr=subprocess.STDOUT, creationflags=qa.NO_WINDOW)
            result['clientPid'] = client.pid
            def fresh_query():
                # All previous responses are consumed before another query begins.
                offset = server_log.stat().st_size
                console('list'); console('qzverdict status'); console('data get entity ' + PLAYER + ' playerGameType')
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline and server.poll() is None and client.poll() is None:
                    with server_log.open('rb') as source: source.seek(offset); suffix = source.read().decode('utf-8', errors='replace')
                    lines = suffix.splitlines()
                    mode = next((line for line in lines if PLAYER + ' has the following entity data: 0' in line), None)
                    online = next((line for line in lines if 'There are 1 of' in line and PLAYER in line), None)
                    status = next((line for line in lines if 'companion=required' in line and 'deviceRequired=true' in line and 'vm=DENY' in line and 'rules=37' in line), None)
                    if mode and online and status:
                        return {'queryByteOffset': offset, 'survivalLine': mode, 'onlineLine': online, 'strictStatusLine': status,
                                'exactSyntheticDeviceAssociation': associated(server_dir)}
                    time.sleep(.2)
                raise RuntimeError('Fresh post-query suffix did not prove Survival, online player and strict status')
            deadline = time.monotonic() + 240
            while time.monotonic() < deadline and server.poll() is None and client.poll() is None:
                windows(client.pid, 'hide')
                if PLAYER + ' joined the game' in text(server_log) and associated(server_dir): break
                if PLAYER + ' lost connection' in text(server_log): raise RuntimeError('Candidate disconnected before accepted report')
                time.sleep(.25)
            else: raise RuntimeError('Client did not join and persist its exact-UUID device association')
            first = fresh_query()
            if not first['exactSyntheticDeviceAssociation']: raise RuntimeError('No device association for this exact player UUID')
            validated = time.monotonic(); result['firstPostReportQuery'] = first
            screenshot = False
            while time.monotonic() - validated < 60:
                if client.poll() is not None or server.poll() is not None: raise RuntimeError('Process exited during post-report observation')
                if PLAYER + ' lost connection' in text(server_log): raise RuntimeError('Player disconnected during observation')
                windows(client.pid, 'hide')
                if not screenshot and time.monotonic() - validated >= 30:
                    result['screenshotHandles'] = windows(client.pid, 'screenshot'); screenshot = True
                time.sleep(.25)
            last = fresh_query(); result['lastPostReportQuery'] = last
            result['onlineObservationSeconds'] = time.monotonic() - validated
            result['clientNormalCloseHandles'] = windows(client.pid, 'close')
            client.wait(timeout=45); normal_client_exit = client.returncode == 0
            console('stop'); server.wait(timeout=90); normal_server_exit = server.returncode == 0
        result['policyAfter'] = after = policy(server_dir)
        result['strict13DefaultsUnchanged'] = before['exact13Defaults'] and after['exact13Defaults'] and before['sha256'] == after['sha256']
        result['default37RulesUnchanged'] = before['default37RulesMatchCatalog'] and after['default37RulesMatchCatalog'] and before['blacklistSha256'] == after['blacklistSha256']
        result['exactSyntheticUUIDAndScopedDeviceAssociation'] = associated(server_dir)
        client_text = text(client_log)
        result['resourcePackMetadataWarning'] = any(word in client_text for word in ('Missing metadata in pack mod:qizhangverdict', 'failed to load a valid ResourcePackInfo'))
        result['renderedClientLogConfirmed'] = 'textures/atlas/' in client_text and 'OpenAL' in client_text
        result['survivalModeConfirmed'] = bool(first and last)
        result['automatedPassed'] = result['strict13DefaultsUnchanged'] and result['default37RulesUnchanged'] and result['renderedClientLogConfirmed'] and result['exactSyntheticUUIDAndScopedDeviceAssociation'] and not result['resourcePackMetadataWarning'] and result['onlineObservationSeconds'] >= 60 and normal_client_exit and normal_server_exit
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        if client is not None and client.poll() is None:
            windows(client.pid, 'close')
            try: client.wait(timeout=30)
            except subprocess.TimeoutExpired: client.terminate(); client.wait(timeout=15); result['clientTerminated'] = True
        if server is not None and server.poll() is None:
            try: server.stdin.write(b'stop\n'); server.stdin.flush(); server.wait(timeout=90)
            except (OSError, subprocess.TimeoutExpired): server.terminate(); server.wait(timeout=15); result['serverTerminated'] = True
        result.update(clientExitCode=client.returncode if client else None, serverExitCode=server.returncode if server else None,
                      normalClientExit=normal_client_exit, normalServerExit=normal_server_exit, elapsedSeconds=time.monotonic() - begin)
        pngs = []
        if client_started_wall is not None:
            for file in (game / 'screenshots').glob('*.png'):
                if file.stat().st_mtime >= client_started_wall:
                    try: pngs.append(png_record(file))
                    except Exception as error: result['pngValidationError'] = type(error).__name__ + ': ' + str(error)
        result['pngs'] = pngs
        try:
            with socket.socket() as probe: probe.bind(('127.0.0.1', port))
            result['serverPortReleased'] = True
        except OSError: result['serverPortReleased'] = False
        result['automatedPassed'] = bool(result['automatedPassed'] and pngs and not result.get('pngValidationError') and result['serverPortReleased'])
        result['passed'] = result['automatedPassed']
        result['passedScope'] = 'Automated predicates only; a separate exact-PNG visual review is required for formal acceptance.'
        result['rawLogs'] = [qa.record(path) for path in (server_log, client_log) if path.exists()]
        result['fixtureHasNoInheritedWorldOrDeviceState'] = True
        qa.save_new(directory / 'result.json', result)
    print({'profile': profile, 'automatedPassed': result['automatedPassed'], 'formalAcceptancePassed': False, 'result': str(directory / 'result.json'), 'error': result.get('error')}, flush=True)
    if not result['automatedPassed']: raise SystemExit(1)
