from pathlib import Path
import hashlib,json,runpy,shutil,subprocess,time,socket

QA=Path(r'E:\Codex_work\QiZhangVerdict\platforms\legacy189-client-smoke.py')
h=runpy.run_path(str(QA)); matrix=h['matrix']
resources=h['memory_gate']('vanilla-forge-visual-baseline-02',minimum_gib=3.5)
with socket.socket() as port: port.bind(('127.0.0.1',h['PORT']))
plan=matrix.read(h['CACHE']/'client/launch-plan.json'); h['verify_prepared_inputs'](plan)
server_dir,entry=h['prepare_server']('vanilla-forge-visual-baseline-02','forge',include_guard=False)
directory=server_dir.parent; game=directory/'client-game'; (game/'mods').mkdir(parents=True)
options='fullscreen:false\nrenderDistance:2\nmaxFps:30\npauseOnLostFocus:false\n'
(game/'options.txt').write_text(options,encoding='ascii')
(game/'config').mkdir()
(game/'config/splash.properties').write_text('enabled=false\n',encoding='ascii')
shutil.copy2(game/'config/splash.properties',directory/'splash-before.properties')
shutil.copy2(game/'options.txt',directory/'options-before.txt')
plan={**plan,'game':str(game)}
assert not list((server_dir/'mods').glob('*.jar')) and not list((game/'mods').glob('*.jar'))
server_log=directory/'server-console.log'; client_log=directory/'client-console.log'
result={'scope':'Diagnostic production official Forge 1.8.9 baseline without QiZhangVerdict on either side',
        'minecraft':'1.8.9','forge':'11.15.1.2318-1.8.9','video_preset':'vanilla defaults',
        'forge_splash_override':'enabled=false',
        'resource_gate':resources,'automated_baseline_completed':False,'visual_review_status':'pending manual screenshot review',
        'harness_sha256':matrix.digest(QA),'baseline_script_sha256':matrix.digest(Path(__file__)),
        'installer_sha256':h['INSTALLER_SHA'],'client_classpath':[{k:v for k,v in row.items() if k in ('sha256','bytes','coordinate')} for row in plan['library_artifacts']],
        'client_heap':['-Xms256M','-Xmx1G'],'server_heap':['-Xms256M','-Xmx768M'],
        'guard_present_client':False,'guard_present_server':False,'driver_cause_established':False}
server=client=None
try:
    with server_log.open('xb') as out,client_log.open('xb') as cout:
        server=subprocess.Popen([str(h['JAVA']),'-Xms256M','-Xmx768M','-Djava.awt.headless=true',
            '-Dfile.encoding=UTF-8','-jar',entry,'nogui'],cwd=server_dir,stdin=subprocess.PIPE,
            stdout=out,stderr=subprocess.STDOUT,creationflags=matrix.NO_WINDOW,env=matrix.runtime_environment(server_dir))
        def console(text):
            if server.poll() is None:
                server.stdin.write((text+'\n').encode()); server.stdin.flush()
        started=time.monotonic()
        while server.poll() is None and time.monotonic()-started<180:
            if 'Done (' in matrix.text_log(server_log): break
            time.sleep(.5)
        else: raise RuntimeError('Unmodified baseline server did not become ready')
        console('gamerule doMobSpawning false')
        command=h['client_command'](plan)
        command[command.index('-Xmx2G')]='-Xmx1G'
        client=subprocess.Popen(command,cwd=game,stdout=cout,stderr=subprocess.STDOUT,
            creationflags=matrix.NO_WINDOW,env=matrix.runtime_environment(game))
        result.update({'owned_server_pid':server.pid,'owned_client_pid':client.pid})
        print('Baseline server',server.pid,'client',client.pid,flush=True)
        began=time.monotonic(); joined=None
        while client.poll() is None and time.monotonic()-began<120:
            matrix.windows(client.pid)
            if joined is None and 'VerdictClient joined the game' in matrix.text_log(server_log): joined=time.monotonic()
            if joined is not None and time.monotonic()-joined>=15:
                console('testfor @a[name=VerdictClient,m=0]')
                matrix.windows(client.pid,screenshot=True); time.sleep(3)
                break
            time.sleep(.25)
        if client.poll() is None:
            h['close_legacy_client'](client.pid); client.wait(timeout=30)
        console('stop'); server.wait(timeout=90)
        result['joined']=joined is not None
except Exception as error:
    result['error']=type(error).__name__+': '+(str(error.timeout) if isinstance(error,subprocess.TimeoutExpired) else str(error))
finally:
    if client is not None and client.poll() is None:
        h['close_legacy_client'](client.pid)
        try: client.wait(timeout=20)
        except subprocess.TimeoutExpired: client.terminate(); client.wait(timeout=10)
    if server is not None and server.poll() is None:
        try: server.stdin.write(b'stop\n'); server.stdin.flush(); server.wait(timeout=90)
        except (OSError,subprocess.TimeoutExpired): server.terminate(); server.wait(timeout=15)
    result['client_exit_code']=client.returncode if client else None
    result['server_exit_code']=server.returncode if server else None
    shutil.copy2(game/'options.txt',directory/'options-after.txt')
    shutil.copy2(game/'config/splash.properties',directory/'splash-after.properties')
    result['raw_evidence']=[matrix.artifact_record(p) for p in (server_log,client_log,directory/'options-before.txt',directory/'options-after.txt',directory/'splash-before.properties',directory/'splash-after.properties') if p.exists()]
    screenshots=[]
    for p in (game/'screenshots').glob('*.png'):
        screenshots.append({**matrix.artifact_record(p),'png_crc_dimensions_valid':h['png_verified'](p)})
    result['screenshots']=screenshots
    result['automated_baseline_completed']=bool(result.get('joined')) and bool(screenshots) and all(p['png_crc_dimensions_valid'] for p in screenshots) and result['client_exit_code']==0 and result['server_exit_code']==0
    matrix.save(directory/'result.json',result)
print(json.dumps({'automated_baseline_completed':result['automated_baseline_completed'],'result':str(directory/'result.json')}),flush=True)
