#!/usr/bin/env python3
"""Single read-only poll of the handles established by poll-01; no rediscovery."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import datetime
import importlib.util
import json
import re
import sys
sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('monitor', BASE / 'ci-monitor.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
COMMIT = '22549cbc1334990801ec1cb87bd3cb395d624ff8'
RUNS = {36435367558: '.github/workflows/build.yml', 36435367429: '.github/workflows/legacy-build.yml'}
PIPELINE = 2889898639

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--commit', required=True)
    p.add_argument('--snapshot', required=True)
    a = p.parse_args()
    m.require(a.commit == COMMIT, 'Different task commit')
    m.require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,80}', a.snapshot), 'Simple snapshot name required')
    out = BASE / 'snapshots' / a.snapshot
    out.mkdir(parents=True, exist_ok=False)
    logs = []
    def gh(rid):
        run, record = m.read_api('gh', f'repos/{m.REPO}/actions/runs/{rid}')
        m.require(run['id'] == rid and run['path'] == RUNS[rid], 'Run identity changed')
        picked = m.select_github({'workflow_runs': [run]}, COMMIT)
        m.require(len(picked) == 1, 'Run no longer matches exact source')
        jobs, job_record = m.read_api('gh', f'repos/{m.REPO}/actions/runs/{rid}/jobs?filter=latest&per_page=100')
        m.require(jobs['total_count'] == len(jobs['jobs']), 'Job pagination required')
        row = picked[0]
        row['jobs'] = [m.fields(j, m.GH_JOB_FIELDS) for j in jobs['jobs']]
        return row, [record, job_record]
    def gl():
        run, record = m.read_api('glab', f'projects/{m.PROJECT}/pipelines/{PIPELINE}')
        m.require(run['id'] == PIPELINE, 'Pipeline identity changed')
        rows = m.select_gitlab([run], COMMIT)
        m.require(len(rows) == 1, 'Pipeline no longer matches exact source')
        jobs, job_record = m.read_api('glab', f'projects/{m.PROJECT}/pipelines/{PIPELINE}/jobs?per_page=100')
        return rows[0], [m.fields(j, m.GL_JOB_FIELDS) for j in jobs], [record, job_record]
    with ThreadPoolExecutor(max_workers=3) as pool:
        runs_f = [pool.submit(gh, rid) for rid in RUNS]
        gl_f = pool.submit(gl)
        runs = []
        for future in runs_f:
            row, records = future.result(); runs.append(row); logs += records
        pipeline, jobs, records = gl_f.result(); logs += records
    result = {'schemaVersion': 1, 'sourceCommit': COMMIT, 'ref': 'main', 'github': runs,
              'gitlab': {'pipeline': pipeline, 'jobs': jobs}, 'assessment': m.assess(runs, pipeline, jobs, COMMIT),
              'checkedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'apiReads': logs, 'followsInitialHandles': True, 'metadataAllowlistOnly': True,
              'credentialOrAuthorFieldsStored': False, 'remoteWrites': False, 'javaInvoked': False,
              'developmentOnly': True, 'finalTagCIClaimed': False, 'releaseValidationClaimed': False}
    (out / 'snapshot.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'snapshot': str(out / 'snapshot.json'), 'assessment': result['assessment'],
                     'jobs': [{'name': j['name'], 'status': j['status'], 'conclusion': j['conclusion']} for r in runs for j in r['jobs']]}))

if __name__ == '__main__': main()
