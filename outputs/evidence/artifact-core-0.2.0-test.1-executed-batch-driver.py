import hashlib,json,re,subprocess,sys
from pathlib import Path
root=Path('E:/Codex_work/QiZhangVerdict')
base=Path('E:/CodexTemp/QiZhangVerdict/release-0.2.0-test.1')
jdk8=Path('E:/CodexTemp/QiZhangVerdict/toolchains/jdk8/jdk8u504-b01/bin/java.exe')
jdk21=Path('D:/Java/jdk-21/bin/java.exe')
items=[]
excluded=[]
reports={}
for report in sorted((base/'builds').glob('*/result.json')):
    receipt=json.loads(report.read_text('utf-8'))
    if receipt.get('buildSuccessful') and receipt.get('oldArtifactsUnchanged'):
        reports[receipt['target']]=report
for report in sorted(reports.values()):
    result=json.loads(report.read_text('utf-8'))
    if not result.get('buildSuccessful') or not result.get('oldArtifactsUnchanged'): continue
    if report.parent.name=='1.12.2-02':
        excluded.append(str(report)+' (pre-annotation diagnostic; awaiting corrected 1.12.2-03)'); continue
    for item in result['artifacts']:
        if not re.fullmatch(r'qizhangverdict-(?:bukkit|(?:fabric|forge|neoforge)-1\.(?:8\.9|12\.2|16\.5|18\.2|19\.4|20\.1|21\.1))-0\.2\.0-test\.1\.jar',Path(item['path']).name):
            excluded.append(item['path']); continue
        jar=root/item['path']; output=base/'artifact-core'/jar.stem
        if (output/'result.json').exists():
            done=json.loads((output/'result.json').read_text('utf-8'))
            if not done['passed'] or done['sha256']!=item['sha256']: raise SystemExit('Existing failed or mismatched attempt requires new output')
        else:
            java=jdk8 if result['target'] in ('root','1.8.9','1.12.2','1.16.5') else jdk21
            cmd=[sys.executable,'-B',str(root/'scripts/artifact_core_checks.py'),'--jar',str(jar),'--sha256',item['sha256'],'--java',str(java),'--javac','D:/Java/jdk-21/bin/javac.exe','--output',str(output)]
            completed=subprocess.run(cmd,cwd=root)
            if completed.returncode: raise SystemExit(completed.returncode)
        items.append(item)
print(json.dumps({'checkedPackagedJars':len(items),'artifactNames':[Path(i['path']).name for i in items],'excludedNonProductOutputs':excluded}),flush=True)
