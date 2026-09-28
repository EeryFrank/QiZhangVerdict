#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Review explicit finished 1.17.1 fixtures; cache stage before optional publication."""
import argparse, collections, datetime, hashlib, json, re, sys, zipfile
from pathlib import Path
ROOT=Path(r'E:\Codex_work\QiZhangVerdict')
CACHE=Path(r'E:\CodexTemp\QiZhangVerdict\compat-1.17.1')
BASE=CACHE/'server-report-01'
NAMESPACE='runtime-server-1.17.1'
MARKER='.qizhang-legacy117-smoke.json'
DEFAULTS={'limits.max-online-per-ip':'3','limits.max-online-per-ip-device':'1',
 'limits.max-accounts-per-ip':'5','limits.account-window-hours':'720','limits.attempts-per-minute':'20',
 'ip.allow':'','ip.deny':'','companion.required':'true','companion.timeout-seconds':'20',
 'device.required':'true','vm.action':'DENY','blacklist.action':'DENY','sanctions.on-deny':'BAN'}
STRICT=(', companion=required,',', vm=DENY,',', blacklist=DENY,',', deviceRequired=true')
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text('utf-8'))
def require(ok,message):
    if not ok:raise ValueError(message)
def check_record(rec):
    b=Path(rec['path']).read_bytes();require(sha(b)==rec['sha256'] and len(b)==rec['bytes'],'Recorded input drift: '+Path(rec['path']).name)
