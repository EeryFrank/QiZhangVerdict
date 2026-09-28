from pathlib import Path
import datetime, hashlib, json, re, tomllib, zipfile
ROOT = Path('E:/Codex_work/QiZhangVerdict')
MOD = ROOT / 'platforms/1.20.6/forge'
PREP = Path('E:/CodexTemp/QiZhangVerdict/compat-1.20.6/forge-preparation-01')
OUT = Path(__file__).parent
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks = []
def check(name, value):
    assert value, name
    checks.append({'name': name, 'passed': True})
files = sorted(p for p in MOD.rglob('*') if p.is_file())
check('No generated build or cache trees', not any(p.relative_to(MOD).parts[0] in ('build', '.gradle') for p in files))
settings = (ROOT / 'platforms/1.20.6/settings.gradle').read_text('utf-8')
includes = [x for line in settings.splitlines() if line.strip().startswith('include ') for x in re.findall(r"['\"]([^'\"]+)['\"]", line)]
check('Parent includes only Fabric and NeoForge', includes == ['fabric', 'neoforge'])
b = (MOD / 'build.gradle').read_text('utf-8')
check('Standalone FG6 and component version pins', "version '6.0.54'" in b and "version = '0.5.0-dev'" in b)
check('Official runtime mappings and no reobf', "mappings channel: 'official', version: '1.20.6'" in b and 'reobf = false' in b)
check('Official combined output arrangement', 'it.output.resourcesDir = destination' in b and 'it.java.destinationDirectory = destination' in b)
check('Java21 and GPL resource inclusion', 'options.release = 21' in b and 'gradle/license-resources.gradle' in b and 'withSourcesJar()' in b)
check('All required contracts depend from check', all("tasks.named('"+t+"')" in b for t in ('commandParserSmoke', 'payloadCodecSmoke', 'connectionDispatchSmoke')))
check('No ignored failures or disabled tests', not re.search(r'ignoreFailures\s*=\s*true|enabled\s*=\s*false|onlyIf|failOnNoDiscoveredTests\s*=\s*false', b))
check('Smoke runtime working directory outside project', 'workingDir = new File(runtimeRoot, taskName)' in b and 'E:/CodexTemp/' in b)
meta = tomllib.loads((MOD/'src/main/resources/META-INF/mods.toml').read_text('utf-8'))
check('Exact game and Forge descriptors', meta['loaderVersion']=='[0,)' and meta['license']=='GPL-3.0-only' and [x['versionRange'] for x in meta['dependencies']['qizhangverdict']]==['[50.2.0]', '[1.20.6]'])
mix = json.loads((MOD/'src/main/resources/qizhangverdict.mixins.json').read_text('utf-8'))
check('Required common command gate without Fabric refmap', mix['required'] and mix['injectors']['defaultRequire']==1 and mix['mixins']==['CommandGate1206Mixin'] and 'refmap' not in mix)
check('Official 1.20.6 pack format', json.loads((MOD/'src/main/resources/pack.mcmeta').read_text('utf-8'))['pack']['pack_format']==32)
mdk = PREP/'inputs/forge-1.20.6-50.2.0-mdk.zip'
check('Fixed official MDK SHA256', sha(mdk)=='de036a47e541d309a8158449ffdf846039ee79852fcf52e2af969cc591295683')
with zipfile.ZipFile(mdk) as z:
    check('Wrapper script and jar match original MDK bytes', all((MOD/n).read_bytes()==z.read(n) for n in ('gradlew','gradlew.bat','gradle/wrapper/gradle-wrapper.jar')))
    check('Original MDK notices retained', (MOD/'third-party/forge-mdk-LICENSE.txt').read_bytes()==z.read('LICENSE.txt') and (MOD/'third-party/forge-mdk-CREDITS.txt').read_bytes()==z.read('CREDITS.txt'))
properties = (MOD/'gradle/wrapper/gradle-wrapper.properties').read_text('utf-8')
check('Gradle8.12.1 official distribution checksum pin', 'gradle-8.12.1-bin.zip' in properties and 'distributionSha256Sum=8d97a97984f6cbd2b85fe4c60a743440a347544bf18818048e611f5288d46c94' in properties)
with zipfile.ZipFile(MOD/'gradle/wrapper/gradle-wrapper.jar') as z:
    check('Wrapper Apache2 notice retained', z.read('META-INF/LICENSE')==(MOD/'third-party/gradle-wrapper-LICENSE.txt').read_bytes())
