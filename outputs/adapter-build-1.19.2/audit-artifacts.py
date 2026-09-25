import argparse,hashlib,json,os,re,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path('E:/Codex_work/QiZhangVerdict');BASE=Path('E:/CodexTemp/QiZhangVerdict/next-platforms/1.19.2')
JDK17=Path('E:/CodexTemp/mods-danzi/minecraft/runtime/java-runtime-gamma/windows-x64/java-runtime-gamma')
JDK21=Path('D:/Java/jdk-21')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf-8'))
def check(loader,artifact):
 p=ROOT/artifact['path'];assert sha(p)==artifact['sha256']
 with zipfile.ZipFile(p) as z:
  assert z.testzip() is None
  for name in ('LICENSE','NOTICE'):assert z.read(name)==(ROOT/name).read_bytes()
  manifest=z.read('META-INF/MANIFEST.MF').decode('utf-8')
  assert 'License: GPL-3.0-only' in manifest
  classes={n:int.from_bytes(z.read(n)[6:8],'big') for n in z.namelist() if n.endswith('.class')}
  assert classes and set(classes.values())=={61},set(classes.values())
  mixin=read_json(z.read('qizhangverdict.mixins.json'))
  assert mixin['required'] and mixin['injectors']['defaultRequire']==1
  assert mixin['mixins']==['CommandGate119Mixin']
  mixins=[n for n in classes if '/mixin/' in n]
  assert mixins==['cn/qizhang/guard/minecraft/mixin/CommandGate119Mixin.class']
  refmap=read_json(z.read('qizhangverdict.refmap.json'))
  gate=refmap['mappings']['cn/qizhang/guard/minecraft/mixin/CommandGate119Mixin']
  assert 'performCommand(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)I' in gate
  assert gate['performCommand(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)I'].endswith('(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)I')
  if loader=='fabric':
   metadata=read_json(z.read('fabric.mod.json'));assert metadata['version']=='0.3.0-dev' and metadata['license']=='GPL-3.0-only'
   assert metadata['depends']['minecraft']=='1.19.2'
  else:
   import tomllib
   metadata=tomllib.loads(z.read('META-INF/mods.toml').decode('utf-8'));assert metadata['mods'][0]['version']=='0.3.0-dev' and metadata['license']=='GPL-3.0-only'
   assert 'MixinConfigs: qizhangverdict.mixins.json' in manifest
   assert read_json(z.read('pack.mcmeta'))['pack']['pack_format']==9
  result={'artifact':artifact,'loader':loader,'crcPassed':True,'rootLicenseNoticeExact':True,'manifestGpl':True,'descriptorVersion':'0.3.0-dev','javaClassMajor':61,'classCount':len(classes),'mixinRequired':True,'mixinClass':mixins[0],'mixinTargetRefmap':gate,'minecraftRuntimeExecuted':False}
 folder=BASE/'artifact-core'/loader
 cmd=[sys.executable,str(ROOT/'scripts/artifact_core_checks.py'),'--jar',str(p),'--sha256',artifact['sha256'],'--java',str(JDK17/'bin/java.exe'),'--javac',str(JDK21/'bin/javac.exe'),'--output',str(folder)]
 log=BASE/('artifact-core-'+loader+'.log')
 environment=os.environ.copy();temporary=BASE/'artifact-core-temp';temporary.mkdir(exist_ok=True)
 environment.update(TEMP=str(temporary),TMP=str(temporary))
 with log.open('xb') as out: proc=subprocess.run(cmd,cwd=ROOT,env=environment,stdout=out,stderr=subprocess.STDOUT,timeout=360)
 assert proc.returncode==0,(loader,proc.returncode)
 core=read(folder/'result.json');assert core['passed'] and core['artifactUnchanged']
 for name,pattern,count in [('security',r'^PASS (\d+):',57),('catalog',r'^PASS rule (\d+):',37),('catalog',r'^PASS control (\d+):',3)]:
  text=(folder/(name+'.log')).read_text('utf-8');assert list(map(int,re.findall(pattern,text,re.M)))==list(range(1,count+1))
 result['exactJarCoreChecks']={'passed':True,'security':57,'catalogRules':37,'catalogControls':3,'javaRuntime':str(JDK17),'report':str(folder/'result.json'),'sha256':sha(folder/'result.json')}
 return result
def read_json(data):return json.loads(data)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--attempt',required=True);args=parser.parse_args()
 receipt=read(BASE/'builds'/args.attempt/'result.json');assert receipt['buildSuccessful'] and receipt['oldArtifactsUnchanged']
 assert len(receipt['artifacts'])==2
 results=[]
 for a in receipt['artifacts']:
  loader='fabric' if '/fabric/' in a['path'] else 'forge';results.append(check(loader,a));print(json.dumps(results[-1]),flush=True)
 report={'schemaVersion':1,'passed':True,'scope':'Static production JAR and Java17 exact-artifact core tests; not Minecraft loader/client acceptance.','checksPerJar':97,'totalExactJarChecks':194,'artifacts':results,'auditorSha256':sha(__file__)}
 (BASE/'artifact-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
