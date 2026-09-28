# SPDX-License-Identifier: GPL-3.0-only
"""Read-only verification of Forge 1.17.1-37.1.1 generated patch overlays.

The fixed official installer does not bind PATCHED_SHA in processor.outputs.
Instead of treating CRC alone as proof, replay its Forge v1 / GDIFF4 patches in
memory and compare every generated class byte. Never write class bytes or return
class-name tables. Importing this module has no file, process or network effects.

Format references: official binarypatcher:1.0.12 (Patch/Patcher) and
com.nothome:javaxdelta:2.0.1 (GDiffPatcher/GDiffWriter) source artifacts.
This does not establish a runtime or explain differing ZIP container hashes.
"""
from __future__ import annotations

from collections import OrderedDict
import hashlib
import io
import json
import lzma
from pathlib import Path
import zipfile
import zlib

INSTALLER_SHA256 = '31f2319b1b9ca491aaccc020887240f8524a4ff2a8e0f8b795e17e889cbc043b'
MAX_CLASS_BYTES = 16 * 1024 * 1024


class _Reader:
    def __init__(self, data):
        self.data, self.position = data, 0

    def take(self, length):
        if length < 0 or self.position + length > len(self.data):
            raise ValueError('Truncated or negative patch length')
        result = self.data[self.position:self.position + length]
        self.position += length
        return result

    def integer(self, width, signed=False):
        return int.from_bytes(self.take(width), 'big', signed=signed)

    def utf(self):
        value = self.take(self.integer(2))
        # All identifiers in these two pinned patchsets are ASCII. Reject other
        # input rather than silently implement Java modified UTF incorrectly.
        if any(byte >= 128 or byte == 0 for byte in value):
            raise ValueError('Unexpected non-ASCII official patch identifier')
        return value.decode('ascii')


def _parse_patch(raw):
    reader = _Reader(raw)
    if reader.integer(1) != 1:
        raise ValueError('Unsupported Forge patch format')
    name, mapped = reader.utf(), reader.utf()
    exists = reader.integer(1)
    if exists not in (0, 1):
        raise ValueError('Invalid patch existence flag')
    checksum = reader.integer(4) if exists else 0
    data = reader.take(reader.integer(4, signed=True))
    if reader.position != len(raw):
        raise ValueError('Trailing Forge patch bytes')
    return name, mapped, bool(exists), checksum, data


def _apply_gdiff(source, patch):
    reader = _Reader(patch)
    if reader.take(5) != bytes.fromhex('d1ffd1ff04'):
        raise ValueError('Wrong GDIFF magic or version')
    result = bytearray()
    widths = {249: (2, 1), 250: (2, 2), 251: (2, 4), 252: (4, 1),
              253: (4, 2), 254: (4, 4), 255: (8, 4)}
    while True:
        command = reader.integer(1)
        if command == 0:
            break
        if command <= 246:
            result.extend(reader.take(command))
        elif command == 247:
            result.extend(reader.take(reader.integer(2)))
        elif command == 248:
            result.extend(reader.take(reader.integer(4, signed=True)))
        else:
            offset_width, length_width = widths[command]
            offset = reader.integer(offset_width, signed=offset_width >= 4)
            length = reader.integer(length_width, signed=length_width >= 4)
            if offset < 0 or length < 0 or offset + length > len(source):
                raise ValueError('GDIFF copy outside its verified input')
            result.extend(source[offset:offset + length])
        if len(result) > MAX_CLASS_BYTES:
            raise ValueError('Bounded per-class output exceeded')
    if reader.position != len(patch):
        raise ValueError('Trailing GDIFF bytes')
    return bytes(result)


def _record(path):
    data = Path(path).read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'sha1': hashlib.sha1(data).hexdigest()}


def _check_zip(archive):
    names = archive.namelist()
    if len(names) != len(set(names)):
        raise ValueError('Duplicate ZIP entries are not accepted')
    if archive.testzip() is not None:
        raise ValueError('ZIP CRC failed')


