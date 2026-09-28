#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Prepare pinned 1.17.1 graphical fixtures; Java installation/run are separate actions."""
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys, tomllib, zipfile
from pathlib import Path
import next_client_smoke as stable
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
CACHE = Path('E:/CodexTemp/QiZhangVerdict/compat-1.17.1')
INPUT_ROOT = CACHE / 'client-inputs-01'
INPUT_RECEIPT_SHA256 = '87e84a9b1486da6893e9f16571a8471f560901326f601e8d69bab21a48acef06'
JAVA16 = Path('E:/CodexTemp/QiZhangVerdict/toolchains/jdk16/installation-01/extracted/jdk-16.0.2+7/bin/java.exe')
MC, VERSION = '1.17.1', '0.6.0-dev'
PROFILES = ('fabric-1.17.1', 'forge-1.17.1')
PINS = {'fabric': '0.19.5', 'forge': '37.1.1'}
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
read, sha, record, save_new = stable.read, stable.sha, stable.record, stable.save_new
safe_name, verified_copy, allowed, coordinate = stable.safe_name, stable.verified_copy, stable.allowed, stable.coordinate
memory_gate, environment = stable.memory_gate, stable.environment


def base_directory(profile, name):
    if profile not in PROFILES: raise ValueError('Unknown 1.17.1 profile')
    return CACHE / 'client-fixtures' / profile / safe_name(name)

def verify_record(item, root=None):
    path = Path(item['path']) if 'path' in item else Path(root) / item['file']
    if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
        raise ValueError('Pinned file differs: ' + str(path))
    return path

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
            descriptor = 'META-INF/mods.toml' if profile.startswith('forge-') else 'META-INF/neoforge.mods.toml'
            mod = tomllib.loads(archive.read(descriptor).decode('utf-8'))
            entry = next(x for x in mod['mods'] if x['modId'] == 'qizhangverdict')
            if entry['version'] != VERSION or mod['license'] != 'GPL-3.0-only': raise ValueError('Forge-family descriptor mismatch')
        classes = [archive.read(name) for name in archive.namelist() if name.endswith('.class')]
        if not classes or any(int.from_bytes(data[6:8], 'big') > 60 for data in classes): raise ValueError('Unexpected class major')
    return {**record(path), 'descriptorVersion': VERSION, 'zipCrcPassed': True, 'gplNoticeVerified': True}


def inputs_for(profile):
    if profile not in PROFILES or not INPUT_RECEIPT_SHA256:
        raise ValueError('Unknown profile or unfrozen official input receipt')
    receipt_path = INPUT_ROOT / 'prepared-inputs.json'
    if sha(receipt_path) != INPUT_RECEIPT_SHA256: raise ValueError('Official receipt changed')
    receipt = read(receipt_path)
    records = {}
    for item in receipt['records']:
        path = verify_record(item)
        path.resolve().relative_to(INPUT_ROOT.resolve())
        records[str(path.resolve()).lower()] = item
    metadata = read(INPUT_ROOT / 'metadata/minecraft-1.17.1.json')
    if metadata['id'] != MC or metadata['javaVersion']['majorVersion'] != 16:
        raise ValueError('Wrong Minecraft or Java version')
    loader = profile.split('-', 1)[0]
    profile_path = INPUT_ROOT / 'metadata' / ('fabric-loader-0.19.5-client.json' if loader == 'fabric' else 'forge-version.json')
    if str(profile_path.resolve()).lower() not in records: raise ValueError('Loader profile absent from pinned receipt')
    return receipt, metadata, read(profile_path), records, profile_path


def generated_paths(libraries, install_profile, side='client'):
    """Expected coordinates come from the official installer; no synthetic hashes."""
    data = install_profile['data']; rows = []
    for role in ('MC_SLIM', 'MC_EXTRA', 'MC_SRG', 'PATCHED'):
        value = data[role][side]
        if not value.startswith('[') or not value.endswith(']'): raise ValueError('Unexpected generated coordinate')
        coordinate_value = value[1:-1]
        _, relative = coordinate({'name': coordinate_value})
        checksum = data.get(role + '_SHA', {}).get(side, '').strip("'")
        if checksum and not re.fullmatch('[a-f0-9]{40}', checksum): raise ValueError('Invalid official generated SHA-1')
        rows.append({'role': role, 'coordinate': coordinate_value, 'relative': relative,
                     'path': str(Path(libraries) / relative), 'officialSha1': checksum or None})
    return rows


