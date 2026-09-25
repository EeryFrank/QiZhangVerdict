"""Isolated official Forge 1.12.2 / Java 8 dedicated validation.

Stage never invokes Java; install/run require >=4 GiB free RAM and use <=1.5 GiB
heaps. Only new child directories of CACHE are accepted. The embedded protocol
fixture uses native QZGuard/REGISTER and default guard policy without modifying
any frozen modern harness. All players/device identifiers are synthetic.
"""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(r"E:\CodexTemp\QiZhangVerdict\legacy-runtime")
JAVA = Path(r"E:\CodexTemp\QiZhangVerdict\toolchains\jdk8\jdk8u504-b01\bin\java.exe")
NODE = Path(r"E:\CodexTemp\Codex\RuntimeCache\codex-primary-runtime\dependencies\node\bin\node.exe")
NODE_MODULES = Path(r"E:\CodexTemp\QiZhangGuard\bot\node_modules")
GUARD = ROOT / "platforms/1.12.2/forge/build/libs/qizhangverdict-forge-1.12.2-0.2.0-dev.jar"
GUARD_SHA = "7ee00ced99919281e2d6851e123c6bcb2d8ddd3e46338870b2034d5a5dcf0966"
FORGE = "1.12.2-14.23.5.2864"
INSTALLER_URL = "https://maven.minecraftforge.net/net/minecraftforge/forge/" + FORGE + "/forge-" + FORGE + "-installer.jar"
INSTALLER_SHA = "2c0065938de6df6f3deb4a08a3018940a1cc86111adb34a3be55d657857a11cc"
MARKER = ".qizhang-112-smoke.json"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

