#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Read-only single-poll exact-commit v0.6.0-dev-preview.1 tag CI monitor; writes only allowlisted public API fields."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse, datetime, hashlib, json, re, subprocess

ROOT=Path('E:/Codex_work/QiZhangVerdict')
BASE=Path(__file__).resolve().parent/'tag-ci'/'snapshots'
REF='v0.6.0-dev-preview.1'
REPO='EeryFrank/QiZhangVerdict'
PROJECT=86881575
MODERN={'core-bukkit','mods-1.17.1','mods-1.19.2','mods-1.20.1','mods-1.20.4','mods-1.20.6','mods-1.21.1','mods-1.21.11','Collect seventeen modern JARs'}
LEGACY={'MC '+v+' development' for v in ('1.8.9','1.12.2','1.16.5','1.18.2','1.19.4')}
GH_EXPECTED={'.github/workflows/build.yml':MODERN,'.github/workflows/legacy-build.yml':LEGACY}
GL_EXPECTED={'build: ['+x+']' for x in MODERN-{'Collect seventeen modern JARs'}}|{'legacy-build: ['+v+']' for v in ('1.8.9','1.12.2','1.16.5','1.18.2','1.19.4')}|{'collect'}
GH_RUN_FIELDS=('id','name','path','head_branch','head_sha','event','status','conclusion','html_url','run_attempt','created_at','updated_at')
GH_JOB_FIELDS=('id','name','status','conclusion','started_at','completed_at','html_url')
GL_PIPELINE_FIELDS=('id','ref','sha','source','status','web_url','created_at','updated_at','started_at','finished_at')
GL_JOB_FIELDS=('id','name','status','failure_reason','started_at','finished_at','web_url')

def require(value,message):
    if not value:raise ValueError(message)

def fields(row,names):return {key:row.get(key) for key in names}

