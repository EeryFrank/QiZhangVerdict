# SPDX-License-Identifier: GPL-3.0-only
"""Read-only result auditor / explicit public evidence collector. No Java invocation."""
from pathlib import Path
import argparse, hashlib, json, re, struct, uuid, winreg, zlib, zipfile, tomllib

ROOT = Path(r'E:\Codex_work\QiZhangVerdict')
BASE = Path(r'E:\CodexTemp\QiZhangVerdict\release-0.2.0-test.1')
HERE = Path(__file__).resolve().parent
PROFILES = ['fabric-1.20.1','forge-1.20.1','fabric-1.21.1','neoforge-1.21.1',
            'fabric-1.19.4','forge-1.19.4','fabric-1.18.2','forge-1.18.2','fabric-1.16.5','forge-1.16.5']
POLICY_SHA = '47310c31b47287ab805bfdbf8ddddf80e8169385bd9c862239a0a0075644da4e'
SHA = lambda data: hashlib.sha256(data).hexdigest()
read = lambda path: json.loads(Path(path).read_text(encoding='utf-8'))
digest = lambda path: SHA(Path(path).read_bytes())

def png_check(path):
    raw = path.read_bytes()
    assert raw[:8] == b'\x89PNG\r\n\x1a\n', 'PNG signature'
    pos, parts, compressed, header = 8, [], bytearray(), None
    while pos < len(raw):
        assert pos + 12 <= len(raw), 'PNG chunk framing'
        size, kind = struct.unpack_from('>I4s', raw, pos)
        data = raw[pos+8:pos+8+size]
        assert pos + 12 + size <= len(raw), 'PNG truncated chunk'
        crc = struct.unpack_from('>I', raw, pos+8+size)[0]
        assert zlib.crc32(kind+data)&0xffffffff == crc, 'PNG CRC'
        parts.append(kind.decode('ascii')); pos += size+12
        if kind == b'IHDR':
            assert header is None and size == 13 and len(parts) == 1
            header = struct.unpack('>IIBBBBB', data)
        elif kind == b'IDAT': compressed.extend(data)
        elif kind == b'IEND':
            assert size == 0 and pos == len(raw)
            break
    assert parts[-1] == 'IEND' and header
    width, height, depth, color, compression, filter_method, interlace = header
    assert width > 0 and height > 0 and depth == 8 and color in (2,6)
    assert (compression,filter_method,interlace)==(0,0,0)
    channels = 3 if color == 2 else 4; stride = width*channels
    decoder=zlib.decompressobj(); decoded=decoder.decompress(bytes(compressed)); decoded+=decoder.flush()
    assert decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
    assert len(decoded)==height*(stride+1), 'PNG decompressed scanline size'
    pixels=bytearray(); prev=bytearray(stride)
    for row in range(height):
        start=row*(stride+1); filt=decoded[start]; line=bytearray(decoded[start+1:start+1+stride])
        assert filt in range(5)
        for i in range(stride):
            left=line[i-channels] if i>=channels else 0; up=prev[i]; upper_left=prev[i-channels] if i>=channels else 0
            if filt==1: predictor=left
            elif filt==2: predictor=up
            elif filt==3: predictor=(left+up)//2
            elif filt==4:
                p=left+up-upper_left; pa=abs(p-left); pb=abs(p-up); pc=abs(p-upper_left)
                predictor=left if pa<=pb and pa<=pc else up if pb<=pc else upper_left
            else: predictor=0
            line[i]=(line[i]+predictor)&255
        pixels.extend(line); prev=line
    return {'width':width,'height':height,'bitDepth':depth,'colorType':color,'crcCheckedChunks':len(parts),
            'zlibAndScanlinesValid':True,'decodedPixelSha256':SHA(pixels),'decodedByteValues':len(set(pixels)),
            'sha256':SHA(raw),'bytes':len(raw),'automaticStructureCheckOnly':True}

