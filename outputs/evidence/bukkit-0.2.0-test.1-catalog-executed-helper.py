"""Fresh two-phase Bukkit catalog/sanctions QA. Prepare performs no Java execution."""
# SPDX-License-Identifier: GPL-3.0-only
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
GUARD_SHA = '1e54c48f744b61cc23efe28b8516132d13dba601d9b36beab88c1da3a849f1b7'
CATALOG_SHA = '66a633ad3faa2d7d666c43e2b3b544437054345e102103d90fe3b5db022c46a3'
DEFAULT_POLICY_SHA = '47310c31b47287ab805bfdbf8ddddf80e8169385bd9c862239a0a0075644da4e'
SERVERS = {'1.20.1':('2062','238e64b33e5c7c9b87506cf1a23f239e6ce7fb71edd9d31837f229c94f4dfa1a'),
           '1.21.1':('2329','30403cf54f981f16e1403f172645e82d3e4a59ad6c9f1d8e98df99edb1f8ae4c')}
DEFAULT_POLICY = '''# QiZhangVerdict: restart/reload after editing; IPs are literals or CIDRs, comma separated.
limits.max-online-per-ip=3
limits.max-online-per-ip-device=1
limits.max-accounts-per-ip=5
limits.account-window-hours=720
limits.attempts-per-minute=20
ip.allow=
ip.deny=
companion.required=true
companion.timeout-seconds=20
vm.action=DENY
blacklist.action=DENY
sanctions.on-deny=BAN
device.required=true
'''

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value): Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def available_memory():
    if os.name=='nt':
        class Status(ctypes.Structure):
            _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(s,ctypes.c_ulonglong) for s in
                       ('totalPhys','availPhys','totalPage','availPage','totalVirtual','availVirtual','extended')]
        status=Status();status.length=ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)): raise OSError('Cannot inspect available memory')
        return status.availPhys
    text=Path('/proc/meminfo').read_text()
    return int(re.search(r'^MemAvailable:\s+(\d+)',text,re.M).group(1))*1024

def no_reparse_tree(path):
    for item in [path,*path.rglob('*')]:
        if item.is_symlink() or getattr(item.lstat(),'st_file_attributes',0)&0x400:
            raise ValueError('Immutable input cache may not contain links/junctions')

def prepare(args):
    source=args.server_fixture.resolve(); guard=args.guard_jar.resolve(); catalog=ROOT/'catalog/blacklist-extension.tsv'
    build,server_sha=SERVERS[args.version]
    assert digest(source/'server.jar')==server_sha, 'Unexpected fixed server JAR'
    assert digest(guard)==GUARD_SHA, 'Unexpected candidate product JAR'
    assert digest(catalog)==CATALOG_SHA, 'Catalog differs from the reviewed 37-row snapshot'
    assert hashlib.sha256(DEFAULT_POLICY.encode()).hexdigest()==DEFAULT_POLICY_SHA
    for exe in [args.java,args.node]:
        if not Path(exe).is_file(): raise ValueError('Explicit runtime executable missing')
    package=read(args.node_modules/'minecraft-protocol/package.json')
    assert package['version']=='1.66.2', 'Use the pinned protocol QA installation'
    sys.path.insert(0,str(ROOT/'integrations'))
    from manage_integrations import fresh_directory
    folder=fresh_directory(args.output)
    shutil.copyfile(source/'server.jar',folder/'server.jar')
    for name in ['cache','libraries','versions']:
        if (source/name).exists(): no_reparse_tree(source/name);shutil.copytree(source/name,folder/name)
    plugins=folder/'plugins';plugins.mkdir();shutil.copyfile(guard,plugins/guard.name)
    data=plugins/'QiZhangVerdict';data.mkdir()
    policy=DEFAULT_POLICY.replace('limits.max-accounts-per-ip=5\n','limits.max-accounts-per-ip=64\n').replace('limits.attempts-per-minute=20\n','limits.attempts-per-minute=200\n')
    (data/'guard.properties').write_bytes(policy.encode())
    (folder/'default-policy-reference.properties').write_bytes(DEFAULT_POLICY.encode())
    (folder/'qa-policy-reference.properties').write_bytes(policy.encode())
    assert not (data/'blacklist.tsv').exists(), 'Fresh default catalog must be created by the product at runtime'
    shutil.copyfile(catalog,folder/'catalog-snapshot.tsv')
    shutil.copyfile(__file__,folder/'executed-helper.py')
    shutil.copyfile(ROOT/'scripts/bukkit_catalog_protocol.cjs',folder/'executed-protocol.cjs')
    shutil.copyfile(ROOT/'scripts/legacy-protocol-qa/package-lock.json',folder/'executed-package-lock.json')
    (folder/'eula.txt').write_text('eula=true\n',encoding='ascii')
    (folder/'server.properties').write_text(f'server-ip=127.0.0.1\nserver-port={args.port}\nonline-mode=false\nenforce-secure-profile=false\n'
        'network-compression-threshold=256\nspawn-protection=0\nview-distance=2\nsimulation-distance=2\nmax-players=10\n'
        'level-type=minecraft:flat\ngenerate-structures=false\nspawn-monsters=false\nspawn-animals=false\ndifficulty=peaceful\n',encoding='utf-8')
    fixture={'schemaVersion':1,'version':args.version,'distribution':'Purpur','build':build,
             'serverSourceUrl':f'https://api.purpurmc.org/v2/purpur/{args.version}/{build}/download','serverSha256':server_sha,
             'guardFile':guard.name,'guardVersion':'0.2.0-test.1','guardSha256':GUARD_SHA,'catalogSha256':CATALOG_SHA,
             'pristineDefaultPolicySha256':DEFAULT_POLICY_SHA,'qaPolicySha256':digest(data/'guard.properties'),
             'expectedQaPolicy':dict(line.split('=',1) for line in policy.splitlines() if line and not line.startswith('#')),
             'declaredQuotaChanges':{'limits.max-accounts-per-ip':{'default':'5','qa':'64'},'limits.attempts-per-minute':{'default':'20','qa':'200'}},
             'temporaryControlChange':'Only restart-phase KICK control temporarily changes sanctions.on-deny from BAN to KICK; restored to BAN before successful stop.',
             'strictUnchanged':['companion.required=true','companion.timeout-seconds=20','device.required=true','vm.action=DENY','blacklist.action=DENY','limits.max-online-per-ip=3','limits.max-online-per-ip-device=1'],
             'java':str(Path(args.java).resolve()),'node':str(Path(args.node).resolve()),'nodeModules':str(args.node_modules.resolve()),
             'helperSha256':digest(__file__),'protocolSha256':digest(folder/'executed-protocol.cjs'),
             'dependencyLockSha256':digest(folder/'executed-package-lock.json'),'port':args.port,'host':'127.0.0.1',
             'prepareExecutedJava':False,'sourceFixtureReadOnly':str(source),
             'scope':'New candidate product; synthetic loopback TCP, catalog and sanction regressions. No third-party detection engine, real hardware, accuracy or performance claim.'}
    save(folder/'fixture.json',fixture)
    print(json.dumps({'prepared':True,'folder':str(folder),'guardSha256':GUARD_SHA,'javaStarted':False}))

