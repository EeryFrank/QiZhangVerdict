#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Separate file preparation, official installation and graphical QA for MC 1.21.11.

stage-base and inspect-inputs never launch Java. install-client and run are explicit
runtime actions, to be scheduled in the project's single Minecraft JVM window.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import tomllib
import zipfile

sys.dont_write_bytecode = True
import next_client_smoke as stable

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path('E:/CodexTemp/QiZhangVerdict/compat-1.21.11')
INPUT_ROOT = CACHE / 'runtime-inputs-01'
INPUT_RECEIPT_SHA256 = 'd524e9e812891c4fccf6fa7a09ec1eb4d119361d2b5adac474800e5d8c1709ad'
JAVA21 = Path('D:/Java/jdk-21/bin/java.exe')
PROFILES = ('fabric-1.21.11', 'neoforge-1.21.11')
PORTS = dict(zip(PROFILES, (25731, 25732)))
VERSION = '0.4.0-dev'
MC = '1.21.11'
NO_WINDOW = stable.NO_WINDOW
read, sha, record, save_new = stable.read, stable.sha, stable.record, stable.save_new
safe_name, memory_gate, environment = stable.safe_name, stable.memory_gate, stable.environment
verified_copy, allowed, coordinate = stable.verified_copy, stable.allowed, stable.coordinate


def verify_record(item, root=None):
    path = Path(item['path']) if 'path' in item else Path(root) / item['file']
    if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
        raise ValueError('Pinned file differs: ' + str(path))
    return path


def inputs_for(profile, verify_all=True):
    if profile not in PROFILES: raise ValueError('Unknown 1.21.11 profile')
    receipt_path = INPUT_ROOT / 'preparation-receipt.json'
    if sha(receipt_path) != INPUT_RECEIPT_SHA256: raise ValueError('Official input receipt changed')
    receipt = read(receipt_path)
    if not receipt['allOfficialHashChecksPassed'] or receipt['javaMajor'] != 21 or receipt['minecraft'] != MC:
        raise ValueError('Unverified or mismatched official input receipt')
    indexes = {}
    for item in receipt['records']:
        path = verify_record(item, INPUT_ROOT)
        if path.name.endswith('-files.json') or path.name == 'binary-inputs.json': indexes[path.name] = read(path)
    for item in receipt['metadata']: verify_record(item, INPUT_ROOT)
    records = {}
    for rows in indexes.values():
        for item in rows:
            path = Path(item['path']).resolve()
            path.relative_to(INPUT_ROOT.resolve())
            if not item.get('officialHashVerified'): raise ValueError('Nonverified official input')
            if verify_all:
                verify_record(item)
                if sha(path, item['officialHashAlgorithm']) != item['officialHash']:
                    raise ValueError('Official checksum differs: ' + str(path))
            records[str(path).lower()] = item
    metadata = read(INPUT_ROOT / 'metadata/minecraft-1.21.11.json')
    if metadata['javaVersion']['majorVersion'] != 21 or metadata['id'] != MC: raise ValueError('Wrong vanilla profile')
    loader = profile.split('-', 1)[0]
    profile_path = INPUT_ROOT / 'metadata' / ('fabric-loader-0.19.5-client.json' if loader == 'fabric' else 'neoforge-version.json')
    loader_profile = read(profile_path)
    expected_main = 'net.fabricmc.loader.impl.launch.knot.KnotClient' if loader == 'fabric' else 'net.neoforged.fml.startup.Client'
    if loader_profile['inheritsFrom'] != MC or loader_profile['mainClass'] != expected_main:
        raise ValueError('Unexpected official loader entry point')
    return receipt, metadata, loader_profile, records, profile_path


def base_directory(profile, name):
    if profile not in PROFILES: raise ValueError('Unknown profile')
    return CACHE / 'client-fixtures' / profile / safe_name(name)


def pin_guard(profile, path, expected):
    path = Path(path).resolve()
    if not re.fullmatch('[0-9a-f]{64}', expected or '') or sha(path) != expected:
        raise ValueError('Explicit candidate SHA-256 does not match')
    if path.name != f'qizhangverdict-{profile}-{VERSION}.jar': raise ValueError('Unexpected product filename')
    with zipfile.ZipFile(path) as archive:
        if archive.testzip(): raise ValueError('Candidate ZIP CRC failure')
        for name in ('LICENSE', 'NOTICE'):
            if archive.read(name) != (ROOT / name).read_bytes(): raise ValueError('Candidate license/notice differs')
        if profile.startswith('fabric'):
            mod = json.loads(archive.read('fabric.mod.json'))
            if mod['id'] != 'qizhangverdict' or mod['version'] != VERSION or mod['depends']['minecraft'] != MC:
                raise ValueError('Fabric descriptor mismatch')
            if mod['license'] != 'GPL-3.0-only': raise ValueError('Fabric license mismatch')
        else:
            mod = tomllib.loads(archive.read('META-INF/neoforge.mods.toml').decode('utf-8'))
            entry = next(x for x in mod['mods'] if x['modId'] == 'qizhangverdict')
            if entry['version'] != VERSION or mod['license'] != 'GPL-3.0-only': raise ValueError('NeoForge descriptor mismatch')
        classes = [archive.read(name) for name in archive.namelist() if name.endswith('.class')]
        if not classes or any(int.from_bytes(data[6:8], 'big') > 65 for data in classes): raise ValueError('Unexpected class major')
    return {**record(path), 'descriptorVersion': VERSION, 'zipCrcPassed': True, 'gplNoticeVerified': True}