def add_file(files, path, label, category, expected=None):
    path=Path(path); raw=path.read_bytes(); sha=SHA(raw)
    if expected is not None: assert expected == sha, 'Evidence SHA differs: '+str(path)
    assert path.is_file() and category in ('result','console','screenshot','harness','policy','blacklist','stage','build-receipt','java-release','video-options','server-properties')
    assert path.suffix.lower() in ('.json','.log','.png','.py','.properties','.tsv','.txt','')
    assert path.name not in ('accounts.state','server-id.txt','installation-id.txt','launch-plan.json','base-plan.json')
    # Exact duplicate public inputs are deliberately kept once.
    key=(sha, category)
    if key not in files:
        name='client-020-'+label+(path.suffix.lower() or '.txt')
        files[key]={'file':'evidence/'+name,'sha256':sha,'bytes':len(raw),'category':category,
                    'originalFiles':[],'rawBytesPreserved':True}
    item=files[key]
    if str(path) not in item['originalFiles']: item['originalFiles'].append(str(path))
    return {'file':item['file'],'sha256':sha,'bytes':len(raw)}

def machine_id():
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\Cryptography',0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
        value=winreg.QueryValueEx(key,'MachineGuid')[0].strip().lower()
    assert re.fullmatch('[a-f0-9-]{16,64}',value)
    return value

def association(config, raw_id, sensitive):
    scope=(config/'server-id.txt').read_text('ascii').strip().lower()
    assert re.fullmatch('[a-f0-9]{64}',scope)
    dev=hashlib.sha256(('QiZhangVerdict|'+scope+'|'+raw_id).encode()).hexdigest()
    offline=bytearray(hashlib.md5(b'OfflinePlayer:VerdictClient').digest()); offline[6]=(offline[6]&15)|48; offline[8]=(offline[8]&63)|128
    player=str(uuid.UUID(bytes=bytes(offline)))
    rows=(config/'accounts.state').read_text('utf-8').splitlines()
    sensitive.update((scope.encode(),dev.encode(),raw_id.encode()))
    for row in rows:
        pieces=row.split('\t')
        if pieces[0]=='D' and len(pieces)==3: sensitive.add(pieces[2].encode())
    return 'D\t'+player+'\t'+dev in rows

def java_metadata(java):
    java=Path(java); release=java.parent.parent/'release'
    values=dict(re.findall(r'^([A-Z0-9_]+)="(.*)"$',release.read_text('utf-8'),re.M))
    return {'executable':str(java),'executableSha256':digest(java),'releaseFileSha256':digest(release),
            'version':values['JAVA_VERSION'],'implementor':values.get('IMPLEMENTOR'),
            'evidenceBasis':'Pinned executable selected by the preserved executed harness; JDK release file read without executing Java.'}

def mod_inventory(folder):
    records=[]
    for path in sorted(Path(folder).glob('*.jar')):
        record={'filename':path.name,'sha256':digest(path),'bytes':path.stat().st_size,'topLevelDescriptorIds':[],'descriptors':[]}
        with zipfile.ZipFile(path) as jar:
            for name in ('fabric.mod.json','META-INF/mods.toml','META-INF/neoforge.mods.toml','mcmod.info','plugin.yml'):
                if name not in jar.namelist(): continue
                raw=jar.read(name); record['descriptors'].append({'entry':name,'sha256':SHA(raw)})
                if name=='fabric.mod.json': record['topLevelDescriptorIds'].append(json.loads(raw)['id'])
                elif name.endswith('.toml'): record['topLevelDescriptorIds'] += [x['modId'] for x in tomllib.loads(raw.decode('utf-8')).get('mods',[]) if 'modId' in x]
                elif name=='mcmod.info':
                    value=json.loads(raw); mods=value if isinstance(value,list) else value.get('modList',[])
                    record['topLevelDescriptorIds'] += [x['modid'] for x in mods if 'modid' in x]
        record['topLevelDescriptorIds']=sorted(set(record['topLevelDescriptorIds']))
        record['inventoryScope']='Top-level JAR files and all supported top-level descriptors only; nested dependencies and runtime-loaded status are not inferred.'
        records.append(record)
    return records

