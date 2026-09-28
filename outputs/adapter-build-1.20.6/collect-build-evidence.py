"""Explicit local evidence collector. No Java, network, installer or game invocation."""
from pathlib import Path
import datetime, hashlib, json, re, shutil, struct, tomllib, xml.etree.ElementTree as ET, zipfile

ROOT = Path('E:/Codex_work/QiZhangVerdict')
CACHE = Path('E:/CodexTemp/QiZhangVerdict/compat-1.20.6')
OUT = ROOT / 'outputs/adapter-build-1.20.6'
REPORT = ROOT / 'outputs/adapter-build-1.20.6.json'
DOC = ROOT / 'docs/adapter-1.20.6.md'
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text('utf-8'))
def rec(path):
    path = Path(path)
    return {'path': str(path), 'sha256': digest(path), 'bytes': path.stat().st_size}
def require_record(path, value):
    assert digest(path) == value['sha256'] and Path(path).stat().st_size == value['bytes'], str(path)
def save(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')

assert not OUT.exists() and not REPORT.exists() and not DOC.exists()
final_dir = CACHE / 'builds/all-42-01'
final = read(final_dir / 'result.json')
log = (final_dir / 'console.log').read_text('utf-8', errors='replace')
assert final['exitCode'] == 0 and final['sourcesUnchanged'] and final['previousArtifactsUnchanged']
assert digest(final_dir / 'console.log') == final['logSha256']
assert '23 actionable tasks: 23 executed' in log
assert 'BUILD SUCCESSFUL' in log
for name, sha in final['sourceSha256'].items(): assert digest(ROOT / name) == sha, name
assert len(final['previousArtifacts']) == 20
for item in final['previousArtifacts']: require_record(ROOT / item['path'], item)
for item in final['artifacts']: require_record(ROOT / item['path'], item)

evidence, pending = [], []
def raw(source, name):
    source = Path(source)
    pending.append((source, name, True))
    return 'adapter-build-1.20.6/' + name

attempts = []
for attempt in ('fabric-01', 'neoforge-01', 'all-42-01'):
    folder = CACHE / 'builds' / attempt; value = read(folder / 'result.json')
    assert value['exitCode'] == 0 and digest(folder / 'console.log') == value['logSha256']
    preserved = []
    if attempt != 'all-42-01':
        for item in value['artifacts']:
            original = folder / 'preserved-artifacts' / Path(item['path']).name
            require_record(original, item)
            preserved.append({**rec(original), 'originalBuildPath': item['path'], 'publishedAsEvidence': False})
    attempts.append({'attempt': attempt, 'target': value['target'], 'exitCode': value['exitCode'],
        'elapsedSeconds': value['elapsedSeconds'], 'catalogRuleCount': 42 if attempt == 'all-42-01' else 39,
        'currentCandidateEvidence': attempt == 'all-42-01', 'sourcesUnchangedDuringAttempt': value['sourcesUnchanged'],
        'previous20ArtifactsUnchanged': value['previousArtifactsUnchanged'],
        'result': raw(folder / 'result.json', 'build-' + attempt + '-result.json'),
        'console': raw(folder / 'console.log', 'build-' + attempt + '-console.log'),
        'preservedSupersededArtifacts': preserved})

catalog_path = ROOT / 'catalog/blacklist-extension.tsv'
catalog = [line for line in catalog_path.read_text('utf-8').splitlines() if line and not line.startswith('#')]
assert len(catalog) == 42
catalog_file = raw(catalog_path, 'catalog-42.tsv')
artifacts = []
for loader in ('fabric', 'neoforge'):
    item = next(x for x in final['artifacts'] if x['path'].endswith('/qizhangverdict-' + loader + '-1.20.6-0.5.0-dev.jar'))
    source_jar = next(x for x in final['artifacts'] if x['path'].endswith('/qizhangverdict-' + loader + '-1.20.6-0.5.0-dev-sources.jar'))
    jar = ROOT / item['path']
    with zipfile.ZipFile(jar) as z:
        assert z.testzip() is None
        names = z.namelist(); assert len(names) == len(set(names))
        classes = [name for name in names if name.endswith('.class')]
        assert len(classes) == 29 and all(name.startswith('cn/qizhang/guard/') for name in classes)
        assert not any(name.endswith('.jar') or '/test/' in name or 'Smoke.class' in name for name in names)
        assert {int.from_bytes(z.read(name)[6:8], 'big') for name in classes} == {65}
        for name in ('LICENSE', 'NOTICE'): assert z.read(name) == (ROOT / name).read_bytes()
        assert 'License: GPL-3.0-only' in z.read('META-INF/MANIFEST.MF').decode('utf-8')
        mixin = json.loads(z.read('qizhangverdict.mixins.json'))
        assert mixin['required'] and mixin['injectors']['defaultRequire'] == 1
        assert mixin['mixins'] == ['CommandGate1206Mixin']
        if loader == 'fabric':
            descriptor = json.loads(z.read('fabric.mod.json'))
            assert descriptor['version'] == '0.5.0-dev' and descriptor['license'] == 'GPL-3.0-only'
            assert descriptor['depends']['minecraft'] == '1.20.6'
            refmap = json.loads(z.read(mixin['refmap']))
            target = refmap['mappings']['cn/qizhang/guard/minecraft/mixin/CommandGate1206Mixin']['performCommand(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)V']
            assert target == 'Lnet/minecraft/class_2170;method_9249(Lcom/mojang/brigadier/ParseResults;Ljava/lang/String;)V'
        else:
            descriptor = tomllib.loads(z.read('META-INF/neoforge.mods.toml').decode('utf-8'))
            assert descriptor['license'] == 'GPL-3.0-only' and descriptor['loaderVersion'] == '[3,4)'
            assert descriptor['mods'][0]['version'] == '0.5.0-dev'
            assert any(x['modId'] == 'minecraft' and x['versionRange'] == '[1.20.6]' for x in descriptor['dependencies']['qizhangverdict'])
            assert 'refmap' not in mixin and not any('refmap' in name for name in names)
            target = 'net.minecraft.commands.Commands.performCommand(ParseResults,String):void (production Mojang names)'
    with zipfile.ZipFile(ROOT / source_jar['path']) as z: assert z.testzip() is None
    folder = CACHE / 'core-checks' / (loader + '-42-01'); core = read(folder / 'result.json')
    assert core['sha256'] == item['sha256'] and core['bytes'] == item['bytes'] and core['passed'] and core['artifactUnchanged']
    assert core['embeddedCoreClassCount'] == 16 and len(core['runnerClassFiles']) == 4
    for test in core['checks']:
        assert test['passed'] and test['exitCode'] == 0
        require_record(folder / test['log'], test)
        raw(folder / test['log'], 'core-' + loader + '-' + test['log'])
    security = (folder / 'security.log').read_text('utf-8'); cat = (folder / 'catalog.log').read_text('utf-8')
    assert [int(n) for n in re.findall(r'^PASS (\d+):', security, re.M)] == list(range(1, 58))
    assert [int(n) for n in re.findall(r'^PASS rule (\d+):', cat, re.M)] == list(range(1, 43))
    assert [int(n) for n in re.findall(r'^PASS control (\d+):', cat, re.M)] == [1,2,3]
    validation = next(x['validation'] for x in core['checks'] if x['name'] == 'catalog')
    assert (validation['rules'], validation['deny'], validation['alert'], validation['controls']) == (42,38,4,3)
    assert validation['catalogSha256'] == digest(catalog_path)
    artifacts.append({'loader': loader, 'artifact': item, 'sourceJar': source_jar, 'classCount': len(classes),
        'classMajor': 65, 'zipCrcPassed': True, 'embeddedLicenseNoticeExact': True,
        'onlyFirstPartyClasses': True, 'noNestedThirdPartyOrTestClasses': True,
        'embeddedDefaults': {'rules':42,'deny':38,'alert':4},
        'requiredMixin': {'name':'CommandGate1206Mixin','required':True,'defaultRequire':1,'mappedTarget':target,
                          'productionRuntimeInjectionClaimed':False},
        'exactJarCoreChecks': {'security':57,'catalogRules':42,'catalogControls':3,'total':102,
            'passed':True,'javaMajorUsed':21,'guardServiceCodeSourcePinnedToArtifact':True,
            'report':raw(folder/'result.json','core-'+loader+'-result.json')}})

for pattern, count in [(r'^PASS fabric-client-dispatch (\d+):',12),(r'^PASS client-dispatch (\d+):',9)]:
    assert [int(n) for n in re.findall(pattern,log,re.M)] == list(range(1,count+1))
assert '> Task :neoforge:test\n' in log and '> Task :neoforge:test FROM-CACHE' not in log
assert log.count('PlatformContractTest > administratorCommandTree() PASSED') == 1
assert log.count('PlatformContractTest > boundedBukkitCompatiblePayload() PASSED') == 1
assert '> Task :fabric:commandParserSmoke\n' in log and '> Task :fabric:payloadCodecSmoke\n' in log
assert '> Task :fabric:test NO-SOURCE' in log
assert str(final_dir / 'runtime/neoforge-junit/config/fml.toml') in log
xml_path = ROOT / 'platforms/1.20.6/neoforge/build/test-results/test/TEST-cn.qizhang.guard.neoforge.PlatformContractTest.xml'
xml = ET.fromstring(xml_path.read_bytes())
assert [xml.attrib[k] for k in ('tests','skipped','failures','errors')] == ['2','0','0','0']
assert len(xml.findall('testcase')) == 2 and xml.attrib['timestamp'].startswith('2026-09-28T10:49:')
junit = {'schemaVersion':1,'derivedSummary':True,'rawXmlPublished':False,'omittedFields':['hostname'],
    'source':rec(xml_path),'attempt':'all-42-01','actualExecution':True,'tests':2,'failures':0,'errors':0,'skipped':0,
    'timestamp':xml.attrib['timestamp'],'testCases':[dict(x.attrib) for x in xml.findall('testcase')],
    'sourceEvidence':'The two PASSED console lines, non-cached Gradle task and matching XML timestamp were checked together.',
    'fmlWorkingDirectory':str(final_dir/'runtime/neoforge-junit')}
derived_path = CACHE / 'build-report-01/neoforge-junit-summary.json'; save(derived_path,junit)
pending.append((derived_path,'neoforge-junit-summary.json',False))

snapshots = [
 ('scripts/artifact_core_checks.py','artifact_core_checks.py'),
 ('core/src/test/java/cn/qizhang/guard/core/SecurityRegressionTest.java','SecurityRegressionTest.java'),
 ('core/src/test/java/cn/qizhang/guard/core/CatalogCompatibilityTest.java','CatalogCompatibilityTest.java'),
 ('platforms/1.20.6/common/src/smoke/java/cn/qizhang/guard/minecraft/CommandParserSmoke.java','CommandParserSmoke.java'),
 ('platforms/1.20.6/common/src/smoke/java/cn/qizhang/guard/minecraft/PayloadCodecSmoke.java','PayloadCodecSmoke.java'),
 ('platforms/1.20.6/fabric/src/smoke/java/cn/qizhang/guard/fabric/ClientChallengeDispatchSmoke.java','FabricClientChallengeDispatchSmoke.java'),
 ('platforms/1.20.6/neoforge/src/smoke/java/cn/qizhang/guard/neoforge/ClientChallengeDispatchSmoke.java','NeoClientChallengeDispatchSmoke.java'),
 ('platforms/1.20.6/neoforge/src/test/java/cn/qizhang/guard/neoforge/PlatformContractTest.java','PlatformContractTest.java')]
for source,name in snapshots: raw(ROOT/source,name)
raw(CACHE/'core-checks/fabric-42-01/ArtifactOriginCheck.java','ArtifactOriginCheck.java')
raw(Path(__file__),'collect-build-evidence.py')

# Inspect only this explicit public whitelist. Never enumerate client state/worlds.
sensitive = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{15,}|Bearer\s+[A-Za-z0-9._-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|MachineGuid\s+REG_SZ\s+[a-fA-F0-9-]{16,64}|(?m:^[DS]\t[^\r\n]+))')
assert len({name for _,name,_ in pending}) == len(pending)
for source,name,is_raw in pending:
    assert not sensitive.search(source.read_bytes()), name
    assert source.suffix in ('.json','.log','.py','.java','.tsv'), name
OUT.mkdir()
for source,name,is_raw in pending:
    dest=OUT/name; shutil.copyfile(source,dest); assert source.read_bytes()==dest.read_bytes()
    evidence.append({'file':'adapter-build-1.20.6/'+name,'publicFile':dest.relative_to(ROOT).as_posix(),
        'source':str(source),'sha256':digest(dest),'bytes':dest.stat().st_size,
        'rawBytesPreserved':is_raw,'derivedSummary':not is_raw})

report = {'schemaVersion':1,'minecraft':'1.20.6','version':'0.5.0-dev',
 'generatedAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'stage':'BUILD_STATIC_AND_EXACT_JAR_CORE_PASSED_RUNTIME_SEPARATE',
 'passed':True,'buildSuccessful':True,'allAttemptsSuccessful':True,
 'passedScope':'Two final 42-rule production JAR builds, exact packaged-core regressions, platform contract execution and static packaging audit only.',
 'formalAcceptancePassed':False,'serverRuntimeIncluded':False,'renderedClientRuntimeIncluded':False,'tcpRuntimeIncluded':False,
 'versions':{'javaMajor':21,'gradle':'9.2.1','fabricLoom':'1.14.10','fabricLoader':'0.19.5','fabricApi':'0.100.8+1.20.6','neoforge':'20.6.141','modDevGradle':'2.0.147','fancyModLoader':'3.0.45'},
 'buildAttempts':attempts,
 'finalBuild':{'attempt':'all-42-01','exitCode':0,'elapsedSeconds':final['elapsedSeconds'],
    'actionableTasks':23,'tasksExecuted':23,'sourceFileCount':len(final['sourceSha256']),'sourceFilesStillMatch':True,
    'previousArtifactsRehashed':20,'previousArtifactsUnchanged':True,'previousArtifactsRebuilt':False,
    'result':'adapter-build-1.20.6/build-all-42-01-result.json','console':'adapter-build-1.20.6/build-all-42-01-console.log'},
 'artifacts':artifacts,
 'coreAssertions':{'distinctAssertions':102,'security':57,'catalogRules':42,'catalogControls':3,
    'exactFinalArtifacts':2,'exactJarExecutions':204,'sourceCoreExecutionIncluded':False,
    'ruleActions':{'DENY':38,'ALERT':4},'catalogSnapshot':catalog_file,'catalogSha256':digest(catalog_path)},
 'platformChecks':{'fabric':{'actualDispatchAssertions':12,'commandParserSmokeExecuted':True,'payloadCodecSmokeExecuted':True,'standardJUnitTask':'NO-SOURCE'},
    'neoforge':{'actualDispatchAssertions':9,'junitActualExecution':True,'junitFromCache':False,'tests':2,'failures':0,'errors':0,'skipped':0,
      'junitSummary':'adapter-build-1.20.6/neoforge-junit-summary.json','workingDirectory':str(final_dir/'runtime/neoforge-junit')},
    'addedToCoreAssertionCount':False},
 'historyBoundary':'fabric-01 and neoforge-01 passed with 39 rules; their preserved original JARs are historical and are not current 42-rule acceptance. The existing 20 published artifacts were rehashed unchanged, not rebuilt or retested.',
 'securityReview':{'readOnly':True,'newAdapterBlockingFindings':0,'javaRunByReviewer':False,
    'scope':'Static common/entrypoint/handshake/connection ownership/command-gate review against exact official 1.20.6 API sources; not a new runtime result.',
    'unsignedAndSignedVanillaCommandCallsitesTargetSameRequiredMixin':True,
    'clientReportedDeviceSignalsRemainForgeableNotHardwareAttestation':True},
 'publicEvidence':evidence,'publicEvidenceCount':len(evidence),'publicEvidenceBytes':sum(x['bytes'] for x in evidence),
 'privacy':{'explicitFileAllowlist':True,'credentialAndRawIdPatternScanPassed':True,
    'excluded':['Third-party/Minecraft binaries and complete source or mappings','Preserved superseded JAR bytes','JUnit raw XML hostname metadata','Worlds, account/device state and server scope','Installers and runtime launch plans']},
 'warningsPreserved':True,
 'limitations':['Compilation/FML unit-test bootstrap does not prove production server startup or Mixin execution.','No actual player admission, device enforcement, TCP protocol or graphical client acceptance is included.','Catalog entries are not an exhaustive inventory of cheat tools.']}
save(REPORT,report)

f,n=artifacts
doc=f'''# Minecraft 1.20.6 构建候选

Fabric 与 NeoForge 的 `0.5.0-dev` 最终两份成品已通过构建、静态包检查和精确 JAR 核心回归。[构建报告](../outputs/adapter-build-1.20.6.json)列出 {len(evidence)} 份显式公开附件及其原文件哈希。报告只覆盖构建和包内核心；服务器、TCP、真实图形客户端及生产服 Mixin 隔离的验收分别记录，不在这里宣称通过。

| 输入 | 固定版本 |
| --- | --- |
| Minecraft / Java | 1.20.6 / Java 21 |
| Gradle | 9.2.1 |
| Fabric Loom / Loader / API | 1.14.10 / 0.19.5 / 0.100.8+1.20.6 |
| NeoForge / ModDevGradle / FML | 20.6.141 / 2.0.147 / 3.0.45 |
| 首方源码和成品许可证 | GPL-3.0-only |

| 最终成品 | 字节 | SHA-256 |
| --- | ---: | --- |
| Fabric | {f['artifact']['bytes']:,} | `{f['artifact']['sha256']}` |
| NeoForge | {n['artifact']['bytes']:,} | `{n['artifact']['sha256']}` |

两份成品各含 29 个首方类，class major 均为 65。ZIP/CRC、版本、GPL 元数据及根目录 `LICENSE`、`NOTICE` 与仓库逐字节一致；没有打入 Minecraft 类、测试类或嵌套第三方 JAR。源码 JAR 的哈希另列在报告中。

最终 [all-42-01 原日志](../outputs/adapter-build-1.20.6/build-all-42-01-console.log)记录 **23 项可执行 Gradle 任务全部实际执行**，用时 {final['elapsedSeconds']:.3f} 秒、退出码 0。Fabric 的连接调度 12 项、命令解析和原始 payload 编解码实际通过；标准 JUnit 为 `NO-SOURCE`。NeoForge 的连接调度 9 项，以及官方 FML 引导下的两项 JUnit 均在本轮实际执行，零失败、错误、跳过，没有把 `FROM-CACHE` 算作执行。[JUnit 派生摘要](../outputs/adapter-build-1.20.6/neoforge-junit-summary.json)绑定原 XML 哈希和本轮时间，原 XML 因含本机 hostname 未公开。FML 配置实际位于 `E:/CodexTemp/QiZhangVerdict/compat-1.20.6/builds/all-42-01/runtime/neoforge-junit/config`。

核心有 **102 项不同断言**：57 项安全回归、42 条目录规则、3 项管理员配置保留及普通 ID 控制。对 [Fabric 精确成品](../outputs/adapter-build-1.20.6/core-fabric-result.json)和 [NeoForge 精确成品](../outputs/adapter-build-1.20.6/core-neoforge-result.json)各执行一次，共 **204 次包内核心断言执行**；平台调度及 JUnit 不加入此数字。测试先核验 `GuardService` 的 CodeSource 是指定 JAR，测试运行器只有 4 个测试/来源检查类，编译禁止生产源码搜索。运行器以 Java 8 语法编译，实际运行及成品使用 Java 21，不意味着 1.20.6 支持 Java 8。本报告不另计源码核心测试。

[本轮目录快照](../outputs/adapter-build-1.20.6/catalog-42.tsv)包含 42 个精确 ID，其中 38 条 `DENY`、4 条 `ALERT`。核心回归验证管理员已有配置、`OFF` 和删除项不会被默认目录自动覆盖；目录数量不证明覆盖所有作弊工具，设备及虚拟机信号仍为可伪造的客户端自报。

构建历史全部保留，旧候选没有冒充最终成品：

| 轮次 | 退出码 | 范围 |
| --- | ---: | --- |
| [fabric-01](../outputs/adapter-build-1.20.6/build-fabric-01-result.json) | 0 | 首轮 39 条规则；原始 JAR 在缓存独立保留，已由 42 条候选替代。 |
| [neoforge-01](../outputs/adapter-build-1.20.6/build-neoforge-01-result.json) | 0 | 首轮 39 条规则；原始 JAR 在缓存独立保留，已由 42 条候选替代。 |
| [all-42-01](../outputs/adapter-build-1.20.6/build-all-42-01-result.json) | 0 | 最终 42 条规则，两端构建和本报告的成品验证对象。 |

最终构建的 47 个输入源码文件哈希复查一致，此前发布的 20 份制品逐一重算哈希均未变化。这不是对旧 20 份重新构建或重新运行验收。原日志中的 Gradle 弃用、API 弃用和 FML 初始化配置警告均原样保留。

本适配使用 1.20.6 的 `ResourceLocation`、`RegistryFriendlyByteBuf` 与 FML 3 接口。两端 `qzguard:main` 保持原始字节协议、30,000 字节上限和数组隔离，不加第二层 VarInt 长度。Fabric 绑定原接收 handler 的稳定 sender，Neo 绑定原 listener/connection；异步报告回复前仍检查连接归属及存活。物理客户端入口不会加载到专用服。

`CommandGate1206Mixin` 为 `HEAD`、`cancellable=true`、`require=1`，配置 `required=true`、`defaultRequire=1`。Fabric 包内 refmap 指向 `class_2170.method_9249(ParseResults,String):void`；Neo 使用生产 Mojang 名称，不带 refmap。只读检查官方 1.20.6 服务端类确认有签名、无签名玩家命令都调用这一目标方法；实际生产注入和玩家门禁仍须运行证据。

公开附件仅包含逐项白名单内的日志、回执、目录快照、首方测试与整理工具。没有复制第三方源码/安装器、失败或历史二进制、世界、账号状态、设备标识或服务器 scope。整理过程没有启动 Java、安装器或游戏。
'''
with DOC.open('x',encoding='utf-8',newline='\n') as f:f.write(doc)
assert not sensitive.search(REPORT.read_bytes()) and not sensitive.search(DOC.read_bytes())
for link in re.findall(r'\]\(([^)]+)\)',doc):
    if not re.match(r'^https?://',link):assert (DOC.parent/link).resolve().is_file(),link
for item in evidence:
    require_record(ROOT/item['publicFile'],item)
    assert (ROOT/item['publicFile']).read_bytes()==Path(item['source']).read_bytes()
summary={'passed':True,'report':rec(REPORT),'document':rec(DOC),'evidenceCount':len(evidence),'evidenceBytes':sum(x['bytes'] for x in evidence),'javaInvoked':False,'allLocalLinksExist':True,'allOriginalBytePairsMatch':True}
save(CACHE/'build-report-01/collection-result.json',summary)
print(json.dumps(summary,ensure_ascii=False))