def stage_base(profile, name, guard, guard_sha256, server_fixture=None):
    directory = base_directory(profile, name)
    directory.mkdir(parents=True, exist_ok=False)
    result = {'profile': profile, 'prepared': False, 'javaInvoked': False, 'runtimeVerified': False, 'helper': record(__file__)}
    try:
        receipt, metadata, loader_profile, records, profile_path = inputs_for(profile)
        loader = profile.split('-', 1)[0]
        pinned = pin_guard(profile, guard, guard_sha256)
        candidate = verified_copy(pinned['path'], directory / 'candidate' / Path(pinned['path']).name, pinned['sha256'])
        guard_record = {**record(candidate), 'original': pinned}
        libraries = directory / 'libraries'; libraries.mkdir()
        # Copy only files listed in the fixed official input manifest; includes
        # install processors but these do not enter the launcher classpath by glob.
        for item in records.values():
            source = Path(item['path'])
            try: relative = source.relative_to(INPUT_ROOT / 'libraries')
            except ValueError: continue
            verified_copy(source, libraries / relative, item['sha256'])
        classpath = {}
        for entry in metadata['libraries'] + loader_profile['libraries']:
            if not allowed(entry): continue
            key, relative = coordinate(entry)
            detail = entry.get('downloads', {}).get('artifact', {})
            relative = detail.get('path', relative)
            source = INPUT_ROOT / 'libraries' / relative
            item = records.get(str(source.resolve()).lower())
            if item is None: raise ValueError('Official classpath library missing from receipt: ' + relative)
            path = libraries / relative
            if detail.get('sha1') and sha(path, 'sha1') != detail['sha1']: raise ValueError('Classpath official SHA-1 mismatch')
            classpath[key] = {**record(path), 'name': entry['name']}
        vanilla_source = INPUT_ROOT / 'minecraft/minecraft-1.21.11-client.jar'
        vanilla = verified_copy(vanilla_source, directory / 'versions' / MC / (MC + '.jar'), records[str(vanilla_source.resolve()).lower()]['sha256'])
        shutil.copyfile(INPUT_ROOT / 'metadata/minecraft-1.21.11.json', vanilla.with_suffix('.json'))
        if loader == 'fabric': classpath['vanilla-client'] = {**record(vanilla), 'name': 'official-vanilla-client'}
        # FML 10 GameLocator locates the installer-generated patched client through
        # -DlibraryDirectory. It is not an old bootstrap/forgeclient launch target.
        natives = directory / 'natives'; natives.mkdir()
        for entry in classpath.values():
            path = Path(entry['path'])
            if 'natives-windows' not in path.name: continue
            if any(x in path.name for x in ('natives-windows-arm64', 'natives-windows-x86')): continue
            with zipfile.ZipFile(path) as archive:
                if archive.testzip(): raise ValueError('Native ZIP CRC failure')
                for member in archive.namelist():
                    if member.endswith('.dll'):
                        target = natives / Path(member).name; data = archive.read(member)
                        if target.exists() and target.read_bytes() != data: raise ValueError('Conflicting native DLL')
                        target.write_bytes(data)
        if not list(natives.glob('*.dll')): raise ValueError('No Windows native libraries extracted')
        shutil.copyfile(profile_path, directory / 'loader-profile.json')
        catalog = ROOT / 'catalog/blacklist-extension.tsv'
        rows = [x for x in catalog.read_text('utf-8').splitlines() if x and not x.startswith('#')]
        if len(rows) != 39: raise ValueError('This fixture requires the 39-rule candidate catalog')
        shutil.copyfile(catalog, directory / 'expected-blacklist.tsv')
        api = INPUT_ROOT / 'mods/fabric-api-0.141.6+1.21.11.jar'
        installer = INPUT_ROOT / 'installers/neoforge-21.11.45-installer.jar'
        logging = metadata['logging']['client']; logging_path = INPUT_ROOT / 'assets/log_configs' / logging['file']['id']
        result.update(prepared=True, minecraft=MC, javaMajor=21, java=str(JAVA21), loader=loader,
            loaderVersion=receipt['pins']['fabricLoader' if loader == 'fabric' else 'neoforge'],
            guard=guard_record, inputReceipt=record(INPUT_ROOT / 'preparation-receipt.json'),
            loaderProfile=record(directory / 'loader-profile.json'), mainClass=loader_profile['mainClass'], loaderId=loader_profile['id'],
            loaderArguments=loader_profile.get('arguments', {}), vanillaJvmArguments=metadata['arguments']['jvm'],
            libraries=str(libraries), classpath=list(classpath.values()), natives=str(natives), nativeFiles=[record(x) for x in sorted(natives.iterdir())],
            assets={'root': str(INPUT_ROOT / 'assets'), 'id': metadata['assetIndex']['id'], 'allOfficialHashesChecked': True},
            logging=record(logging_path), loggingArgument=logging['argument'].replace('${path}', str(logging_path)),
            expectedCatalog=record(directory / 'expected-blacklist.tsv'), expectedRuleCount=39,
            fabricApi=record(api) if loader == 'fabric' else None, installer=record(installer) if loader != 'fabric' else None,
            needsClientInstaller=loader != 'fabric',
            patchedClient=str(libraries / 'net/neoforged/minecraft-client-patched/21.11.45/minecraft-client-patched-21.11.45.jar') if loader != 'fabric' else None,
            serverFixtureSource=str(Path(server_fixture).resolve() if server_fixture else CACHE / 'servers' / (loader + '-01')))
        save_new(directory / 'base-plan.json', result)
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        save_new(directory / 'preparation-result.json', result)
    print({'profile': profile, 'prepared': True, 'javaInvoked': False, 'basePlan': str(directory / 'base-plan.json')}, flush=True)


