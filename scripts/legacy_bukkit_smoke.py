"""Isolated legacy Paper compatibility checks; no production server is modified.

Downloads are selected from Paper's official API, checked against its SHA-256,
and pinned in the local cache receipt. The test leaves guard.properties unchanged.
Only synthetic offline players on a loopback listener are used.
"""
import argparse
import concurrent.futures
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
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(r"E:\CodexTemp\QiZhangVerdict\legacy-runtime")
VERSIONS = ["1.8.8", "1.12.2", "1.16.5", "1.18.2", "1.19.4"]
USER_AGENT = "QiZhangVerdict-compatibility-validation/0.1.0"
NODE = Path(r"E:\CodexTemp\Codex\RuntimeCache\codex-primary-runtime\dependencies\node\bin\node.exe")
NODE_MODULES = Path(r"E:\CodexTemp\QiZhangGuard\bot\node_modules")
JAVA17 = Path(r"E:\CodexTemp\mods-danzi\java\jdk-17.0.20.1+1-jre\bin\java.exe")
EXPECTED_PLUGIN = "b752cac809c9247c7f8fc14560d1f06236b12f627cb6342e6afa684712362141"

PROTOCOL = r'''
const mc = require('minecraft-protocol');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const [version, rawPort, folder] = process.argv.slice(2);
const modern = Number(version.split('.')[1]) >= 13;
const channel = modern ? 'qzguard:main' : 'QZGuard';
const registerChannel = modern ? 'minecraft:register' : 'REGISTER';
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
    try { const bytes=report(p.data,opts); s.sent=true; c.write('custom_payload',{channel,data:bytes}); }
    catch(e) {s.error=String(e);c.end('invalid server challenge');}
  });
  const until=Date.now()+(opts.silent?26000:12000);
  while(!s.ended && !s.sent && (!opts.silent || Date.now()<until) && Date.now()<until)await pause(25);
  if(!opts.silent)await pause(900);
  return s;
}
function snapshot(s){return {name:s.name,joined:s.joined,sent:s.sent,ended:s.ended,kick:s.kick,error:s.error,challenge:s.challenge};}
function allowed(s, title) {assert(s.joined&&s.sent&&!s.ended&&!s.error,title+': '+JSON.stringify(snapshot(s)));cases.push(title);}
function denied(s, title, fragment) {assert(s.ended,title+': still connected '+JSON.stringify(snapshot(s)));if(fragment)assert(s.kick.toLowerCase().includes(fragment.toLowerCase()),title+': '+s.kick);cases.push(title);}
async function close(...clients){for(const s of clients)if(s&&!s.ended)s.client.end('legacy test complete');await pause(500);}
async function main(){
  const a=await connect('QVLegacyA','a');allowed(a,'strict default companion report accepted on expected plugin channel');
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
  const result={passed:true,cases,caseCount:cases.length,version,channel,registerChannel,defaultPolicyUnmodified:true,waits,
    scope:'Real loopback TCP clients with synthetic self-reports; not a rendered companion, real VM, external anticheat or general gameplay compatibility test.'};
  fs.writeFileSync(path.join(folder,'protocol-result.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{for(const c of active)c.end('test finished');await pause(300);});
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def prepare_server(version):
    downloads = CACHE / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    receipt = downloads / ("paper-" + version + ".json")
    if receipt.exists():
        item = json.loads(receipt.read_text(encoding="utf-8"))
    else:
        api = "https://fill.papermc.io/v3/projects/paper/versions/" + version + "/builds"
        candidates = json.loads(fetch(api))
        latest = max(candidates, key=lambda entry: entry["id"])
        source = latest["downloads"]["server:default"]
        item = {"version": version, "distribution": "Paper", "build": latest["id"], "buildTime": latest["time"],
                "metadataUrl": api, "sourceUrl": source["url"], "sha256": source["checksums"]["sha256"],
                "size": source["size"], "filename": source["name"], "path": str(downloads / source["name"])}
        save(downloads / ("paper-" + version + "-build-metadata.json"), latest)
    target = Path(item["path"])
    if not target.exists():
        target.write_bytes(fetch(item["sourceUrl"]))
    if digest(target) != item["sha256"] or target.stat().st_size != item["size"]:
        raise ValueError("Official Paper checksum/size mismatch: " + version)
    save(receipt, item)
    return item


def prepare_java8():
    downloads = CACHE / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    receipt = downloads / "temurin-java8.json"
    if receipt.exists():
        item = json.loads(receipt.read_text(encoding="utf-8"))
    else:
        api = "https://api.adoptium.net/v3/assets/latest/8/hotspot?architecture=x64&image_type=jre&os=windows&vendor=eclipse"
        source = json.loads(fetch(api))[0]
        package = source["binary"]["package"]
        item = {"metadataUrl": api, "release": source["release_name"], "sourceUrl": package["link"],
                "sha256": package["checksum"], "filename": package["name"]}
    archive = downloads / item["filename"]
    if not archive.exists():
        archive.write_bytes(fetch(item["sourceUrl"]))
    if digest(archive) != item["sha256"]:
        raise ValueError("Official Temurin checksum mismatch")
    target = CACHE / "java8"
    target.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as contents:
        for name in contents.namelist():
            destination = (target / name).resolve()
            destination.relative_to(target.resolve())
            if name.endswith("/"):
                destination.mkdir(parents=True, exist_ok=True)
            elif destination.exists():
                if hashlib.sha256(destination.read_bytes()).digest() != hashlib.sha256(contents.read(name)).digest():
                    raise ValueError("Extracted Java cache differs from official archive: " + name)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(contents.read(name))
    java = next(target.glob("*/bin/java.exe"))
    item["javaExecutable"] = str(java)
    item["javaVersion"] = subprocess.run([str(java), "-version"], capture_output=True, text=True, check=True).stderr.strip()
    save(receipt, item)
    return item


def wait_for(log, marker, child, seconds=240):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        if marker in text:
            return text
        if child.poll() is not None:
            raise RuntimeError("Server exited before marker: " + marker + "; inspect " + str(log))
        time.sleep(.25)
    raise TimeoutError("Startup timeout; inspect " + str(log))


def run(version, guard_jar=None, expected_guard_sha256=None):
    source = prepare_server(version)
    java = Path(prepare_java8()["javaExecutable"]) if version in VERSIONS[:3] else JAVA17
    if not java.is_file():
        raise FileNotFoundError(java)
    plugin = Path(guard_jar).resolve() if guard_jar else ROOT / "bukkit/build/libs/qizhangverdict-bukkit-0.1.0.jar"
    plugin_hash = digest(plugin)
    expected = expected_guard_sha256.lower() if expected_guard_sha256 else (None if guard_jar else EXPECTED_PLUGIN)
    if expected and plugin_hash != expected:
        raise ValueError("Product hash differs from requested test target")
    port = 25600 + VERSIONS.index(version)
    with socket.socket() as test:
        test.bind(("127.0.0.1", port))
    folder = CACHE / ("paper-" + version + "-" + time.strftime("%Y%m%d-%H%M%S"))
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "plugins").mkdir()
    shutil.copy2(plugin, folder / "plugins" / plugin.name)
    if digest(folder / "plugins" / plugin.name) != plugin_hash or digest(plugin) != plugin_hash:
        raise ValueError("Product changed while creating isolated fixture")
    shutil.copy2(source["path"], folder / "server.jar")
    (folder / "eula.txt").write_text("eula=true\n", encoding="ascii")
    generator = ""
    if int(version.split(".")[1]) >= 13:
        generator = "generator-settings=" + json.dumps({"layers": [{"block": "minecraft:bedrock", "height": 1},
                    {"block": "minecraft:dirt", "height": 2}, {"block": "minecraft:grass_block", "height": 1}],
                    "biome": "minecraft:plains", "structures": {}}, separators=(",", ":")) + "\n"
    (folder / "server.properties").write_text(
        f"server-ip=127.0.0.1\nserver-port={port}\nonline-mode=false\nenforce-secure-profile=false\n"
        "spawn-protection=0\nview-distance=2\nsimulation-distance=2\nmax-players=10\n"
        "level-type=flat\ngenerate-structures=false\nlevel-seed=12955\ndifficulty=peaceful\n"
        "spawn-monsters=false\nspawn-animals=false\nnetwork-compression-threshold=256\n" + generator, encoding="utf-8")
    queue = folder / "commands.queue"
    queue.write_text("", encoding="utf-8")
    (folder / "protocol.cjs").write_text(PROTOCOL, encoding="utf-8")
    log = folder / "console.log"
    result = {"version": version, "source": source, "pluginFile": plugin.name, "pluginSha256": plugin_hash,
              "javaExecutable": str(java), "javaVersion": subprocess.run([str(java), "-version"], capture_output=True, text=True, check=True).stderr.strip(),
              "directory": str(folder), "serverHost": "127.0.0.1", "port": port, "onlineMode": False,
              "log": str(log), "defaultGuardPolicyUnmodified": True,
              "scope": "Unmodified strict Bukkit defaults, real TCP synthetic reports, startup/status/clean stop; no external anticheat or graphical companion validation."}
    result["protocolScriptSha256"] = digest(folder / "protocol.cjs")
    print(json.dumps({"starting": version, "directory": str(folder), "java": str(java)}), flush=True)
    started = time.monotonic()
    with log.open("w", encoding="utf-8") as output:
        child = subprocess.Popen([str(java), "-Xms256M", "-Xmx1024M", "-jar", "server.jar", "nogui"],
                                 cwd=folder, stdin=subprocess.PIPE, stdout=output, stderr=subprocess.STDOUT,
                                 text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            text = wait_for(log, "Done (", child)
            if "Enabling QiZhangVerdict" not in text or "companion=required, vm=DENY" not in text:
                raise AssertionError("Strict plugin did not start; inspect log")
            props = folder / "plugins/QiZhangVerdict/guard.properties"
            expected = {"limits.max-online-per-ip": "3", "limits.max-online-per-ip-device": "1", "limits.max-accounts-per-ip": "5",
                        "companion.required": "true", "device.required": "true", "vm.action": "DENY", "companion.timeout-seconds": "20"}
            actual = dict(line.split("=", 1) for line in props.read_text(encoding="utf-8").splitlines() if "=" in line and not line.startswith("#"))
            for key, value in expected.items():
                if actual.get(key) != value:
                    raise AssertionError("Unexpected policy value for " + key)
            result["policy"] = expected
            result["guardPropertiesSha256"] = digest(props)
            child.stdin.write("qzverdict status\n"); child.stdin.flush()
            result["startupPassed"] = True
            env = dict(os.environ, NODE_PATH=str(NODE_MODULES))
            with (folder / "protocol.log").open("w", encoding="utf-8") as test_log:
                tests = subprocess.Popen([str(NODE), str(folder / "protocol.cjs"), version, str(port), str(folder)],
                                         env=env, stdout=test_log, stderr=subprocess.STDOUT,
                                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                consumed = 0
                deadline = time.monotonic() + 150
                while tests.poll() is None:
                    commands = queue.read_text(encoding="utf-8").splitlines()
                    for command in commands[consumed:]:
                        child.stdin.write(command + "\n"); child.stdin.flush()
                    consumed = len(commands)
                    if time.monotonic() > deadline:
                        tests.kill(); tests.wait(); raise TimeoutError("Protocol run timed out")
                    time.sleep(.1)
            result["protocolExitCode"] = tests.returncode
            if tests.returncode:
                raise AssertionError("Protocol assertions failed; inspect " + str(folder / "protocol.log"))
            result["protocol"] = json.loads((folder / "protocol-result.json").read_text(encoding="utf-8"))
            if digest(props) != result["guardPropertiesSha256"]:
                raise AssertionError("Test changed guard policy")
            text = log.read_text(encoding="utf-8", errors="replace")
            result["statusCommandObserved"] = text.count("QiZhangVerdict sessions=") >= 2
            if not result["statusCommandObserved"]:
                raise AssertionError("No separate status command response")
            result["passed"] = True
        except Exception as error:
            result["passed"] = False
            result["failure"] = str(error)
        finally:
            if child.poll() is None:
                child.stdin.write("stop\n"); child.stdin.flush()
                try:
                    child.wait(timeout=90)
                except subprocess.TimeoutExpired:
                    child.kill(); child.wait(); result["forcedStop"] = True
            result["serverExitCode"] = child.returncode
            result["elapsedSeconds"] = round(time.monotonic() - started, 2)
    result["consoleSha256"] = digest(log)
    result["passed"] = result.get("passed", False) and result["serverExitCode"] == 0 and not result.get("forcedStop")
    save(folder / "result.json", result)
    print(json.dumps(result), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "run"])
    parser.add_argument("versions", nargs="*")
    parser.add_argument("--guard-jar", help="Explicit built/published plugin; default retains the frozen 0.1.0 artifact")
    parser.add_argument("--expected-guard-sha256", help="Reject artifact drift before starting any server")
    args = parser.parse_args()
    selected = args.versions or ["1.16.5", "1.18.2", "1.19.4", "1.12.2", "1.8.8"]
    if any(version not in VERSIONS for version in selected):
        parser.error("Supported versions: " + ", ".join(VERSIONS))
    if args.action == "prepare":
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for item in pool.map(prepare_server, selected):
                print(json.dumps(item), flush=True)
        print(json.dumps(prepare_java8()), flush=True)
    else:
        outcomes = [run(version, args.guard_jar, args.expected_guard_sha256) for version in selected]
        if any(not result["passed"] for result in outcomes):
            raise SystemExit(1)
