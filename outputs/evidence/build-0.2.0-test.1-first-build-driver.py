import argparse, ctypes, datetime, hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT=Path('E:/Codex_work/QiZhangVerdict')
BASE=Path('E:/CodexTemp/QiZhangVerdict/release-0.2.0-test.1')
VERSION='0.2.0-test.1'
JDK8=Path('E:/CodexTemp/QiZhangVerdict/toolchains/jdk8/jdk8u504-b01')
JDK17=Path('E:/CodexTemp/mods-danzi/minecraft/runtime/java-runtime-gamma/windows-x64/java-runtime-gamma')
JDK21=Path('D:/Java/jdk-21')
TARGETS=['root','1.20.1','1.21.1','1.19.4','1.18.2','1.16.5','1.12.2','1.8.9']
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,data): Path(p).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
def run(target,attempt):
    folder=BASE/'builds'/(target+'-'+attempt); folder.mkdir(parents=True,exist_ok=False)
    project=ROOT if target=='root' else ROOT/'platforms'/target
    java=JDK8 if target in ('1.8.9','1.12.2') else JDK21
    env=os.environ.copy()
    for name in ('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS'): env.pop(name,None)
    gradle_home=Path('E:/CodexTemp/Gradle/QiZhang_Games')
    if target=='1.8.9': gradle_home=Path('E:/CodexTemp/QiZhangVerdict/legacy-build/1.8.9/gradle-user-home')
    env.update(JAVA_HOME=str(java),GRADLE_USER_HOME=str(gradle_home),TEMP=str(folder/'temp'),TMP=str(folder/'temp'))
    (folder/'temp').mkdir()
    env['PATH']=str(java/'bin')+';'+env['PATH']
    env['JAVA_TOOL_OPTIONS']='-Dqzguard.testDir='+str(folder/'core-tests').replace('\\','/')
    if java==JDK21:
        env['JAVA_TOOL_OPTIONS']+=' -Djavax.net.ssl.trustStoreType=Windows-ROOT -Djavax.net.ssl.trustStore=NONE'
    env['GRADLE_OPTS']='-Dorg.gradle.internal.http.connectionTimeout=15000 -Dorg.gradle.internal.http.socketTimeout=15000'
    wrapper=project/'gradlew.bat'
    if target=='1.19.4': wrapper=ROOT/'gradlew.bat'
    if target=='1.8.9': wrapper=Path('E:/CodexTemp/QiZhangVerdict/legacy-build/1.8.9/tools/gradle-2.7/bin/gradle.bat')
    cmd=[str(wrapper),'--no-daemon','--max-workers=1','--stacktrace','-Dorg.gradle.jvmargs=-Xmx1536M -Dfile.encoding=UTF-8']
    if target!='1.8.9': cmd+=['--console=plain','--project-cache-dir',str(folder/'project-cache')]
    if target not in ('1.8.9','1.12.2'):
        cmd+=['-Porg.gradle.java.installations.paths='+','.join(str(x).replace('\\','/') for x in (JDK8,JDK17,JDK21)),
              '-Porg.gradle.java.installations.auto-detect=false','-Porg.gradle.java.installations.auto-download=false']
    cmd+=['-PqzRuntimeRoot='+str(folder/'runtime').replace('\\','/')]
    if target=='1.8.9': cmd+=['setupCIWorkspace']
    cmd+=['build']
    if target in ('1.20.1','1.21.1','1.19.4','1.18.2'): cmd+=[':fabric:commandParserSmoke']
    class Mem(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ['totalPhysical','availablePhysical','totalPageFile','availablePageFile','totalVirtual','availableVirtual','availableExtendedVirtual']]
    mem=Mem();mem.length=ctypes.sizeof(mem)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
    free=mem.availablePhysical/(1024**3)
    if free<3.5: raise RuntimeError('Build resource gate: only %.3f GiB available'%free)
    old={str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob('build/libs/qizhangverdict-*.jar') if VERSION not in p.name}
    sources={str(p.relative_to(ROOT)):sha(p) for base in [ROOT/'core/src',ROOT/'client-common/src',ROOT/'platforms'] for p in base.rglob('*.java') if 'build' not in p.parts}
    sources[str((project/'build.gradle').relative_to(ROOT))]=sha(project/'build.gradle')
    receipt={'target':target,'version':VERSION,'startedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':cmd,'javaHome':str(java),'gradleUserHome':str(gradle_home),'sourceSha256':sources,'availablePhysicalGiB':free,'oldArtifactSha256':old,'gameStarted':False}
    save(folder/'plan.json',receipt)
    print(json.dumps({'starting':target,'log':str(folder/'gradle.log'),'freeGiB':round(free,3)}),flush=True)
    with (folder/'gradle.log').open('xb') as log:
        process=subprocess.Popen(cmd,cwd=project,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        code=process.wait()
    text=(folder/'gradle.log').read_text('utf-8',errors='replace')
    preserved=all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in old.items())
    receipt.update(exitCode=code,buildSuccessful=code==0 and 'BUILD SUCCESSFUL' in text,finishedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),logSha256=sha(folder/'gradle.log'),oldArtifactsUnchanged=preserved)
    jars=list((ROOT/'bukkit/build/libs').glob('*'+VERSION+'.jar')) if target=='root' else list(project.glob('*/build/libs/*'+VERSION+'.jar'))
    receipt['artifacts']=[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)} for p in jars]
    save(folder/'result.json',receipt)
    print(json.dumps({'target':target,'exitCode':code,'buildSuccessful':receipt['buildSuccessful'],'oldArtifactsUnchanged':preserved,'artifacts':receipt['artifacts']}),flush=True)
    return code if code else (0 if preserved and receipt['buildSuccessful'] else 1)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--target',choices=TARGETS);parser.add_argument('--attempt',default='01');args=parser.parse_args()
    for target in ([args.target] if args.target else TARGETS):
        result=run(target,args.attempt)
        if result: sys.exit(result)