def install_client(profile, name):
    directory = base_directory(profile, name); plan = read(directory / 'base-plan.json')
    result_path = directory / 'client-install-result.json'
    if result_path.exists(): raise ValueError('Preserve earlier installation attempts; create a new base')
    if not plan['prepared']: raise ValueError('Base preparation failed')
    if not plan['needsClientInstaller']:
        save_new(result_path, {'exitCode': 0, 'installerRequired': False, 'javaInvoked': False})
        return
    installer = verify_record(plan['installer'])
    verify_record(plan['loaderProfile'])
    free = memory_gate(3.5)
    save_new(directory / 'launcher_profiles.json', {'profiles': {}})
    temp = directory / 'tmp'; temp.mkdir(exist_ok=True)
    command = [str(JAVA21), '-Xmx768M', '-Djava.awt.headless=true', '-Djava.io.tmpdir=' + str(temp),
               '-Djavax.net.ssl.trustStoreType=Windows-ROOT', '-Djavax.net.ssl.trustStore=NONE',
               '-jar', str(installer), '--installClient', str(directory)]
    result = {'profile': profile, 'installer': record(installer), 'command': command, 'exitCode': None,
              'javaInvoked': True, 'runtimeVerified': False, 'availablePhysicalGiB': free, 'minimumFreeGiB': 3.5, 'helper': record(__file__)}
    console = directory / 'install-console.log'
    try:
        with console.open('xb') as output:
            process = subprocess.run(command, cwd=directory, env=environment(directory), stdout=output, stderr=subprocess.STDOUT,
                                     timeout=900, creationflags=NO_WINDOW)
        result['exitCode'] = process.returncode
        if process.returncode != 0: raise RuntimeError('Official NeoForge client installer failed')
        generated = directory / 'versions' / plan['loaderId'] / (plan['loaderId'] + '.json')
        if read(generated) != read(plan['loaderProfile']['path']): raise ValueError('Installed profile differs from pinned official JSON')
        patched = Path(plan['patchedClient'])
        with zipfile.ZipFile(patched) as archive:
            if archive.testzip() or 'net/minecraft/client/main/Main.class' not in archive.namelist():
                raise ValueError('Installed patched client CRC or entrypoint validation failed')
        result.update(generatedLibrariesVerified=True, patchedClient=record(patched),
            patchedClientVerification='Generated by the successful fixed official installer; local SHA-256 and ZIP CRC recorded. Upstream profile provides no expected patched-JAR checksum.')
        for item in plan['classpath']: verify_record(item)
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        if console.exists(): result['console'] = record(console)
        save_new(result_path, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inspect-inputs', 'stage-base', 'install-client', 'run'))
    parser.add_argument('profile', choices=PROFILES)
    parser.add_argument('--base-name', default='base-01')
    parser.add_argument('--run-name', default='candidate-0.4.0-dev-01')
    parser.add_argument('--guard', type=Path)
    parser.add_argument('--guard-sha256')
    parser.add_argument('--server-fixture', type=Path)
    parser.add_argument('--port', type=int)
    args = parser.parse_args()
    if args.action == 'inspect-inputs':
        receipt, metadata, loader, records, path = inputs_for(args.profile)
        print({'profile': args.profile, 'officialFilesRehashed': len(records), 'mainClass': loader['mainClass'], 'javaInvoked': False})
    elif args.action == 'stage-base':
        if not args.guard or not args.guard_sha256: parser.error('stage-base requires --guard and explicit --guard-sha256')
        stage_base(args.profile, args.base_name, args.guard, args.guard_sha256, args.server_fixture)
    elif args.action == 'install-client': install_client(args.profile, args.base_name)
    else:
        from modern12111_client_runtime import run
        run(args.profile, args.base_name, args.run_name, args.port or PORTS[args.profile])


if __name__ == '__main__': main()
