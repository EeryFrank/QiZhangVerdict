#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Prepare fresh 1.19.2/1.20.4 fixtures; install and run are separate actions.

No existing game directory is modified. Inputs must have independently reviewed
SHA-256 values. The existing protocol runner uses synthetic reports over real TCP.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

sys.dont_write_bytecode = True
import mod_runtime_smoke as runner

CACHE = Path('E:/CodexTemp/QiZhangVerdict/next-platforms')
JAVA17 = Path('E:/CodexTemp/mods-danzi/java/jdk-17.0.20.1+1-jre/bin/java.exe')
JAVA21 = Path('D:/Java/jdk-21/bin/java.exe')
PINS = {
    'fabric-1.19.2': ('fabric', '1.19.2', '0.16.14'),
    'forge-1.19.2': ('forge', '1.19.2', '43.5.2'),
    'fabric-1.20.4': ('fabric', '1.20.4', '0.16.14'),
    'forge-1.20.4': ('forge', '1.20.4', '49.2.9'),
    'neoforge-1.20.4': ('neoforge', '1.20.4', '20.4.251'),
}


def safe_directory(path):
    directory = Path(path).resolve()
    directory.relative_to(CACHE.resolve())
    if directory == CACHE.resolve():
        raise ValueError('Expected a new child fixture directory')
    return directory


def record(path):
    path = Path(path).resolve()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': runner.digest(path)}


def verified_copy(source, expected, target):
    source = Path(source).resolve()
    if runner.digest(source) != expected.lower():
        raise ValueError('Input SHA256 mismatch: ' + source.name)
    with source.open('rb') as inp, target.open('xb') as out:
        shutil.copyfileobj(inp, out)
    if runner.digest(source) != expected.lower() or runner.digest(target) != expected.lower():
        raise ValueError('Input changed while copying')
    return record(source)


def read_marker(path):
    directory = safe_directory(path)
    metadata = json.loads((directory / runner.MARKER).read_text('utf-8'))
    if metadata.get('fixture_tool') != 'next_mod_smoke' or metadata.get('profile') not in PINS:
        raise ValueError('Not this tool\'s isolated fixture')
    if (metadata['loader'], metadata['minecraft'], metadata['loader_version']) != PINS[metadata['profile']]:
        raise ValueError('Fixture pin mismatch')
    return directory, metadata


def memory_gate():
    class Mem(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(x, ctypes.c_ulonglong) for x in ('totalPhysical', 'availablePhysical', 'totalPageFile', 'availablePageFile', 'totalVirtual', 'availableVirtual', 'availableExtendedVirtual')]
    mem = Mem(); mem.length = ctypes.sizeof(mem)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
        raise OSError('Cannot read free physical memory')
    free = mem.availablePhysical / (1024 ** 3)
    if free < 5:
        raise RuntimeError('Need 5 GiB free before Java; actual %.3f' % free)
    return free