def run_phase(folder,fixture,phase):
    result_path=folder/('result-'+phase+'.json')
    if result_path.exists() or (folder/('console-'+phase+'.log')).exists():raise ValueError('Refusing to overwrite a prior phase')
    result={'phase':phase,'passed':False};started=time.monotonic();process=tests=None
    log=folder/('console-'+phase+'.log');queue=folder/'commands.queue';queue.write_text('',encoding='utf-8')
    policy=folder/'plugins/QiZhangVerdict/guard.properties'
    try:
        available=available_memory();result['availableBytesBeforeJava']=available;result['minimumAvailableGiB']=3.5
        if available<3.5*1024**3: raise RuntimeError('Resource gate rejected launch below 3.5 GiB')
        with socket.socket() as probe:
            if os.name!='nt':probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            probe.bind(('127.0.0.1',fixture['port']));probe.listen(1)
        assert digest(folder/'server.jar')==fixture['serverSha256']
        assert digest(folder/'plugins'/fixture['guardFile'])==GUARD_SHA
        assert digest(folder/'executed-protocol.cjs')==fixture['protocolSha256']
        assert digest(policy)==fixture['qaPolicySha256']
        if phase=='initial': assert not (folder/'plugins/QiZhangVerdict/blacklist.tsv').exists()
        result['policyBeforeSha256']=digest(policy)
        with log.open('w',encoding='utf-8') as output:
            command=[fixture['java'],'-Xms256M','-Xmx1536M','-jar','server.jar','--nogui']
            result['command']=command
            process=subprocess.Popen(command,cwd=folder,stdin=subprocess.PIPE,stdout=output,stderr=subprocess.STDOUT,
                                     text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            result['ownedServerPid']=process.pid;deadline=time.monotonic()+240
            while 'Done (' not in log.read_text('utf-8',errors='replace'):
                if process.poll() is not None:raise RuntimeError('Server exited before Done')
                if time.monotonic()>deadline:raise TimeoutError('Server startup timeout')
                time.sleep(.25)
            process.stdin.write('qzverdict status\n');process.stdin.flush()
            deadline=time.monotonic()+15
            while 'companion=required, vm=DENY' not in log.read_text('utf-8',errors='replace'):
                if time.monotonic()>deadline:raise AssertionError('Strict status missing')
                time.sleep(.1)
            assert 'deviceRequired=true' in log.read_text('utf-8',errors='replace')
            result['startupPassed']=True
            env=dict(os.environ,NODE_PATH=fixture['nodeModules'])
            with (folder/('protocol-'+phase+'.log')).open('w',encoding='utf-8') as protocol_log:
                tests=subprocess.Popen([fixture['node'],str(folder/'executed-protocol.cjs'),fixture['version'],str(fixture['port']),str(folder),phase],
                                       stdout=protocol_log,stderr=subprocess.STDOUT,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                consumed=0;deadline=time.monotonic()+360
                while tests.poll() is None:
                    lines=queue.read_text('utf-8').splitlines()
                    for line in lines[consumed:]:process.stdin.write(line+'\n');process.stdin.flush()
                    consumed=len(lines)
                    if time.monotonic()>deadline:raise TimeoutError('Protocol phase timeout')
                    if process.poll() is not None:raise RuntimeError('Server exited during protocol phase')
                    time.sleep(.05)
            result['protocolExitCode']=tests.returncode
            if tests.returncode!=0:raise AssertionError('TCP regression failed; see retained raw protocol log')
            protocol=read(folder/('protocol-'+phase+'.json'))
            assert protocol['passed'] and protocol['caseCount']==(14 if phase=='initial' else 9)
            result['protocol']=protocol;result['passed']=True
    except Exception as exc:
        result['error']=str(exc)
    finally:
        if tests is not None and tests.poll() is None:tests.kill();tests.wait();result['forcedProtocolStop']=True
        if process is not None and process.poll() is None:
            try:process.stdin.write('stop\n');process.stdin.flush()
            except (OSError,BrokenPipeError):result['stopWriteFailed']=True
            try:process.wait(timeout=90)
            except subprocess.TimeoutExpired:process.kill();process.wait();result['forcedServerStop']=True
        if process is not None and process.stdin is not None:process.stdin.close()
        result['serverExitCode']=process.returncode if process is not None else None
        text=log.read_text('utf-8',errors='replace') if log.exists() else ''
        result['normalStop']=result['serverExitCode']==0 and 'Stopping server' in text and 'Saving chunks for level' in text and not result.get('forcedServerStop')
        result['policyAfterSha256']=digest(policy) if policy.exists() else None
        result['finalPolicyMatchesDeclaredQaPolicy']=result.get('policyBeforeSha256')==result['policyAfterSha256']==fixture['qaPolicySha256']
        result['passed']=bool(result['passed'] and result['normalStop'] and result['finalPolicyMatchesDeclaredQaPolicy'] and not result.get('forcedProtocolStop'))
        result['elapsedSeconds']=round(time.monotonic()-started,3);result['consoleSha256']=digest(log) if log.exists() else None
        save(result_path,result)
    if not result['passed']:raise RuntimeError(result.get('error','Phase verification/normal shutdown failed'))
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','run']);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--version',choices=SERVERS,default='1.21.1')
    parser.add_argument('--server-fixture',type=Path,default=Path('E:/CodexTemp/QiZhangGuard/runtime/1.21.1-startup'))
    parser.add_argument('--guard-jar',type=Path,default=ROOT/'bukkit/build/libs/qizhangverdict-bukkit-0.2.0-test.1.jar')
    parser.add_argument('--java',default='D:/Java/jdk-21/bin/java.exe')
    parser.add_argument('--node',default='E:/CodexTemp/Codex/RuntimeCache/codex-primary-runtime/dependencies/node/bin/node.exe')
    parser.add_argument('--node-modules',type=Path,default=Path('E:/CodexTemp/QiZhangVerdict/legacy-protocol-qa/node_modules'))
    parser.add_argument('--port',type=int,default=25675);args=parser.parse_args()
    if args.action=='prepare':prepare(args);return
    folder=args.output.resolve();fixture=read(folder/'fixture.json')
    if not (folder/'.qizhang-verdict-stage').is_file():raise ValueError('Missing fresh-fixture ownership marker')
    if (folder/'acceptance.json').exists():raise ValueError('Refusing to rerun a completed fixture')
    assert fixture['guardSha256']==GUARD_SHA and fixture['catalogSha256']==CATALOG_SHA
    java=subprocess.run([fixture['java'],'-version'],capture_output=True,text=True,check=True)
    (folder/'java-version.log').write_text(java.stderr,encoding='utf-8')
    results=[]
    for phase in ['initial','restart']:
        result=run_phase(folder,fixture,phase);results.append(result)
        print(json.dumps({'phase':phase,'passed':result['passed'],'groups':result['protocol']['caseCount'],'serverExit':result['serverExitCode']}),flush=True)
    save(folder/'acceptance.json',{'passed':True,'fixture':fixture,'phases':results,'assertionGroups':23,
                                 'scope':'New candidate real TCP proof with declared batch quota changes, not an unmodified-full-default quota test.'})

if __name__=='__main__':main()