def verify_generated(libraries, install_profile, side='client'):
    rows = []
    for item in generated_paths(libraries, install_profile, side):
        path = Path(item['path'])
        with zipfile.ZipFile(path) as archive:
            if archive.testzip(): raise ValueError('Generated library CRC failure')
        if item['officialSha1'] and sha(path, 'sha1') != item['officialSha1']:
            raise ValueError('Generated library differs from official SHA-1: ' + item['role'])
        rows.append({**item, **record(path), 'zipCrcPassed': True,
                     'officialHashVerified': bool(item['officialSha1']),
                     'scope': 'Official SHA-1' if item['officialSha1'] else 'Installer-generated SRG: local digest and CRC only'})
    return rows


def stage_base(profile, name, guard, guard_sha256, server_fixture):
    directory = base_directory(profile, name)
    directory.mkdir(parents=True, exist_ok=False)
    result = {'profile': profile, 'prepared': False, 'javaInvoked': False, 'runtimeVerified': False, 'helper': record(__file__)}
    try:
        receipt, metadata, loader_profile, records, profile_path = inputs_for(profile)
        loader = profile.split('-', 1)[0]
        def pinned(path):
            item = records.get(str(Path(path).resolve()).lower())
            if item is None: raise ValueError('File absent from official receipt: ' + str(path))
            return item
        product = pin_guard(profile, guard, guard_sha256)
        candidate = verified_copy(product['path'], directory / 'candidate' / Path(product['path']).name, product['sha256'])
        libraries = directory / 'libraries'; libraries.mkdir()
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
            item = pinned(source); target = libraries / relative
            if detail.get('sha1') and sha(target, 'sha1') != detail['sha1']: raise ValueError('Official classpath SHA-1 differs')
            classpath[key] = {**record(target), 'name': entry['name']}
        vanilla_source = INPUT_ROOT / 'minecraft/minecraft-1.17.1-client.jar'
        vanilla = verified_copy(vanilla_source, directory / 'versions' / MC / (MC + '.jar'), pinned(vanilla_source)['sha256'])
        metadata_source = INPUT_ROOT / 'metadata/minecraft-1.17.1.json'
        verified_copy(metadata_source, vanilla.with_suffix('.json'), pinned(metadata_source)['sha256'])
        if loader == 'fabric': classpath['vanilla-client'] = {**record(vanilla), 'name': 'official-vanilla-client'}
        natives = directory / 'natives'; natives.mkdir()
        for item in records.values():
            source = Path(item['path'])
            if source.suffix.lower() != '.dll': continue
            source.relative_to(INPUT_ROOT / 'natives')
            target = natives / source.name
            if target.exists() and sha(target) != item['sha256']: raise ValueError('Conflicting native DLL')
            if not target.exists(): verified_copy(source, target, item['sha256'])
        if not list(natives.glob('*.dll')): raise ValueError('No pinned Windows native DLLs')
        verified_copy(profile_path, directory / 'loader-profile.json', pinned(profile_path)['sha256'])
        catalog = ROOT / 'catalog/blacklist-extension.tsv'
        rows = [x for x in catalog.read_text('utf-8').splitlines() if x and not x.startswith('#')]
        if not 1 <= len(rows) <= 4096: raise ValueError('Empty or unbounded catalog')
        shutil.copyfile(catalog, directory / 'expected-blacklist.tsv')
        api = next((Path(x['path']) for x in records.values() if Path(x['path']).name == 'fabric-api-0.46.1+1.17.jar'), None)
        installer = next((Path(x['path']) for x in records.values() if Path(x['path']).name == 'forge-1.17.1-37.1.1-installer.jar'), None)
        if loader == 'fabric' and api is None: raise ValueError('Full official Fabric API missing')
        if loader == 'forge' and installer is None: raise ValueError('Official Forge installer missing')
        logging = metadata['logging']['client']
        logging_path = next((Path(x['path']) for x in records.values() if Path(x['path']).name == logging['file']['id']), None)
        if logging_path is None or sha(logging_path, 'sha1') != logging['file']['sha1']: raise ValueError('Official logging configuration missing')
        install_profile = INPUT_ROOT / 'metadata/forge-install_profile.json'
        result.update(prepared=True, minecraft=MC, javaMajor=16, java=str(JAVA16), loader=loader,
            loaderVersion=PINS[loader], guard={**record(candidate), 'original': product},
            inputReceipt=record(INPUT_ROOT / 'prepared-inputs.json'), loaderProfile=record(directory / 'loader-profile.json'),
            mainClass=loader_profile['mainClass'], loaderId=loader_profile['id'],
            loaderArguments=loader_profile.get('arguments', {}), vanillaJvmArguments=metadata['arguments']['jvm'],
            libraries=str(libraries), classpath=list(classpath.values()), natives=str(natives),
            nativeFiles=[record(x) for x in sorted(natives.iterdir())],
            assets={'root': str(INPUT_ROOT / 'assets'), 'id': metadata['assetIndex']['id'], 'allOfficialHashesChecked': True},
            logging=record(logging_path), loggingArgument=logging['argument'].replace('${path}', str(logging_path)),
            expectedCatalog=record(directory / 'expected-blacklist.tsv'), expectedRuleCount=len(rows),
            fabricApi=record(api) if loader == 'fabric' else None, installer=record(installer) if loader == 'forge' else None,
            installProfile=record(verify_record(pinned(install_profile))) if loader == 'forge' else None,
            needsClientInstaller=loader == 'forge', serverFixtureSource=str(Path(server_fixture).resolve()))
        save_new(directory / 'base-plan.json', result)
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        save_new(directory / 'preparation-result.json', result)
    print({'profile': profile, 'prepared': True, 'javaInvoked': False}, flush=True)