main = (MOD/'src/main/java/cn/qizhang/guard/forge/GuardForge.java').read_text('utf-8')
client = (MOD/'src/main/java/cn/qizhang/guard/forge/GuardForgeClient.java').read_text('utf-8')
check('Uses Forge50 direction and inbound phase APIs', all(x in main for x in ('context.isServerSide()', 'context.isClientSide()', 'getInboundProtocolInfo()', 'protocol.id() == ConnectionProtocol.PLAY')) and 'getDirection(' not in main)
check('Captures and rechecks active server player connection', all(x in main for x in ('origin.getPacketListener() == listener','player.connection == listener','player.connection.getConnection() == origin','getPlayer(player.getUUID()) == player')))
check('No common client implementation linkage', 'net.minecraft.client.' not in main and 'GuardForgeClient' not in main)
check('Client-only event bridge and response identity check', 'value = Dist.CLIENT' in client and '@SubscribeEvent' in client and 'origin.getPacketListener(), origin.isConnected()' in client and 'if (current(client, origin, listener)) channel.send' in client)
dispatch = (MOD/'src/main/java/cn/qizhang/guard/forge/ConnectionDispatch.java').read_text('utf-8')
smoke = (MOD/'src/smoke/java/cn/qizhang/guard/forge/ConnectionDispatchSmoke.java').read_text('utf-8')
check('Exact production helper checks local and transport listener', 'originListener == currentListener' in dispatch and 'originListener == transportListener' in dispatch)
check('Fifteen unexecuted production dispatch assertions supplied', len(re.findall(r'\bcheck\(',smoke))-1==15)
raw = (MOD/'src/main/java/cn/qizhang/guard/forge/ForgeWire.java').read_text('utf-8')
payload = (MOD/'src/smoke/java/cn/qizhang/guard/forge/ForgePayloadSmoke.java').read_text('utf-8')
check('Bounded owned raw bytes and real EventNetworkChannel encoder test', 'MAX_BYTES = 30_000' in raw and 'source.clone()' in raw and 'source.getBytes(source.readerIndex(), result)' in raw and 'channel.encode(encoded, outgoing)' in payload)
java = [p for p in files if p.suffix=='.java']
for path in java:
    code=re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])\'', '', path.read_text('utf-8'), flags=re.S)
    stack=[]
    for c in code:
        if c in '({[': stack.append(c)
        elif c in ')}]': assert stack and '({['[')}]'.index(c)]==stack.pop(), str(path)
    assert not stack, str(path)
check('Six Java files have balanced lexical delimiters, not compiled',len(java)==6)
for p in (MOD/'README.md',MOD/'THIRD_PARTY.md'):
    for link in re.findall(r'\]\(([^)]+)\)',p.read_text('utf-8')):
        if not link.startswith('http'): assert (p.parent/link).resolve().is_file(),link
check('Own-module Markdown links resolve',True)
report={'schemaVersion':1,'status':'SOURCE_FROZEN_STATIC_CHECKS_ONLY','checkedAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'module':'platforms/1.20.6/forge','minecraft':'1.20.6','componentVersion':'0.5.0-dev','forge':'50.2.0','forgeGradle':'6.0.54','gradle':'8.12.1','javaMajor':21,
    'javaInvoked':False,'gradleInvoked':False,'compiled':False,'runtimeVerified':False,'checks':checks,'staticCheckCount':len(checks),
    'files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in files],'fileCount':len(files),
    'pendingChecks':['commandParserSmoke actual Forge initialization','payloadCodecSmoke actual EventNetworkChannel','connectionDispatchSmoke 15 actual production-helper assertions','dedicated/client runtime and required Mixin injection'],
    'officialPreparation':{'path':str(PREP/'forge-adapter-preparation.json'),'sha256':sha(PREP/'forge-adapter-preparation.json')},
    'reviewTool':{'path':str(Path(__file__)),'sha256':sha(__file__)},
    'preflightNote':'An initial inventory check incorrectly used the substring forge to test parent exclusion and also matched neoforge; exact include names are now checked. No Java/build was attempted.'}
with (OUT/'result.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'result':str(OUT/'result.json'),'sha256':sha(OUT/'result.json'),'staticChecks':len(checks),'files':len(files),'javaInvoked':False}))
