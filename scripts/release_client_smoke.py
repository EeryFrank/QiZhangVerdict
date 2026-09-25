#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Run an explicitly pinned candidate with cached official clients in fresh fixtures.

This wrapper retains the existing loader-specific acceptance criteria. It copies
only public library references and Fabric API into a new client game directory;
historical launch plans, device identifiers and accepted run directories stay put.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PROFILES = ['fabric-1.20.1', 'forge-1.20.1', 'fabric-1.21.1', 'neoforge-1.21.1',
            'fabric-1.16.5', 'forge-1.16.5', 'fabric-1.18.2', 'forge-1.18.2',
            'fabric-1.19.4', 'forge-1.19.4']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', choices=PROFILES)
    parser.add_argument('--guard-jar', required=True, type=Path)
    parser.add_argument('--guard-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path, help='New isolated cache directory')
    parser.add_argument('--stage-only', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}', args.guard_sha256):
        parser.error('Expected a lowercase SHA256')
    jar = args.guard_jar.resolve()
    if not jar.name.startswith('qizhangverdict-' + args.profile + '-') or jar.suffix != '.jar':
        parser.error('Candidate filename does not match the selected profile')
    if digest(jar) != args.guard_sha256:
        parser.error('Candidate SHA256 differs')
    legacy = args.profile.split('-', 1)[1] in ('1.16.5', '1.18.2', '1.19.4')
    helper = ROOT / 'platforms' / ('legacy-client-smoke.py' if legacy else 'client-matrix-smoke.py')
    spec = importlib.util.spec_from_file_location('release_client_helpers', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    matrix = module.matrix if legacy else module
    previous = module.CACHE / args.profile / 'client'
    source_plan = previous / 'launch-plan.json'
    plan = matrix.read(source_plan)
    cfg = module.PROFILES[args.profile]
    if plan['minecraft'] != cfg['mc'] or plan['loader_version'] != cfg['version']:
        raise ValueError('Cached official client plan belongs to a different loader/version')
    for entry in plan['classpath']:
        if not Path(entry).is_file():
            raise ValueError('Missing official cached library: ' + entry)
    sys.path.insert(0, str(ROOT / 'integrations'))
    from manage_integrations import fresh_directory
    output = fresh_directory(args.output)
    client = output / args.profile / 'client'
    game = client / 'game'
    (game / 'mods').mkdir(parents=True)
    shutil.copyfile(jar, game / 'mods' / jar.name)
    if cfg['loader'] == 'fabric':
        # Only the single API dependency from the already checked client fixture.
        apis = list((Path(plan['game']) / 'mods').glob('fabric-api-*.jar'))
        if len(apis) != 1:
            raise ValueError('Expected exactly one cached Fabric API distribution')
        if cfg.get('fabric_api_sha256') and digest(apis[0]) != cfg['fabric_api_sha256']:
            raise ValueError('Pinned legacy Fabric API checksum differs')
        shutil.copyfile(apis[0], game / 'mods' / apis[0].name)
    (game / 'options.txt').write_text('fullscreen:false\nrenderDistance:2\nmaxFps:30\npauseOnLostFocus:false\n', encoding='ascii')
    if legacy and cfg['loader'] == 'forge':
        installation = previous / 'client-install-result.json'
        if matrix.read(installation).get('exit_code') != 0:
            raise ValueError('Original official Forge client installation did not succeed')
        shutil.copyfile(installation, client / installation.name)
    plan.update(game=str(game), guard_source=str(jar), guard_sha256=args.guard_sha256, guard_filename=jar.name)
    matrix.save(client / 'launch-plan.json', plan)
    stage = {'profile':args.profile, 'guard':{'path':str(jar),'sha256':digest(jar)},
             'historicalLaunchPlanSha256':digest(source_plan), 'historicalLaunchPlan':str(source_plan),
             'minecraft':cfg['mc'], 'loaderVersion':cfg['version'], 'helperSha256':digest(helper),
             'wrapperSha256':digest(__file__), 'sharedHelperSha256':digest(ROOT/'platforms/client-matrix-smoke.py'),
             'newClientGame':str(game), 'privateStateCopied':False, 'javaStarted':False}
    matrix.save(output / 'stage.json', stage)
    shutil.copyfile(__file__, output / 'executed-wrapper.py')
    shutil.copyfile(helper, output / 'executed-helper.py')
    shutil.copyfile(ROOT/'platforms/client-matrix-smoke.py', output/'executed-shared-helper.py')
    module.CACHE = output
    matrix.CACHE = output
    if args.stage_only:
        print(json.dumps(stage))
        return
    from grim_link_smoke import free_memory
    available = free_memory()
    matrix.save(output / 'resource-gate.json', {'availableBytes':available,'minimumGiB':5,'allowed':available>=5*1024**3})
    if available < 5*1024**3:
        raise RuntimeError('No client/server launched: less than 5 GiB of physical memory available')
    module.run(args.profile, 'run-01')
    result = matrix.read(output / args.profile / 'run-01/result.json')
    if digest(source_plan) != stage['historicalLaunchPlanSha256'] or digest(jar) != args.guard_sha256:
        raise RuntimeError('Historical launch plan or candidate changed during QA')
    print(json.dumps({'profile':args.profile,'passed':result['passed'],'guardSha256':args.guard_sha256,'output':str(output)}))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
