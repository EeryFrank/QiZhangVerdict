import difflib
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path('E:/Codex_work/QiZhangVerdict')
BASE=Path(__file__).resolve().parent
TOOL=ROOT/'integrations/compat/patch_antixray116.py'
INPUT=Path('E:/CodexTemp/QiZhangVerdict/legacy-integration-research/binary-audit-01/jars/anti-xray-mc1.16.5-1.1.0.jar')
NAME='anti-xray-mc1.16.5-1.1.0-qzcompat.1.jar'
EXPECTED='fa72bb5e4424bc8ffb9cda83298f8c27b704dd36c3bd413660a3a58d69cc9484'
OLD=BASE.parent/'compat-artifact-01'
HISTORY=ROOT/'outputs/legacy-fabric116-antixray-qzcompat1-java17-validation.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):Path(p).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
assert not (BASE/'result.json').exists(),'Refuse to overwrite finished CLI acceptance'
assert sha(INPUT)=='7c8d22a2e9c8d0f88a33ce76cdb7bade18c63bb2a5cc9b3a11991bd28c742f43'
old_receipt=json.loads((OLD/'receipt.json').read_text('utf-8'))
original=TOOL.read_bytes().replace(b'    if args.output.resolve() == args.receipt.resolve():\n        parser.error("Output and receipt must resolve to different paths")\n',b'')
assert hashlib.sha256(original).hexdigest()==old_receipt['toolSha256']
history_sha=sha(HISTORY)
(BASE/'executed-tool.py').write_bytes(TOOL.read_bytes())
(BASE/'source.diff').write_text(''.join(difflib.unified_diff(original.decode().splitlines(True),TOOL.read_text().splitlines(True),
    fromfile='historical/patch_antixray116.py',tofile='current/patch_antixray116.py')),encoding='utf-8')
cases=[]
def run(name,output,receipt,expect_error=None):
    log=BASE/(name+'.log'); assert not log.exists()
    command=[sys.executable,'-B',str(TOOL),'--input',str(INPUT),'--output',str(output),'--receipt',str(receipt)]
    with log.open('xb') as f:r=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=30,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    text=log.read_text('utf-8')
    okay=r.returncode==2 and expect_error in text if expect_error else r.returncode==0
    assert okay,(name,r.returncode)
    return {'name':name,'command':command,'exitCode':r.returncode,'passed':True,
        'log':log.name,'logSha256':sha(log),'outputPath':str(output),'receiptPath':str(receipt)}
for kind in ['identical','windows-case-alias','resolved-parent-alias']:
    output=BASE/kind/'uncreated'/NAME
    receipt=output if kind=='identical' else Path(str(output).upper()) if kind=='windows-case-alias' else output.parent/'unused'/'..'/NAME
    assert output.resolve()==receipt.resolve()
    row=run(kind,output,receipt,'Output and receipt must resolve to different paths')
    assert not output.exists() and not receipt.exists() and not output.parent.exists()
    row.update({'newOutputAbsent':True,'newReceiptAbsent':True,'outputParentNotCreated':True})
    cases.append(row)
receipt=BASE/'existing-receipt.json'; sentinel=b'{"sentinel":"preserve-existing-receipt"}\n'
receipt.write_bytes(sentinel);output=BASE/'existing-receipt-case'/'uncreated'/NAME
row=run('existing-receipt',output,receipt,'Use new output and receipt files')
assert not output.exists() and not output.parent.exists() and receipt.read_bytes()==sentinel
row.update({'newOutputAbsent':True,'outputParentNotCreated':True,'existingReceiptBytesUnchanged':True})
cases.append(row)
output=BASE/'normal'/NAME;receipt=BASE/'normal'/'receipt.json'
row=run('normal-generation',output,receipt)
proof=json.loads(receipt.read_text('utf-8'))
assert sha(output)==EXPECTED and output.read_bytes()==(OLD/NAME).read_bytes()
assert proof['outputSha256']==EXPECTED and proof['allClassBytesUnchanged'] and proof['unchangedClassCount']==32
assert proof['nestedJarsUnchanged'] and proof['toolSha256']==sha(TOOL)
row.update({'outputSha256':EXPECTED,'bytes':output.stat().st_size,'historicalArtifactByteIdentical':True,
    'allClassBytesUnchanged':True,'unchangedClassCount':32,'nestedJarsUnchanged':True,'runtimeVerified':False})
cases.append(row)
assert sha(HISTORY)==history_sha and sha(INPUT)==proof['inputSha256']
result={'schemaVersion':1,'passed':True,'caseCount':5,'cases':cases,
    'createdUtc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'python':sys.version,
    'javaExecuted':False,'minecraftExecuted':False,'tool':{'path':TOOL.relative_to(ROOT).as_posix(),'sha256':sha(TOOL),
        'previousSha256':old_receipt['toolSha256'],'bytes':TOOL.stat().st_size},
    'input':{'path':str(INPUT),'sha256':sha(INPUT),'bytes':INPUT.stat().st_size},
    'outputSha256':EXPECTED,'historicalRuntimeReport':{'path':HISTORY.relative_to(ROOT).as_posix(),'sha256':history_sha,'unchanged':True},
    'scope':'CLI preflight checks only; normal JAR bytes equal the previously tested compatibility artifact. No new Minecraft runtime acceptance.'}
save(BASE/'result.json',result)
print(json.dumps({'passed':True,'cases':5,'toolSha256':sha(TOOL),'outputSha256':EXPECTED}))
