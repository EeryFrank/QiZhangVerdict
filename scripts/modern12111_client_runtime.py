# SPDX-License-Identifier: GPL-3.0-only
"""Explicit Java runtime half of modern12111_client_smoke; imports start no process."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import time
import uuid

import modern12111_client_smoke as qa
import next_client_runtime as stable

PLAYER = 'Verdict12111'
identity = bytearray(hashlib.md5(('OfflinePlayer:' + PLAYER).encode('utf-8')).digest())
identity[6] = (identity[6] & 15) | 48
identity[8] = (identity[8] & 63) | 128
PLAYER_UUID = str(uuid.UUID(bytes=bytes(identity)))
STRICT = dict(stable.STRICT)
text, windows, png_record = stable.text, stable.windows, stable.png_record


def policy(server, catalog_record):
    catalog = qa.verify_record(catalog_record)
    path = server / 'config/qizhangverdict/guard.properties'
    values = dict(line.split('=', 1) for line in path.read_text('utf-8').splitlines() if line and not line.startswith('#'))
    blacklist = path.parent / 'blacklist.tsv'
    def rows(file): return sorted(line for line in file.read_text('utf-8').splitlines() if line and not line.startswith('#'))
    expected, actual = rows(catalog), rows(blacklist)
    return {**qa.record(path), 'strictSettingCount': len(STRICT), 'exact13Defaults': values == STRICT,
            'defaultRuleCount': len(actual), 'default39RulesMatchCatalog': len(expected) == 39 and actual == expected,
            'blacklistSha256': qa.sha(blacklist), 'catalogSha256': qa.sha(catalog)}


def device_association(server, game, client_log):
    """Compare actual scoped device identity privately; never return ID/scope/digest."""
    result = {'uuidShapeAssociation': False, 'matchingUuidDeviceRowCount': 0, 'expectedDigestMatch': False,
              'expectedDigestMatchCount': 0, 'installationSourceKind': 'unavailable', 'serverScopeValid': False,
              'algorithm': 'SHA-256 of QiZhangVerdict|lowercase trimmed server scope|lowercase trimmed installation ID',
              'privateIdentifiersExposed': False}
    state, scope_path = (server / 'config/qizhangverdict' / name for name in ('accounts.state', 'server-id.txt'))
    if not state.is_file() or not scope_path.is_file(): return result
    values = []
    for line in state.read_text('utf-8').splitlines():
        fields = line.split('\t')
        if len(fields) == 3 and fields[:2] == ['D', PLAYER_UUID] and re.fullmatch('[0-9a-f]{64}', fields[2]): values.append(fields[2])
    result.update(uuidShapeAssociation=bool(values), matchingUuidDeviceRowCount=len(values))
    with scope_path.open('rb') as source: scope = source.read(128).decode('utf-8').strip().lower()
    if not re.fullmatch('[0-9a-f]{64}', scope): return result
    result['serverScopeValid'] = True
    fallback_logged = '[QiZhangVerdict] Device report uses a local random installation ID fallback;' in text(client_log)
    raw = ''
    if fallback_logged:
        fallback = game / 'config/qizhangverdict/installation-id.txt'
        if fallback.is_file():
            with fallback.open('rb') as source: value = source.read(128).decode('utf-8').strip().lower()
            if re.fullmatch('[a-f0-9-]{36}', value): raw = value; result['installationSourceKind'] = 'local-random-fallback'
    else:
        raw = stable.windows_installation_id()
        if raw: result['installationSourceKind'] = 'windows-machineguid'
    if not raw: return result
    expected = hashlib.sha256(('QiZhangVerdict|' + scope + '|' + raw).encode('utf-8')).hexdigest()
    matches = sum(value == expected for value in values)
    result.update(expectedDigestMatchCount=matches, expectedDigestMatch=len(values) == 1 and matches == 1)
    return result


def validate_launch_profile(plan):
    if plan['minecraft'] != qa.MC or plan['javaMajor'] != 21: raise ValueError('Wrong launch game/Java version')
    if plan['loader'] == 'fabric':
        if plan['mainClass'] != 'net.fabricmc.loader.impl.launch.knot.KnotClient' or plan['loaderVersion'] != '0.19.5':
            raise ValueError('Wrong fixed Fabric entrypoint/version')
    else:
        if plan['mainClass'] != 'net.neoforged.fml.startup.Client' or plan['loaderVersion'] != '21.11.45':
            raise ValueError('Wrong fixed FML10 entrypoint/version')
        game_args = plan['loaderArguments']['game']
        if '--launchTarget' in game_args: raise ValueError('Old FML launch target is not valid for this fixed profile')
        for option, value in (('--fml.mcVersion', '1.21.11'), ('--fml.neoForgeVersion', '21.11.45'), ('--fml.neoFormVersion', '20251209.172050')):
            if game_args.count(option) != 1 or game_args[game_args.index(option) + 1] != value:
                raise ValueError('Official FML10 version argument differs')


def client_command(plan, game, port):
    stable.validate_player_name(PLAYER)
    validate_launch_profile(plan)
    entries = [str(qa.verify_record(item)) for item in plan['classpath']]
    for item in plan['nativeFiles']: qa.verify_record(item)
    qa.verify_record(plan['logging']); qa.verify_record(plan['loaderProfile'])
    if plan['needsClientInstaller']:
        base = Path(plan['loaderProfile']['path']).parent
        install = qa.read(base / 'client-install-result.json')
        if install.get('exitCode') != 0 or not install.get('generatedLibrariesVerified') or install.get('error'):
            raise ValueError('Successful verified official install-client required')
        qa.verify_record(install['patchedClient'])
    replacements = {'library_directory': plan['libraries'].replace('\\', '/'), 'classpath_separator': os.pathsep,
        'version_name': plan['loaderId'], 'natives_directory': plan['natives'], 'launcher_name': 'QiZhangVerdict-QA',
        'launcher_version': '12111', 'classpath': os.pathsep.join(entries)}
    def expand(value):
        for key, replacement in replacements.items(): value = value.replace('${' + key + '}', replacement)
        if '${' in value: raise ValueError('Unknown official launch placeholder')
        return value
    def expand_args(args):
        result = []
        for entry in args:
            if isinstance(entry, str): result.append(expand(entry))
            elif qa.allowed(entry):
                value = entry['value']; result.extend(expand(x) for x in (value if isinstance(value, list) else [value]))
        return result
    temp = game / 'tmp'; temp.mkdir(exist_ok=True)
    command = [str(qa.JAVA21), '-Xms256M', '-Xmx2G', '-Dfile.encoding=UTF-8', '-Djava.io.tmpdir=' + str(temp),
        plan['loggingArgument'], *expand_args(plan['vanillaJvmArguments']), *expand_args(plan['loaderArguments'].get('jvm', [])),
        plan['mainClass'], '--username', PLAYER, '--version', plan['loaderId'], '--gameDir', str(game),
        '--assetsDir', plan['assets']['root'], '--assetIndex', plan['assets']['id'], '--uuid', PLAYER_UUID,
        '--accessToken', '0', '--userType', 'legacy', '--versionType', 'release', '--width', '640', '--height', '360',
        '--quickPlayMultiplayer', '127.0.0.1:' + str(port), *expand_args(plan['loaderArguments'].get('game', []))]
    return command


def isolated_server_arguments(marker, source, server):
    """Bind the installed entry point to the clone, including manifest-relative CP."""
    source, server = Path(source).resolve(), Path(server).resolve()
    original = qa.verify_record(marker['serverEntry']).resolve()
    relative = original.relative_to(source)
    cloned = server / relative
    qa.verify_record({**marker['serverEntry'], 'path': str(cloned)})
    arguments = marker['runtimeArgs']
    if marker['loader'] == 'fabric':
        if len(arguments) != 3 or arguments[0] != '-jar' or arguments[2] != 'nogui':
            raise ValueError('Unexpected Fabric dedicated entrypoint arguments')
        argument_entry = Path(arguments[1])
        if not argument_entry.is_absolute(): argument_entry = source / argument_entry
        if argument_entry.resolve() != original: raise ValueError('Fabric runtime does not name its pinned entrypoint')
        rewritten = ['-jar', str(cloned), 'nogui']
    else:
        if len(arguments) != 2 or not arguments[0].startswith('@') or arguments[1] != 'nogui':
            raise ValueError('Unexpected NeoForge dedicated entrypoint arguments')
        argfile = Path(arguments[0][1:])
        if argfile.is_absolute() or (source / argfile).resolve() != original:
            raise ValueError('NeoForge must use its pinned relative argument file')
        if re.search(r'(?m)^\s*-Xm[xs]', cloned.read_text('utf-8')):
            raise ValueError('Official argument file unexpectedly overrides QA heap limits')
        rewritten = list(arguments)
    return rewritten, {'originalEntry': marker['serverEntry'], 'clonedEntry': qa.record(cloned),
        'originalArguments': arguments, 'isolatedArguments': rewritten, 'entrySha256Unchanged': True}


def prepare_run(profile, base_name, directory, port):
    stable.validate_player_name(PLAYER)
    if not 1024 <= port <= 65535: raise ValueError('Use an isolated nonprivileged loopback port')
    base = qa.base_directory(profile, base_name); plan = qa.read(base / 'base-plan.json')
    if not plan.get('prepared') or plan['profile'] != profile: raise ValueError('Prepared base profile mismatch')
    validate_launch_profile(plan)
    qa.inputs_for(profile)  # Rehash official assets and inputs before an actual run.
    guard = qa.verify_record(plan['guard'])
    qa.verify_record(plan['expectedCatalog'])
    source = Path(plan['serverFixtureSource'])
    marker_path = source / '.qizhang-modern12111-smoke.json'
    marker = qa.read(marker_path)
    if not marker.get('prepared') or marker['profile'] != profile or marker['minecraft'] != qa.MC or marker['loaderVersion'] != plan['loaderVersion']:
        raise ValueError('Matching dedicated-server fixture is not installed')
    for key in ('serverEntry', 'patchedServer'):
        if key in marker: qa.verify_record(marker[key])
    # Reject cloning a source fixture that is still serving, even on another port.
    with socket.socket() as probe: probe.bind(('127.0.0.1', marker['port']))
    source_run = source / 'smoke-result.json'
    if source_run.exists():
        previous = qa.read(source_run)
        if previous.get('serverExitCode') != 0 or not previous.get('normalStop'):
            raise ValueError('Source dedicated server did not complete a normal stop')
    with socket.socket() as probe: probe.bind(('127.0.0.1', port))
    server, game = directory / 'server', directory / 'client-game'
    server.mkdir(); (game / 'mods').mkdir(parents=True)
    for folder in ('libraries', 'versions', '.fabric'):
        if (source / folder).is_dir(): shutil.copytree(source / folder, server / folder)
    for file in source.glob('*.jar'):
        if 'installer' not in file.name.lower(): shutil.copyfile(file, server / file.name)
    launcher_properties = source / 'fabric-server-launcher.properties'
    if launcher_properties.is_file(): shutil.copyfile(launcher_properties, server / launcher_properties.name)
    arguments, entry_receipt = isolated_server_arguments(marker, source, server)
    marker = {**marker, 'runtimeArgs': arguments, 'isolatedEntrypoint': entry_receipt}
    # Never inherit config, world, operators, account/device or player state.
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
    helpers = [Path(__file__), Path(qa.__file__), Path(stable.__file__), Path(qa.stable.__file__)]
    for helper in helpers: shutil.copyfile(helper, directory / helper.name)
    return server, game, plan, marker, [qa.record(path) for path in helpers], qa.record(marker_path)


def run(profile, base_name, run_name, port):
    directory = qa.base_directory(profile, base_name).parent / 'runs' / qa.safe_name(run_name)
    directory.mkdir(parents=True, exist_ok=False)
    server_log, client_log = directory / 'server-console.log', directory / 'client-console.log'
    result = {'profile': profile, 'javaMajor': 21, 'syntheticPlayerUuid': PLAYER_UUID,
        'authentication': 'Loopback offline-mode fixture, synthetic access token 0; does not validate online account authentication.',
        'passed': False, 'automatedPassed': False, 'formalAcceptancePassed': False, 'manualVisualReviewRequired': True,
        'minimumPostReportSeconds': 60, 'minecraftRuntimeExecuted': False, 'helper': qa.record(__file__), 'preparationHelper': qa.record(qa.__file__)}
    server = client = None; game = None; client_started_wall = None
    normal_client_exit = normal_server_exit = False
    begin = time.monotonic()
    try:
        server_dir, game, plan, marker, helpers, marker_ref = prepare_run(profile, base_name, directory, port)
        result.update(candidate=plan['guard'], basePlan=qa.record(qa.base_directory(profile, base_name) / 'base-plan.json'),
            helperDependencies=helpers, sourceFixtureMarker=marker_ref, fixtureHasNoInheritedWorldOrDeviceState=True,
            isolatedServerEntrypoint=marker['isolatedEntrypoint'])
        arguments = marker['runtimeArgs']
        if any(x.startswith(('-Xmx', '-Xms')) for x in arguments): raise ValueError('Server arguments must not override fixed QA heap limits')
        result['availablePhysicalGiBBeforeServer'] = qa.memory_gate(5)
        temp = server_dir / 'tmp'; temp.mkdir()
        with server_log.open('xb') as server_out, client_log.open('xb') as client_out:
            server = subprocess.Popen([str(qa.JAVA21), '-Xms256M', '-Xmx1536M', '-Djava.awt.headless=true', '-Dfile.encoding=UTF-8',
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
            result['policyBefore'] = before = policy(server_dir, plan['expectedCatalog'])
            if not before['exact13Defaults'] or not before['default39RulesMatchCatalog']: raise RuntimeError('Strict 13 defaults or 39-rule catalog differs before login')
            command = client_command(plan, game, port)
            qa.save_new(directory / 'private-launch-plan.json', {'command': command, 'classpathOrigin': 'Fixed official 1.21.11 profile only; no wildcard enumeration'})
            result['availablePhysicalGiBBeforeClient'] = qa.memory_gate(3.5)
            client_started_wall = time.time()
            client = subprocess.Popen(command, cwd=game, env=qa.environment(game), stdout=client_out, stderr=subprocess.STDOUT, creationflags=qa.NO_WINDOW)
            result['clientPid'] = client.pid
            print({'profile': profile, 'phase': 'client-started', 'serverPid': server.pid, 'clientPid': client.pid}, flush=True)
            def fresh_query():
                offset = server_log.stat().st_size
                token = 'QZ_GUI_SURVIVAL_' + secrets.token_hex(8)
                console('list'); console('qzverdict status')
                console('execute if entity @a[name=' + PLAYER + ',gamemode=survival,limit=1] run say ' + token)
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline and server.poll() is None and client.poll() is None:
                    with server_log.open('rb') as source: source.seek(offset); suffix = source.read().decode('utf-8', errors='replace')
                    lines = suffix.splitlines()
                    mode = next((line for line in lines if '[Server] ' + token in line), None)
                    online = next((line for line in lines if 'There are 1 of' in line and PLAYER in line), None)
                    status = next((line for line in lines if 'companion=required' in line and 'deviceRequired=true' in line and 'vm=DENY' in line and re.search(r'rules=39\b', line)), None)
                    if mode and online and status:
                        return {'queryByteOffset': offset, 'queryToken': token, 'survivalLine': mode, 'onlineLine': online,
                            'strictStatusLine': status, 'deviceAssociation': device_association(server_dir, game, client_log)}
                    time.sleep(.2)
                raise RuntimeError('Fresh tagged query did not prove Survival, online player and strict status')
            deadline = time.monotonic() + 240
            while time.monotonic() < deadline and server.poll() is None and client.poll() is None:
                windows(client.pid, 'hide')
                association = device_association(server_dir, game, client_log)
                if PLAYER + ' joined the game' in text(server_log) and association['expectedDigestMatch']: break
                if PLAYER + ' lost connection' in text(server_log): raise RuntimeError('Candidate disconnected before accepted report')
                time.sleep(.25)
            else: raise RuntimeError('Client did not join and persist the independently recomputed scoped device association')
            first = fresh_query()
            if not first['deviceAssociation']['expectedDigestMatch']: raise RuntimeError('Initial scoped device recomputation failed')
            validated = time.monotonic(); result['firstPostReportQuery'] = first
            print({'profile': profile, 'phase': 'report-accepted-observing', 'secondsRequired': 60}, flush=True)
            screenshot = False
            while time.monotonic() - validated < 60:
                if client.poll() is not None or server.poll() is not None: raise RuntimeError('Process exited during post-report observation')
                if PLAYER + ' lost connection' in text(server_log): raise RuntimeError('Player disconnected during observation')
                windows(client.pid, 'hide')
                if not screenshot and time.monotonic() - validated >= 30:
                    result['screenshotHandles'] = windows(client.pid, 'screenshot'); screenshot = True
                time.sleep(.25)
            last = fresh_query(); result['lastPostReportQuery'] = last
            if not last['deviceAssociation']['expectedDigestMatch']: raise RuntimeError('Final scoped device recomputation failed')
            result['onlineObservationSeconds'] = time.monotonic() - validated
            result['clientNormalCloseHandles'] = windows(client.pid, 'close')
            client.wait(timeout=45); normal_client_exit = client.returncode == 0
            console('stop'); server.wait(timeout=90); normal_server_exit = server.returncode == 0
        result['policyAfter'] = after = policy(server_dir, plan['expectedCatalog'])
        result['strict13DefaultsUnchanged'] = before['exact13Defaults'] and after['exact13Defaults'] and before['sha256'] == after['sha256']
        result['default39RulesUnchanged'] = before['default39RulesMatchCatalog'] and after['default39RulesMatchCatalog'] and before['blacklistSha256'] == after['blacklistSha256']
        result['deviceAssociationAfterExit'] = device_association(server_dir, game, client_log)
        result['exactSyntheticUUIDAndScopedDeviceAssociation'] = result['deviceAssociationAfterExit']['expectedDigestMatch']
        result['candidateCopiesAfterExit'] = [qa.record(folder / Path(plan['guard']['path']).name) for folder in (server_dir / 'mods', game / 'mods')]
        result['exactCandidateBytesUnchanged'] = all(item['sha256'] == plan['guard']['sha256'] for item in result['candidateCopiesAfterExit'])
        client_text = text(client_log)
        result['resourcePackMetadataWarning'] = any(word in client_text for word in ('Missing metadata in pack mod:qizhangverdict', 'failed to load a valid ResourcePackInfo'))
        result['renderedClientLogConfirmed'] = 'textures/atlas/' in client_text and 'OpenAL' in client_text
        result['survivalModeConfirmed'] = True
        result['automatedPassed'] = all((result['strict13DefaultsUnchanged'], result['default39RulesUnchanged'],
            result['exactSyntheticUUIDAndScopedDeviceAssociation'], result['exactCandidateBytesUnchanged'], result['renderedClientLogConfirmed'],
            not result['resourcePackMetadataWarning'], result['onlineObservationSeconds'] >= 60, normal_client_exit, normal_server_exit))
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        if client is not None and client.poll() is None:
            result['cleanupClientCloseHandles'] = windows(client.pid, 'close')
            try: client.wait(timeout=30); normal_client_exit = client.returncode == 0
            except subprocess.TimeoutExpired: client.terminate(); client.wait(timeout=15); result['clientTerminated'] = True
        if server is not None and server.poll() is None:
            try: server.stdin.write(b'stop\n'); server.stdin.flush(); server.wait(timeout=90); normal_server_exit = server.returncode == 0
            except (OSError, subprocess.TimeoutExpired): server.terminate(); server.wait(timeout=15); result['serverTerminated'] = True
        result.update(clientExitCode=client.returncode if client else None, serverExitCode=server.returncode if server else None,
            normalClientExit=normal_client_exit, normalServerExit=normal_server_exit, elapsedSeconds=time.monotonic() - begin,
            ownedProcessesEnded=all(process is None or process.poll() is not None for process in (server, client)))
        pngs = []
        if client_started_wall is not None and game:
            for file in (game / 'screenshots').glob('*.png'):
                if file.stat().st_mtime >= client_started_wall:
                    try: pngs.append(png_record(file))
                    except Exception as error: result['pngValidationError'] = type(error).__name__ + ': ' + str(error)
        result['pngs'] = pngs
        try:
            with socket.socket() as probe: probe.bind(('127.0.0.1', port))
            result['serverPortReleased'] = True
        except OSError: result['serverPortReleased'] = False
        result['automatedPassed'] = bool(result['automatedPassed'] and pngs and not result.get('pngValidationError')
            and result['serverPortReleased'] and result['ownedProcessesEnded'] and not result.get('clientTerminated') and not result.get('serverTerminated'))
        result['passed'] = result['automatedPassed']
        result['passedScope'] = 'Automated predicates only; separate exact-PNG human visual review is required for formal acceptance.'
        result['rawLogs'] = [qa.record(path) for path in (server_log, client_log) if path.exists()]
        qa.save_new(directory / 'result.json', result)
    print({'profile': profile, 'automatedPassed': result['automatedPassed'], 'formalAcceptancePassed': False,
           'result': str(directory / 'result.json'), 'error': result.get('error')}, flush=True)
    if not result['automatedPassed']: raise SystemExit(1)
