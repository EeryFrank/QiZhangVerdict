import argparse, ctypes, datetime, hashlib, json, os, subprocess, sys
from pathlib import Path

ROOT = Path('E:/Codex_work/QiZhangVerdict')
CACHE = Path('E:/CodexTemp/QiZhangVerdict/next-platforms')
JDK17 = Path('E:/CodexTemp/mods-danzi/minecraft/runtime/java-runtime-gamma/windows-x64/java-runtime-gamma')
JDK21 = Path('D:/Java/jdk-21')

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, value): path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
def sources(project):
    roots = [ROOT/'core/src', ROOT/'client-common/src', ROOT/'platforms/shared/src', ROOT/'gradle']
    roots += [ROOT/'bukkit'] if project == ROOT else [project, ROOT/'platforms/1.20.1/fabric/src/main/java']
    found = {}
    for base in roots:
        for path in base.rglob('*'):
            if not path.is_file() or any(x in path.relative_to(ROOT).parts for x in ('build', '.gradle', '.git', 'outputs', 'node_modules')): continue
            if path.suffix in ('.java', '.gradle', '.properties', '.json', '.toml', '.yml', '.mcmeta') or path.name in ('LICENSE', 'NOTICE'):
                found[path.relative_to(ROOT).as_posix()] = sha(path)
    for path in (ROOT/'build.gradle', ROOT/'settings.gradle', ROOT/'core/build.gradle', ROOT/'LICENSE', ROOT/'NOTICE'):
        found[path.relative_to(ROOT).as_posix()] = sha(path)
    return found

def run(target, attempt):
    project = ROOT if target == 'root' else ROOT/'platforms'/target
    version = '0.2.1-dev' if target == 'root' else '0.3.0-dev'
    folder = CACHE/target/'builds'/attempt
    folder.mkdir(parents=True, exist_ok=False)
    (folder/'temp').mkdir()
    class Mem(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(x, ctypes.c_ulonglong) for x in ['totalPhysical', 'availablePhysical', 'totalPageFile', 'availablePageFile', 'totalVirtual', 'availableVirtual', 'availableExtendedVirtual']]
    mem = Mem(); mem.length = ctypes.sizeof(mem)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
    free = mem.availablePhysical/(1024**3)
    if free < 5: raise RuntimeError('Need 5 GiB free before Gradle; actual %.3f'%free)
    env = dict(os.environ)
    for key in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS'): env.pop(key, None)
    env.update(JAVA_HOME=str(JDK21), GRADLE_USER_HOME='E:/CodexTemp/Gradle/QiZhang_Games', CI='true', TEMP=str(folder/'temp'), TMP=str(folder/'temp'))
    env['PATH'] = str(JDK21/'bin')+';'+env['PATH']
    env['JAVA_TOOL_OPTIONS'] = '-Djava.io.tmpdir='+str(folder/'temp').replace('\\','/')+' -Dqzguard.testDir='+str(folder/'core-tests').replace('\\','/')+' -Djavax.net.ssl.trustStoreType=Windows-ROOT -Djavax.net.ssl.trustStore=NONE'
    env['GRADLE_OPTS'] = '-Dorg.gradle.internal.http.connectionTimeout=15000 -Dorg.gradle.internal.http.socketTimeout=15000'
    cmd = [str(project/'gradlew.bat'), '--no-daemon', '--max-workers=1', '--console=plain', '--stacktrace', '--project-cache-dir', str(folder/'project-cache'), '-Dorg.gradle.jvmargs=-Xmx1536M -Dfile.encoding=UTF-8', '-Porg.gradle.java.installations.paths='+','.join(x.as_posix() for x in (JDK17, JDK21)), '-Porg.gradle.java.installations.auto-detect=false', '-Porg.gradle.java.installations.auto-download=false', '-PqzRuntimeRoot='+(folder/'runtime').as_posix(), '-PqzTestRoot='+(folder/'tests').as_posix(), ':neoforge:build']
    old = {p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.rglob('build/libs/qizhangverdict-*.jar') if '/1.20.4/neoforge/' not in p.as_posix()}
    receipt = {'schemaVersion':1,'target':target,'version':version,'attempt':attempt,'startedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':cmd,'workingDirectory':str(project),'environment':{k:env[k] for k in ('JAVA_HOME','GRADLE_USER_HOME','CI','TEMP','TMP','JAVA_TOOL_OPTIONS','GRADLE_OPTS')},'availablePhysicalGiB':free,'minimumFreeGiB':5,'sourceSha256':sources(project),'oldArtifactSha256':old,'gameStarted':False,'helperSha256':sha(Path(__file__))}
    save(folder/'plan.json',receipt)
    print(json.dumps({'starting':target,'attempt':attempt,'freeGiB':round(free,3),'log':str(folder/'gradle.log')}),flush=True)
    with (folder/'gradle.log').open('xb') as log:
        code=subprocess.call(cmd,cwd=project,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    data=(folder/'gradle.log').read_text('utf-8',errors='replace')
    unchanged=all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in old.items())
    stable=sources(project)==receipt['sourceSha256']
    jars=list((ROOT/'bukkit/build/libs').glob('*'+version+'.jar')) if target=='root' else list((project/'neoforge/build/libs').glob('*'+version+'.jar'))
    receipt.update(exitCode=code,buildSuccessful=code==0 and 'BUILD SUCCESSFUL' in data,finishedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),logSha256=sha(folder/'gradle.log'),oldArtifactsUnchanged=unchanged,sourceUnchanged=stable,artifacts=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in jars])
    save(folder/'result.json',receipt)
    print(json.dumps({k:receipt[k] for k in ('target','version','exitCode','buildSuccessful','oldArtifactsUnchanged','sourceUnchanged','artifacts')}),flush=True)
    return code or (0 if unchanged and stable and receipt['buildSuccessful'] else 1)

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(); parser.add_argument('--target',choices=('root','1.20.4'),required=True);parser.add_argument('--attempt',required=True)
    args=parser.parse_args();sys.exit(run(args.target,args.attempt))
