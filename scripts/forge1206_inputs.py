#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Verify pinned Forge 50.2.0 inputs without network, Java, or fixture writes."""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(r'E:\CodexTemp\QiZhangVerdict\compat-1.20.6\forge-runtime-inputs-01')
SHARED_ROOT = Path(r'E:\CodexTemp\QiZhangVerdict\compat-1.20.6\runtime-inputs-01')
RECEIPT_SHA256 = '1ea9ed29410e89d54775ac0426ca821564409f5db2c470b9763badfcb8e3c79c'
SHARED_RECEIPT_SHA256 = 'c6cd228089d5d15a0083885eda69a585d186c21ade8dac155bd40f5321519080'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _hash(data, algorithm='sha256'):
    return hashlib.new(algorithm, data).hexdigest()


def _relative(value):
    _require(isinstance(value, str) and value and '\\' not in value, 'Invalid relative input path')
    path = PurePosixPath(value)
    _require(not path.is_absolute() and ':' not in value and all(x not in ('', '.', '..') for x in value.split('/')), 'Unsafe relative input path')
    return path.as_posix()


def _inside(base, relative):
    path = (base / _relative(relative)).resolve()
    _require(path.is_relative_to(base.resolve()), 'Input escaped its pinned root')
    return path


def _checked(path, *, sha256=None, size=None, algorithm=None, official=None, authority=None):
    path = Path(path).resolve()
    _require(path.is_file(), f'Missing input: {path}')
    data = path.read_bytes()
    _require(size is None or len(data) == size, f'Input size mismatch: {path}')
    actual_sha256 = _hash(data)
    _require(sha256 is None or actual_sha256 == sha256, f'Input SHA256 mismatch: {path}')
    if algorithm is not None:
        _require(algorithm in ('sha1', 'sha256', 'sha512'), 'Unsupported official hash algorithm')
        _require(isinstance(official, str) and bool(re.fullmatch(r'[0-9a-f]+', official)), 'Invalid official checksum')
        _require(_hash(data, algorithm) == official, f'Official checksum mismatch: {path}')
    if path.suffix.lower() in ('.jar', '.zip'):
        with zipfile.ZipFile(path) as archive:
            _require(archive.testzip() is None, f'ZIP CRC mismatch: {path}')
    return {'path': str(path), 'bytes': len(data), 'sha256': actual_sha256,
            'officialHashAlgorithm': algorithm, 'officialHash': official,
            'officialHashVerified': algorithm is not None, 'officialHashAuthority': authority,
            'zipCrcVerified': path.suffix.lower() in ('.jar', '.zip')}


def _json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _receipt(root, pin):
    path = root / 'preparation-receipt.json'
    _checked(path, sha256=pin)
    receipt = _json(path)
    _require(receipt.get('schemaVersion') == 1, 'Unsupported input receipt schema')
    seen = set()
    for row in receipt['records']:
        relative = _relative(row['file'])
        _require(relative not in seen, 'Duplicate receipt record')
        seen.add(relative)
        _checked(_inside(root, relative), sha256=row['sha256'], size=row['bytes'])
    return receipt, seen


