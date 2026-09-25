# SPDX-License-Identifier: GPL-3.0-only
"""Run a one-use prepared fixture only after the root agent grants the Java slot."""
import argparse, ctypes, hashlib, json, os, pathlib, socket, subprocess, time

BASE = pathlib.Path(__file__).resolve().parent
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write_json(path, data):
    with path.open('x', encoding='utf-8') as out: json.dump(data, out, ensure_ascii=False, indent=2); out.write('\n')
def memory():
    class Status(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(n,ctypes.c_ulonglong) for n in ['total','available','pageTotal','pageAvailable','virtualTotal','virtualAvailable','extended']]
    state = Status(); state.length = ctypes.sizeof(Status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)): raise OSError('Cannot inspect physical memory')
    return state.available
def wait_for(path, marker, proc, timeout=240):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        text = path.read_text('utf-8',errors='replace') if path.exists() else ''
        if marker in text: return text
        if proc.poll() is not None: raise RuntimeError('Server exited before required marker: ' + marker)
        time.sleep(.25)
    raise TimeoutError('Missing server marker: ' + marker)
def properties(data):
    return dict(line.split('=',1) for line in data.decode('utf-8').splitlines() if line and not line.startswith('#'))

def run(version):
    folder = BASE / ('purpur-' + version + '-full-01')
    meta = json.loads((folder / 'fixture.json').read_text('utf-8'))
    assert meta['preparedOnly'] is True and meta['minecraft'] == version
    assert not (folder/'run-started.json').exists(), 'A previous attempt must never be reused'
    assert not (folder/'console.log').exists() and not (folder/'world').exists()
    assert not (folder/'plugins/QiZhangVerdict').exists(), 'Require fresh plugin state'
    for item in meta['inputs']:
        path = folder/item['target']
        assert path.is_file() and not path.is_symlink() and digest(path) == item['sha256'], item['target']
    assert digest(pathlib.Path(__file__)) == meta['runnerSha256'], 'Runner changed after preparation'
    for item in meta['externalExecutables']:
        assert digest(pathlib.Path(item['path'])) == item['sha256'], 'Executable changed'
    for name, item in meta['dependencies'].items():
        assert digest(pathlib.Path(item['packageJsonPath'])) == item['packageJsonSha256'], name
    assert digest(pathlib.Path(meta['nodeLock']['path'])) == meta['nodeLock']['sha256']
    assert {p.name for p in (folder/'plugins').glob('*.jar')} == {meta['guard']['filename']}
    available = memory()
    if available < 3.5 * 1024**3: raise RuntimeError('Physical memory below required 3.5 GiB; no Java started')
    with socket.socket() as probe:
        if hasattr(socket,'SO_EXCLUSIVEADDRUSE'): probe.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        probe.bind(('127.0.0.1',meta['port'])); probe.listen(1)
    lock = BASE/'owned-java-slot.lock'
    with lock.open('x',encoding='utf-8') as out: out.write(str(os.getpid()))
    proc = tests = None
    result = {'minecraft':version,'guardSha256':meta['guard']['sha256'],'fixtureSha256':digest(folder/'fixture.json'),'started':False,'passed':False,'normalStop':False,'availablePhysicalBytesBeforeJava':available,'minimumAvailableGiB':3.5,'scope':'Real loopback TCP with synthetic reports; no rendered companion or third-party anti-cheat integration.'}
    started = time.monotonic()
    try:
        write_json(folder/'run-started.json',{'pid':os.getpid(),'time':time.time(),'availableBytes':available,'runnerSha256':digest(pathlib.Path(__file__))})
        flags = getattr(subprocess,'CREATE_NO_WINDOW',0)
        command = [meta['java'],'-Xms256M','-Xmx1536M','-Djava.io.tmpdir='+str(folder/'runtime-temp'),'-jar','server.jar','--nogui']
        result['serverCommand'] = command
        with (folder/'console.log').open('x',encoding='utf-8') as log:
            proc = subprocess.Popen(command,cwd=folder,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True,encoding='utf-8',creationflags=flags)
            result['ownedServerPid'] = proc.pid
            try:
                text = wait_for(folder/'console.log','Done (',proc)
                assert 'Enabling QiZhangVerdict' in text and 'QiZhangVerdict sessions=' in text
                initial = (folder/'plugins/QiZhangVerdict/guard.properties').read_bytes()
                assert properties(initial) == meta['expectedDefaultPolicy'], 'Fresh defaults differ'
                (folder/'initial-default-guard.properties').write_bytes(initial)
                result['initialDefaultPolicySha256'] = hashlib.sha256(initial).hexdigest()
                result['initialAll13DefaultsMatched'] = True
                result['started'] = True
                proc.stdin.write('qzverdict status\nqzverdict integrations\n'); proc.stdin.flush()
                queue = folder/'commands.queue'; queue.write_text('',encoding='utf-8')
                env = dict(os.environ,NODE_PATH=meta['nodeModules'],QV_TEST_ANTIXRAY='0',QV_TEST_COMMAND_GATE='1',QV_DATA_DIR=str(folder/'plugins/QiZhangVerdict'))
                with (folder/'protocol-console.log').open('x',encoding='utf-8') as out:
                    tests = subprocess.Popen([meta['node'],str(folder/'qa/protocol_smoke.cjs'),version,str(meta['port']),str(folder)],cwd=folder,env=env,stdout=out,stderr=subprocess.STDOUT,creationflags=flags)
                    result['ownedNodePid'] = tests.pid
                    consumed = 0; deadline = time.monotonic()+240
                    while tests.poll() is None:
                        if proc.poll() is not None: raise RuntimeError('Server exited during protocol suite')
                        commands = queue.read_text('utf-8').splitlines()
                        for line in commands[consumed:]: proc.stdin.write(line+'\n'); proc.stdin.flush()
                        consumed = len(commands)
                        if time.monotonic() > deadline: raise TimeoutError('Protocol suite exceeded 240 seconds')
                        time.sleep(.1)
                result['protocolExitCode'] = tests.returncode
                assert tests.returncode == 0, 'Protocol failed; original console retained'
                protocol = json.loads((folder/'protocol-result.json').read_text('utf-8'))
                assert protocol['passed'] == len(protocol['cases']) == 26
                assert protocol['cases'] == meta['expectedCases'], 'Actual cases differ from pinned 26-group baseline'
                result['protocol'] = protocol
                result['allProtocolCasesPassed'] = True
            finally:
                if tests is not None and tests.poll() is None:
                    tests.kill(); tests.wait(timeout=15); result['forcedProtocolStop'] = True
                if proc.poll() is None:
                    proc.stdin.write('stop\n'); proc.stdin.flush()
                    try: proc.wait(timeout=90); result['normalStop'] = proc.returncode == 0
                    except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=15); result['forcedServerStop'] = True
                result['serverExitCode'] = proc.returncode
        assert result['normalStop'] and result['serverExitCode'] == 0
        result['passed'] = True
    except BaseException as exc:
        result['failureType'] = type(exc).__name__; result['failure'] = str(exc)
        raise
    finally:
        result['elapsedSeconds'] = round(time.monotonic()-started,3)
        for name in ['console.log','protocol-console.log','protocol-result.json','protocol-disconnect-observations.json']:
            p=folder/name
            if p.exists():result[name+'Sha256']=digest(p)
        policy=folder/'plugins/QiZhangVerdict/guard.properties'
        if policy.exists():
            (folder/'final-guard.properties').write_bytes(policy.read_bytes())
            result['finalPolicy']=properties(policy.read_bytes())
        write_json(folder/'result.json',result)
        assert lock.resolve().parent == BASE.resolve()
        lock.unlink()
    print(json.dumps({'passed':result['passed'],'caseCount':26,'serverExitCode':result['serverExitCode'],'folder':str(folder)}))

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version',choices=['1.20.1','1.21.1'])
    parser.add_argument('--run-authorized',action='store_true',help='Use only after explicit Java-slot handoff')
    args=parser.parse_args()
    if not args.run_authorized: parser.error('Preparation is complete; explicit runtime handoff required before --run-authorized')
    run(args.version)
