import ctypes
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(r'E:\Codex_work\QiZhangVerdict')
CACHE=Path(__file__).resolve().parent
LEGACY=Path(r'E:\CodexTemp\QiZhangGuard')
EXPECTED='1e54c48f744b61cc23efe28b8516132d13dba601d9b36beab88c1da3a849f1b7'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
class Memory(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(s,ctypes.c_ulonglong) for s in ['total','available','totalPage','availablePage','totalVirtual','availableVirtual','extended']]

version=sys.argv[1];assert version in ['1.20.1','1.21.1']
review=CACHE/('base-'+version);review.mkdir(exist_ok=False)
memory=Memory();memory.length=ctypes.sizeof(memory);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
gate={'availableBytes':memory.available,'minimumGiB':3.5,'passed':memory.available>=3.5*1024**3,'timeUtc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
save(review/'resource-gate.json',gate)
assert gate['passed'],'Available physical memory below 3.5 GiB; no Minecraft launched'
product=ROOT/'bukkit/build/libs/qizhangverdict-bukkit-0.2.0-test.1.jar';assert sha(product)==EXPECTED
servers=json.loads((LEGACY/'downloads/servers.json').read_text());server=next(x for x in servers if x['version']==version);assert sha(server['path'])==server['sha256']
snapshots={}
for source,name in [(ROOT/'scripts/runtime_smoke.py','executed-runtime_smoke.py'),(ROOT/'scripts/protocol_smoke.cjs','executed-protocol_smoke.cjs'),(LEGACY/'bot/package-lock.json','executed-package-lock.json')]:
    target=review/name;target.write_bytes(source.read_bytes());snapshots[name]={'sha256':sha(target),'bytes':target.stat().st_size,'source':str(source)}
packages={name:json.loads((LEGACY/'bot/node_modules'/name/'package.json').read_text())['version'] for name in ['minecraft-protocol','minecraft-data','protodef']}
before=set((LEGACY/'runtime').glob(version+'-full-*'))
command=[sys.executable,'-B',str(ROOT/'scripts/runtime_smoke.py'),version,'--mode','full','--guard-jar',str(product),'--expected-guard-sha256',EXPECTED]
start=time.monotonic()
with (review/'driver.log').open('wb') as log:
    run=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=480)
created=set((LEGACY/'runtime').glob(version+'-full-*'))-before
result={'version':version,'wrapperExitCode':run.returncode,'command':command,'gate':gate,'packages':packages,'snapshots':snapshots,'elapsedSeconds':round(time.monotonic()-start,3)}
assert len(created)==1,'Expected one new isolated timestamped fixture'
folder=created.pop();result['folder']=str(folder)
raw=json.loads((folder/'result.json').read_text());result['rawResult']=raw
console=(folder/'console.log').read_text(encoding='utf-8',errors='replace')
result['normalStop']=raw['exitCode']==0 and 'Stopping server' in console and 'Saving chunks for level' in console and not raw.get('forcedStop')
result['passCount']=raw.get('protocol',{}).get('passed',0)
result['passed']=run.returncode==0 and raw.get('protocolExit')==0 and result['normalStop'] and result['passCount']==26 and raw['pluginSha256']==EXPECTED
result['antiXrayExecuted']=False;result['commandGateExecuted']=True
assert sha(folder/'server.jar')==server['sha256'] and sha(folder/'plugins'/product.name)==EXPECTED
save(review/'result.json',result)
print(json.dumps({'version':version,'passed':result['passed'],'groups':result['passCount'],'normalStop':result['normalStop'],'folder':str(folder),'packages':packages}),flush=True)
assert result['passed'],'Base TCP regression failed; retain full logs'