def verify(installer, clean, patched, side):
    """Return only digest/count/boolean evidence; raise on any verification error.

    `clean` is the successful installer's generated MC_SRG for this side, whose
    whole-file digest is local evidence, not an upstream expected hash. Every
    class consumed by a patch must additionally match its official Adler32.
    """
    if side not in ('client', 'server'):
        raise ValueError('Expected explicit client or server side')
    paths = [Path(installer), Path(clean), Path(patched)]
    before = [_record(path) for path in paths]
    if before[0]['sha256'] != INSTALLER_SHA256:
        raise ValueError('Wrong fixed official Forge installer')
    patches = OrderedDict()
    patch_entry_count = 0
    with zipfile.ZipFile(paths[0]) as archive:
        _check_zip(archive)
        profile = json.loads(archive.read('install_profile.json'))
        if (profile['minecraft'], profile['version']) != ('1.17.1', '1.17.1-forge-37.1.1'):
            raise ValueError('Wrong official installer target')
        member = 'data/' + side + '.lzma'
        compressed = archive.read(member)
        decompressed = lzma.decompress(compressed, format=lzma.FORMAT_ALONE)
        with zipfile.ZipFile(io.BytesIO(decompressed)) as patch_archive:
            _check_zip(patch_archive)
            for name in patch_archive.namelist():
                if name.endswith('.binpatch'):
                    item = _parse_patch(patch_archive.read(name))
                    patches.setdefault(item[0], []).append(item)
                    patch_entry_count += 1
    if not patches:
        raise ValueError('Official patchset is empty')
    expected_names = set()
    existing = added = removed = input_checks = 0
    with zipfile.ZipFile(paths[1]) as clean_archive, zipfile.ZipFile(paths[2]) as output:
        _check_zip(clean_archive)
        _check_zip(output)
        clean_names, output_names = set(clean_archive.namelist()), set(output.namelist())
        for name, steps in patches.items():
            member = name + '.class'
            raw = clean_archive.read(member) if member in clean_names else b''
            initial_exists = bool(raw)
            for _, _, exists, checksum, patch in steps:
                if exists != bool(raw):
                    raise ValueError('Input class existence disagrees with official patch')
                actual = (zlib.adler32(raw) & 0xffffffff) if raw else 0
                if actual != checksum:
                    raise ValueError('Input class Adler32 disagrees with official patch')
                input_checks += 1
                raw = _apply_gdiff(raw, patch) if patch else b''
            if raw:
                expected_names.add(member)
                if member not in output_names or output.read(member) != raw:
                    raise ValueError('Generated class bytes differ from official patch replay')
                existing += int(initial_exists)
                added += int(not initial_exists)
            else:
                removed += 1
                if member in output_names:
                    raise ValueError('Officially deleted class still present')
        if output_names != expected_names:
            raise ValueError('Unexpected or missing generated overlay ZIP entry')
    if [_record(path) for path in paths] != before:
        raise ValueError('Original input changed during read-only verification')
    reference = profile['data']['PATCHED_SHA'][side].strip("'")
    return {
        'schemaVersion': 1, 'passed': True, 'side': side,
        'scope': 'Every official Forge v1/GDIFF4 patch replayed in memory; exact generated class bytes and output entry set. Not a runtime or whole-clean-file upstream hash claim.',
        'javaExecuted': False, 'jarsModified': False,
        'installer': before[0], 'cleanSrg': before[1], 'patchedOverlay': before[2],
        'patchSource': {'member': 'data/' + side + '.lzma', 'bytes': len(compressed),
                        'sha256': hashlib.sha256(compressed).hexdigest()},
        'patchEntryCount': patch_entry_count, 'patchClassCount': len(patches),
        'existingPatchedClassCount': existing, 'addedClassCount': added, 'removedClassCount': removed,
        'inputAdler32CheckCount': input_checks, 'allInputAdler32ChecksPassed': True,
        'outputClassCount': len(expected_names), 'everyOutputEntryAccountedFor': True,
        'allOutputClassBytesMatchOfficialReplay': True,
        'dataPatchedSha1Reference': reference,
        'dataReferenceMatchesActual': before[2]['sha1'] == reference,
        'containerDifferenceCauseEstablished': False,
        'classBytesOrNameTableExposed': False}
