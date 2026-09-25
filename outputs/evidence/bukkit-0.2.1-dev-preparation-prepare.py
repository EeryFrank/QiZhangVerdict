# SPDX-License-Identifier: GPL-3.0-only
"""Pure file preparation. Does not execute Java, Node, installers or servers."""
from pathlib import Path
import ast, datetime, hashlib, json, re, shutil, stat, subprocess

ROOT=Path('E:/Codex_work/QiZhangVerdict')
BASE=Path(__file__).resolve().parent
OLD=Path('E:/CodexTemp/QiZhangGuard')
GUARD=ROOT/'bukkit/build/libs/qizhangverdict-bukkit-0.2.1-dev.jar'
EXPECTED='9849a60374ea1bb18aae2af0ee479593312437a9665b803a3f847a07c570b2c8'
NODE=Path('E:/CodexTemp/Codex/RuntimeCache/codex-primary-runtime/dependencies/node/bin/node.exe')
DEFAULT={'limits.max-online-per-ip':'3','limits.max-online-per-ip-device':'1','limits.max-accounts-per-ip':'5','limits.account-window-hours':'720','limits.attempts-per-minute':'20','ip.allow':'','ip.deny':'','companion.required':'true','companion.timeout-seconds':'20','device.required':'true','vm.action':'DENY','blacklist.action':'DENY','sanctions.on-deny':'BAN'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def info(p):return {'path':str(p),'sha256':digest(p),'bytes':p.stat().st_size}
def ordinary(p):
    s=p.lstat();assert not p.is_symlink() and not getattr(s,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0)
    assert p.is_file() or p.is_dir()
assert digest(GUARD)==EXPECTED and GUARD.stat().st_size==74976
history=json.loads((ROOT/'outputs/bukkit-validation-0.2.0-test.1.json').read_text('utf-8'))
servers=json.loads((OLD/'downloads/servers.json').read_text('utf-8'))
for p in [BASE/'prepare.py',BASE/'run_prepared.py']:ast.parse(p.read_text('utf-8'))
ready=[]
for version,port,java in [('1.20.1',25685,Path('E:/CodexTemp/mods-danzi/java/jdk-17.0.20.1+1-jre/bin/java.exe')),('1.21.1',25686,Path('D:/Java/jdk-21/bin/java.exe'))]:
    folder=BASE/('purpur-'+version+'-full-01')
    assert not folder.exists(),'Never overwrite a prepared or executed attempt'
    server=next(x for x in servers if x['version']==version)
    previous=next(x for x in history['modernBaseRuns'] if x['minecraft']==version)
    assert server['sha256']==previous['server']['sha256'] and digest(Path(server['path']))==server['sha256']
    assert Path(server['path']).stat().st_size==server['size']==previous['server']['bytes']
    folder.mkdir()
    inputs=[]
    def copy(source,target):
        source=Path(source);ordinary(source);dest=folder/target;dest.parent.mkdir(parents=True,exist_ok=True)
        assert not dest.exists();shutil.copyfile(source,dest);assert digest(source)==digest(dest)
        inputs.append({'source':str(source),'target':target,'sha256':digest(dest),'bytes':dest.stat().st_size})
    copy(GUARD,'plugins/'+GUARD.name)
    copy(server['path'],'server.jar')
    bootstrap=OLD/'runtime'/(version+'-startup')
    for name in ['cache','libraries','versions']:
        source=bootstrap/name;ordinary(source)
        for item in sorted(source.rglob('*')):
            ordinary(item)
            if item.is_file():copy(item,name+'/'+item.relative_to(source).as_posix())
    for name in ['runtime_smoke.py','protocol_smoke.cjs','protocol_disconnect_observer.cjs']:
        copy(ROOT/'scripts'/name,'qa/'+name)
    copy(OLD/'bot/package-lock.json','qa/package-lock.json')
    copy(ROOT/'core/src/main/java/cn/qizhang/guard/core/GuardConfig.java','qa/GuardConfig-source.java')
    generator=json.dumps({'layers':[{'block':'minecraft:bedrock','height':1},{'block':'minecraft:stone','height':60},{'block':'minecraft:dirt','height':2},{'block':'minecraft:grass_block','height':1}],'biome':'minecraft:plains'},separators=(',',':'))
    properties=f'server-ip=127.0.0.1\nserver-port={port}\nonline-mode=false\nenforce-secure-profile=false\nnetwork-compression-threshold=256\nspawn-protection=0\nview-distance=2\nsimulation-distance=2\nmax-players=20\nlevel-type=minecraft:flat\ngenerator-settings={generator}\ngenerate-structures=false\nlevel-seed=12955\n'
    for name,data in [('server.properties',properties),('eula.txt','eula=true\n')]:
        (folder/name).write_text(data,encoding='utf-8',newline='\n')
        inputs.append({'source':'generated isolated QA configuration','target':name,'sha256':digest(folder/name),'bytes':(folder/name).stat().st_size})
    (folder/'runtime-temp').mkdir()
    dependencies={}
    for name in ['minecraft-protocol','minecraft-data','protodef']:
        package=OLD/'bot/node_modules'/name/'package.json';value=json.loads(package.read_bytes());dependencies[name]={'version':value['version'],'packageJsonPath':str(package),'packageJsonSha256':digest(package)}
    assert dependencies['minecraft-protocol']['version']=='1.66.2'
    data={'schemaVersion':1,'preparedOnly':True,'javaStarted':False,'createdUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'minecraft':version,'mode':'full','port':port,'host':'127.0.0.1','networkCompressionThreshold':256,'guard':{'filename':GUARD.name,**info(GUARD)},'server':server,'java':str(java),'node':str(NODE),'externalExecutables':[info(java),info(NODE)],'nodeModules':str(OLD/'bot/node_modules'),'nodeLock':info(OLD/'bot/package-lock.json'),'dependencies':dependencies,'expectedDefaultPolicy':DEFAULT,'expectedCases':previous['cases'],'expectedCaseCount':26,'policyDisclosure':{'firstStartup':'No plugin data or properties copied. Runner verifies all 13 generated defaults before protocol starts.','protocolBaseOverrides':{'limits.max-accounts-per-ip':'5 -> 100','limits.attempts-per-minute':'20 -> 1000','companion.timeout-seconds':'20 -> 4','vm.action':'DENY -> ALERT'},'namedTestChanges':['command-gate timeout temporarily 10 seconds','CIDR deny 127.0.0.0/8 case','VM policy DENY for known VM / VBS control','max online per IP reduced to 2 for final quota checks'],'unchangedProtection':['companion.required=true','device.required=true','limits.max-online-per-ip-device=1','blacklist.action=DENY','sanctions.on-deny=BAN'],'scope':'Synthetic reports; not strict untouched-policy real-client/real-VM evidence.'},'thirdPartyAnticheatInstalled':False,'antiXrayTestEnabled':False,'commandGateTestEnabled':True,'sourceCommitAtPreparation':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),'inputs':inputs,'runnerSha256':digest(BASE/'run_prepared.py'),'prepareScriptSha256':digest(BASE/'prepare.py'),'doNotCopy':['world','world_nether','world_the_end','plugins/QiZhangVerdict','accounts.state','server-id.txt','ops.json','logs','old server configuration'],'command':['python','-B',str(BASE/'run_prepared.py'),version,'--run-authorized'],'executionPrecondition':'Explicit root Java-slot handoff, physical free >=3.5 GiB, one owned server at a time, fresh unused fixture, port free; Xmx1536M and CREATE_NO_WINDOW.'}
    (folder/'fixture.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert not (folder/'world').exists() and not (folder/'plugins/QiZhangVerdict').exists()
    ready.append({'minecraft':version,'fixture':str(folder),'metadata':info(folder/'fixture.json'),'serverSha256':server['sha256'],'guardSha256':EXPECTED,'inputFileCount':len(inputs),'inputBytes':sum(x['bytes'] for x in inputs),'command':data['command']})
(BASE/'prepared-summary.json').write_text(json.dumps({'preparedOnly':True,'javaExecuted':False,'fixtures':ready},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'preparedOnly':True,'javaExecuted':False,'fixtures':ready}))