def log_observations(raw_evidence):
    records=[]
    for item in raw_evidence:
        path=Path(item['path'])
        if path.suffix!='.log': continue
        text=path.read_text('utf-8',errors='replace')
        records.append({'log':path.name,'warnLevelLineCount':len(re.findall(r'(?:/|\[)WARN\]',text)),
                        'errorLevelLineCount':len(re.findall(r'(?:/|\[)ERROR\]',text)),
                        'zeroErrorLinesIsNotAcceptanceCriterion':True})
    return records

def inspect_modern(profile, result_path, files, sensitive, raw_id):
    d=read(result_path); run=result_path.parent; fixture=run.parent.parent; stage=read(fixture/'stage.json')
    mc=d['minecraft']; build_path=BASE/'builds'/f'{mc}-01'/'result.json'; build=read(build_path)
    assert build['buildSuccessful'] and build['exitCode']==0 and build['oldArtifactsUnchanged']
    artifact=next(x for x in build['artifacts'] if Path(x['path']).name==f'qizhangverdict-{profile}-0.2.0-test.1.jar')
    assert d['guard_sha256']==stage['guard']['sha256']==artifact['sha256']==digest(ROOT/artifact['path'])
    mods=list((run/'server/mods').glob('qizhangverdict-*.jar'))
    client_game=Path(stage['newClientGame']); client_mods=list((client_game/'mods').glob('qizhangverdict-*.jar'))
    assert len(mods)==len(client_mods)==1 and digest(mods[0])==digest(client_mods[0])==artifact['sha256']
    refs=[add_file(files,result_path,profile+'-'+fixture.name.rsplit('-',1)[1]+'-result','result'),
          add_file(files,fixture/'stage.json',profile+'-'+fixture.name.rsplit('-',1)[1]+'-stage','stage')]
    for name,key in [('executed-wrapper.py','wrapperSha256'),('executed-helper.py','helperSha256'),('executed-shared-helper.py','sharedHelperSha256')]:
        refs.append(add_file(files,fixture/name,'harness-'+stage[key][:16],'harness',stage[key]))
    config=run/'server/config/qizhangverdict'; policy=config/'guard.properties'; assert digest(policy)==POLICY_SHA
    refs.append(add_file(files,policy,'strict-defaults','policy',POLICY_SHA))
    refs.append(add_file(files,run/'server/server.properties',profile+'-server','server-properties'))
    refs.append(add_file(files,config/'blacklist.tsv','blacklist-default37','blacklist'))
    rules=[x.split('\t') for x in (config/'blacklist.tsv').read_text('utf-8').splitlines() if x and not x.startswith('#')]
    assert len(rules)==37
    current=[x.split('\t') for x in (ROOT/'catalog/blacklist-extension.tsv').read_text('utf-8').splitlines() if x and not x.startswith('#')]
    norm=lambda rows: sorted((('mod' if r[0]=='automation' else r[0]),r[1],r[2],r[3]) for r in rows)
    assert norm(rules)==norm(current)
    exact=association(config,raw_id,sensitive)
    assert exact and d['passed'] and d['strict_defaults'] and d['policy_unchanged'] and d['restored_survival']
    assert d['client_exit_code']==d['server_exit_code']==0
    assert d['policy_before_client']['sha256']==d['policy_after_client']['sha256']==POLICY_SHA
    pngs=[]
    for item in d['raw_evidence']:
        path=Path(item['path']); assert path.is_relative_to(run) and path.stat().st_size==item['bytes']
        assert path.name in ('client-console.log','server-console.log') or path.parent.name=='screenshots' and path.suffix=='.png'
        ref=add_file(files,path,profile+'-'+fixture.name.rsplit('-',1)[1]+'-'+path.stem,'screenshot' if path.suffix=='.png' else 'console',item['sha256'])
        refs.append(ref)
        if path.suffix=='.png': pngs.append({**png_check(path),'file':ref['file']})
    assert pngs
    java=d.get('java_executable') or (r'D:\Java\jdk-21\bin\java.exe' if mc=='1.21.1' else r'E:\CodexTemp\mods-danzi\java\jdk-17.0.20.1+1-jre\bin\java.exe')
    jm=java_metadata(java)
    refs.append(add_file(files,Path(java).parent.parent/'release','java-release-'+jm['releaseFileSha256'][:16],'java-release'))
    elapsed=d.get('confirmed_online_seconds_after_first_restored_mode',d.get('confirmed_online_after_join_seconds'))
    return {'id':profile,'kind':'matching-mod-server','passed':True,'minecraft':mc,'loader':profile.split('-')[0],
            'loaderVersion':d['loader_version'],'clientAndServerArtifact':artifact,'java':jm,
            'clientGuardSha256':artifact['sha256'],'serverGuardSha256':artifact['sha256'],
            'buildReceipt':{'originalFile':str(build_path),'sha256':digest(build_path)},
            'onlineObservationSeconds':elapsed,'onlineObservationBasis':'after first observed survival restoration' if 'confirmed_online_seconds_after_first_restored_mode' in d else 'after observed join',
            'strict13DefaultsUnchanged':True,'default37RulesMatchCatalog':True,'exactSyntheticUUIDAndScopedDeviceAssociation':exact,
            'clientExitCode':0,'serverExitCode':0,'pngs':pngs,'evidence':refs,
            'clientModInventory':mod_inventory(client_game/'mods'),'serverModInventory':mod_inventory(run/'server/mods'),
            'logObservations':log_observations(d['raw_evidence']),
            'freshWorld':d.get('fresh_world'),'authenticationFixture':d.get('authentication_fixture'),
            'fabricApi':d.get('fabric_api')}