def read_api(tool,endpoint):
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    completed=subprocess.run([tool,'api',endpoint],cwd=ROOT,capture_output=True,timeout=40)
    require(completed.returncode==0,tool+' read-only API failed with exit '+str(completed.returncode))
    value=json.loads(completed.stdout)
    return value,{'tool':tool,'method':'GET','endpoint':endpoint,'startedAtUtc':started,
                  'completedAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'rawResponseSha256':hashlib.sha256(completed.stdout).hexdigest(),'rawResponseStored':False}

def select_github(data,commit):
    rows=data['workflow_runs'];selected=[]
    for row in rows:
        if row.get('head_branch')!=REF or row.get('head_sha')!=commit or row.get('event')!='push':continue
        require(row.get('path') in GH_EXPECTED,'Unexpected workflow for exact release tag/SHA')
        require(row.get('head_repository',{}).get('full_name')==REPO,'Different source repository')
        selected.append(fields(row,GH_RUN_FIELDS))
    require(len(selected)<=2 and len({r['path'] for r in selected})==len(selected),'Ambiguous duplicated exact release tag workflow runs')
    require(len({r['id'] for r in selected})==len(selected),'Duplicate GitHub run IDs')
    return sorted(selected,key=lambda x:x['path'])

def select_gitlab(rows,commit):
    matches=[r for r in rows if r.get('ref')==REF and r.get('sha')==commit and r.get('source')=='push']
    require(len(matches)<=1,'Ambiguous duplicated exact release tag pipelines')
    return [fields(r,GL_PIPELINE_FIELDS) for r in matches]

def assess(runs,pipeline,jobs,commit):
    require(re.fullmatch('[0-9a-f]{40}',commit),'Invalid assessment commit')
    require(len(runs)<=2 and len({r['path'] for r in runs})==len(runs),'Duplicate or excess workflow summaries')
    require(len({r['id'] for r in runs})==len(runs),'Duplicate workflow IDs')
    all_job_ids=[];gh_complete=len(runs)==2;errors=[]
    for run in runs:
        require(run['head_branch']==REF and run['head_sha']==commit and run['event']=='push','GitHub tag/SHA/event drift')
        require(run['path'] in GH_EXPECTED,'Unexpected workflow path')
        expected=GH_EXPECTED[run['path']];actual=run.get('jobs',[])
        require(len({j['id'] for j in actual})==len(actual),'Duplicate GitHub job IDs')
        require(len({j['name'] for j in actual})==len(actual) and {j['name'] for j in actual}<=expected,'Unexpected or duplicate GitHub job names')
        if run['status']=='completed':require({j['name'] for j in actual}==expected,'Completed GitHub workflow missing required jobs')
        all_job_ids.extend(j['id'] for j in actual)
        complete=run['status']=='completed' and run['conclusion']=='success' and len(actual)==len(expected) and all(j['status']=='completed' and j['conclusion']=='success' and j.get('started_at') and j.get('completed_at') for j in actual)
        gh_complete=gh_complete and complete
        for job in actual:
            if job['status']=='completed' and job['conclusion'] not in ('success','skipped'):
                errors.append({'host':'github','run':run['id'],'job':job['id'],'name':job['name'],'conclusion':job['conclusion']})
    require(len(all_job_ids)==len(set(all_job_ids)),'GitHub job IDs reused across workflows')
    gl_state='not-discovered'
    if pipeline:
        require(pipeline['ref']==REF and pipeline['sha']==commit and pipeline['source']=='push','GitLab ref/SHA/source drift')
        require(len({j['id'] for j in jobs})==len(jobs) and len({j['name'] for j in jobs})==len(jobs),'Duplicate GitLab jobs')
        require({j['name'] for j in jobs}<=GL_EXPECTED,'Unexpected GitLab jobs')
        if pipeline['status'] in ('success','failed','canceled'):
            require(len(jobs)==14 and {j['name'] for j in jobs}==GL_EXPECTED,'Terminal GitLab pipeline missing required jobs')
        if pipeline['status']=='success' and len(jobs)==14 and all(j['status']=='success' and j.get('started_at') and j.get('finished_at') and not j.get('failure_reason') for j in jobs):gl_state='success-executed'
        elif pipeline['status']=='failed' and len(jobs)==14 and all(j['status']=='failed' and j.get('failure_reason')=='ci_quota_exceeded' and j.get('started_at') is None for j in jobs):gl_state='quota_not_started'
        elif pipeline['status'] in ('failed','canceled'):
            gl_state='failed-or-canceled';errors.extend({'host':'gitlab','pipeline':pipeline['id'],**fields(j,GL_JOB_FIELDS)} for j in jobs if j['status'] in ('failed','canceled'))
        else:gl_state='pending-or-running'
    if pipeline is None: require(not jobs,'GitLab jobs without matching pipeline')
    return {'githubAll14Passed':bool(gh_complete),'githubObservedJobs':len(all_job_ids),'gitlabState':gl_state,'gitlabObservedJobs':len(jobs),
            'tagChecksTerminalAndAccepted':bool(gh_complete and gl_state in ('success-executed','quota_not_started')),'failures':errors}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit',required=True,help='Exact pushed tag source commit, lowercase full 40-character SHA')
    parser.add_argument('--snapshot',required=True)
    parser.add_argument('--github',nargs=2,type=int,metavar=('MODERN_RUN','LEGACY_RUN'),help='Optional exact run IDs; both are still verified against tag, SHA, repository and workflow')
    parser.add_argument('--gitlab',type=int,help='Optional exact pipeline ID; ref, source and SHA are still verified')
    args=parser.parse_args()
    require(not args.github or (all(x>0 for x in args.github) and len(set(args.github))==2),'Two distinct positive GitHub IDs required')
    require(args.gitlab is None or args.gitlab>0,'Positive GitLab pipeline ID required')
    require(re.fullmatch('[0-9a-f]{40}',args.commit),'Full lowercase source commit required')
    commit=args.commit
    require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,80}',args.snapshot) and args.snapshot not in ('.','..'),'Fresh simple snapshot name required')
    out=BASE/args.snapshot;require(not out.exists(),'Never replace a CI snapshot');out.mkdir(parents=True)
    logs=[];runs=[];pipeline=None;jobs=[]
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            if args.github:
                futures=[pool.submit(read_api,'gh',f'repos/{REPO}/actions/runs/{run_id}') for run_id in args.github]
                rows=[]
                for run_id,future in zip(args.github,futures):
                    data,meta=future.result();logs.append(meta)
                    require(data.get('id')==run_id,'GitHub direct run ID mismatch');rows.append(data)
                runs=select_github({'workflow_runs':rows},commit)
                require(len(runs)==2,'Direct GitHub handles must both match the exact tag/SHA/push')
            else:
                data,meta=read_api('gh',f'repos/{REPO}/actions/runs?head_sha={commit}&branch={REF}&event=push&per_page=100')
                logs.append(meta);runs=select_github(data,commit)
            if args.gitlab:
                data,meta=read_api('glab',f'projects/{PROJECT}/pipelines/{args.gitlab}');logs.append(meta)
                require(data.get('id')==args.gitlab,'GitLab direct pipeline ID mismatch')
                candidates=select_gitlab([data],commit)
                require(len(candidates)==1,'Direct GitLab handle must match the exact tag/SHA/push')
            else:
                data,meta=read_api('glab',f'projects/{PROJECT}/pipelines?ref={REF}&sha={commit}&source=push&per_page=100')
                logs.append(meta);candidates=select_gitlab(data,commit)
            pending=[]
            for run in runs:pending.append(('gh',run,pool.submit(read_api,'gh',f'repos/{REPO}/actions/runs/{run["id"]}/jobs?filter=latest&per_page=100')))
            if candidates:pending.append(('gl',candidates[0],pool.submit(read_api,'glab',f'projects/{PROJECT}/pipelines/{candidates[0]["id"]}')))
            for kind,owner,future in pending:
                data,meta=future.result();logs.append(meta)
                if kind=='gh':owner['jobs']=[fields(j,GH_JOB_FIELDS) for j in data['jobs']]
                else:pipeline=fields(data,GL_PIPELINE_FIELDS)
            if pipeline:
                data,meta=read_api('glab',f'projects/{PROJECT}/pipelines/{pipeline["id"]}/jobs?per_page=100');logs.append(meta);jobs=[fields(j,GL_JOB_FIELDS) for j in data]
        result={'schemaVersion':1,'ref':REF,'sourceCommit':commit,'checkedAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'github':runs,'gitlab':{'pipeline':pipeline,'jobs':jobs},'assessment':assess(runs,pipeline,jobs,commit),'apiReads':logs,
                'developmentOnly':False,'finalTagMonitor':True,'javaInvoked':False,'metadataAllowlistOnly':True,'credentialOrAuthorFieldsStored':False,'remoteWrites':False,'releaseValidationClaimed':False,'requestedHandles':{'github':args.github,'gitlab':args.gitlab}}
        (out/'snapshot.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
        print(json.dumps({'snapshot':str(out),'github':[{'id':r['id'],'url':r['html_url'],'status':r['status'],'conclusion':r['conclusion']} for r in runs],
                          'gitlab':pipeline,'assessment':result['assessment']}))
    except Exception as exc:
        failure={'ref':REF,'sourceCommit':commit,'errorType':type(exc).__name__,'message':str(exc) if isinstance(exc,ValueError) else 'API or local parsing did not complete',
                 'apiReads':logs,'github':runs,'gitlab':{'pipeline':pipeline,'jobs':jobs},'remoteWrites':False}
        (out/'failure.json').write_text(json.dumps(failure,indent=2)+'\n',encoding='utf8');raise

if __name__=='__main__':main()