def stage(args):
    directory = safe_directory(args.directory)
    if directory.exists():
        raise ValueError('Stage requires a new directory')
    loader, mc, version = PINS[args.profile]
    if (loader == 'fabric') != bool(args.fabric_api and args.fabric_api_sha256):
        raise ValueError('Only Fabric requires a full pinned Fabric API distribution')
    if not args.accept_eula:
        raise ValueError('Explicit --accept-eula is required')
    inputs = json.loads((CACHE / mc / 'runtime-inputs/prepared-inputs.json').read_text('utf-8'))
    if inputs['minecraft'] != mc or inputs['pins'][loader] != version:
        raise ValueError('Reviewed input manifest belongs to a different profile')
    expected_inputs = [(args.installer_sha256, inputs['installers'][loader]['sha256']),
                       (args.server_sha256, inputs['vanillaServer']['sha256'])]
    if loader == 'fabric':
        expected_inputs.append((args.fabric_api_sha256, inputs['fabricApi']['sha256']))
    if any(actual.lower() != reviewed for actual, reviewed in expected_inputs):
        raise ValueError('Requested input SHA differs from the reviewed official profile')
    directory.mkdir(parents=True)
    (directory / 'mods').mkdir()
    installer = verified_copy(args.installer, args.installer_sha256, directory / 'loader-installer.jar')
    server = verified_copy(args.server, args.server_sha256, directory / 'server.jar')
    api = None
    if loader == 'fabric':
        api = verified_copy(args.fabric_api, args.fabric_api_sha256, directory / 'mods' / Path(args.fabric_api).name)
    else:
        # The official installers validate this Mojang bundler before extracting it.
        suffix = '-bundled.jar' if args.profile == 'forge-1.20.4' else '.jar'
        bundled = directory / 'libraries/net/minecraft/server' / mc / ('server-' + mc + suffix)
        bundled.parent.mkdir(parents=True)
        verified_copy(args.server, args.server_sha256, bundled)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    (directory / 'eula.txt').write_text('eula=true\n', encoding='ascii')
    (directory / 'server.properties').write_text(
        'server-ip=127.0.0.1\nserver-port=' + str(port) + '\nonline-mode=true\nenforce-secure-profile=false\n'
        'view-distance=2\nsimulation-distance=2\nmax-players=20\nspawn-protection=0\nallow-flight=false\n'
        'enable-rcon=false\nenable-query=false\nlevel-name=world\nlevel-seed=12955\ndifficulty=peaceful\n'
        'generate-structures=false\nlevel-type=minecraft:flat\n'
        'generator-settings={"layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:dirt","height":2},{"block":"minecraft:grass_block","height":1}],"biome":"minecraft:plains"}\n', encoding='ascii')
    metadata = {'product':'QiZhangVerdict', 'fixture_tool':'next_mod_smoke', 'profile':args.profile,
        'loader':loader, 'minecraft':mc, 'loader_version':version, 'prepared':False,
        'java':str(JAVA17), 'installer_java':str(JAVA21), 'port':port,
        'installer':installer, 'mojang_server':server, 'fabric_api':api,
        'helper':record(__file__), 'staged_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'java_started':False}
    runner.json_write(directory / runner.MARKER, metadata)
    runner.json_write(directory / 'integration-receipt.json', {'profile':args.profile, 'artifacts':[],
        'scope':'QiZhangVerdict and loader dependencies only; no Grim or AntiXray integration claim'})
    print(json.dumps({'staged':args.profile,'directory':str(directory),'javaStarted':False}),flush=True)
    return 0


def install(args):
    directory, metadata = read_marker(args.directory)
    if metadata['prepared'] or (directory / 'install-result.json').exists():
        raise ValueError('Installation attempts require a fresh staged directory')
    installer = directory / 'loader-installer.jar'
    if runner.digest(installer) != metadata['installer']['sha256']:
        raise ValueError('Staged installer changed')
    free = memory_gate()
    loader, mc, version = PINS[metadata['profile']]
    arguments = ['server','-mcversion',mc,'-loader',version,'-dir',str(directory)] if loader == 'fabric' else ['--installServer',str(directory)]
    temporary = directory / 'temp'; temporary.mkdir()
    environment = dict(os.environ)
    for key in ('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS'):
        environment.pop(key, None)
    environment.update(TEMP=str(temporary), TMP=str(temporary))
    command = [str(JAVA21),'-Xmx1536M','-Djava.awt.headless=true','-Djava.io.tmpdir='+str(temporary),
        '-Djavax.net.ssl.trustStoreType=Windows-ROOT','-Djavax.net.ssl.trustStore=NONE','-jar',str(installer),*arguments]
    result = {'command':command,'availablePhysicalGiB':free,'installerSha256':runner.digest(installer),'gameStarted':False,'helper':record(__file__)}
    with (directory / 'install-console.log').open('xb') as log:
        try:
            completed = subprocess.run(command,cwd=directory,env=environment,stdout=log,stderr=subprocess.STDOUT,
                timeout=900,creationflags=runner.NO_WINDOW)
            result['exitCode'] = completed.returncode
        except subprocess.TimeoutExpired:
            result.update(exitCode=None,timedOut=True)
    result['console'] = record(directory / 'install-console.log')
    runner.json_write(directory / 'install-result.json', result)
    if result['exitCode'] != 0:
        raise RuntimeError('Official installer failed; preserve this attempt and use a new directory')
    if loader == 'fabric':
        runtime_args = ['-jar','fabric-server-launch.jar','nogui']
    else:
        argument_files = list((directory / 'libraries').rglob('win_args.txt'))
        if len(argument_files) != 1:
            raise ValueError('Expected exactly one official loader argument file')
        runtime_args = ['@'+str(argument_files[0].relative_to(directory)),'nogui']
    metadata.update(prepared=True,runtime_args=['-Dmixin.debug.verbose=true','-Dmixin.debug.export=true','-Dmixin.debug.countInjections=true',*runtime_args],install_exit_code=0)
    runner.json_write(directory / runner.MARKER, metadata)
    print(json.dumps({'installed':metadata['profile'],'exitCode':0,'gameStarted':False}),flush=True)
    return 0


def run(args):
    directory, metadata = read_marker(args.directory)
    if runner.digest(args.guard_jar) != args.guard_sha256.lower():
        raise ValueError('Candidate JAR changed')
    memory_gate()
    runner.json_write(directory / 'run-plan.json', {'helper':record(__file__),'sharedRunner':record(runner.__file__),
        'guard':record(args.guard_jar),'protocolRequested':bool(args.protocol_node)})
    temporary = directory / 'runtime-temp'; temporary.mkdir(exist_ok=False)
    os.environ['TEMP'] = os.environ['TMP'] = str(temporary)
    for key in ('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS'):
        os.environ.pop(key, None)
    os.environ['JAVA_TOOL_OPTIONS'] = '-Djava.io.tmpdir=' + temporary.as_posix()
    return runner.run(args)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('stage');p.add_argument('--profile',choices=PINS,required=True)
    for key in ('directory','installer','installer-sha256','server','server-sha256'):
        p.add_argument('--'+key,required=True)
    p.add_argument('--fabric-api');p.add_argument('--fabric-api-sha256');p.add_argument('--accept-eula',action='store_true');p.set_defaults(func=stage)
    p=sub.add_parser('install');p.add_argument('--directory',required=True);p.set_defaults(func=install)
    p=sub.add_parser('run');p.add_argument('--directory',required=True);p.add_argument('--guard-jar',required=True);p.add_argument('--guard-sha256',required=True)
    p.add_argument('--timeout',type=int,default=300);p.add_argument('--protocol-node');p.add_argument('--protocol-node-modules',default='E:/CodexTemp/QiZhangGuard/bot/node_modules');p.add_argument('--protocol-timeout',type=int,default=360);p.set_defaults(func=run)
    args=parser.parse_args();return args.func(args)

if __name__ == '__main__':
    sys.exit(main())
