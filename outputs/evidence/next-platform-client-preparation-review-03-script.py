import copy,hashlib,importlib.util,json,os,re,struct,sys,tempfile,unittest.mock,zipfile,zlib
from pathlib import Path
ROOT=Path('E:/Codex_work/QiZhangVerdict');BASE=Path('E:/CodexTemp/QiZhangVerdict/next-platforms')
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'scripts'))
import next_client_smoke as qa
import next_client_runtime as runtime
review=BASE/'client-preparation-review-03';review.mkdir(exist_ok=False)
checks=[]
def check(name,condition):
 assert condition,name;checks.append(name)
def fail_if_process(*args,**kwargs):raise AssertionError('Preparation review must not launch any process')
with unittest.mock.patch.object(qa.subprocess,'Popen',fail_if_process),unittest.mock.patch.object(qa.subprocess,'run',fail_if_process):
 check('current Minecraft name satisfies ASCII length boundary',runtime.validate_player_name(runtime.PLAYER)==runtime.PLAYER)
 check('name and offline UUID remain coupled',str(__import__('uuid').UUID(bytes=bytes(runtime.identity)))==runtime.PLAYER_UUID)
 for invalid in ('VerdictNextClient','','a'*17,'bad-name','玩家','x\n'):
  try:runtime.validate_player_name(invalid)
  except ValueError:pass
  else:raise AssertionError('Invalid Minecraft username accepted')
 check('overlong empty nonASCII and invalid-character names rejected',True)
 for accepted in ('a','A'*16,'Verdict_1'):
  assert runtime.validate_player_name(accepted)==accepted
 check('valid boundary names accepted',True)
 with unittest.mock.patch.object(runtime,'PLAYER','VerdictNextClient'):
  for call in (lambda:runtime.prepare_run('fabric-1.19.2','does-not-exist','does-not-exist',25711),lambda:runtime.client_command('fabric-1.19.2',{},review,25711)):
   try:call()
   except ValueError as error:assert 'Synthetic Minecraft username' in str(error)
   else:raise AssertionError('Unsafe name reached fixture or launch-plan IO')
 check('both prepare and launch validate username before IO',True)
 profiles=[]
 for profile in qa.PROFILES:
  base=qa.base_directory(profile,'base-01');plan=qa.read(base/'base-plan.json');result=qa.read(base/'preparation-result.json')
  check(profile+' preparation explicitly non-runtime',plan['prepared'] and not plan['javaInvoked'] and not plan['runtimeVerified'])
  check(profile+' candidate still exact',qa.sha(plan['guard']['path'])==plan['guard']['sha256'])
  check(profile+' private game state not cloned',not (base/'game').exists() and not (base/'client-game').exists() and not (base/'config').exists())
  for item in plan['seededLibraries']:
   assert qa.sha(item['path'])==item['sha256'] and Path(item['path']).stat().st_size==item['bytes']
  check(profile+' all seeded libraries rehashed',True)
  for item in plan['nativeFiles']:assert qa.sha(item['path'])==item['sha256']
  check(profile+' native DLLs exist and rehashed',bool(plan['nativeFiles']))
  expected='net/fabricmc/loader/impl/launch/knot/KnotClient.class' if profile.startswith('fabric') else ('net/minecraftforge/bootstrap/ForgeBootstrap.class' if profile=='forge-1.20.4' else 'cpw/mods/bootstraplauncher/BootstrapLauncher.class')
  owners=[]
  for entry in plan['classpath']:
   path=Path(entry['path'])
   if not path.exists():continue
   with zipfile.ZipFile(path) as archive:
    if expected in archive.namelist():owners.append(path.name)
  check(profile+' actual official entrypoint present exactly once',len(owners)==1)
  inspection=review/profile;inspection.mkdir()
  if profile=='forge-1.20.4':
   check(profile+' keeps exactly one pending installer-generated client',len(plan['pendingInstallerGeneratedLibraries'])==1)
   check(profile+' uses Forge49 target',plan['loaderArguments']['game']==['--launchTarget','forge_client'])
   check(profile+' excludes duplicate vanilla client',not any(x.get('name')=='official-vanilla-client' for x in plan['classpath']))
   try:runtime.client_command(profile,plan,inspection,qa.PORTS[profile])
   except ValueError as error:check(profile+' cannot launch missing generated client',str(error).startswith('Missing exact classpath'))
   else:raise AssertionError('Uninstalled Forge49 client unexpectedly ready')
  else:
   command=runtime.client_command(profile,plan,inspection,qa.PORTS[profile])
   check(profile+' all placeholders resolved',not any('${' in arg for arg in command))
   check(profile+' official JVM native/classpath args',command.count('-cp')==1 and any(arg.startswith('-Djava.library.path=') for arg in command))
   if plan['minecraft']=='1.19.2':check(profile+' legacy autoconnect', '--server' in command and '--port' in command and '--quickPlayMultiplayer' not in command)
   else:check(profile+' quickplay autoconnect','--quickPlayMultiplayer' in command and '--server' not in command)
  profiles.append({'profile':profile,'basePlan':qa.record(base/'base-plan.json'),'preparationResult':qa.record(base/'preparation-result.json'),
                   'candidate':plan['guard'],'officialEntrypointOwner':owners[0],'classpathCount':len(plan['classpath']),
                   'seededLibraryCount':plan['seededLibraryCount'],'nativeFileCount':len(plan['nativeFiles']),
                   'assets':plan['assets'],'pendingInstallerGeneratedLibraries':plan['pendingInstallerGeneratedLibraries'],
                   'installClientCommand':['python','-B','scripts/next_client_smoke.py','install-client',profile,'--base-name','base-01'],
                   'futureRunCommand':['python','-B','scripts/next_client_smoke.py','run',profile,'--base-name','base-01','--run-name','candidate-0.3.0-dev-01','--port',str(qa.PORTS[profile])]})
 check('Maven classifiers preserve distinct coordinates',qa.coordinate({'name':'org.lwjgl:lwjgl:3.3.1:natives-windows'})[0]!=qa.coordinate({'name':'org.lwjgl:lwjgl:3.3.1'})[0])
 check('Neo @jar does not become part of version/path','@jar' not in qa.coordinate({'name':'net.neoforged.fancymodloader:loader:2.0.17@jar'})[1])
 for unsafe in ('../old','x/y','x\\y'):
  try:qa.safe_name(unsafe)
  except ValueError:pass
  else:raise AssertionError('Unsafe fixture name accepted')
 check('fixture names reject traversal',True)
 item=review/'immutable-test';item.write_bytes(b'good')
 try:qa.fetch_verified(item,'https://example.invalid',hashlib.sha1(b'evil').hexdigest(),4)
 except ValueError:pass
 else:raise AssertionError('Same-size wrong-hash asset accepted')
 check('assets verify hash even when size matches',item.read_bytes()==b'good')
 server=review/'synthetic-server';state=server/'config/qizhangverdict/accounts.state';state.parent.mkdir(parents=True)
 state.write_text('D\t00000000-0000-3000-8000-000000000000\t'+'a'*64+'\n')
 check('other UUID device association is rejected',not runtime.uuid_has_device_shape(server))
 state.write_text('D\t'+runtime.PLAYER_UUID+'\t'+'a'*64+'\n')
 check('exact synthetic UUID association is accepted',runtime.uuid_has_device_shape(server))

 game=review/'synthetic-game';(game/'config/qizhangverdict').mkdir(parents=True)
 client_log=review/'synthetic-client.log';client_log.write_text('')
 scope='c'*64;raw_id='11111111-2222-3333-8444-555555555555'
 (state.parent/'server-id.txt').write_text(scope)
 expected=hashlib.sha256(('QiZhangVerdict|'+scope+'|'+raw_id).encode()).hexdigest()
 def state_value(value):state.write_text('D\t'+runtime.PLAYER_UUID+'\t'+value+'\n')
 with unittest.mock.patch.object(runtime,'windows_installation_id',lambda:raw_id):
  state_value('a'*64)
  shape_only=runtime.device_association(server,game,client_log)
  check('valid UUID and 64hex shape alone never proves scoped match',shape_only['uuidShapeAssociation'] and not shape_only['expectedDigestMatch'])
  state_value(expected)
  matched=runtime.device_association(server,game,client_log)
  check('actual algorithm recomputation matches exactly one row',matched['expectedDigestMatch'] and matched['expectedDigestMatchCount']==1 and matched['matchingUuidDeviceRowCount']==1)
  check('system installation source kind is explicit',matched['installationSourceKind']=='windows-machineguid')
  check('comparison result contains no private ID scope or digest',all(value not in json.dumps(matched) for value in (raw_id,scope,expected)))
  (state.parent/'server-id.txt').write_text('d'*64)
  check('different server scope rejects previous expected digest',not runtime.device_association(server,game,client_log)['expectedDigestMatch'])
  (state.parent/'server-id.txt').write_text(scope)
  state.write_text(state.read_text()*2)
  check('duplicate matching UUID rows fail independent association',not runtime.device_association(server,game,client_log)['expectedDigestMatch'])
  fallback='66666666-7777-3888-8999-000000000000'
  fallback_path=game/'config/qizhangverdict/installation-id.txt';fallback_path.write_text(fallback)
  fallback_expected=hashlib.sha256(('QiZhangVerdict|'+scope+'|'+fallback).encode()).hexdigest()
  state_value(fallback_expected)
  check('unconfirmed fallback file is not used when client reports system source',not runtime.device_association(server,game,client_log)['expectedDigestMatch'])
  client_log.write_text('[QiZhangVerdict] Device report uses a local random installation ID fallback; it is not hardware attestation.\n')
  fallback_result=runtime.device_association(server,game,client_log)
  check('explicit client fallback selects local ID despite available registry',fallback_result['expectedDigestMatch'] and fallback_result['installationSourceKind']=='local-random-fallback')
  check('fallback result contains no private values',all(value not in json.dumps(fallback_result) for value in (fallback,scope,fallback_expected)))
  fallback_path.write_text('invalid')
  check('invalid fallback ID fails closed',not runtime.device_association(server,game,client_log)['expectedDigestMatch'])
 def chunk(kind,payload):return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
 png=review/'synthetic-structure-only.png';png.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',640,360,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\x00'+b'\x00'*640*3)*360))+chunk(b'IEND',b''))
 result=runtime.png_record(png);check('valid bytes never imply visual PASS',result['manualVisualReviewPassed'] is None)
 raw=bytearray(png.read_bytes());raw[-1]^=1;png.write_bytes(raw)
 try:runtime.png_record(png)
 except AssertionError:pass
 else:raise AssertionError('Corrupt PNG accepted')
 check('PNG CRC corruption is rejected',True)
for file in ('scripts/next_client_smoke.py','scripts/next_client_runtime.py'):
 compile((ROOT/file).read_text('utf-8'),file,'exec');(review/Path(file).name).write_bytes((ROOT/file).read_bytes())
summary={'schemaVersion':1,'prepared':True,'staticReviewPassed':True,'staticChecks':checks,'staticCheckCount':len(checks),
         'javaInvoked':False,'installersExecuted':False,'minecraftRuntimeExecuted':False,'formalAcceptancePassed':False,
         'profiles':profiles,'helpers':[qa.record(ROOT/file) for file in ('scripts/next_client_smoke.py','scripts/next_client_runtime.py')],
         'boundary':'Official inputs/assets and launch-plan inspection only; Forge/Neo client installers and successful game/client/visual acceptance remains unexecuted; candidate01 pre-login failure is preserved separately.',
         'reviewScript':qa.record(__file__)}
qa.save_new(review/'result.json',summary)
print(json.dumps({'report':str(review/'result.json'),'sha256':qa.sha(review/'result.json'),'checks':len(checks),'profiles':len(profiles),'javaInvoked':False}))