def verify():
    """Rehash all locked source files; return paths/data only, never install them."""
    receipt, own_locked = _receipt(ROOT, RECEIPT_SHA256)
    shared_receipt, shared_locked = _receipt(SHARED_ROOT, SHARED_RECEIPT_SHA256)
    _require(receipt['sharedInputs']['receipt']['sha256'] == SHARED_RECEIPT_SHA256, 'Shared receipt binding mismatch')
    _require(Path(receipt['inputRoot']).resolve() == ROOT.resolve(), 'Forge input root mismatch')
    _require(Path(receipt['sharedInputs']['root']).resolve() == SHARED_ROOT.resolve(), 'Shared input root mismatch')
    for item in receipt['sharedInputs']['records']:
        _checked(_inside(SHARED_ROOT, item['file']), sha256=item['sha256'], size=item['bytes'])
    records_by_path = {}

    def add_record(item):
        key = item['path'].casefold()
        prior = records_by_path.get(key)
        _require(prior is None or (prior['sha256'], prior['bytes']) == (item['sha256'], item['bytes']), 'Conflicting source input records')
        if prior is None:
            records_by_path[key] = item
        return records_by_path[key]

    shared_rows = {}
    for name in ['binary-inputs.json', 'minecraft-inputs-files.json', 'client-libraries-files.json',
                 'client-assets-files.json', 'fabric-loader-libraries-files.json', 'neoforge-loader-libraries-files.json']:
        _require(name in shared_locked, 'Unpinned shared index')
        rows = _json(SHARED_ROOT / name)
        shared_rows[name] = rows
        for row in rows:
            path = _inside(SHARED_ROOT, row['file'])
            _require(path == Path(row['path']).resolve(), 'Shared index path disagreement')
            add_record(_checked(path, sha256=row['sha256'], size=row['bytes'],
                                algorithm=row['officialHashAlgorithm'], official=row['officialHash'], authority=row.get('authority')))
    installer_receipt = _json(ROOT / 'installer-receipt.json')
    installer_row = next(x for x in installer_receipt['downloads'] if x['file'].endswith('.jar'))
    installer = add_record(_checked(_inside(ROOT, installer_row['file']), sha256=installer_row['sha256'],
                                   size=installer_row['bytes'], algorithm='sha1', official=installer_receipt['officialSha1'], authority=installer_row['url'] + '.sha1'))
    with zipfile.ZipFile(installer['path']) as archive:
        for row in installer_receipt['extractedMembers']:
            path = _inside(ROOT, row['file'])
            _require(path.read_bytes() == archive.read(row['installerMember']), 'Installer metadata member differs')
            add_record(_checked(path, sha256=row['sha256'], size=row['bytes'], algorithm='sha256', official=row['sha256'],
                                authority='SHA1-verified official installer member: ' + row['installerMember']))
    profile_path = _inside(ROOT, receipt['profiles']['forge']['version']['file'])
    install_profile_path = _inside(ROOT, receipt['profiles']['forge']['installProfile']['file'])
    profile = _json(profile_path)
    install_profile = _json(install_profile_path)
    metadata = _json(ROOT / 'metadata/minecraft-1.20.6.json')
    plan = _json(ROOT / 'launch-plan.json')
    _require(profile['id'] == '1.20.6-forge-50.2.0' and profile['inheritsFrom'] == '1.20.6', 'Wrong Forge profile')
    _require(profile['mainClass'] == 'net.minecraftforge.bootstrap.ForgeBootstrap', 'Wrong client main class')
    _require(profile['arguments']['game'] == ['--launchTarget', 'forge_client'], 'Wrong production launch target')
    _require(metadata['id'] == '1.20.6' and metadata['javaVersion']['majorVersion'] == 21, 'Wrong Mojang profile')
    libraries_by_relative = {}

    def add_library(relative, item):
        relative = _relative(relative)
        key = relative.casefold()
        prior = libraries_by_relative.get(key)
        _require(prior is None or (prior['relative'], prior['sha256'], prior['bytes']) == (relative, item['sha256'], item['bytes']), 'Conflicting Maven library path')
        if prior is None:
            libraries_by_relative[key] = {**item, 'relative': relative}

    for row in _json(ROOT / 'forge-libraries-files.json'):
        path = _inside(ROOT, 'libraries/' + _relative(row['path']))
        _require(path == Path(row['localPath']).resolve(), 'Forge index path disagreement')
        item = add_record(_checked(path, sha256=row['sha256'], size=row['bytes'], algorithm='sha1', official=row['sha1'], authority=row['url']))
        add_library(row['path'], item)
    for row in shared_rows['client-libraries-files.json']:
        _require(row['file'].startswith('libraries/'), 'Shared library is outside Maven layout')
        add_library(row['file'][len('libraries/'):], records_by_path[str(Path(row['path']).resolve()).casefold()])
    classpaths = {}
    for index_name in ['client-launch-libraries.json', 'server-shim-libraries.json']:
        _require(index_name in own_locked, 'Unpinned classpath index')
        rows = _json(ROOT / index_name)
        for row in rows:
            if row['generated']:
                _require(row.get('requiresInstaller') is True and not row.get('localPath'), 'Generated input incorrectly claims a source file')
                continue
            path = Path(row['localPath']).resolve()
            _require(path.is_relative_to(ROOT.resolve()) or path.is_relative_to(SHARED_ROOT.resolve()), 'Classpath escaped pinned roots')
            official_algorithm = 'sha256' if index_name.startswith('server') else 'sha1'
            official = row['sha256'] if official_algorithm == 'sha256' else row['sha1']
            item = add_record(_checked(path, sha256=row['sha256'], size=row['bytes'], algorithm=official_algorithm,
                                       official=official, authority=row.get('authority', index_name)))
            if row.get('path') is not None:
                add_library(row['path'], item)
        classpaths[index_name] = rows
    client_cp, server_cp = classpaths.values()
    _require(len(client_cp) == 108 and len(server_cp) == 66, 'Pinned classpath count mismatch')
    _require(sum(x['generated'] for x in client_cp) == sum(x['generated'] for x in server_cp) == 1, 'Unexpected generated classpath entries')
    shim = ROOT / 'libraries/net/minecraftforge/forge/1.20.6-50.2.0/forge-1.20.6-50.2.0-shim.jar'
    with zipfile.ZipFile(shim) as archive:
        for name in ['bootstrap-shim.list', 'bootstrap-shim.properties']:
            _require(archive.read(name) == (ROOT / 'metadata' / name).read_bytes(), 'Shim metadata differs from verified library')
    binary_rows = {x['role']: x for x in shared_rows['binary-inputs.json']}
    def binary(role):
        return records_by_path[str(Path(binary_rows[role]['path']).resolve()).casefold()]
    return {'receipt': receipt, 'sharedReceipt': shared_receipt, 'sharedRoot': SHARED_ROOT, 'inputRoot': ROOT,
            'metadata': metadata, 'loaderProfile': profile, 'installProfile': install_profile,
            'profilePath': profile_path, 'installProfilePath': install_profile_path,
            'installer': installer, 'serverJar': binary('mojang-server'), 'clientJar': binary('mojang-client'),
            'libraries': list(libraries_by_relative.values()), 'clientClasspath': client_cp, 'serverClasspath': server_cp,
            'generated': _json(ROOT / 'generated-coordinates.json'), 'launchPlan': plan, 'records': list(records_by_path.values())}


