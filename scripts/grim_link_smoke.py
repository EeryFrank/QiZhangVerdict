"""Run the published GPL plugin + pinned Grim in a fresh loopback-only fixture.

Two JVM runs test a real upstream violation, linked bans, restart persistence,
and explicit unban. This does not test cheating detection accuracy or hardware.
Only processes started here are stopped; installed servers are never touched.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
GUARD_SHA = 'e1194b8b694763afbc431e22799f40d357dd80493d194f680edfb219afe94845'
# Exact GuardConfig.DEFAULTS bytes embedded in the pinned GPL Bukkit artifact.
DEFAULT_POLICY_SHA = '47310c31b47287ab805bfdbf8ddddf80e8169385bd9c862239a0a0075644da4e'
SERVERS = {
    '1.20.1': ('2062', '238e64b33e5c7c9b87506cf1a23f239e6ce7fb71edd9d31837f229c94f4dfa1a'),
    '1.21.1': ('2329', '30403cf54f981f16e1403f172645e82d3e4a59ad6c9f1d8e98df99edb1f8ae4c'),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def free_memory():
    if os.name == 'nt':
        class Status(ctypes.Structure):
            _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(name, ctypes.c_ulonglong) for name in
                ('totalPhys', 'availPhys', 'totalPage', 'availPage', 'totalVirtual', 'availVirtual', 'extended')]
        status = Status(); status.length = ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError('Cannot read available physical memory')
        return status.availPhys
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1]) * 1024
    raise OSError('Cannot read available physical memory')


def obtain(url, target, sha):
    target = Path(target)
    if not target.exists():
        request = urllib.request.Request(url, headers={'User-Agent':'QiZhangVerdict-runtime-QA/0.2'})
        with urllib.request.urlopen(request, timeout=180) as response, target.open('xb') as output:
            shutil.copyfileobj(response, output)
    if digest(target) != sha:
        raise ValueError('SHA256 mismatch: ' + str(target))


def run_phase(args, folder, phase):
    available = free_memory()
    if available < 3.5 * 1024**3:
        save(folder / ('resource-gate-' + phase + '.json'), {'launched':False, 'availableBytes':available, 'minimumGiB':3.5})
        raise RuntimeError('Insufficient available memory for the 1536M JVM')
    with socket.socket() as probe:
        # Match POSIX server rebinding after our previous JVM has exited: sockets
        # in TIME_WAIT are not another live listener. Do not enable this on Windows.
        if os.name != 'nt':
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(('127.0.0.1', args.port))
        probe.listen(1)  # Still reject a port owned by an active listening server.
    log = folder / ('console-' + phase + '.log')
    queue = folder / 'commands.queue'; queue.write_text('', encoding='utf-8')
    result = {'phase':phase, 'passed':False, 'availableBytesBeforeJava':available}
    fixture = json.loads((folder/'fixture.json').read_text('utf-8'))
    policy = folder/'plugins/QiZhangVerdict/guard.properties'
    punishments = folder/'plugins/GrimAC/punishments.yml'
    if digest(punishments) != fixture['punishmentsTemplateSha256']:
        raise AssertionError('Punishments template changed before the phase')
    process = tests = None
    started = time.monotonic()
    try:
        with log.open('w', encoding='utf-8') as output:
            process = subprocess.Popen([args.java, '-Xms256M', '-Xmx1536M', '-jar', 'server.jar', '--nogui'], cwd=folder,
                stdin=subprocess.PIPE, stdout=output, stderr=subprocess.STDOUT, text=True)
            result['ownedServerPid'] = process.pid
            deadline = time.monotonic() + 240
            while 'Done (' not in log.read_text('utf-8', errors='replace'):
                if process.poll() is not None: raise RuntimeError('Server exited before ready')
                if time.monotonic() > deadline: raise TimeoutError('Server startup timed out')
                time.sleep(.25)
            process.stdin.write('qzverdict status\nqzverdict integrations\n'); process.stdin.flush()
            time.sleep(1)
            contents = log.read_text('utf-8', errors='replace')
            if 'companion=required, vm=DENY' not in contents or 'deviceRequired=true' not in contents:
                raise AssertionError('Strict Guard defaults not active')
            if not re.search(r'GrimAC=[^;\s]+ enabled \(check configuration\)', contents):
                raise AssertionError('Grim not reported enabled')
            if 'Error while loading punishments.yml' in contents:
                raise AssertionError('Grim did not load punishment configuration')
            result['defaultPolicyBeforeSha256'] = digest(policy)
            result['punishmentsBeforeSha256'] = digest(punishments)
            shutil.copyfile(punishments, folder/('punishments-' + phase + '-after-startup.yml'))
            if result['defaultPolicyBeforeSha256'] != DEFAULT_POLICY_SHA:
                raise AssertionError('Full Guard policy differs from pinned defaults')
            if result['punishmentsBeforeSha256'] != fixture['punishmentsTemplateSha256']:
                raise AssertionError('Grim changed the complete copied punishments template')
            with (folder / ('protocol-' + phase + '.log')).open('w', encoding='utf-8') as test_output:
                tests = subprocess.Popen([args.node, str(ROOT/'scripts/grim_link_protocol.cjs'), args.version,
                    str(args.port), str(folder), phase], stdout=test_output, stderr=subprocess.STDOUT)
                consumed = 0; deadline = time.monotonic() + 150
                while tests.poll() is None:
                    lines = queue.read_text('utf-8').splitlines()
                    for line in lines[consumed:]:
                        process.stdin.write(line + '\n'); process.stdin.flush()
                    consumed = len(lines)
                    if time.monotonic() > deadline: raise TimeoutError('Protocol verification timed out')
                    if process.poll() is not None: raise RuntimeError('Server exited during protocol check')
                    time.sleep(.05)
            result['protocolExit'] = tests.returncode
            if tests.returncode != 0: raise AssertionError('Protocol check failed; inspect retained log')
            result['protocol'] = json.loads((folder / ('protocol-' + phase + '.json')).read_text('utf-8'))
            result['passed'] = result['protocol']['passed'] and result['protocol'].get('caseCount') == 6
    except Exception as exc:
        result['error'] = str(exc)
        result['passed'] = False
    finally:
        if tests is not None and tests.poll() is None:
            tests.kill(); tests.wait(); result['forcedProtocolStop'] = True
        if process is not None and process.poll() is None:
            try:
                process.stdin.write('stop\n'); process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                result['stopInputError'] = str(exc)
            try: process.wait(timeout=90)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(); result['forcedServerStop'] = True
        if process is not None and process.stdin is not None:
            try: process.stdin.close()
            except OSError: pass
        result['serverExit'] = process.returncode if process is not None else None
        contents = log.read_text('utf-8', errors='replace') if log.exists() else ''
        result['normalStop'] = result['serverExit'] == 0 and 'Stopping server' in contents and 'Saving chunks for level' in contents and not result.get('forcedServerStop')
        result['defaultPolicyAfterSha256'] = digest(policy) if policy.exists() else None
        result['punishmentsAfterSha256'] = digest(punishments) if punishments.exists() else None
        if punishments.exists():
            shutil.copyfile(punishments, folder/('punishments-' + phase + '-after-stop.yml'))
        result['strictGuardPolicyUnmodified'] = result.get('defaultPolicyBeforeSha256') == result['defaultPolicyAfterSha256'] == DEFAULT_POLICY_SHA
        result['completePunishmentsTemplateUnmodified'] = result.get('punishmentsBeforeSha256') == result['punishmentsAfterSha256'] == fixture['punishmentsTemplateSha256']
        result['passed'] = result['passed'] and result['normalStop'] and result['strictGuardPolicyUnmodified'] and result['completePunishmentsTemplateUnmodified'] and not result.get('forcedProtocolStop')
        result['elapsedSeconds'] = round(time.monotonic() - started, 3)
        result['logSha256'] = digest(log) if log.exists() else None
        save(folder / ('result-' + phase + '.json'), result)
    if not result['passed']:
        raise RuntimeError(result.get('error', 'Server did not exit normally'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', choices=SERVERS)
    parser.add_argument('--output', type=Path, required=True, help='New empty isolated fixture under a cache directory')
    parser.add_argument('--java', required=True)
    parser.add_argument('--node', required=True)
    parser.add_argument('--port', type=int, default=25672)
    args = parser.parse_args()
    # Use the integration tool's existing symlink/junction and nonempty-directory guard.
    import sys
    sys.path.insert(0, str(ROOT / 'integrations'))
    from manage_integrations import fresh_directory, obtain as obtain_integration, verify
    folder = fresh_directory(args.output)
    build, server_sha = SERVERS[args.version]
    obtain(f'https://api.purpurmc.org/v2/purpur/{args.version}/{build}/download', folder/'server.jar', server_sha)
    plugins = folder/'plugins'; plugins.mkdir()
    obtain('https://github.com/EeryFrank/QiZhangVerdict/releases/download/v0.1.1-test.1/qizhangverdict-bukkit-0.1.1.jar',
        plugins/'qizhangverdict-bukkit-0.1.1.jar', GUARD_SHA)
    lock = json.loads((ROOT/'integrations/dependencies.lock.json').read_text('utf-8'))
    profile = lock['profiles']['paper-' + args.version]
    grim = next(a for a in lock['artifacts'] if a['key'] in profile['artifacts'] and a['key'].startswith('grim-'))
    grim_path = obtain_integration(grim, folder/'dependency-downloads')
    shutil.copyfile(grim_path, plugins/grim['filename']); verify(plugins/grim['filename'], grim)
    grim_folder = plugins/'GrimAC'; grim_folder.mkdir()
    template = ROOT/'integrations/grim-punishments-verdict.example.yml'
    shutil.copyfile(template, grim_folder/'punishments.yml')
    (folder/'eula.txt').write_text('eula=true\n', encoding='utf-8')
    generator = json.dumps({'layers':[{'block':'minecraft:bedrock','height':1}, {'block':'minecraft:stone','height':60},
        {'block':'minecraft:dirt','height':2}, {'block':'minecraft:grass_block','height':1}], 'biome':'minecraft:plains'}, separators=(',', ':'))
    (folder/'server.properties').write_text(f'server-ip=127.0.0.1\nserver-port={args.port}\nonline-mode=false\n'
        'enforce-secure-profile=false\nnetwork-compression-threshold=256\nspawn-protection=0\nview-distance=2\nsimulation-distance=2\n'
        f'level-type=minecraft:flat\ngenerator-settings={generator}\ngenerate-structures=false\nlevel-seed=12955\n', encoding='utf-8')
    metadata = {'version':args.version, 'server':'Purpur', 'build':build, 'serverSha256':server_sha, 'guardSha256':GUARD_SHA,
        'grimSha256':grim['hashes']['sha256'], 'grimVersion':grim['version_number'], 'punishmentsTemplateSha256':digest(template),
        'javaExecutable':args.java, 'nodeExecutable':args.node, 'helperSha256':digest(__file__),
        'protocolSha256':digest(ROOT/'scripts/grim_link_protocol.cjs'), 'expectedDefaultPolicySha256':DEFAULT_POLICY_SHA,
        'scope':'Isolated offline loopback synthetic reports; shipped Grim command template activated only in this new QA fixture.'}
    save(folder/'fixture.json', metadata)
    results = []
    for phase in ('trigger', 'restart'):
        result = run_phase(args, folder, phase)
        results.append(result)
        print(json.dumps(result), flush=True)
    save(folder/'acceptance.json', {**metadata, 'passed':True, 'phases':results,
        'strictGuardPolicyUnmodified':all(r['strictGuardPolicyUnmodified'] for r in results),
        'completePunishmentsTemplateUnmodified':all(r['completePunishmentsTemplateUnmodified'] for r in results)})


if __name__ == '__main__':
    main()
