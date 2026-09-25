#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Exact modern CI artifact names; historical and source JARs are never globbed in."""
import argparse
import hashlib
from pathlib import Path
import re
import shutil


TARGETS = {
    'core-bukkit': ('.', '0.2.1-dev', ('bukkit',)),
    'mods-1.19.2': ('platforms/1.19.2', '0.3.0-dev', ('fabric', 'forge')),
    'mods-1.20.1': ('platforms/1.20.1', '0.2.0-test.1', ('fabric', 'forge')),
    'mods-1.20.4': ('platforms/1.20.4', '0.3.0-dev', ('fabric', 'forge', 'neoforge')),
    'mods-1.21.1': ('platforms/1.21.1', '0.2.0-test.1', ('fabric', 'neoforge')),
}
DELIVERABLE_COUNT = 10


def artifact_paths(target):
    project, version, loaders = TARGETS[target]
    if target == 'core-bukkit':
        return [f'bukkit/build/libs/qizhangverdict-bukkit-{version}.jar']
    minecraft = target.removeprefix('mods-')
    return [f'{project}/{loader}/build/libs/qizhangverdict-{loader}-{minecraft}-{version}.jar'
            for loader in loaders]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_plain_file(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Expected regular file: {path}')


def write_checksums(directory, names):
    (directory / 'SHA256SUMS').write_text(
        ''.join(f'{digest(directory / name)}  {name}\n' for name in sorted(names)),
        encoding='ascii')


def stage(root, target, output):
    root, output = Path(root), Path(output)
    sources = [root / path for path in artifact_paths(target)]
    for source in sources:
        require_plain_file(source)
    output.mkdir(parents=True, exist_ok=False)
    for source in sources:
        shutil.copyfile(source, output / source.name)
        if digest(source) != digest(output / source.name):
            raise ValueError(f'Copied artifact differs: {source}')
    write_checksums(output, [source.name for source in sources])


def verify_folder(folder, expected):
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError(f'Expected artifact directory: {folder}')
    actual = {p.name for p in folder.iterdir()}
    if actual != set(expected) | {'SHA256SUMS'}:
        raise ValueError(f'Unexpected or missing artifact files in {folder}: {sorted(actual)}')
    require_plain_file(folder / 'SHA256SUMS')
    recorded = {}
    for line in (folder / 'SHA256SUMS').read_text('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9._+-]+\.jar)', line)
        if not match or match[2] in recorded:
            raise ValueError(f'Invalid or duplicate checksum row in {folder}')
        recorded[match[2]] = match[1]
    if set(recorded) != set(expected):
        raise ValueError(f'Checksum names differ from pinned target in {folder}')
    for name in expected:
        require_plain_file(folder / name)
        if digest(folder / name) != recorded[name]:
            raise ValueError(f'Checksum mismatch: {folder / name}')


def collect(input_root, output, layout):
    input_root, output = Path(input_root), Path(output)
    folders = {target: ('qizhang-ci-' + target if layout == 'github' else target)
               for target in TARGETS}
    if not input_root.is_dir() or input_root.is_symlink():
        raise ValueError('Expected ordinary artifact input directory')
    if {p.name for p in input_root.iterdir()} != set(folders.values()):
        raise ValueError('Input target folders differ from the five pinned modern jobs')
    sources = []
    for target, folder_name in folders.items():
        expected = [Path(path).name for path in artifact_paths(target)]
        folder = input_root / folder_name
        verify_folder(folder, expected)
        sources.extend(folder / name for name in expected)
    if len(sources) != DELIVERABLE_COUNT or len({p.name for p in sources}) != DELIVERABLE_COUNT:
        raise ValueError('Expected exactly ten distinct pinned production JARs')
    # Validate the entire input before creating the new result directory.
    output.mkdir(parents=True, exist_ok=False)
    for source in sources:
        shutil.copyfile(source, output / source.name)
        if digest(source) != digest(output / source.name):
            raise ValueError(f'Copied artifact differs: {source}')
    write_checksums(output, [source.name for source in sources])
    print(f'PASS: {DELIVERABLE_COUNT} exact modern artifact names and SHA-256 checksums; no legacy/source JARs included')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    target = commands.add_parser('target')
    target.add_argument('--target', choices=TARGETS, required=True)
    target.add_argument('--field', choices=['project', 'version', 'paths'], required=True)
    stage_parser = commands.add_parser('stage')
    stage_parser.add_argument('--root', type=Path, default=Path('.'))
    stage_parser.add_argument('--target', choices=TARGETS, required=True)
    stage_parser.add_argument('--output', type=Path, required=True)
    collect_parser = commands.add_parser('collect')
    collect_parser.add_argument('--input', type=Path, required=True)
    collect_parser.add_argument('--output', type=Path, required=True)
    collect_parser.add_argument('--layout', choices=['github', 'gitlab'], required=True)
    args = parser.parse_args()
    if args.command == 'target':
        if args.field == 'paths':
            print('\n'.join(artifact_paths(args.target)))
        else:
            print(TARGETS[args.target][0 if args.field == 'project' else 1])
    elif args.command == 'stage':
        stage(args.root, args.target, args.output)
    else:
        collect(args.input, args.output, args.layout)


if __name__ == '__main__':
    main()