PROTOCOL = r'''
const mc = require('minecraft-protocol');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const [version, rawPort, folder] = process.argv.slice(2);
assert.equal(version, '1.12.2');
const channel = 'QZGuard', registerChannel = 'REGISTER';
const active = new Set(), cases = [], waits = [];
const pause = ms => new Promise(r => setTimeout(r, ms));
const hash = s => crypto.createHash('sha256').update(s).digest('hex');
function str(s) { const d = Buffer.from(s); const n = Buffer.alloc(2); n.writeUInt16BE(d.length); return Buffer.concat([n,d]); }
function list(a) { const n=Buffer.alloc(2); n.writeUInt16BE(a.length); return Buffer.concat([n,...a.map(str)]); }
function report(bytes, opts) {
  assert.equal(bytes.readUInt32BE(0),0x515a4731);
  assert.equal(bytes[4],2); assert.equal(bytes[5],1);
  assert.equal(bytes.readUInt16BE(6),64); assert.equal(bytes.readUInt16BE(72),64);
  assert.equal(bytes.length,138); assert(/^[0-9a-f]{64}$/.test(bytes.subarray(74).toString()));
  const nonce=bytes.subarray(8,72).toString();
  const device=opts.missingDevice ? '' : hash('synthetic-legacy-device-'+opts.device);
  const r=Buffer.concat([Buffer.from([0x51,0x5a,0x47,0x31,2,2]),str(nonce),Buffer.from([1]),list(['qizhangverdict']),list([]),list([]),str(device)]);
  return opts.malformed ? Buffer.concat([r,Buffer.from([1])]) : r;
}
async function connect(name, device, options={}) {
  const opts={name,device,...options};
  const s={name,joined:false,sent:false,ended:false,kick:'',error:'',challenge:false,started:Date.now()};
  const c=mc.createClient({host:'127.0.0.1',port:Number(rawPort),version,username:name,auth:'offline',checkTimeoutInterval:30000,disableChatSigning:true});
  s.client=c; active.add(c);
  c.on('error',e=>{s.error=String(e);});
  c.on('kick_disconnect',p=>{s.kick=JSON.stringify(p);});
  c.on('disconnect',p=>{s.kick=JSON.stringify(p);});
  c.on('end',()=>{s.ended=true;s.elapsed=Date.now()-s.started;active.delete(c);});
  c.on('login',()=>{s.joined=true;c.write('custom_payload',{channel:registerChannel,data:Buffer.from(channel)});});
  c.on('position',p=>{if(p.teleportId!==undefined)c.write('teleport_confirm',{teleportId:p.teleportId});});
  c.on('custom_payload',p=>{
    if(p.channel!==channel||s.sent)return;
    s.challenge=true;
    if(opts.silent)return;
    if(opts.hold){s.challengeBytes=p.data;return;}
    try { const bytes=report(p.data,opts); s.sent=true; c.write('custom_payload',{channel,data:bytes}); }
    catch(e) {s.error=String(e);c.end('invalid server challenge');}
  });
  const until=Date.now()+(opts.silent?26000:12000);
  while(!s.ended && !s.sent && !(opts.hold&&s.challenge) && (!opts.silent || Date.now()<until) && Date.now()<until)await pause(25);
  if(!opts.silent)await pause(900);
  return s;
}
function snapshot(s){return {name:s.name,joined:s.joined,sent:s.sent,ended:s.ended,kick:s.kick,error:s.error,challenge:s.challenge};}
function allowed(s, title) {assert(s.joined&&s.sent&&!s.ended&&!s.error,title+': '+JSON.stringify(snapshot(s)));cases.push(title);}
function denied(s, title, fragment) {assert(s.ended,title+': still connected '+JSON.stringify(snapshot(s)));if(fragment)assert(s.kick.toLowerCase().includes(fragment.toLowerCase()),title+': '+s.kick);cases.push(title);}
async function close(...clients){for(const s of clients)if(s&&!s.ended)s.client.end('legacy test complete');await pause(500);}
async function command(text){fs.appendFileSync(path.join(folder,'commands.queue'),text+'\n');await pause(700);}
async function main(){
  const gate=await connect('QVLegacyGate','gate',{hold:true});
  assert(gate.challengeBytes && !gate.ended,'operator gate has a pending report');
  await command('op QVLegacyGate');
  assert(/Opped QVLegacyGate/.test(fs.readFileSync(path.join(folder,'console.log'),'utf8')),'console confirms actual operator grant');
  gate.client.chat('/say QZ112_PRE_GATE');await pause(600);
  assert(!/\[QVLegacyGate\] QZ112_PRE_GATE/.test(fs.readFileSync(path.join(folder,'console.log'),'utf8')),'pending operator command must not execute');
  gate.sent=true;gate.client.write('custom_payload',{channel,data:report(gate.challengeBytes,{name:gate.name,device:'gate'})});await pause(700);
  assert(!gate.ended && !gate.error,'operator report accepted');
  gate.client.chat('/say QZ112_POST_GATE');await pause(600);
  assert(/\[QVLegacyGate\] QZ112_POST_GATE/.test(fs.readFileSync(path.join(folder,'console.log'),'utf8')),'verified operator command executes');
  cases.push('real operator command blocked while pending and restored after native QZGuard report');
  await close(gate);await command('deop QVLegacyGate');
  const a=await connect('QVLegacyA','a');allowed(a,'strict default companion report accepted on native Forge QZGuard channel');
  const observedFrom=fs.readFileSync(path.join(folder,'console.log'),'utf8').length;
  const sustainedAt=Date.now();await pause(22000);
  assert(!a.ended&&!a.error,'valid companion must survive beyond the default report deadline');
  fs.appendFileSync(path.join(folder,'commands.queue'),'qzverdict status\n');
  let status='';const statusEnd=Date.now()+3000;
  do {await pause(50);status=fs.readFileSync(path.join(folder,'console.log'),'utf8').slice(observedFrom);}
  while(!/QiZhangVerdict sessions=1,.*companion=required, vm=DENY,.*deviceRequired=true/.test(status)&&Date.now()<statusEnd);
  assert(/QiZhangVerdict sessions=1,.*companion=required, vm=DENY,.*deviceRequired=true/.test(status),'post-deadline console status must show the live strict session');
  assert(!a.ended,'valid client must still be connected at the status response');
  cases.push('valid report keeps account online for at least 22 seconds with strict server status');
  waits.push({case:'valid companion stays online beyond default deadline',elapsedMilliseconds:Date.now()-sustainedAt});
  const same=await connect('QVLegacyB','a');denied(same,'same IP and same device second account rejected','same IP and device');
  const b=await connect('QVLegacyB','b');allowed(b,'same IP second distinct device accepted');
  const c=await connect('QVLegacyC','c');allowed(c,'same IP third distinct device accepted');
  const fourth=await connect('QVLegacyD','d');denied(fourth,'default fourth concurrent account rejected','simultaneous');
  await close(a);
  const reuse=await connect('QVLegacyD','a');allowed(reuse,'disconnect releases IP and device concurrent slots');
  await close(b,c,reuse);
  const empty=await connect('QVLegacyA','a',{missingDevice:true});denied(empty,'strict default rejects missing device identifier','device identifier');
  const malformed=await connect('QVLegacyA','a',{malformed:true});denied(malformed,'malformed report rejected','malformed');
  const recovered=await connect('QVLegacyA','a');allowed(recovered,'invalid report does not permanently ban account');await close(recovered);
  const silent=await connect('QVLegacyA','a',{silent:true});denied(silent,'default required companion timeout enforced','timed out');
  assert(silent.challenge,'server sent a challenge to silent client');
  assert(silent.elapsed>=19000&&silent.elapsed<26000,'default 20-second timeout timing: '+silent.elapsed);
  waits.push({case:'default required report timeout',elapsedMilliseconds:silent.elapsed});
  const after=await connect('QVLegacyA','a');allowed(after,'timeout releases session and does not permanently ban account');await close(after);
  fs.appendFileSync(path.join(folder,'commands.queue'),'qzverdict status\n');
  await pause(600);
  const result={passed:true,cases,caseCount:cases.length,version,channel,registerChannel,defaultPolicyUnmodified:true,waits,loader:'Forge 14.23.5.2864',
    scope:'Real loopback TCP clients with synthetic self-reports; not a rendered companion, real VM, external anticheat or general gameplay compatibility test.'};
  fs.writeFileSync(path.join(folder,'protocol-result.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{for(const c of active)c.end('test finished');await pause(300);});
'''