def generated_paths(libraries, side):
    """Return official installer outputs under a fresh fixture's libraries directory.

    Client MC_UNPACKED is the original versions JAR, so it is deliberately absent.
    No files are created. The libraries argument is a directory Path, not an index.
    """
    _require(side in ('client', 'server'), 'Expected client or server side')
    receipt, locked = _receipt(ROOT, RECEIPT_SHA256)
    _require('generated-coordinates.json' in locked, 'Unpinned generated-output index')
    base = Path(libraries).resolve()
    rows = []
    for row in _json(ROOT / 'generated-coordinates.json'):
        if row['side'] != side or not row['requiresInstaller']:
            continue
        rows.append({'role': row['key'], 'name': row['coordinate'], 'path': str(_inside(base, row['path'])),
                     'relative': row['path'], 'expectedOfficialOutputChecksum': row['sha1'],
                     'expectedBytes': row.get('bytes'), 'expectedSha256': row.get('sha256')})
    _require(len(rows) == (4 if side == 'client' else 5), 'Generated-output count mismatch')
    return rows


def verify_generated(libraries, side):
    """Check real installer outputs; absent files fail rather than becoming PASS."""
    result = []
    for row in generated_paths(libraries, side):
        item = _checked(row['path'], sha256=row['expectedSha256'], size=row['expectedBytes'],
                        algorithm='sha1', official=row['expectedOfficialOutputChecksum'], authority='official install_profile.data output SHA')
        item.update(role=row['role'], name=row['name'], relative=row['relative'], officialSha1Verified=True)
        if row['role'] in ('MC_OFF', 'PATCHED'):
            with zipfile.ZipFile(row['path']) as archive:
                names = set(archive.namelist())
                required = ['net/minecraft/client/Minecraft.class', 'net/minecraft/client/main/Main.class'] if side == 'client' else ['net/minecraft/server/MinecraftServer.class', 'net/minecraft/server/Main.class']
                _require(all(name in names for name in required), 'Generated JAR lacks expected named Minecraft classes')
                item['namedMinecraftClassesVerified'] = True
                if row['role'] == 'PATCHED':
                    resource_prefix = 'assets/minecraft/' if side == 'client' else 'data/minecraft/'
                    _require(any(name.startswith(resource_prefix) and not name.endswith('/') for name in names), 'Patched JAR lost Minecraft resources')
                    item['minecraftResourcesVerified'] = True
        result.append(item)
    return result


if __name__ == '__main__':
    checked = verify()
    print(json.dumps({'passed': True, 'receiptSha256': RECEIPT_SHA256, 'officialFiles': len(checked['records']),
                      'libraries': len(checked['libraries']), 'clientClasspath': len(checked['clientClasspath']),
                      'serverClasspath': len(checked['serverClasspath']), 'generatedCoordinates': len(checked['generated']),
                      'javaExecuted': False, 'installerExecuted': False}, indent=2))
