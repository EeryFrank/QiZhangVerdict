import argparse, ctypes, datetime, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT=Path('E:/Codex_work/QiZhangVerdict')
BASE=Path('E:/CodexTemp/QiZhangVerdict/next-platforms/1.19.2')
PROJECT=ROOT/'platforms/1.19.2'
JDK21=Path('D:/Java/jdk-21')
JDK17=Path('E:/CodexTemp/mods-danzi/minecraft/runtime/java-runtime-gamma/windows-x64/java-runtime-gamma')
VERSION='0.3.0-dev'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v): Path(p).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def run(attempt):
    folder=BASE/'builds'/attempt; folder.mkdir(parents=True,exist_ok=False)
    class Mem(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ['totalPhysical','availablePhysical','totalPageFile','availablePageFile','totalVirtual','availableVirtual','availableExtendedVirtual']]
    mem=Mem();mem.length=ctypes.sizeof(mem)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
    free=mem.availablePhysical/1024**3
    if free<5:
        save(folder/'resource-gate.json',{'passed':False,'requiredFreeGiB':5,'availablePhysicalGiB':free,'javaStarted':False})
        raise RuntimeError('Build requires 5 GiB free; observed %.3f'%free)
    old={p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.rglob('build/libs/qizhangverdict-*.jar') if p.name.endswith(('.jar',)) and VERSION not in p.name}
    prior=[]
    for p in PROJECT.glob('*/build/libs/*.jar'):
        backup=folder/'prior-candidates'/p.parent.parent.parent.name/p.name
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,backup)
        assert sha(p)==sha(backup)
        prior.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'backup':str(backup)})
    source={}
    for base in (ROOT/'core/src',ROOT/'client-common/src',ROOT/'platforms/shared/src',PROJECT):
        for p in base.rglob('*'):
            if p.is_file() and 'build' not in p.relative_to(base).parts and '.gradle' not in p.parts:
                source[p.relative_to(ROOT).as_posix()]=sha(p)
    temp=folder/'temp';temp.mkdir()
    env=os.environ.copy()
    for k in ('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS'):env.pop(k,None)
    env.update(JAVA_HOME=str(JDK21),GRADLE_USER_HOME='E:/CodexTemp/Gradle/QiZhang_Games',TEMP=str(temp),TMP=str(temp),CI='true')
    env['PATH']=str(JDK21/'bin')+';'+env['PATH']
    env['JAVA_TOOL_OPTIONS']='-Djava.io.tmpdir='+temp.as_posix()+' -Dqzguard.testDir='+(folder/'core-tests').as_posix()+' -Djavax.net.ssl.trustStoreType=Windows-ROOT -Djavax.net.ssl.trustStore=NONE'
    env['GRADLE_OPTS']='-Dorg.gradle.internal.http.connectionTimeout=15000 -Dorg.gradle.internal.http.socketTimeout=15000'
    cmd=[str(PROJECT/'gradlew.bat'),'--no-daemon','--max-workers=1','--stacktrace','--console=plain','--project-cache-dir',str(folder/'project-cache'),'-Dorg.gradle.jvmargs=-Xmx1536M -Dfile.encoding=UTF-8','-Porg.gradle.java.installations.paths='+JDK17.as_posix()+','+JDK21.as_posix(),'-Porg.gradle.java.installations.auto-detect=false','-Porg.gradle.java.installations.auto-download=false','-PqzRuntimeRoot='+(folder/'runtime').as_posix(),'build']
    result={'schemaVersion':1,'minecraft':'1.19.2','candidateVersion':VERSION,'attempt':attempt,'startedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':cmd,'workingDirectory':str(PROJECT),'env':{k:env[k] for k in ('JAVA_HOME','GRADLE_USER_HOME','TEMP','TMP','CI','JAVA_TOOL_OPTIONS','GRADLE_OPTS')},'javaToolchain':str(JDK17),'availablePhysicalGiB':free,'minimumFreeGiB':5,'sourceSha256':source,'oldArtifactSha256':old,'priorCandidates':prior,'minecraftRuntimeExecuted':False,'driverSha256':sha(__file__)}
    shutil.copyfile(__file__,folder/'build-attempt.py')
    save(folder/'plan.json',result)
    print(json.dumps({'attempt':attempt,'starting':True,'freeGiB':round(free,3),'log':str(folder/'gradle.log')}),flush=True)
    started=time.monotonic()
    with (folder/'gradle.log').open('xb') as log:
        proc=subprocess.Popen(cmd,cwd=PROJECT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        result['ownedPid']=proc.pid;save(folder/'plan.json',result)
        code=proc.wait()
    logtext=(folder/'gradle.log').read_text('utf-8',errors='replace')
    result.update(exitCode=code,buildSuccessful=code==0 and 'BUILD SUCCESSFUL' in logtext,elapsedSeconds=time.monotonic()-started,finishedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),logSha256=sha(folder/'gradle.log'),oldArtifactsUnchanged=all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in old.items()))
    result['artifacts']=[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in PROJECT.glob('*/build/libs/*'+VERSION+'.jar')]
    save(folder/'result.json',result)
    print(json.dumps({k:result[k] for k in ('attempt','exitCode','buildSuccessful','elapsedSeconds','oldArtifactsUnchanged','artifacts')}),flush=True)
    return 0 if result['buildSuccessful'] and result['oldArtifactsUnchanged'] else 1
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',required=True);args=parser.parse_args();sys.exit(run(args.attempt))