def digest(path, algorithm="sha256"):
    return hashlib.new(algorithm, Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"QiZhangVerdict/0.2-112-validation"}), timeout=120) as response:
        return response.read()


def path_in_cache(value):
    directory = Path(value).resolve()
    directory.relative_to(CACHE.resolve())
    if directory == CACHE.resolve():
        raise ValueError("Use a new child directory")
    return directory


def free_memory():
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(name, ctypes.c_ulonglong) for name in ("totalPhys", "availPhys", "totalPage", "availPage", "totalVirtual", "availVirtual", "extended")]
    memory = MemoryStatus()
    memory.length = ctypes.sizeof(memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise OSError("Cannot verify free physical memory")
    if memory.availPhys < 4 * 1024**3:
        raise RuntimeError("Java deferred: fewer than 4 GiB physical memory available")
    return memory.availPhys


def load_fixture(args):
    directory = path_in_cache(args.directory)
    meta = json.loads((directory / MARKER).read_text("utf-8"))
    assert meta["minecraft"] == "1.12.2" and meta["forge"] == FORGE
    assert digest(directory / "loader-installer.jar") == INSTALLER_SHA
    assert digest(directory / "mods" / GUARD.name) == GUARD_SHA
    return directory, meta


def stage(args):
    directory = path_in_cache(args.directory)
    if directory.exists():
        raise ValueError("Stage requires a NEW directory")
    if digest(GUARD) != GUARD_SHA:
        raise ValueError("Guard artifact differs from pinned build")
    official = fetch(INSTALLER_URL + ".sha1").decode("ascii").strip().split()[0]
    downloads = CACHE / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    installer = downloads / ("forge-" + FORGE + "-installer.jar")
    if not installer.exists():
        installer.write_bytes(fetch(INSTALLER_URL))
    assert digest(installer, "sha1") == official and digest(installer) == INSTALLER_SHA
    manifest_url = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
    manifest = json.loads(fetch(manifest_url))
    entry = next(v for v in manifest["versions"] if v["id"] == "1.12.2")
    raw = fetch(entry["url"])
    assert hashlib.sha1(raw).hexdigest() == entry["sha1"]
    version = json.loads(raw)
    vanilla = version["downloads"]["server"]
    server = downloads / "minecraft-server-1.12.2.jar"
    if not server.exists():
        server.write_bytes(fetch(vanilla["url"]))
    assert digest(server, "sha1") == vanilla["sha1"] and server.stat().st_size == vanilla["size"]
    directory.mkdir(parents=True)
    (directory / "mods").mkdir()
    (directory / "config").mkdir()
    shutil.copy2(installer, directory / "loader-installer.jar")
    shutil.copy2(server, directory / "minecraft_server.1.12.2.jar")
    shutil.copy2(GUARD, directory / "mods" / GUARD.name)
    (directory / "protocol-112.cjs").write_text(PROTOCOL, encoding="utf-8")
    (directory / "official-minecraft-version.json").write_bytes(raw)
    meta = {"product":"QiZhangVerdict", "minecraft":"1.12.2", "forge":FORGE,
            "createdUtc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()), "java":str(Path(args.java).resolve()),
            "guard":{"path":str(GUARD),"sha256":GUARD_SHA,"bytes":GUARD.stat().st_size},
            "installer":{"url":INSTALLER_URL,"checksumUrl":INSTALLER_URL+".sha1","officialSha1":official,"sha256":INSTALLER_SHA,"bytes":installer.stat().st_size},
            "minecraftServer":dict(vanilla,sha256=digest(server),versionMetadataUrl=entry["url"],versionMetadataSha1=entry["sha1"]),
            "port":args.port,"prepared":False,"stageInvokedJava":False,
            "helperSha256":digest(__file__),"protocolSha256":digest(directory/"protocol-112.cjs")}
    write_json(directory / MARKER, meta)
    print(json.dumps({"staged":str(directory),"javaExecuted":False,"guardSha256":GUARD_SHA}),flush=True)


def install(args):
    directory, meta = load_fixture(args)
    if meta["prepared"] or (directory / "install-result.json").exists():
        raise ValueError("Preserve existing installer evidence; use a new fixture")
    if not args.accept_eula:
        raise ValueError("An isolated setup requires --accept-eula")
    before = free_memory()
    command = [meta["java"],"-Xmx1024M","-Djava.awt.headless=true","-jar","loader-installer.jar","--installServer"]
    started = time.time()
    with (directory / "install-console.log").open("wb") as console:
        process = subprocess.run(command,cwd=directory,stdout=console,stderr=subprocess.STDOUT,timeout=900,creationflags=NO_WINDOW)
    entry = directory / ("forge-" + FORGE + ".jar")
    result = {"exitCode":process.returncode,"elapsedSeconds":round(time.time()-started,2),"command":command,"freeBytesBeforeJava":before,"entryFound":entry.exists(),"helperSha256":digest(__file__)}
    write_json(directory / "install-result.json", result)
    if process.returncode != 0 or not entry.exists():
        raise RuntimeError("Official Forge installer did not produce expected entry; inspect preserved log")
    (directory/"eula.txt").write_text("eula=true\n",encoding="ascii")
    (directory/"server.properties").write_text("server-ip=127.0.0.1\nserver-port="+str(meta["port"])+"\nonline-mode=false\nlevel-name=world\nlevel-type=FLAT\ngenerator-settings=3;minecraft:bedrock,2*minecraft:dirt,minecraft:grass;1;\nspawn-protection=0\nview-distance=3\nmax-players=10\nenable-command-block=false\nnetwork-compression-threshold=256\nmax-tick-time=60000\n",encoding="ascii")
    meta.update(prepared=True,serverEntry=entry.name,entrySha256=digest(entry),installerExitCode=process.returncode)
    write_json(directory/MARKER,meta)
    print(json.dumps(result),flush=True)


def run(args):
    directory, meta = load_fixture(args)
    if not meta["prepared"] or (directory/"smoke-result.json").exists():
        raise ValueError("Needs installed fixture without previous run evidence")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1",meta["port"]))
    before = free_memory()
    java_version = subprocess.check_output([meta["java"],"-version"],stderr=subprocess.STDOUT,creationflags=NO_WINDOW).decode("utf-8","replace").strip()
    command = [meta["java"],"-Xms256M","-Xmx1536M","-XX:+UseG1GC","-Dfile.encoding=UTF-8","-jar",meta["serverEntry"],"nogui"]
    (directory/"commands.queue").write_text("",encoding="utf-8")
    logfile=directory/"console.log"
    start=time.time(); done=False; status=False; protocol=None; protocol_log=None; offset=0; timed_out=False; failure=None; policy_before=None
    with logfile.open("wb") as console:
        server=subprocess.Popen(command,cwd=directory,stdin=subprocess.PIPE,stdout=console,stderr=subprocess.STDOUT,creationflags=NO_WINDOW)
        (directory/"owned-server.pid").write_text(str(server.pid),encoding="ascii")
        def send(text):
            server.stdin.write((text+"\n").encode("utf-8"));server.stdin.flush()
        try:
            deadline=time.time()+210
            while server.poll() is None and time.time()<deadline:
                text=logfile.read_text("utf-8",errors="replace")
                if re.search(r'Done \([0-9.]+s\)!',text):
                    done=True;break
                time.sleep(.2)
            if not done:
                raise RuntimeError("Server failed to reach Done before deadline")
            old=len(text);send("qzverdict status")
            deadline=time.time()+10
            while server.poll() is None and time.time()<deadline:
                text=logfile.read_text("utf-8",errors="replace")
                if re.search(r'QiZhangVerdict sessions=0,.*companion=required, vm=DENY,.*deviceRequired=true',text[old:]):
                    status=True;break
                time.sleep(.1)
            if not status:
                raise RuntimeError("Strict console status did not succeed")
            policy=directory/"config/qizhangverdict/guard.properties"
            policy_before=digest(policy)
            if args.protocol:
                protocol_log=(directory/"protocol-console.log").open("wb")
                env=dict(os.environ,NODE_PATH=str(NODE_MODULES))
                protocol=subprocess.Popen([str(NODE),str(directory/"protocol-112.cjs"),"1.12.2",str(meta["port"]),str(directory)],cwd=directory,env=env,stdout=protocol_log,stderr=subprocess.STDOUT,creationflags=NO_WINDOW)
                deadline=time.time()+160
                while protocol.poll() is None and server.poll() is None and time.time()<deadline:
                    queued=(directory/"commands.queue").read_text("utf-8")
                    for line in queued[offset:].splitlines():
                        if line:send(line)
                    offset=len(queued)
                    time.sleep(.05)
                if protocol.poll() is None:
                    protocol.kill();protocol.wait();timed_out=True
                if protocol.returncode != 0:
                    raise RuntimeError("Native-channel TCP fixture failed; inspect retained protocol-console.log")
            send("qzverdict status");time.sleep(.6)
        except Exception as error:
            failure=str(error)
        finally:
            if protocol is not None and protocol.poll() is None:
                protocol.kill();protocol.wait()
            if protocol_log:protocol_log.close()
            if server.poll() is None:
                try:send("stop");server.wait(timeout=60)
                except Exception:
                    server.kill();server.wait();timed_out=True
            server.stdin.close()
    text=logfile.read_text("utf-8",errors="replace")
    policy=directory/"config/qizhangverdict/guard.properties"
    tcp_path=directory/"protocol-result.json"
    tcp=json.loads(tcp_path.read_text("utf-8")) if tcp_path.exists() else None
    normal_stop=server.returncode==0 and "Stopping server" in text and "Saving chunks for level" in text
    result={"product":"QiZhangVerdict","minecraft":"1.12.2","forge":FORGE,"artifactVersion":"0.2.0-dev","license":"GPL-3.0-only",
            "guardSha256":GUARD_SHA,"serverEntrySha256":digest(directory/meta["serverEntry"]),"java":meta["java"],"javaVersion":java_version,"javaExecutableSha256":digest(meta["java"]),
            "command":command,"freeBytesBeforeJava":before,"runtime":str(directory),"helperSha256":digest(__file__),"protocolSha256":digest(directory/"protocol-112.cjs"),
            "started":done,"strictConsoleStatus":status,"serverExitCode":server.returncode,"normalStop":normal_stop,"elapsedSeconds":round(time.time()-start,2),"timedOut":timed_out,
            "protocolRequested":args.protocol,"protocolExitCode":protocol.returncode if protocol else None,"protocol":tcp,
            "defaultPolicyBeforeSha256":policy_before,"defaultPolicyAfterSha256":digest(policy) if policy.exists() else None,"defaultPolicyUnmodified":policy_before is not None and policy_before==digest(policy),
            "statusResponses":[line for line in text.splitlines() if "QiZhangVerdict sessions=" in line and "started:" not in line],
            "warnings":[line for line in text.splitlines() if "/WARN]" in line],"errors":[line for line in text.splitlines() if "/ERROR]" in line],"failure":failure,
            "passed":done and status and normal_stop and not timed_out and failure is None and (not args.protocol or bool(tcp and tcp.get("passed"))),
            "scope":"Official Forge dedicated adapter; synthetic TCP reports if requested. No rendered client, real VM detection, cheat accuracy, external anticheat, modpack or performance acceptance."}
    write_json(directory/"smoke-result.json",result)
    print(json.dumps({k:result[k] for k in ("runtime","started","strictConsoleStatus","serverExitCode","protocolExitCode","passed","failure")}),flush=True)
    if not result["passed"]:raise SystemExit(1)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="action",required=True)
    stage_p=sub.add_parser("stage");stage_p.add_argument("directory");stage_p.add_argument("--java",default=str(JAVA));stage_p.add_argument("--port",type=int,default=25641);stage_p.set_defaults(func=stage)
    install_p=sub.add_parser("install");install_p.add_argument("directory");install_p.add_argument("--accept-eula",action="store_true");install_p.set_defaults(func=install)
    run_p=sub.add_parser("run");run_p.add_argument("directory");run_p.add_argument("--protocol",action="store_true");run_p.set_defaults(func=run)
    args=parser.parse_args();args.func(args)


if __name__=="__main__":main()