def props(p):return dict(l.strip().split('=',1) for l in p.read_text('utf8').splitlines() if l.strip() and not l.lstrip().startswith('#'))
def rows(p):return sorted(tuple(l.split('\t')) for l in p.read_text('utf8').splitlines() if l and not l.startswith('#'))
def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--attempt',action='append',required=True)
    cli.add_argument('--name',required=True)
    cli.add_argument('--build-receipt',type=Path,default=CACHE/'builds/build-01/result.json')
    cli.add_argument('--final-build-receipt',type=Path,default=CACHE/'builds/build-02/result.json')
    cli.add_argument('--publish',action='store_true',help='Requires final Fabric and Forge successes; refuses existing repository output')
    args=cli.parse_args()
    require(re.fullmatch(r'[a-z0-9-]+',args.name),'Invalid cache stage name')
    stage=BASE/args.name;require(not stage.exists(),'Refuse to overwrite cache stage')
    build=load(args.build_receipt);final_build=load(args.final_build_receipt)
    require(build['exitCode']==final_build['exitCode']==0,'Build receipt did not pass')
    pins={};historical_pins={}
    for loader in ('fabric','forge'):
        rel=f'platforms/1.17.1/{loader}/build/libs/qizhangverdict-{loader}-1.17.1-0.6.0-dev.jar'
        old=next(x for x in build['artifacts'] if x['path']==rel)
        final=old if loader=='fabric' else next(x for x in final_build['artifacts'] if x['path']==rel)
        require(sha((ROOT/rel).read_bytes())==final['sha256'],'Current product differs from final selected build')
        pins[loader]=final;historical_pins[loader]=old
    require(pins['forge']['sha256']=='d88ac5a343d48905ac8212b7f85337bb78a35762e6a605ee0ed389fda73bb839','Unexpected final Forge candidate')
    planned={};attempts=[];scopes=set();private_devices=set();synthetic=set();private_summary={}
    def add(path,name):
        require(Path(name).name==name and not name.startswith('.'),'Unsafe public filename')
        b=path.read_bytes()
        if name in planned:
            require(planned[name]['bytes']==b,'Shared snapshot mismatch')
            planned[name]['sources'].append(str(path))
        else:planned[name]={'bytes':b,'sources':[str(path)]}
        return NAMESPACE+'/'+name
    collector_ref=add(Path(__file__),'collection-review.py')
    diagnosis_path=CACHE/'forge-channel-review-01/result.json'
    diagnosis=load(diagnosis_path)
    require(diagnosis['candidate']['sha256']==historical_pins['forge']['sha256'],'Channel diagnosis product differs')
    for key in ('result','protocolConsole'):check_record(diagnosis['observedAttempt'][key])
    diagnosis_ref=add(diagnosis_path,'forge-channel-static-review.json')
    for name in args.attempt:
        require(re.fullmatch(r'(?:fabric|forge)-44-[0-9]+',name),'Invalid explicit fixture name')
        p=CACHE/'servers'/name
        require(p.is_dir() and not p.is_symlink(),'Missing/plain fixture expected')
        m=load(p/MARKER);loader=m['loader'];install=load(p/'install-result.json')
        require(m['minecraft']=='1.17.1' and loader in pins,'Wrong profile')
        expected=historical_pins[loader] if name in ('forge-44-01','forge-44-02') else pins[loader]
        check_record(m['guardRecord'])
        for rec in (m['guardRecord'],m['guardSource']):
            require(rec['sha256']==expected['sha256'] and rec['bytes']==expected['bytes'],'Wrong exact product')
        # Historical build/libs was replaced by build02. Verify its original
        # fixture copy and build01 pin, never reinterpret it as the new product.
        if expected==pins[loader]:check_record(m['guardSource'])
        else:
            old_jar=CACHE/'superseded-build-01/artifacts'/Path(expected['path']).name
            require(sha(old_jar.read_bytes())==expected['sha256'] and old_jar.stat().st_size==expected['bytes'],'Archived old product drift')
        for rec in m['officialInputRecords'].values():check_record(rec)
        for rec in m['protocolSnapshots']:check_record(rec)
        for rec in (m['javaRecord'],m['javaRelease'],m['javapRecord'],m['catalog'],install['console']):check_record(rec)
        executed=p/'qa/legacy117_mod_smoke.py'
        require(sha(executed.read_bytes())==m['helper']['sha256'],'Executed helper snapshot differs')
        refs={filename:add(p/filename,name+'-'+filename) for filename in ('install-result.json','install-console.log')}
        refs['fixture']=add(p/MARKER,name+'-fixture.json')
        refs['helper']=add(executed,'helper-'+m['helper']['sha256'][:12]+'.py')
        for dependency in m.get('helperDependencies',[]):
            source=p/'qa'/Path(dependency['path']).name
            require(sha(source.read_bytes())==dependency['sha256'] and source.stat().st_size==dependency['bytes'],'Executed helper dependency differs')
            refs['helperDependency-'+source.name]=add(source,'helper-'+dependency['sha256'][:12]+'-'+source.name)
        for filename in ('protocol_smoke.cjs','protocol_disconnect_observer.cjs','protocol_player_loaded.cjs','package-lock.json','catalog.tsv'):
            source=p/'qa'/filename
            refs[filename]=add(source,'shared-'+sha(source.read_bytes())[:12]+'-'+filename)
        profile='official-server-profile.json' if loader=='fabric' else 'official-install-profile.json'
        refs['officialProfile']=add(p/'qa'/profile,name+'-'+profile)
        attempt={'attempt':name,'profile':m['profile'],'loader':loader,'loaderVersion':m['loaderVersion'],
          'minecraft':'1.17.1','artifact':dict(expected,version='0.6.0-dev'),'isFinalArtifact':expected==pins[loader],
          'historicalBuildPathReplaced':expected!=pins[loader],
          'installer':{'exitCode':install['installerExitCode'],'installedOutputsVerified':install['installedOutputsVerified'],
          'sha256':install['installerSha256'],'officialReceiptSha256':m['officialReceiptSha256'],'baseReceiptSha256':m['baseReceiptSha256']},
          'evidenceRefs':refs}
        if 'generatedServerLibraries' in m:
            for rec in m['generatedServerLibraries']:check_record(rec)
            attempt['generatedServerLibraries']=m['generatedServerLibraries']
            attempt['patchedServerVerification']=m.get('patchedServerVerification')
        if not (p/'smoke-result.json').exists():
            require(not install['installedOutputsVerified'] and install.get('gameStarted') is False,'Incomplete fixture is not a recorded installation failure')
            require(not (p/'console.log').exists(),'Unexpected unreported game execution')
            attempt.update(stage='INSTALLATION_VALIDATION_FAILED',actualServerStarted=False,passed=False,
                passedCaseGroups=0,serverExitCode=None,error=install.get('error'),
                boundary='Installer exit0 alone is not server acceptance. No game process or TCP suite was started in this fixture.')
            attempts.append(attempt);continue
        r=load(p/'smoke-result.json');require(r['guard']['sha256']==expected['sha256'],'Result product pin mismatch')
        for key in ('console','protocolConsole','protocolResultRecord'):
            if key in r:check_record(r[key])
        attempt.update(stage='SERVER_TCP',actualServerStarted=r['started'],passed=r['passed'],
            serverExitCode=r['serverExitCode'],normalStop=r['normalStop'],protocolExitCode=r.get('protocolExitCode'),
            elapsedSeconds=r['elapsedSeconds'],protocolElapsedSeconds=r.get('protocolElapsedSeconds'),passedCaseGroups=0)
        for filename in ('smoke-result.json','console.log','protocol-console.log','protocol-result.json',
                'protocol-disconnect-observations.json','protocol-metadata-trace.json','protocol-handshake-trace.json','server.properties','commands.queue'):
            if (p/filename).is_file():refs[filename]=add(p/filename,name+'-'+filename)
        for filename in ('guard-default.properties','blacklist-default.tsv'):
            if (p/filename).is_file():refs[filename]=add(p/filename,'shared-'+sha((p/filename).read_bytes())[:12]+'-'+filename)
        if not r['passed']:
            attempt['error']=r.get('error') or ('TCP suite did not complete; exitCode='+str(r.get('protocolExitCode')))
            attempt['partialObservations']={k:r.get(k) for k in ('defaultPolicyVerified','defaultCatalogVerified','expectedRuleCount',
                'expectedCatalogActions','freshStatus','mixinAudit','restoreReloadStatus','restoredStatus','strictPolicyRestored',
                'portReleased','protocolDecoderErrors','warningAndErrorLines')}
            if r.get('defaultPolicyVerified'):require(props(p/'guard-default.properties')==DEFAULTS,'Failed-attempt fresh policy receipt differs')
            if r.get('defaultCatalogVerified'):require(rows(p/'blacklist-default.tsv')==rows(p/'qa/catalog.tsv'),'Failed-attempt catalog receipt differs')
            if r.get('strictPolicyRestored'):
                require((p/'guard-default.properties').read_bytes()==(p/'config/qizhangverdict/guard.properties').read_bytes(),'Failed-attempt restoration bytes differ')
            if r.get('mixinAudit'):
                for key in ('export','privateDisassembly'):check_record(r['mixinAudit'][key])
            attempt['boundary']='Startup, defaults, required Mixin and clean stop observations are retained separately; the first TCP admission assertion failed, so no completed26-case result is claimed.'
            attempts.append(attempt);continue
        require(r['started'] and r['normalStop'] and r['serverExitCode']==0 and r['protocolPassed'] and r['protocolExitCode']==0,'Success missing process/TCP result')
        require(not any(r.get(k) for k in ('forcedServerTermination','protocolForcedTermination','error','stopError')),'Success contains termination/failure')
        require(r.get('portReleased') is True,'Success lacks historical post-stop bind receipt')
        protocol=load(p/'protocol-result.json');console=(p/'console.log').read_text('utf8');node=(p/'protocol-console.log').read_text('utf8')
        require(protocol==r['protocolResult'] and protocol['passed']==26 and len(protocol['cases'])==26 and len(set(protocol['cases']))==26,'Expected actual26 unique cases')
        require(protocol['version']=='1.17.1' and protocol['orePalette']==[] and protocol['maxChunkZeroPadding']==0,'Wrong suite/version/ore scope')
        require(props(p/'guard-default.properties')==DEFAULTS,'Fresh strict13 mismatch')
        require((p/'guard-default.properties').read_bytes()==(p/'config/qizhangverdict/guard.properties').read_bytes(),'Final13 bytes not restored')
        catalog=rows(p/'qa/catalog.tsv');fresh=rows(p/'blacklist-default.tsv')
        require(catalog==fresh and len(fresh)==44 and collections.Counter(x[2] for x in fresh)=={'DENY':40,'ALERT':4},'Default44 rows/action mismatch')
        require(r['defaultPolicyVerified'] and r['defaultCatalogVerified'] and r['expectedRuleCount']==44,'Missing default receipt')
        require(all(t in r['freshStatus'] for t in STRICT) and ', rules=44,' in r['freshStatus'],'Fresh effective status mismatch')
        for field in ('restoreReloadStatus','restoredStatus'):
            require(all(t in r[field] for t in STRICT) and ', rules=45,' in r[field] and r[field] in console,'Missing strict restoration live status')
        require(console.count(r['restoredStatus'])>=2 and r['strictPolicyRestored'],'Two independent restoration responses missing')
        helper=executed.read_text('utf8')
        require("result['restoreReloadStatus'] = wait_status(server, console, command='qzverdict reload')" in helper
            and "result['restoredStatus'] = wait_status(server, console)" in helper,'Async restoration helper differs')
        finalblack=rows(p/'config/qizhangverdict/blacklist.tsv');finalrules=rows(p/'config/qizhangverdict/rules.tsv')
        require(len(finalblack)==43 and len(finalrules)==2,'Unexpected final test rule counts')
        require(all(x in fresh and x[1]!='meteor-client' for x in finalblack),'Unexplained final blacklist edit')
        require(sorted(x[1:] for x in finalrules)==sorted([('BLACK','MOD','EXACT','meteor-client'),('BLACK','MOD','GLOB','test*cheat')]),'Unexplained administrator rule')
        require(r['requiredMixinObserved'] and r['mixinAudit']['passed'] and r['mixinAudit']['javapExitCode']==0,'Required command Mixin receipt missing')
        for k in ('dispatchCallsInjectedHandler','handlerCallsGuardWaiting','handlerCancelsCommand'):require(r['mixinAudit'][k] is True,'Mixin chain missing '+k)
        for k in ('export','privateDisassembly'):check_record(r['mixinAudit'][k])
        require('[GateAccount] QZ_PRE_GATE' not in console and '[GateAccount] QZ_POST_GATE' in console,'Actual OP before/after command gate mismatch')
        require('Made GateAccount a server operator' in console and 'Made GateAccount no longer a server operator' in console,'Actual OP grant/removal absent')
        observations=load(p/'protocol-disconnect-observations.json')['disconnectObservations']
        require(observations==protocol['disconnectObservations'] and len(observations)==13,'Disconnect evidence mismatch')
        require(all(x['source']=='minecraft-protocol.deserializer.data' and x['packetName']=='kick_disconnect' for x in observations),'Wrong disconnect source')
        errors=[x for x in node.splitlines() if x.startswith('PartialReadError:')]
        require(errors==r['protocolDecoderErrors'],'Decoder warnings changed')
        warnings=[x for x in console.splitlines() if any(s in x for s in ('WARN','ERROR','Exception'))]
        require(warnings==r['warningAndErrorLines'],'Upstream warning list changed')
        for filename in ('blacklist.tsv','rules.tsv'):
            refs['final-'+filename]=add(p/'config/qizhangverdict'/filename,name+'-final-'+filename)
        attempt.update(passedCaseGroups=26,cases=protocol['cases'],protocol=r['protocolSupport'],
          policy={'fresh13DefaultsVerified':True,'freshDefaults':DEFAULTS,'freshDefaultRuleCount':44,'freshDefaultDeny':40,'freshDefaultAlert':4,
           'freshCatalogSha256':m['catalog']['sha256'],'qaOverrides':r['syntheticPolicyOverrides'],'freshStatus':r['freshStatus'],
           'strict13RestoredByteForByte':True,'restoreReloadStatus':r['restoreReloadStatus'],'restoredLiveStatus':r['restoredStatus'],
           'finalLegacyRows':43,'finalAdministratorRows':2,'finalEffectiveRules':45,
           'boundary':'Only guard.properties is restored; retained QA rules are not a production template.'},
          mixin=r['mixinAudit'],operatorGate={'opBeforeReportBlocked':True,'opAfterReportExecuted':True,'grantAndRemovalObserved':True},
          closure={'normalExit0':True,'portReleasedAtHelperEnd':r['portReleased'],'currentPortNotProbed':True},
          nodeDecoderObservations={'partialReadErrorCount':len(errors),'rawMessages':errors,'decodedDisconnects':13,
           'boundary':'Admission case results do not establish complete game packet decoding.'},warnings=warnings)
        attempts.append(attempt)
    # Read private identifiers only into memory. Never copy state, scope or hardware sources.
    for name in args.attempt:
        p=CACHE/'servers'/name;state=p/'config/qizhangverdict/accounts.state';scope=p/'config/qizhangverdict/server-id.txt'
        if scope.is_file():scopes.add(scope.read_text('ascii').strip())
        if state.is_file():
            values=set(re.findall(r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])',state.read_text('utf8')))
            text=(p/'qa/protocol_smoke.cjs').read_text('utf8')
            literals=re.findall(r"hash\('([^']+)'\)",text)+re.findall(r"name:'([^']+)'",text)
            names=re.findall(r'UUID of player ([A-Za-z0-9_]+) is ',(p/'console.log').read_text('utf8'))
            require(all(re.fullmatch(r'QVBot\d+|GateAccount|MalformedAccount|BadWire|CheatAccount|LinkedAccount',x) for x in names),'Unrecognized player provenance (value omitted)')
            synthetic.update(sha(x.encode()) for x in literals+names+['QVBot'+str(i) for i in range(1,31)])
            require(values<=synthetic,'Device provenance is not the executed synthetic fixture (value omitted)')
            private_devices.update(values);private_summary[name]={'storedDigests':len(values),'allMatchSyntheticFixture':True}
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\Cryptography',0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
        guid=winreg.QueryValueEx(key,'MachineGuid')[0]
    hardware={guid,guid.lower(),guid.upper(),guid.replace('-','')}
    sensitive=re.compile(rb'(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{15,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|Authorization:\s*Bearer\s+[A-Za-z0-9._-]{16,})')
    for name,v in planned.items():
        b=v['bytes'];require(not any(x.encode() in b for x in scopes),'Private server scope in selected file: '+name)
        require(not any(x.encode() in b or x.encode('utf-16le') in b for x in hardware),'Hardware identifier in selected file: '+name)
        require(not sensitive.search(b),'Credential pattern in selected file: '+name)
    passing=[a for a in attempts if a['passed']]
    selected=[a for a in passing if a['isFinalArtifact']]
    allprofiles={a['loader'] for a in selected}=={'fabric','forge'}
    if args.publish:
        require(allprofiles,'Cannot publish final dual-loader success before both real server runs pass')
        require(len(passing)==2,'Explicit final selection required for multiple passing retries')
        require(not (ROOT/'outputs'/NAMESPACE).exists() and not (ROOT/'outputs'/(NAMESPACE+'.json')).exists(),'Public report already exists')
    stage.mkdir();evidence_dir=stage/NAMESPACE;evidence_dir.mkdir();evidence=[]
    for name,v in planned.items():
        (evidence_dir/name).write_bytes(v['bytes'])
        evidence.append({'file':NAMESPACE+'/'+name,'publicFile':'outputs/'+NAMESPACE+'/'+name,'originalPaths':v['sources'],
          'sha256':sha(v['bytes']),'bytes':len(v['bytes']),'rawBytesPreserved':True})
    report={'schemaVersion':1,'generatedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'product':'QiZhangVerdict','artifactVersion':'0.6.0-dev','minecraft':'1.17.1','finalCandidatePassed':allprofiles,
      'allAttemptsPassed':all(a['passed'] for a in attempts),'actualServerAttempts':sum(a['stage']=='SERVER_TCP' for a in attempts),
      'installationOnlyFailedAttempts':sum(a['stage']=='INSTALLATION_VALIDATION_FAILED' for a in attempts),
      'failedServerAttempts':sum(a['stage']=='SERVER_TCP' and not a['passed'] for a in attempts),
      'finalSelectedAttempts':[a['attempt'] for a in selected],'finalArtifacts':pins,
      'passingServerAttempts':len(passing),'passedCaseGroups':sum(a['passedCaseGroups'] for a in attempts),'uniqueCaseDefinitions':26,
      'formalAcceptancePassed':False,'attempts':attempts,
      'transportReview':{'evidence':diagnosis_ref,'initialArtifact':historical_pins['forge']['sha256'],'finalArtifact':pins['forge']['sha256'],
        'boundary':'Static official-source analysis predicts the old FML-only channel gate failure; old runtime did not log FMLConnectionData directly. New product passed unchanged26 TCP definitions. This is not cross-loader GUI proof.'},'evidence':evidence,'evidenceCount':len(evidence),'evidenceBytes':sum(e['bytes'] for e in evidence),
      'scope':'Actual dedicated servers and real TCP synthetic-report clients; not rendered ClientReporter, real VM/hardware attestation, online-mode authentication, behavior anticheat, Anti-Xray or performance acceptance.',
      'privacyReview':{'scopeFilesComparedInMemory':len(scopes),'stateDigestSources':private_summary,'uniqueSyntheticDigests':len(private_devices),
        'scopeMatches':0,'machineGuidMatches':0,'credentialPatternMatches':0,
        'excluded':['accounts.state','server-id.txt','world/player data','full Minecraft javap/class exports','third-party JARs','duplicate installer JAR logs'],
        'boundary':'Known fixture scopes/devices and local MachineGuid plus credential patterns checked; synthetic device hashes are allowed only after reproducing their QA inputs. Not an exhaustive secret detector.'},
      'boundaries':['Each passing loader runs26 admission definitions; two passing loaders would make52 executions, not52 distinct features.',
        'Fresh13/default44 are checked before overrides; final13 runtime restoration waits for asynchronous reload status and another fresh status. Rule tests retain45 effective rules.',
        'Failed installer validation is retained separately; installer exit0 does not prove server startup.',
        'Original warning/error lines and protocol decoder observations are preserved without turning successful admission into a complete gameplay-decoding claim.'],
      'collectionAudit':{'collectorSha256':sha(Path(__file__).read_bytes()),'collectorEvidence':collector_ref,'sourceBuildReceipt':str(args.build_receipt),'sourceBuildReceiptSHA256':sha(args.build_receipt.read_bytes()),'finalBuildReceipt':str(args.final_build_receipt),'finalBuildReceiptSHA256':sha(args.final_build_receipt.read_bytes()),'javaExecutedDuringCollection':False,'publicationRequested':args.publish}}
    reportpath=stage/(NAMESPACE+'.json');reportpath.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if args.publish:
        import shutil
        shutil.copytree(evidence_dir,ROOT/'outputs'/NAMESPACE)
        with (ROOT/'outputs'/(NAMESPACE+'.json')).open('xb') as f:f.write(reportpath.read_bytes())
    print(json.dumps({'stage':str(stage),'finalCandidatePassed':allprofiles,'actualServerAttempts':report['actualServerAttempts'],
      'installationOnlyFailedAttempts':report['installationOnlyFailedAttempts'],'passedCaseGroups':report['passedCaseGroups'],
      'evidenceCount':len(evidence),'evidenceBytes':report['evidenceBytes'],'reportSHA256':sha(reportpath.read_bytes())},indent=2))
if __name__=='__main__':main()
