# SPDX-License-Identifier: GPL-3.0-only
"""Isolated official Forge 1.8.9 / Java 8 dedicated validation.

Prepare/stage never invoke Java. Stage clones only official dependencies from a
completed, stopped basic fixture; no worlds, player state or configuration are
reused. Run requires >=4 GiB free RAM and uses <=1.5 GiB heap. Only new child
directories of CACHE are accepted. The embedded protocol
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
import zipfile
import stat

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(r"E:\CodexTemp\QiZhangVerdict\legacy-runtime")
JAVA = Path(r"E:\CodexTemp\QiZhangVerdict\toolchains\jdk8\jdk8u504-b01\bin\java.exe")
NODE = Path(r"E:\CodexTemp\Codex\RuntimeCache\codex-primary-runtime\dependencies\node\bin\node.exe")
NODE_MODULES = Path(r"E:\CodexTemp\QiZhangGuard\bot\node_modules")
GUARD = ROOT / "platforms/1.8.9/forge/build/libs/qizhangverdict-forge-1.8.9-0.2.0-dev.jar"
GUARD_SHA = "f00943b06e87dbfc04e88336134ab4ae1a571a6e9b53924ab6bc06b311918424"
FORGE = "1.8.9-11.15.1.2318-1.8.9"
INSTALLER_URL = "https://maven.minecraftforge.net/net/minecraftforge/forge/" + FORGE + "/forge-" + FORGE + "-installer.jar"
INSTALLER_SHA = "f9fdf4945ca02d73ec6cc46300942f4e199e4add068877d517157b3677563656"
MARKER = ".qizhang-189-smoke.json"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

PROTOCOL = r'''
const mc = require('minecraft-protocol');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');
const [version, rawPort, folder] = process.argv.slice(2);
assert.equal(version, '1.8.9');
const protocolData = require('minecraft-data')(version);
assert.equal(protocolData.version.version,47);
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
  const s={name,joined:false,sent:false,ended:false,kick:'',error:'',challenge:false,chats:[],started:performance.now()};
  const c=mc.createClient({host:'127.0.0.1',port:Number(rawPort),version,username:name,auth:'offline',checkTimeoutInterval:30000,disableChatSigning:true});
  s.client=c; active.add(c);
  c.on('error',e=>{s.error=String(e);});
  c.on('chat',p=>{s.chats.push(JSON.stringify(p));});
  c.on('kick_disconnect',p=>{s.kick=JSON.stringify(p);});
  c.on('disconnect',p=>{s.kick=JSON.stringify(p);});
  c.on('end',()=>{s.ended=true;s.elapsed=performance.now()-s.started;active.delete(c);});
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
  const until=performance.now()+(opts.silent?26000:12000);
  while(!s.ended && !s.sent && !(opts.hold&&s.challenge) && (!opts.silent || performance.now()<until) && performance.now()<until)await pause(25);
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
  const gateOffset=fs.readFileSync(path.join(folder,'console.log'),'utf8').length;
  gate.client.chat('/say QZ189_PRE_GATE');await pause(600);
  assert(gate.chats.some(t=>t.includes('waiting for required companion report')),'pending OP receives the explicit Guard command-denial response');
  assert(!/\[QVLegacyGate\] QZ189_PRE_GATE/.test(fs.readFileSync(path.join(folder,'console.log'),'utf8').slice(gateOffset)),'pending operator command must not execute');
  gate.sent=true;gate.client.write('custom_payload',{channel,data:report(gate.challengeBytes,{name:gate.name,device:'gate'})});await pause(700);
  assert(!gate.ended && !gate.error,'operator report accepted');
  gate.client.chat('/say QZ189_POST_GATE');await pause(600);
  assert(/\[QVLegacyGate\] QZ189_POST_GATE/.test(fs.readFileSync(path.join(folder,'console.log'),'utf8').slice(gateOffset)),'verified operator command executes');
  cases.push('real operator command blocked while pending and restored after native QZGuard report');
  await close(gate);await command('deop QVLegacyGate');
  const a=await connect('QVLegacyA','a');allowed(a,'strict default companion report accepted on native Forge QZGuard channel');
  const observedFrom=fs.readFileSync(path.join(folder,'console.log'),'utf8').length;
  const sustainedAt=performance.now();await pause(22000);
  assert(!a.ended&&!a.error,'valid companion must survive beyond the default report deadline');
  fs.appendFileSync(path.join(folder,'commands.queue'),'qzverdict status\n');
  let status='';const statusEnd=performance.now()+3000;
  do {await pause(50);status=fs.readFileSync(path.join(folder,'console.log'),'utf8').slice(observedFrom);}
  while(!/QiZhangVerdict sessions=1,.*companion=required, vm=DENY,.*deviceRequired=true/.test(status)&&performance.now()<statusEnd);
  assert(/QiZhangVerdict sessions=1,.*companion=required, vm=DENY,.*deviceRequired=true/.test(status),'post-deadline console status must show the live strict session');
  assert(!a.ended,'valid client must still be connected at the status response');
  cases.push('valid report keeps account online for at least 22 seconds with strict server status');
  waits.push({case:'valid companion stays online beyond default deadline',elapsedMilliseconds:performance.now()-sustainedAt});
  const same=await connect('QVLegacyB','a');denied(same,'same IP and same device second account rejected','same IP and device');
  const b=await connect('QVLegacyB','b');allowed(b,'same IP second distinct device accepted');
  const c=await connect('QVLegacyC','c');allowed(c,'same IP third distinct device accepted');
  const fourth=await connect('QVLegacyD','d');denied(fourth,'default fourth concurrent account rejected','simultaneous');
  await close(a);
  const reuse=await connect('QVLegacyD','a');allowed(reuse,'disconnect releases IP and device concurrent slots');
  await close(b,c,reuse);
  const sixth=await connect('QVLegacyE','e');denied(sixth,'default sixth distinct rolling account rejected after five successful accounts','rolling account limit');
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
  assert.equal(cases.length,14,'all expected assertion groups must complete');
  const result={passed:true,cases,caseCount:cases.length,version,protocolVersion:47,protocolDataAlias:protocolData.version.minecraftVersion,channel,registerChannel,defaultPolicyUnmodified:true,waits,loader:'Forge 11.15.1.2318',
    scope:'Real loopback TCP clients with synthetic self-reports; not a rendered companion, real VM, external anticheat or general gameplay compatibility test.'};
  fs.writeFileSync(path.join(folder,'protocol-result.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}
if(process.argv.includes('--self-check')) {
  const serializer=mc.createSerializer({state:'play',isServer:false,version});
  const parser=mc.createDeserializer({state:'play',isServer:true,version});
  const nonce='a'.repeat(64), scope='b'.repeat(64);
  const challenge=Buffer.concat([Buffer.from([0x51,0x5a,0x47,0x31,2,1]),str(nonce),str(scope)]);
  const payload=report(challenge,{device:'offline-self-check'});
  for(const [name,data] of [[channel,payload],[registerChannel,Buffer.from(channel)]]) {
    const encoded=serializer.createPacketBuffer({name:'custom_payload',params:{channel:name,data}});
    const decoded=parser.parsePacketBuffer(encoded).data;
    assert.equal(decoded.name,'custom_payload');assert.equal(decoded.params.channel,name);assert.deepEqual(decoded.params.data,data);
  }
  const chat=serializer.createPacketBuffer({name:'chat',params:{message:'/say QZ189_SELF_CHECK'}});
  assert.equal(parser.parsePacketBuffer(chat).data.params.message,'/say QZ189_SELF_CHECK');
  console.log(JSON.stringify({passed:true,syntheticOnly:true,noTcpConnection:true,version,protocolVersion:47,protocolDataAlias:protocolData.version.minecraftVersion,packetChecks:['QZGuard report custom_payload','REGISTER custom_payload','legacy chat command'],minecraftProtocol:require('minecraft-protocol/package.json').version}));
} else main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{for(const c of active)c.end('test finished');await pause(300);});
'''


def digest(path, algorithm="sha256"):
    return hashlib.new(algorithm, Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def path_in_cache(value):
    # Check lexical ancestors before resolving: resolving first would hide junctions.
    directory = Path(os.path.abspath(value))
    for candidate in reversed((directory, *directory.parents)):
        if candidate.exists():
            info = candidate.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("Reparse points are not accepted")
    directory.relative_to(CACHE)
    if directory == CACHE:
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


DEFAULT_POLICY = (
    "# QiZhangVerdict: restart/reload after editing; IPs are literals or CIDRs, comma separated.\n"
    "limits.max-online-per-ip=3\nlimits.max-online-per-ip-device=1\nlimits.max-accounts-per-ip=5\nlimits.account-window-hours=720\n"
    "limits.attempts-per-minute=20\nip.allow=\nip.deny=\ncompanion.required=true\ncompanion.timeout-seconds=20\n"
    "vm.action=DENY\nblacklist.action=DENY\nsanctions.on-deny=BAN\ndevice.required=true\n"
).encode("utf-8")


def check_guard(path):
    if digest(path) != GUARD_SHA:
        raise ValueError("Guard differs from pinned build")
    with zipfile.ZipFile(path) as archive:
        if DEFAULT_POLICY not in archive.read("cn/qizhang/guard/core/GuardConfig.class"):
            raise ValueError("Expected complete policy is absent from the pinned Guard class")


def load_fixture(args):
    directory = path_in_cache(args.directory)
    meta = json.loads((directory / MARKER).read_text("utf-8"))
    assert meta["minecraft"] == "1.8.9" and meta["forge"] == FORGE
    assert meta["helperSha256"] == digest(__file__)
    assert meta["protocolSha256"] == digest(directory / "protocol-189.cjs")
    assert digest(directory / "loader-installer.jar") == INSTALLER_SHA
    assert digest(directory / meta["serverEntry"]) == meta["entrySha256"]
    assert digest(directory / "minecraft_server.1.8.9.jar", "sha1") == meta["minecraftServer"]["sha1"]
    for row in meta["copiedLibraries"]:
        assert digest(directory / row["file"]) == row["sha256"]
    check_guard(directory / "mods" / GUARD.name)
    return directory, meta


def prepare(args):
    directory = path_in_cache(args.directory)
    directory.mkdir(parents=True, exist_ok=False)
    check_guard(GUARD)
    script = directory / "protocol-189.cjs"
    script.write_text(PROTOCOL, encoding="utf-8")
    env = dict(os.environ, NODE_PATH=str(NODE_MODULES))
    process = subprocess.run([str(NODE), str(script), "1.8.9", "0", str(directory), "--self-check"],
                             env=env, capture_output=True, creationflags=NO_WINDOW, timeout=30)
    (directory / "protocol-self-check.log").write_bytes(process.stdout + process.stderr)
    result = {"javaExecuted": False, "tcpConnectionAttempted": False, "exitCode": process.returncode,
              "helperSha256": digest(__file__), "guardSha256": GUARD_SHA,
              "protocolSha256": digest(script), "result": json.loads(process.stdout) if process.returncode == 0 else None}
    write_json(directory / "preparation-result.json", result)
    print(json.dumps(result), flush=True)
    if process.returncode: raise SystemExit(process.returncode)


def stage(args):
    source = path_in_cache(args.from_fixture)
    directory = path_in_cache(args.directory)
    if directory.exists():
        raise ValueError("Stage requires a NEW directory")
    check_guard(GUARD)
    source_marker = source / ".qizhang-189-basic.json"
    meta = json.loads(source_marker.read_text("utf-8"))
    if meta["minecraft"] != "1.8.9" or meta["forge"] != FORGE or not meta["prepared"]:
        raise ValueError("Source is not a prepared 1.8.9 official fixture")
    smoke = json.loads((source / "smoke-result.json").read_text("utf-8"))
    if not smoke["normalStop"] or smoke["serverExitCode"] != 0 or not smoke["passed"]:
        raise ValueError("Source basic run did not complete successfully")
    if (source / "owned-server.pid").exists():
        pid = int((source / "owned-server.pid").read_text("ascii"))
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            raise ValueError("Source server PID still exists; wait for explicit handoff")
    entry = meta["serverEntry"]
    if Path(entry).name != entry or not entry.endswith(".jar"):
        raise ValueError("Unsafe source entry name")
    assert digest(source / "loader-installer.jar") == INSTALLER_SHA == meta["installer"]["sha256"]
    assert digest(source / "loader-installer.jar", "sha1") == meta["installer"]["officialSha1"]
    assert digest(source / entry) == meta["entrySha256"]
    assert digest(source / "minecraft_server.1.8.9.jar", "sha1") == meta["minecraftServer"]["sha1"]
    if not args.accept_eula:
        raise ValueError("Isolated setup requires --accept-eula")
    directory.mkdir(parents=True)
    (directory / "mods").mkdir(); (directory / "config").mkdir()
    copied = []
    for item in sorted((source / "libraries").rglob("*")):
        path_in_cache(item)
        if item.is_file():
            relative = item.relative_to(source)
            target = directory / relative; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            assert digest(item) == digest(target)
            copied.append({"file":relative.as_posix(),"sha256":digest(target),"bytes":target.stat().st_size})
    if not copied: raise ValueError("Source did not contain official installed libraries")
    for name in (entry, "minecraft_server.1.8.9.jar", "loader-installer.jar", "official-minecraft-version.json"):
        path_in_cache(source / name)
        shutil.copy2(source / name, directory / name)
    shutil.copy2(GUARD, directory / "mods" / GUARD.name)
    (directory / "protocol-189.cjs").write_text(PROTOCOL, encoding="utf-8")
    (directory / "eula.txt").write_text("eula=true\n", encoding="ascii")
    (directory / "server.properties").write_text(
        "server-ip=127.0.0.1\nserver-port=" + str(args.port) + "\nonline-mode=false\nlevel-name=world\n"
        "level-type=FLAT\ngenerator-settings=3;minecraft:bedrock,2*minecraft:dirt,minecraft:grass;1;\n"
        "spawn-protection=0\nview-distance=3\nmax-players=10\nenable-command-block=false\n"
        "network-compression-threshold=256\nmax-tick-time=60000\n", encoding="ascii")
    meta.update(product="QiZhangVerdict", port=args.port, sourceFixture=str(source),
                sourceMarkerSha256=digest(source_marker), sourceSmokeSha256=digest(source / "smoke-result.json"),
                createdUtc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()), copiedLibraries=copied,
                helperSha256=digest(__file__), protocolSha256=digest(directory / "protocol-189.cjs"),
                freshWorld=True, copiedConfiguration=False, copiedPlayerState=False, stageInvokedJava=False)
    write_json(directory / MARKER, meta)
    print(json.dumps({"staged":str(directory),"javaExecuted":False,"guardSha256":GUARD_SHA,"copiedLibraries":len(copied)}),flush=True)


def run(args):
    directory, meta = load_fixture(args)
    if not meta["prepared"] or (directory/"smoke-result.json").exists():
        raise ValueError("Needs installed fixture without previous run evidence")
    for name in ("world", "logs", "console.log", "protocol-result.json", "owned-server.pid",
                 "config/qizhangverdict", "ops.json", "usercache.json", "banned-players.json"):
        if (directory / name).exists():
            raise ValueError("Preserve any previous state/evidence; stage another fresh fixture: " + name)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1",meta["port"]))
    before = free_memory()
    java_version = subprocess.check_output([meta["java"],"-version"],stderr=subprocess.STDOUT,creationflags=NO_WINDOW).decode("utf-8","replace").strip()
    command = [meta["java"],"-Xms256M","-Xmx1536M","-XX:+UseG1GC","-Dfile.encoding=UTF-8","-jar",meta["serverEntry"],"nogui"]
    (directory/"commands.queue").write_text("",encoding="utf-8")
    logfile=directory/"console.log"
    start=time.monotonic(); done=False; status=False; protocol=None; protocol_log=None; offset=0; timed_out=False; failure=None; policy_before=None
    with logfile.open("wb") as console:
        server=subprocess.Popen(command,cwd=directory,stdin=subprocess.PIPE,stdout=console,stderr=subprocess.STDOUT,creationflags=NO_WINDOW)
        (directory/"owned-server.pid").write_text(str(server.pid),encoding="ascii")
        def send(text):
            server.stdin.write((text+"\n").encode("utf-8"));server.stdin.flush()
        try:
            deadline=time.monotonic()+210
            while server.poll() is None and time.monotonic()<deadline:
                text=logfile.read_text("utf-8",errors="replace")
                if re.search(r'Done \([0-9.]+s\)!',text):
                    done=True;break
                time.sleep(.2)
            if not done:
                raise RuntimeError("Server failed to reach Done before deadline")
            old=len(text);send("qzverdict status")
            deadline=time.monotonic()+10
            while server.poll() is None and time.monotonic()<deadline:
                text=logfile.read_text("utf-8",errors="replace")
                if re.search(r'QiZhangVerdict sessions=0,.*companion=required, vm=DENY,.*deviceRequired=true',text[old:]):
                    status=True;break
                time.sleep(.1)
            if not status:
                raise RuntimeError("Strict console status did not succeed")
            policy=directory/"config/qizhangverdict/guard.properties"
            policy_before=digest(policy)
            if policy.read_bytes() != DEFAULT_POLICY:
                raise RuntimeError("Server policy differs from every byte of pinned Guard defaults")
            if args.protocol:
                protocol_log=(directory/"protocol-console.log").open("wb")
                env=dict(os.environ,NODE_PATH=str(NODE_MODULES))
                protocol=subprocess.Popen([str(NODE),str(directory/"protocol-189.cjs"),"1.8.9",str(meta["port"]),str(directory)],cwd=directory,env=env,stdout=protocol_log,stderr=subprocess.STDOUT,creationflags=NO_WINDOW)
                deadline=time.monotonic()+180
                while protocol.poll() is None and server.poll() is None and time.monotonic()<deadline:
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
    result={"product":"QiZhangVerdict","minecraft":"1.8.9","forge":FORGE,"artifactVersion":"0.2.0-dev","license":"GPL-3.0-only",
            "guardSha256":GUARD_SHA,"serverEntrySha256":digest(directory/meta["serverEntry"]),"java":meta["java"],"javaVersion":java_version,"javaExecutableSha256":digest(meta["java"]),
            "command":command,"freeBytesBeforeJava":before,"runtime":str(directory),"helperSha256":digest(__file__),"protocolSha256":digest(directory/"protocol-189.cjs"),
            "started":done,"strictConsoleStatus":status,"serverExitCode":server.returncode,"normalStop":normal_stop,"elapsedSeconds":round(time.monotonic()-start,2),"timedOut":timed_out,
            "protocolRequested":args.protocol,"protocolExitCode":protocol.returncode if protocol else None,"protocol":tcp,
            "defaultPolicyBeforeSha256":policy_before,"defaultPolicyAfterSha256":digest(policy) if policy.exists() else None,"defaultPolicyUnmodified":policy_before is not None and policy.exists() and policy_before==digest(policy),
            "entirePolicyEqualsPinnedDefaults":policy.exists() and policy.read_bytes()==DEFAULT_POLICY,
            "statusResponses":[line for line in text.splitlines() if "QiZhangVerdict sessions=" in line and "started:" not in line],
            "warnings":[line for line in text.splitlines() if "/WARN]" in line],"errors":[line for line in text.splitlines() if "/ERROR]" in line],"failure":failure,
            "passed":done and status and normal_stop and not timed_out and failure is None and policy.exists() and policy.read_bytes()==DEFAULT_POLICY and (not args.protocol or bool(tcp and tcp.get("passed") and tcp.get("caseCount")==14)),
            "scope":"Official Forge dedicated adapter; synthetic TCP reports if requested. No rendered client, real VM detection, cheat accuracy, external anticheat, modpack or performance acceptance."}
    write_json(directory/"smoke-result.json",result)
    print(json.dumps({k:result[k] for k in ("runtime","started","strictConsoleStatus","serverExitCode","protocolExitCode","passed","failure")}),flush=True)
    if not result["passed"]:raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare"); prep.add_argument("directory"); prep.set_defaults(func=prepare)
    stage_p = sub.add_parser("stage"); stage_p.add_argument("directory")
    stage_p.add_argument("--from-fixture", required=True); stage_p.add_argument("--accept-eula", action="store_true")
    stage_p.add_argument("--port", type=int, default=25662); stage_p.set_defaults(func=stage)
    run_p = sub.add_parser("run"); run_p.add_argument("directory")
    run_p.add_argument("--protocol", action="store_true"); run_p.set_defaults(func=run)
    args = parser.parse_args(); args.func(args)


if __name__ == "__main__": main()