def inspect_old(entry, files, sensitive, raw_id):
    result_path=Path(entry['result']); d=read(result_path); run=result_path.parent
    mc=d['minecraft']; profile='forge-'+mc; cid=profile+('-paper' if d['server_kind']!='forge' else '')
    assert entry['id']==cid
    build_path=Path(entry.get('buildReceipt',BASE/'builds'/f'{mc}-01'/'result.json')); build=read(build_path)
    assert build['buildSuccessful'] and build['exitCode']==0 and build['oldArtifactsUnchanged']
    artifact=next(x for x in build['artifacts'] if Path(x['path']).name==f'qizhangverdict-{profile}-0.2.0-test.1.jar')
    assert d['guard_sha256']==artifact['sha256']==digest(ROOT/artifact['path'])
    plan=read(run/'candidate-launch-plan.json'); game=Path(plan['game'])
    client_mods=list((game/'mods').glob('qizhangverdict-*.jar'))
    assert len(client_mods)==1 and digest(client_mods[0])==artifact['sha256']
    if d['server_kind']!='forge':
        server_build=read(BASE/'builds/root-01/result.json')
        server_artifact=next(x for x in server_build['artifacts'] if Path(x['path']).name=='qizhangverdict-bukkit-0.2.0-test.1.jar')
        assert server_build['buildSuccessful'] and server_build['exitCode']==0
        config=run/'server/plugins/QiZhangVerdict'; server_mods=list((run/'server/plugins').glob('qizhangverdict-*.jar'))
    else:
        server_artifact=artifact; config=run/'server/config/qizhangverdict'; server_mods=list((run/'server/mods').glob('qizhangverdict-*.jar'))
    assert len(server_mods)==1 and digest(server_mods[0])==d['server_guard_sha256']==server_artifact['sha256']
    refs=[add_file(files,result_path,cid+'-'+run.name+'-result','result')]
    if 'command' in entry:
        command=read(entry['command']); args=command['command']
        assert command['helperSha256']==d['harness_sha256'] and command['sharedHelperSha256']==d['helper_sha256']
        assert args[args.index('--guard-sha256')+1]==d['guard_sha256']
        if d['server_kind']!='forge': assert args[args.index('--bukkit-sha256')+1]==d['server_guard_sha256']
        refs.append(add_file(files,Path(entry['command']),cid+'-command','stage'))
    for key in ['harness','helper']:
        path=Path(entry[key]); refs.append(add_file(files,path,'harness-'+d[key+'_sha256'][:16],'harness',d[key+'_sha256']))
    assert digest(config/'guard.properties')==POLICY_SHA
    refs.append(add_file(files,config/'guard.properties','strict-defaults','policy',POLICY_SHA))
    refs.append(add_file(files,config/'blacklist.tsv','blacklist-default37','blacklist'))
    refs.append(add_file(files,run/'server/server.properties',cid+'-server','server-properties'))
    norm=lambda rows: sorted((('mod' if r[0]=='automation' else r[0]),r[1],r[2],r[3]) for r in rows)
    parsed=lambda path: [x.split('\t') for x in path.read_text('utf-8').splitlines() if x and not x.startswith('#')]
    assert len(parsed(config/'blacklist.tsv'))==37 and norm(parsed(config/'blacklist.tsv'))==norm(parsed(ROOT/'catalog/blacklist-extension.tsv'))
    exact=association(config,raw_id,sensitive)
    assert exact and d['passed'] and d['strict_defaults'] and d['policy_unchanged'] and d['survival_mode_confirmed']
    assert d['client_exit_code']==d['server_exit_code']==0
    assert d['policy_before_client']['sha256']==d['policy_after_client']['sha256']==POLICY_SHA
    pngs=[]
    for item in d['raw_evidence']:
        path=Path(item['path']); assert path.is_relative_to(run) and path.stat().st_size==item['bytes']
        assert path.name in ('client-console.log','server-console.log') or path.parent.name=='screenshots' and path.suffix=='.png'
        ref=add_file(files,path,cid+'-'+run.name+'-'+path.stem,'screenshot' if path.suffix=='.png' else 'console',item['sha256']); refs.append(ref)
        if path.suffix=='.png': pngs.append({**png_check(path),'file':ref['file']})
    assert pngs
    for key in ('video_options_before','video_options_after','forge_splash_before','forge_splash_after'):
        if key in d:
            item=d[key]; refs.append(add_file(files,Path(item['path']),cid+'-'+key,'video-options',item['sha256']))
    jm=java_metadata(d['java']); refs.append(add_file(files,Path(d['java']).parent.parent/'release','java-release-'+jm['releaseFileSha256'][:16],'java-release'))
    elapsed=d.get('confirmed_online_seconds_after_report_evidence',d.get('confirmed_online_seconds_after_first_restored_mode'))
    assert elapsed>=65
    return {'id':cid,'kind':'bukkit-interoperability' if d['server_kind']!='forge' else 'matching-mod-server','passed':True,
            'minecraft':mc,'serverMinecraft':d.get('server_minecraft',mc),'loader':'forge','loaderVersion':d['loader'].split(' ',1)[1],
            'clientGuardSha256':artifact['sha256'],'serverGuardSha256':server_artifact['sha256'],
            'clientArtifact':artifact,'serverArtifact':server_artifact,'java':jm,'buildReceipt':{'originalFile':str(build_path),'sha256':digest(build_path)},
            'onlineObservationSeconds':elapsed,'onlineObservationBasis':'after exact UUID association and first survival query; monotonic interval followed by a fresh successful query',
            'strict13DefaultsUnchanged':True,'default37RulesMatchCatalog':True,'exactSyntheticUUIDAndScopedDeviceAssociation':exact,
            'clientExitCode':0,'serverExitCode':0,'pngs':pngs,'evidence':refs,
            'clientModInventory':mod_inventory(game/'mods'),'serverModInventory':mod_inventory(run/'server'/('mods' if d['server_kind']=='forge' else 'plugins')),
            'logObservations':log_observations(d['raw_evidence']),
            'restoredSurvivalFromSpectator':d['restored_survival_from_spectator'],'forgeSplashOverride':d.get('forge_splash_override','not overridden by this harness'),
            'nativeForge188Claimed':False}

