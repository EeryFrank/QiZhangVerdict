#!/usr/bin/env python3
"""Read-only terminal development CI logs and exact modern artifact audit, cache only."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tomllib
import zipfile

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('monitor', BASE / 'ci-monitor.py')
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)
require = monitor.require
COMMIT = '22549cbc1334990801ec1cb87bd3cb395d624ff8'
RUNS = {36435367558, 36435367429}
PIPELINE = 2889898639

def digest(raw): return hashlib.sha256(raw).hexdigest()
def record(path): return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest(path.read_bytes())}
def dump(path, value):
    with path.open('x', encoding='utf-8') as target: target.write(json.dumps(value, indent=2) + '\n')
def get(tool, endpoint, binary=False):
    command = [tool, 'api'] + (['--allow-escape-sequences'] if binary and tool == 'gh' else []) + [endpoint]
    done = subprocess.run(command, cwd=monitor.ROOT, capture_output=True, timeout=60)
    require(done.returncode == 0, 'Read-only API failed: ' + tool + ' exit ' + str(done.returncode))
    return done.stdout if binary else json.loads(done.stdout)
def git_blob(path):
    done = subprocess.run(['git', 'show', COMMIT + ':' + path], cwd=monitor.ROOT, capture_output=True, timeout=30)
    require(done.returncode == 0, 'Cannot read committed source blob: ' + path)
    return done.stdout

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    summary = json.loads(args.snapshot.read_text('utf-8'))
    require(summary['sourceCommit'] == COMMIT and summary['ref'] == 'main', 'Wrong exact source anchor')
    require({r['id'] for r in summary['github']} == RUNS, 'Different workflow handles')
    pipeline = summary['gitlab']['pipeline']
    require(pipeline['id'] == PIPELINE, 'Different pipeline handle')
    assessment = monitor.assess(summary['github'], pipeline, summary['gitlab']['jobs'], COMMIT)
    require(assessment['developmentChecksTerminalAndAccepted'], 'Required terminal checks not satisfied')
    output = args.output.resolve()
    output.relative_to(BASE.resolve())
    output.mkdir(parents=True, exist_ok=False)
    result = {'sourceCommit': COMMIT, 'ref': 'main', 'developmentOnly': True, 'tagCIClaimed': False,
              'javaInvoked': False, 'remoteWrites': False, 'runtimeClaimed': False, 'passed': False,
              'snapshot': record(args.snapshot), 'assessment': assessment,
              'collector': record(Path(__file__)), 'monitor': record(BASE / 'ci-monitor.py')}
    try:
        def retrieve(item):
            host, run, job = item
            endpoint = ('repos/' + monitor.REPO + '/actions/jobs/' + str(job['id']) + '/logs' if host == 'github'
                        else 'projects/' + str(monitor.PROJECT) + '/jobs/' + str(job['id']) + '/trace')
            raw = get('gh' if host == 'github' else 'glab', endpoint, True)
            require(raw, 'Empty original job log')
            path = output / (host + '-job-' + str(job['id']) + '.log')
            path.write_bytes(raw)
            secret_shapes = len(re.findall(rb'(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{25,}|glpat-[A-Za-z0-9_-]{15,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)', raw))
            email_shapes = len(re.findall(rb'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', raw))
            rows = raw.decode('utf-8-sig', errors='replace').splitlines()
            pattern = r'BUILD SUCCESSFUL|actionable tasks:|\bPASS[: ]|regressions? passed|checks? passed|checks? PASS|dispatch|Mixin compatibility|Collected|collected|seventeen|17 exact|tests? completed|FROM-CACHE'
            proofs = [{'line': n, 'text': line} for n, line in enumerate(rows, 1) if re.search(pattern, line, re.I)]
            return {'host': host, 'runId': run, 'job': job, 'log': record(path), 'rawBytesPreserved': True,
                    'credentialShapeMatches': secret_shapes, 'emailShapeMatches': email_shapes,
                    'publicCopyAuthorized': False, 'proofLines': proofs}
        items = [('github', run['id'], job) for run in summary['github'] for job in run['jobs']]
        items += [('gitlab', pipeline['id'], job) for job in summary['gitlab']['jobs'] if job['started_at']]
        with ThreadPoolExecutor(max_workers=4) as pool: logs = list(pool.map(retrieve, items))
        require(len([r for r in logs if r['host'] == 'github']) == 14, 'Missing GitHub primary logs')
        result['jobLogs'] = logs
        require(not any(x['credentialShapeMatches'] for x in logs), 'Credential-shaped text present; cache-only review required')

        modern = next(r for r in summary['github'] if r['path'] == '.github/workflows/build.yml')
        payload = get('gh', 'repos/' + monitor.REPO + '/actions/runs/' + str(modern['id']) + '/artifacts?per_page=100')
        require(payload['total_count'] == len(payload['artifacts']), 'Artifact response needs pagination')
        name = 'qizhangverdict-seventeen-modern-jars-' + COMMIT
        selected = [x for x in payload['artifacts'] if x['name'] == name]
        require(len(selected) == 1, 'Exactly one complete modern collection required')
        artifact = selected[0]
        require(not artifact['expired'], 'Artifact expired')
        require(artifact['workflow_run']['id'] == modern['id'] and artifact['workflow_run']['head_sha'] == COMMIT, 'Artifact source mismatch')
        require(artifact['workflow_run']['head_branch'] == 'main', 'Artifact ref mismatch')
        archive_bytes = get('gh', 'repos/' + monitor.REPO + '/actions/artifacts/' + str(artifact['id']) + '/zip', True)
        require(artifact['digest'] == 'sha256:' + digest(archive_bytes), 'Artifact API ZIP digest mismatch')
        require(artifact['size_in_bytes'] == len(archive_bytes), 'Artifact API ZIP size mismatch')
        archive_path = output / 'seventeen-modern-jars.zip'
        archive_path.write_bytes(archive_bytes)
        tree = ast.parse(git_blob('scripts/ci_modern_artifacts.py'))
        targets = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'TARGETS' for t in n.targets))
        names = {}
        for target, (_project, version, loaders) in targets.items():
            mc = None if target == 'core-bukkit' else target.removeprefix('mods-')
            for loader in loaders:
                filename = f'qizhangverdict-{loader}-' + (mc + '-' if mc else '') + version + '.jar'
                names[filename] = {'target': target, 'minecraft': mc, 'loader': loader, 'version': version}
        require(len(names) == 17, 'Committed target model must enumerate exactly 17')
        license_raw, notice_raw = git_blob('LICENSE'), git_blob('NOTICE')
        jars = []
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            require(archive.testzip() is None, 'Collection ZIP CRC failure')
            require(len(archive.namelist()) == len(set(archive.namelist())), 'Duplicate collection ZIP entry')
            require(set(archive.namelist()) == set(names) | {'SHA256SUMS'}, 'Unexpected collection files')
            sums = {}
            for line in archive.read('SHA256SUMS').decode('ascii').splitlines():
                match = re.fullmatch(r'([a-f0-9]{64})  ([A-Za-z0-9._+-]+\.jar)', line)
                require(match is not None and match[2] not in sums, 'Invalid or duplicate SHA256SUMS line')
                sums[match[2]] = match[1]
            require(set(sums) == set(names), 'Checksum names mismatch')
            for filename, info in names.items():
                raw = archive.read(filename)
                require(digest(raw) == sums[filename], 'JAR checksum differs')
                with zipfile.ZipFile(io.BytesIO(raw)) as jar:
                    require(jar.testzip() is None, 'JAR CRC failure')
                    require(jar.read('LICENSE') == license_raw and jar.read('NOTICE') == notice_raw, 'GPL/NOTICE blob mismatch')
                    if info['loader'] == 'fabric':
                        desc = json.loads(jar.read('fabric.mod.json'))
                        require(desc['id'] == 'qizhangverdict' and desc['version'] == info['version'] and desc['license'] == 'GPL-3.0-only', 'Fabric descriptor mismatch')
                    elif info['loader'] == 'bukkit':
                        require(re.search(r'(?m)^version:\s*[\'\"]?' + re.escape(info['version']) + r'[\'\"]?\s*$', jar.read('plugin.yml').decode('utf-8')), 'Bukkit version mismatch')
                    else:
                        descriptor = 'META-INF/neoforge.mods.toml' if 'META-INF/neoforge.mods.toml' in jar.namelist() else 'META-INF/mods.toml'
                        desc = tomllib.loads(jar.read(descriptor).decode('utf-8'))
                        mods = [m for m in desc['mods'] if m['modId'] == 'qizhangverdict']
                        require(len(mods) == 1 and mods[0]['version'] == info['version'] and desc['license'] == 'GPL-3.0-only', 'Forge descriptor mismatch')
                    majors = sorted({int.from_bytes(jar.read(n)[6:8], 'big') for n in jar.namelist() if n.endswith('.class')})
                jars.append({'file': filename, **info, 'bytes': len(raw), 'sha256': digest(raw), 'zipCrcPassed': True,
                             'descriptorMatched': True, 'gplNoticeExactSourceBlob': True, 'classMajorsObserved': majors})
        result.update(passed=True, collection={'artifact': monitor.fields(artifact, ('id', 'name', 'size_in_bytes', 'digest', 'expired', 'created_at', 'updated_at')),
                      'archive': record(archive_path), 'apiZipDigestMatched': True, 'apiZipBytesMatched': True,
                      'exact17NamesAndChecksumsMatched': True, 'jars': jars},
                      scope='Exact main development CI status and original logs; collected 17 rebuilt JARs statically verified. No local Java/runtime or release substitution claimed.')
    except Exception as error:
        result.update(errorType=type(error).__name__, error=str(error) if isinstance(error, ValueError) else 'Read-only evidence collection did not complete')
        raise
    finally:
        dump(output / 'result.json', result)
        print(json.dumps({'passed': result['passed'], 'result': str(output / 'result.json'), 'jobLogCount': len(result.get('jobLogs', [])), 'jars': len(result.get('collection', {}).get('jars', []))}))

if __name__ == '__main__': main()