def install_client(profile, name):
    directory = base_directory(profile, name); plan = read(directory / 'base-plan.json')
    if not plan['prepared']: raise ValueError('Base preparation failed')
    if (directory / 'client-install-result.json').exists(): raise ValueError('Preserve previous installation attempt')
    if not plan['needsClientInstaller']:
        save_new(directory / 'client-install-result.json', {'exitCode': 0, 'installerRequired': False, 'javaInvoked': False})
        return
    inputs_for(profile)
    installer = verify_record(plan['installer'])
    free = memory_gate(4)
    save_new(directory / 'launcher_profiles.json', {'profiles': {}})
    temp = directory / 'tmp'; temp.mkdir(exist_ok=True)
    command = [str(JAVA16), '-Xmx768M', '-Djava.awt.headless=true', '-Djava.io.tmpdir=' + str(temp),
        '-Djavax.net.ssl.trustStoreType=Windows-ROOT', '-Djavax.net.ssl.trustStore=NONE', '-jar', str(installer), '--installClient', str(directory)]
    result = {'profile': profile, 'installer': record(installer), 'command': command, 'exitCode': None, 'javaInvoked': True,
              'runtimeVerified': False, 'availablePhysicalGiB': free, 'helper': record(__file__)}
    console = directory / 'install-console.log'
    try:
        with console.open('xb') as output:
            process = subprocess.run(command, cwd=directory, env=environment(directory), stdout=output, stderr=subprocess.STDOUT,
                                     timeout=900, creationflags=NO_WINDOW)
        result['exitCode'] = process.returncode
        if process.returncode: raise RuntimeError('Official Forge client installer failed')
        generated = verify_generated(Path(plan['libraries']), read(verify_record(plan['installProfile'])))
        profile_path = directory / 'versions' / plan['loaderId'] / (plan['loaderId'] + '.json')
        if read(profile_path) != read(verify_record(plan['loaderProfile'])): raise ValueError('Installed profile differs from official input')
        result.update(generatedLibrariesVerified=True, generatedClientLibraries=generated, installedProfile=record(profile_path))
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        if console.exists(): result['console'] = record(console)
        save_new(directory / 'client-install-result.json', result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    verify = sub.add_parser('verify-inputs'); verify.add_argument('--profile', choices=PROFILES, required=True)
    stage = sub.add_parser('stage-base'); stage.add_argument('--profile', choices=PROFILES, required=True)
    stage.add_argument('--name', required=True); stage.add_argument('--guard-jar', type=Path, required=True)
    stage.add_argument('--guard-sha256', required=True); stage.add_argument('--server-fixture', type=Path, required=True)
    install = sub.add_parser('install-client'); install.add_argument('--profile', choices=PROFILES, required=True); install.add_argument('--name', required=True)
    run = sub.add_parser('run'); run.add_argument('--profile', choices=PROFILES, required=True); run.add_argument('--name', required=True)
    run.add_argument('--run-name', required=True); run.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    if args.action == 'verify-inputs':
        _, _, loader, records, _ = inputs_for(args.profile)
        print({'profile': args.profile, 'verifiedFiles': len(records), 'mainClass': loader['mainClass'], 'javaInvoked': False})
    elif args.action == 'stage-base': stage_base(args.profile, args.name, args.guard_jar, args.guard_sha256, args.server_fixture)
    elif args.action == 'install-client': install_client(args.profile, args.name)
    else:
        import legacy117_client_runtime
        return legacy117_client_runtime.run(args.profile, args.name, args.run_name, args.port)
    return 0


if __name__ == '__main__': raise SystemExit(main())