def run():
    files={}; cases=[]; pending=[]; failures=[]; sensitive=set(); raw_id=machine_id()
    for profile in PROFILES:
        path=BASE/'client-runs'/f'{profile}-01'/profile/'run-01/result.json'
        if not path.exists(): pending.append(profile); continue
        cases.append(inspect_modern(profile,path,files,sensitive,raw_id))
    oldfile=HERE/'old-inputs.json'
    old_expected=['forge-1.12.2','forge-1.12.2-paper','forge-1.8.9','forge-1.8.9-paper']
    if oldfile.exists():
        for entry in read(oldfile):
            assert entry['id'] in old_expected
            if not Path(entry['result']).is_file(): continue
            cases.append(inspect_old(entry,files,sensitive,raw_id)); old_expected.remove(entry['id'])
    failedfile=HERE/'failed-inputs.json'
    if failedfile.exists():
        for entry in read(failedfile):
            path=Path(entry['result']); data=read(path); run_dir=path.parent
            assert data.get('passed') is False, 'Failure history must contain a failed result'
            refs=[add_file(files,path,entry['id']+'-result','result')]
            pngs=[]
            for item in data.get('raw_evidence',[]):
                source=Path(item['path']); assert source.is_relative_to(run_dir)
                assert source.name in ('client-console.log','server-console.log') or source.parent.name=='screenshots' and source.suffix=='.png'
                refs.append(add_file(files,source,entry['id']+'-'+source.stem,'screenshot' if source.suffix=='.png' else 'console',item['sha256']))
                if source.suffix=='.png': pngs.append(png_check(source))
            for kind in ('harness','helper'):
                if kind in entry:
                    refs.append(add_file(files,Path(entry[kind]),'harness-'+data[kind+'_sha256'][:16],'harness',data[kind+'_sha256']))
            for folder in ('config/qizhangverdict','plugins/QiZhangVerdict'):
                cfg=run_dir/'server'/folder
                if (cfg/'guard.properties').is_file(): refs.append(add_file(files,cfg/'guard.properties',entry['id']+'-guard','policy'))
                if (cfg/'server-id.txt').is_file(): sensitive.add((cfg/'server-id.txt').read_bytes().strip())
                if (cfg/'accounts.state').is_file():
                    for line in (cfg/'accounts.state').read_bytes().splitlines():
                        parts=line.split(b'\t')
                        if len(parts)==3 and parts[0]==b'D': sensitive.add(parts[2])
            failures.append({'id':entry['id'],'passed':False,'guardSha256':data.get('guard_sha256'),'clientExitCode':data.get('client_exit_code'),
                             'serverExitCode':data.get('server_exit_code'),'reportedError':data.get('error'),'evidence':refs,'pngs':pngs,
                             'interpretation':entry['interpretation']})
    items=list(files.values()); leaked=[]
    for item in items:
        data=Path(item['originalFiles'][0]).read_bytes()
        if any(secret and secret in data for secret in sensitive): leaked.append(item['file'])
    assert not leaked, 'Private values present in public candidate evidence (values suppressed)'
    output={'scope':'IN_PROGRESS independent file audit; not final 14-case acceptance','expectedCases':14,'completedAuditedCases':len(cases),
            'pendingCases':pending+old_expected,
            'cases':cases,'failedAttempts':failures,'evidence':items,'privacy':{'exactKnownPrivateValuesScanned':len(sensitive),'matches':0,'privateStateCopied':False},
            'noJavaExecutedByAuditor':True,'auditScriptSha256':digest(__file__)}
    (HERE/'progress.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'auditedCases':len(cases),'evidenceFiles':len(items),'evidenceBytes':sum(x['bytes'] for x in items),'pendingCases':output['pendingCases'],'privacyMatches':0}))

if __name__=='__main__': run()
