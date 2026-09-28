#!/usr/bin/env python3
"""Pure, synthetic CI-state checks. No subprocess, network, Java or CI run."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
TOOL = BASE / 'ci-monitor.py'
spec = importlib.util.spec_from_file_location('monitor_under_review', TOOL)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)
COMMIT = '1' * 40
CASES = []

def check(name, action):
    assert action(), name
    CASES.append({'name': name, 'passed': True})

def rejects(action):
    try: action()
    except ValueError: return True
    return False

def fixture():
    runs = []
    number = 10
    for rid, (path, names) in enumerate(monitor.GH_EXPECTED.items(), 1):
        jobs = []
        for name in sorted(names):
            number += 1
            jobs.append({'id': number, 'name': name, 'status': 'completed', 'conclusion': 'success',
                         'started_at': '2026-01-01T00:00:00Z', 'completed_at': '2026-01-01T00:01:00Z'})
        runs.append({'id': rid, 'path': path, 'head_branch': 'main', 'head_sha': COMMIT, 'event': 'push',
                     'status': 'completed', 'conclusion': 'success', 'jobs': jobs})
    pipeline = {'id': 3, 'ref': 'main', 'sha': COMMIT, 'source': 'push', 'status': 'failed'}
    jobs = [{'id': 100 + index, 'name': name, 'status': 'failed', 'failure_reason': 'ci_quota_exceeded',
             'started_at': None, 'finished_at': None} for index, name in enumerate(sorted(monitor.GL_EXPECTED))]
    return runs, pipeline, jobs

def assess(change=None):
    args = fixture()
    if change: change(*args)
    return monitor.assess(*args, COMMIT)

def mutate_run(field, value): return lambda runs, _p, _j: runs[0].__setitem__(field, value)

check('exact modern9 legacy5 and GL14 sets', lambda: len(monitor.MODERN) == 9 and len(monitor.LEGACY) == 5 and len(monitor.GL_EXPECTED) == 14)
check('complete GH14 plus GL quota stays quota_not_started', lambda: assess()['githubAll14Passed'] and assess()['gitlabState'] == 'quota_not_started' and assess()['developmentChecksTerminalAndAccepted'])
check('GL success requires actually started and finished jobs', lambda: assess(lambda _r, p, js: (p.update(status='success'), [j.update(status='success', failure_reason=None, started_at='start', finished_at='finish') for j in js]))['gitlabState'] == 'success-executed')
check('missing workflows cannot pass', lambda: not monitor.assess([], None, [], COMMIT)['githubAll14Passed'])
check('wrong GH branch rejected', lambda: rejects(lambda: assess(mutate_run('head_branch', 'v0.6.0-dev-preview.1'))))
check('wrong GH SHA rejected', lambda: rejects(lambda: assess(mutate_run('head_sha', '2' * 40))))
check('nonpush GH event rejected', lambda: rejects(lambda: assess(mutate_run('event', 'workflow_dispatch'))))
check('duplicate GH workflow rejected', lambda: rejects(lambda: assess(lambda rs, _p, _j: rs.__setitem__(1, copy.deepcopy(rs[0])))))
check('terminal GH job missing rejected', lambda: rejects(lambda: assess(lambda rs, _p, _j: rs[0]['jobs'].pop())))
check('unknown GH job rejected', lambda: rejects(lambda: assess(lambda rs, _p, _j: rs[0]['jobs'][0].update(name='unexpected'))))
check('failed GH job cannot pass', lambda: not assess(lambda rs, _p, _j: rs[0]['jobs'][0].update(conclusion='failure'))['githubAll14Passed'])
check('skipped GH job cannot pass', lambda: not assess(lambda rs, _p, _j: rs[0]['jobs'][0].update(conclusion='skipped'))['githubAll14Passed'])
check('pending GH run cannot pass', lambda: not assess(mutate_run('status', 'in_progress'))['githubAll14Passed'])
check('GH success without actual start cannot pass', lambda: not assess(lambda rs, _p, _j: rs[0]['jobs'][0].update(started_at=None))['githubAll14Passed'])
check('wrong GL ref rejected', lambda: rejects(lambda: assess(lambda _r, p, _j: p.update(ref='other'))))
check('wrong GL SHA rejected', lambda: rejects(lambda: assess(lambda _r, p, _j: p.update(sha='2' * 40))))
check('terminal GL missing job rejected', lambda: rejects(lambda: assess(lambda _r, _p, js: js.pop())))
check('duplicate GL job rejected', lambda: rejects(lambda: assess(lambda _r, _p, js: js.__setitem__(1, copy.deepcopy(js[0])))))
check('started GL quota is not quota_not_started', lambda: assess(lambda _r, _p, js: js[0].update(started_at='start'))['gitlabState'] == 'failed-or-canceled')
check('nonquota GL failure is not accepted', lambda: not assess(lambda _r, _p, js: js[0].update(failure_reason='script_failure'))['developmentChecksTerminalAndAccepted'])
check('GL pending is not accepted', lambda: not assess(lambda _r, p, _j: p.update(status='running'))['developmentChecksTerminalAndAccepted'])
check('orphan GL jobs rejected', lambda: rejects(lambda: monitor.assess([], None, fixture()[2], COMMIT)))
sample = fixture()[0][0] | {'head_repository': {'full_name': monitor.REPO}, 'actor': {'email': 'SYNTHETIC_ONLY'}, 'head_commit': {'author': {'email': 'SYNTHETIC_ONLY'}}}
check('GH selection filters other SHA/ref and excludes author fields', lambda: len(monitor.select_github({'workflow_runs': [sample, sample | {'head_sha': '2' * 40}, sample | {'head_branch': 'tag'}]}, COMMIT)) == 1 and 'actor' not in monitor.select_github({'workflow_runs': [sample]}, COMMIT)[0])
check('GH wrong source repository rejected', lambda: rejects(lambda: monitor.select_github({'workflow_runs': [sample | {'head_repository': {'full_name': 'wrong/repo'}}]}, COMMIT)))
check('GL selection filters other SHA/ref/source', lambda: len(monitor.select_gitlab([fixture()[1], fixture()[1] | {'ref': 'tag'}, fixture()[1] | {'source': 'web'}], COMMIT)) == 1)
source = TOOL.read_text('utf-8')
tree = ast.parse(source)
required = {node.args[0].value for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'add_argument' and node.args and any(k.arg == 'required' and isinstance(k.value, ast.Constant) and k.value.value is True for k in node.keywords)}
check('commit and snapshot are required CLI parameters', lambda: required == {'--commit', '--snapshot'})
yaml = (monitor.ROOT / '.github/workflows/build.yml').read_text('utf-8')
targets = set(re.search(r'target: \[([^\]]+)\]', yaml).group(1).replace(' ', '').split(','))
check('current YAML modern target and collector names exactly match', lambda: targets | {'Collect seventeen modern JARs'} == monitor.MODERN and 'name: Collect seventeen modern JARs' in yaml)
legacy = (monitor.ROOT / '.github/workflows/legacy-build.yml').read_text('utf-8')
legacy_versions = re.findall(r"'([^']+)'", re.search(r'minecraft: \[([^\]]+)\]', legacy).group(1))
check('current YAML legacy five names match', lambda: {'MC ' + v + ' development' for v in legacy_versions} == monitor.LEGACY)
result = {'syntheticOnly': True, 'remoteRequests': 0, 'javaInvoked': False, 'CIExecuted': False,
          'toolSha256': hashlib.sha256(TOOL.read_bytes()).hexdigest(),
          'originToolSha256': hashlib.sha256((BASE / 'origin-ci-monitor.py').read_bytes()).hexdigest(),
          'cases': CASES, 'passed': True, 'count': len(CASES)}
(BASE / 'model-checks.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'passed': True, 'syntheticCases': len(CASES), 'toolSha256': result['toolSha256'], 'remoteRequests': 0}))
