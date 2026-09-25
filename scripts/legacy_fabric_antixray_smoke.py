#!/usr/bin/env python3
"""Isolated Fabric 1.16.5 / Drex AntiXray 1.1.0 integration fixture.

Stage performs file operations only. It never starts Java, reuses accounts/worlds,
changes the accepted Java 8 fixture, or rebuilds the frozen Verdict artifact.
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
import sys
import time
import urllib.request
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
TEMP = Path(r"E:\CodexTemp\QiZhangVerdict")
CACHE = TEMP / "legacy-fabric-antixray"
BASE = TEMP / "legacy-runtime/fabric-1.16.5-guard-01"
JAVA = Path(r"E:\CodexTemp\mods-danzi\java\jdk-17.0.20.1+1-jre\bin\java.exe")
NODE = Path(r"E:\CodexTemp\Codex\RuntimeCache\codex-primary-runtime\dependencies\node\bin\node.exe")
MODULES = TEMP / "legacy-protocol-qa/node_modules"
GUARD = ROOT / "platforms/1.16.5/fabric/build/libs/qizhangverdict-fabric-1.16.5-0.2.0-dev.jar"
GUARD_SHA = "d9bb0837f97ccf30c4b0f19a5cd8b65197eab4b2c5137b246b0e56c94fe6aae6"
API_SHA = "3df8dd503f35aa0ac9fab8ad9f9a369fdfd0b1ab544af19a3d626d948fb4586c"
ANTI_SHA = "7c8d22a2e9c8d0f88a33ce76cdb7bade18c63bb2a5cc9b3a11991bd28c742f43"
COMPAT_SHA = "fa72bb5e4424bc8ffb9cda83298f8c27b704dd36c3bd413660a3a58d69cc9484"
COMPAT_VERSION = "1.1.0-qzcompat.1"
SOURCE_COMMIT = "a113ce0b0616052de80ca8719986a09849348ce0"
SOURCE_URL = f"https://raw.githubusercontent.com/DrexHD/AntiXray/{SOURCE_COMMIT}/"
SOURCE_FILES = [
    "src/main/resources/data/antixray.toml",
    "src/main/resources/fabric.mod.json",
    "src/main/java/me/drex/antixray/AntiXray.java",
    "src/main/java/me/drex/antixray/config/Config.java",
    "src/main/java/me/drex/antixray/config/WorldConfig.java",
    "src/main/java/me/drex/antixray/util/ChunkPacketBlockControllerAntiXray.java",
    "src/main/java/me/drex/antixray/mixin/ClientboundLevelChunkPacketMixin.java",
    "src/main/java/me/drex/antixray/mixin/LevelMixin.java",
    "src/main/java/me/drex/networking/mixin/ConnectionMixin.java",
]
MARKER = ".qizhang-fabric-antixray.json"
EXPECTED_POLICY = {
    "limits.max-online-per-ip": "3", "limits.max-online-per-ip-device": "1", "limits.max-accounts-per-ip": "5",
    "limits.account-window-hours": "720", "limits.attempts-per-minute": "20", "ip.allow": "", "ip.deny": "",
    "companion.required": "true", "companion.timeout-seconds": "20", "vm.action": "DENY",
    "blacklist.action": "DENY", "sanctions.on-deny": "BAN", "device.required": "true",
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def record(path):
    path = Path(path)
    return {"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size}


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def memory_available_gib():
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (key, ctypes.c_ulonglong) for key in
            ("totalPhysical", "availablePhysical", "totalPage", "availablePage", "totalVirtual", "availableVirtual", "availableExtended")]
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("GlobalMemoryStatusEx failed")
    return status.availablePhysical / 1024**3


def isolated_directory(value):
    path = Path(value).resolve()
    path.relative_to(CACHE.resolve())
    if path == CACHE.resolve():
        raise ValueError("Use a new child directory of the dedicated integration cache")
    return path


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "QiZhangVerdict-integration-QA/0.2"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def checked_copy(source, target, expected=None):
    source, target = Path(source), Path(target)
    actual = digest(source)
    if expected and actual != expected:
        raise ValueError("Input SHA256 mismatch: " + str(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError("Refusing to overwrite: " + str(target))
    shutil.copyfile(source, target)
    if digest(target) != actual:
        raise ValueError("Copied bytes differ: " + str(target))
    return {"source": str(source), **record(target)}


def stage(args):
    directory = isolated_directory(args.directory)
    if directory.exists():
        raise ValueError("Stage requires a NEW directory")
    if not args.accept_eula:
        raise ValueError("Pass --accept-eula for this already-authorized isolated server test")
    lock = get_json(ROOT / "integrations/legacy-dependencies.lock.json")
    artifact = next(a for a in lock["artifacts"] if a["key"] == "antixray-fabric-1.16.5")
    assert artifact["hashes"]["sha256"] == ANTI_SHA
    base_marker = get_json(BASE / ".qizhang-verdict-smoke.json")
    assert base_marker["prepared"] and base_marker["minecraft"] == "1.16.5"
    assert base_marker["loader_version"] == "0.16.14"
    api = Path(base_marker["fabric_api"]["path"])
    anti = TEMP / "legacy-integration-research/binary-audit-01/jars" / artifact["filename"]
    for path, expected in [(GUARD, GUARD_SHA), (api, API_SHA), (anti, ANTI_SHA)]:
        if digest(path) != expected:
            raise ValueError("Frozen input mismatch: " + str(path))
    if hashlib.sha512(anti.read_bytes()).hexdigest() != artifact["hashes"]["sha512"]:
        raise ValueError("AntiXray official SHA512 mismatch")
    anti_version, anti_sha = "1.1.0", ANTI_SHA
    if args.compat_jar:
        anti = Path(args.compat_jar).resolve()
        anti_version, anti_sha = COMPAT_VERSION, COMPAT_SHA
        if digest(anti) != anti_sha:
            raise ValueError("Only the separately reviewed deterministic compatibility output is accepted")
    with zipfile.ZipFile(api) as jar:
        assert len(get_json_from_jar(jar, "fabric.mod.json")["jars"]) == 44
        assert jar.testzip() is None
    with zipfile.ZipFile(anti) as jar:
        default_config = jar.read("data/antixray.toml")
        assert get_json_from_jar(jar, "fabric.mod.json")["version"] == anti_version
        assert jar.testzip() is None
    assert JAVA.is_file() and (JAVA.parent.parent / "release").is_file()
    java_release = (JAVA.parent.parent / "release").read_text(encoding="utf-8")
    assert 'JAVA_VERSION="17.' in java_release
    # Allowlist immutable installation inputs only: no .fabric cache, configs,
    # world, player data, ops, sanctions, account cache, logs or old QA output.
    directory.mkdir(parents=True)
    files = []
    for name in ("server.jar", "fabric-server-launch.jar", "fabric-server-launcher.properties"):
        files.append(checked_copy(BASE / name, directory / name))
    for source in sorted((BASE / "libraries").rglob("*")):
        if source.is_file():
            if source.is_symlink():
                raise ValueError("Symlink input rejected")
            files.append(checked_copy(source, directory / source.relative_to(BASE)))
    files.extend([
        checked_copy(GUARD, directory / "mods" / GUARD.name, GUARD_SHA),
        checked_copy(api, directory / "mods" / "fabric-api-0.42.0+1.16.jar", API_SHA),
        checked_copy(anti, directory / "mods" / anti.name, anti_sha),
    ])
    with socket.socket() as check:
        check.bind(("127.0.0.1", args.port))
    # This exact flat world has no naturally generated ores or structures.
    properties = {
        "server-ip": "127.0.0.1", "server-port": args.port, "online-mode": "false", "enable-rcon": "false",
        "level-name": "world", "level-type": "flat", "generator-settings": "",
        "generate-structures": "false", "gamemode": "survival", "difficulty": "peaceful", "spawn-protection": 0,
        "spawn-animals": "false", "spawn-monsters": "false", "spawn-npcs": "false", "view-distance": 2,
        "max-players": 3, "max-tick-time": 60000, "enable-command-block": "false", "level-seed": 11650110,
    }
    (directory / "server.properties").write_text("\n".join(f"{k}={v}" for k, v in properties.items()) + "\n", encoding="utf-8")
    (directory / "eula.txt").write_text("eula=true\n", encoding="ascii")
    (directory / "evidence").mkdir()
    (directory / "evidence/upstream-default-antixray.toml").write_bytes(default_config)
    source_cache = CACHE / "source" / SOURCE_COMMIT
    source_cache.mkdir(parents=True, exist_ok=True)
    sources = []
    for name in SOURCE_FILES:
        path = source_cache / name.replace("/", "__")
        if not path.exists():
            path.write_bytes(fetch(SOURCE_URL + name))
        sources.append({"url": SOURCE_URL + name, **record(path)})
        if name == SOURCE_FILES[0] and path.read_bytes() != default_config:
            raise ValueError("Exact-source default config does not match embedded release config")
    plan = {
        "schemaVersion": 1, "profile": "fabric-1.16.5-antixray-1.1.0-java17", "status": "PREPARED_NOT_RUN",
        "runtimeVerified": False, "stageExecutedJava": False, "directory": str(directory), "port": args.port,
        "antiXrayVersion": anti_version, "antiXraySha256": anti_sha, "independentCompatFork": bool(args.compat_jar),
        "java": str(JAVA), "javaRelease": record(JAVA.parent.parent / "release"), "maximumHeapMiB": 1536,
        "minimumAvailableGiBBeforeEachJava": 3.5, "availableGiBAtStageOnly": round(memory_available_gib(), 3),
        "node": str(NODE), "nodeModules": str(MODULES), "harness": record(__file__),
        "lock": record(ROOT / "integrations/legacy-dependencies.lock.json"), "copiedInputs": files, "officialSources": sources,
        "upstreamDefaultConfig": record(directory / "evidence/upstream-default-antixray.toml"),
        "baselineNotModified": str(BASE), "strictPolicy": "Generate complete defaults; compare every value plus raw hash before/after; no relax/reload overrides",
        "bootstrap": "Start Java17, let exact AntiXray and Verdict generate config, save copies, status, normal stop; require exit 0",
        "testConfigChange": "Only [overworld] engineMode 2 -> 1 in the generated antixray.toml; enabled remains true",
        "oreScene": {"chunk": [0, 0], "hiddenDiamond": [8, 32, 8], "exposedDiamond": [12, 32, 8],
                     "exposedNeighborAir": [13, 32, 8], "stoneControl": [9, 32, 8]},
        "runtimeAssertions": [
            "Exact loader, API, Verdict and AntiXray loaded under Java17 with unchanged input hashes",
            "Generated AntiXray defaults equal release resource and selected overworld engineMode is 1",
            "Verdict entire default policy equals expected strict values and never changes",
            "A synthetic protocol player with held report and operator privilege cannot run /say sentinel",
            "Same player after a valid Wire2 report may execute /say, is then deopped and returns to survival",
            "Report associates the exact synthetic UUID and scoped synthetic device; remain online >20 seconds",
            "Console verifies true hidden/exposed diamonds, their surrounding stone/air, and stone control",
            "Capture an actual map_chunk packet; decode positions with prismarine-chunk 1.41.0 for protocol 754",
            "Require hidden diamond position -> stone, exposed diamond -> diamond_ore, adjacent stone -> stone",
            "Opening one stone neighbor gives the legitimate client an unhidden diamond block update",
            "Normal protocol disconnect then console stop; both exit codes 0 and port released",
        ],
        "boundaries": ["No graphical client or real VM probe", "Synthetic report is not a trusted device proof",
                       "No Grim or movement/combat checks", "No inference about Java8 AntiXray compatibility",
                       "No rebuilt Verdict; later core source fixes are absent from this frozen JAR",
                       "Controlled ore correctness, not throughput or adversarial coverage"],
    }
    write_json(directory / MARKER, plan)
    print(json.dumps({"status": plan["status"], "marker": str(directory / MARKER), "copiedFiles": len(files),
                      "guardSha256": GUARD_SHA, "availableGiB": plan["availableGiBAtStageOnly"]}, indent=2))


def get_json_from_jar(jar, member):
    return json.loads(jar.read(member))


PROTOCOL_JS = r'''
'use strict';
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const assert = require('node:assert/strict');
const mc = require('minecraft-protocol');
const nbt = require('prismarine-nbt');
const Chunk = require('prismarine-chunk')('1.16.5');
const data = require('minecraft-data')('1.16.5');
const [folder, portText] = process.argv.slice(2);
const port = Number(portText), name = 'QVAxGate';
const pause = ms => new Promise(r => setTimeout(r, ms));
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const evidence = path.join(folder, 'evidence');
const logFile = path.join(folder, 'integration-console.log');
const readLog = () => fs.readFileSync(logFile, 'utf8');
const cases = [];
const result = {passed:false, syntheticProtocolClient:true, graphicalClient:false, version:'1.16.5', cases};
let client, ended = false, kick = '', challenge, device, capture = false, packet, updates = [];
const packetCounts = {}, chunkReceipts = [];
let currentPosition={x:0,y:0,z:0}, currentYaw=0, currentPitch=0;
const clients = new Set();
function check(ok, label) { assert(ok, label); cases.push(label); console.log('PASS ' + label); }
async function until(predicate, label, timeout=12000) {
  const end = performance.now() + timeout;
  while (!predicate()) { assert(performance.now()<end, 'timeout: '+label); await pause(40); }
}
async function command(text, expected, timeout=12000) {
  const before=readLog().length;
  fs.appendFileSync(path.join(folder, 'commands.queue'), text+'\n');
  if(expected) await until(()=>readLog().slice(before).includes(expected), text, timeout);
  else await pause(250);
  return readLog().slice(before);
}
function str(v) { const b=Buffer.from(v), n=Buffer.alloc(2); n.writeUInt16BE(b.length);return Buffer.concat([n,b]); }
function list(v) { const n=Buffer.alloc(2);n.writeUInt16BE(v.length);return Buffer.concat([n,...v.map(str)]); }
function makeReport(b) {
  assert(b.subarray(0,6).equals(Buffer.from([0x51,0x5a,0x47,0x31,2,1])));
  const n=b.readUInt16BE(6), nonce=b.subarray(8,8+n).toString();
  const s=b.readUInt16BE(8+n), scope=b.subarray(10+n,10+n+s).toString();
  assert(n===64 && scope.length>0 && b.length===10+n+s);
  device=sha('synthetic-antixray-QA|'+scope+'|'+name);
  return Buffer.concat([Buffer.from([0x51,0x5a,0x47,0x31,2,2]),str(nonce),Buffer.from([1]),
                        list(['qizhangverdict']),list([]),list([]),str(device)]);
}
function offlineUUID(v) {
  const b=crypto.createHash('md5').update('OfflinePlayer:'+v).digest();b[6]=(b[6]&15)|48;b[8]=(b[8]&63)|128;
  const h=b.toString('hex');return [h.slice(0,8),h.slice(8,12),h.slice(12,16),h.slice(16,20),h.slice(20)].join('-');
}
function association() {
  const file=path.join(folder,'config','qizhangverdict','accounts.state');
  return fs.existsSync(file) && fs.readFileSync(file,'utf8').split(/\r?\n/).includes('D\t'+offlineUUID(name)+'\t'+device);
}
function nameAt(chunk, pos) {return data.blocksByStateId[chunk.getBlockStateId(pos)].name;}
function readChunk(p) {
  const chunk=new Chunk();chunk.load(p.chunkData,p.bitMap);if(p.biomes)chunk.loadBiomes(p.biomes);
  return chunk;
}
async function main() {
  const parsedLevel=await nbt.parse(fs.readFileSync(path.join(folder,'world','level.dat')));
  const worldgen=nbt.simplify(parsedLevel.parsed).Data.WorldGenSettings;
  const generator=worldgen.dimensions['minecraft:overworld'].generator;
  assert.equal(generator.type,'minecraft:flat','exact generator type, no silent fallback to noise');
  assert.deepEqual(generator.settings.layers,[{height:1,block:'minecraft:bedrock'},
    {height:2,block:'minecraft:dirt'},{height:1,block:'minecraft:grass_block'}]);
  assert.equal(worldgen.generate_features,0);
  result.worldGenerator={type:generator.type,layers:generator.settings.layers,generateFeatures:false};
  check(true,'saved level NBT confirms ore-free flat layers and structures disabled');
  // World controls are set before any player sees the target chunk.
  await command('gamerule spawnRadius 0');
  await command('gamerule doMobSpawning false');
  await command('setworldspawn 8 37 8');
  await command('forceload add 0 0');
  await command('fill 4 28 4 14 36 12 minecraft:stone');
  await command('setblock 8 32 8 minecraft:diamond_ore');
  await command('setblock 12 32 8 minecraft:diamond_ore');
  await command('setblock 13 32 8 minecraft:air');
  const real=[['hidden',[8,32,8],'diamond_ore'],['exposed',[12,32,8],'diamond_ore'],
              ['exposed_air',[13,32,8],'air'],['control',[9,32,8],'stone'],
              ...[[7,32,8],[8,31,8],[8,33,8],[8,32,7],[8,32,9]].map((p,i)=>['neighbor'+i,p,'stone'])];
  for(const [key,p,block] of real) await command(`execute if block ${p.join(' ')} minecraft:${block} run say AX_REAL_${key}`,`[Server] AX_REAL_${key}`);
  result.authoritativeScene=real.map(([role,position,block])=>({role,position,block,consoleVerified:true}));
  check(true,'authoritative hidden/exposed ore and six-face stone controls verified');
  client=mc.createClient({host:'127.0.0.1',port,username:name,auth:'offline',version:'1.16.5',checkTimeoutInterval:15000});
  clients.add(client);
  client.on('error',e=>{result.clientError=String(e)});
  client.on('kick_disconnect',p=>{kick=JSON.stringify(p)});
  client.on('end',()=>{ended=true;clients.delete(client)});
  client.on('packet',(_p,meta)=>{packetCounts[meta.name]=(packetCounts[meta.name]||0)+1});
  client.on('login',()=>{
    client.write('custom_payload',{channel:'minecraft:register',data:Buffer.from('qzguard:main')});
    client.write('settings',{locale:'en_us',viewDistance:2,chatFlags:0,chatColors:true,skinParts:127,mainHand:1});
  });
  client.on('position',p=>{
    const flags=p.flags||0;
    currentPosition={x:p.x+((flags&1)?currentPosition.x:0),y:p.y+((flags&2)?currentPosition.y:0),z:p.z+((flags&4)?currentPosition.z:0)};
    currentYaw=p.yaw+((flags&8)?currentYaw:0);currentPitch=p.pitch+((flags&16)?currentPitch:0);
    if(p.teleportId!==undefined)client.write('teleport_confirm',{teleportId:p.teleportId});
    // Vanilla's player movement handling updates chunk subscriptions. A protocol
    // fixture must send the normal post-teleport position, not only the ACK.
    client.write('position_look',{...currentPosition,yaw:currentYaw,pitch:currentPitch,onGround:false});
  });
  client.on('custom_payload',p=>{if(p.channel==='qzguard:main')challenge=p.data});
  client.on('map_chunk',p=>{
    if(chunkReceipts.length<120)chunkReceipts.push({x:p.x,z:p.z,afterReportCapture:capture,bytes:p.chunkData.length});
    if(capture && p.x===0 && p.z===0)packet=p;
  });
  client.on('block_change',p=>updates.push({kind:'single',position:p.location,stateId:p.type}));
  client.on('multi_block_change',p=>{
    for(const v of p.records) {
      const bits=Number(v), local=bits&4095;
      updates.push({kind:'multi',position:{x:p.chunkCoordinates.x*16+(local>>8),
        y:p.chunkCoordinates.y*16+(local&15),z:p.chunkCoordinates.z*16+((local>>4)&15)},stateId:Math.floor(bits/4096)});
    }
  });
  await until(()=>challenge || ended,'held challenge');
  check(!!challenge && !ended,'companion challenge received with default 20s timeout');
  await command('op '+name,'Made '+name+' a server operator');
  const before=readLog().length;
  client.write('chat',{message:'/say AX_BEFORE_REPORT'});
  await pause(1200);
  check(!readLog().slice(before).includes('['+name+'] AX_BEFORE_REPORT'),'operator command blocked before report');
  client.write('custom_payload',{channel:'qzguard:main',data:makeReport(challenge)});
  await pause(750);
  const after=readLog().length;
  client.write('chat',{message:'/say AX_AFTER_REPORT'});
  await until(()=>readLog().slice(after).includes('['+name+'] AX_AFTER_REPORT'),'operator command after report');
  check(!ended,'same operator command allowed after valid report');
  await command('deop '+name,'Made '+name+' no longer a server operator');
  await command('execute if entity @a[name='+name+',gamemode=survival] run say AX_SURVIVAL','[Server] AX_SURVIVAL');
  await until(association,'exact synthetic UUID device association');
  result.exactSyntheticUUIDDeviceAssociation=true;result.syntheticUUID=offlineUUID(name);
  const verifiedAt=performance.now();
  await command('tp '+name+' 512.5 70 512.5','Teleported '+name);
  await pause(1500);
  capture=true;packet=undefined;
  await command('tp '+name+' 8.5 37 8.5','Teleported '+name);
  await until(()=>packet,'fresh sent target chunk after report');
  const chunk=readChunk(packet);
  const positions=[['hidden',{x:8,y:32,z:8},'stone'],['exposed',{x:12,y:32,z:8},'diamond_ore'],
                   ['stoneControl',{x:9,y:32,z:8},'stone'],['exposedAir',{x:13,y:32,z:8},'air']];
  result.sentChunk={x:packet.x,z:packet.z,bitMap:packet.bitMap,groundUp:packet.groundUp,
    chunkDataSha256:sha(packet.chunkData),chunkDataBytes:packet.chunkData.length,
    positions:positions.map(([role,p,expected])=>({role,position:p,expected,actual:nameAt(chunk,p)}))};
  fs.writeFileSync(path.join(evidence,'sent-chunk-0-0.bin'),packet.chunkData);
  fs.writeFileSync(path.join(evidence,'sent-chunk-0-0.json'),JSON.stringify(result.sentChunk,null,2)+'\n');
  for(const item of result.sentChunk.positions)check(item.actual===item.expected,'sent chunk '+item.role+' = '+item.expected);
  updates=[];
  await command('setblock 8 32 7 minecraft:air');
  await until(()=>updates.some(p=>p.position.x===8 && p.position.y===32 && p.position.z===8 && data.blocksByStateId[p.stateId]?.name==='diamond_ore'),
              'real diamond revealed in block update after neighboring stone is removed');
  result.revealUpdates=updates.filter(p=>p.position.x===8&&p.position.y===32&&p.position.z===8)
    .map(p=>({...p,block:data.blocksByStateId[p.stateId]?.name}));
  check(true,'opening neighboring stone reveals true diamond in actual block update');
  while(performance.now()-verifiedAt<22000) {assert(!ended,'unexpected disconnect: '+kick);await pause(100);}
  result.onlineAfterReportSeconds=(performance.now()-verifiedAt)/1000;
  await command('execute if entity @a[name='+name+',gamemode=survival] run say AX_FRESH_SURVIVAL','[Server] AX_FRESH_SURVIVAL');
  await command('qzverdict status','QiZhangVerdict sessions=');
  check(!ended && association(),'legal player remains online beyond default timeout with exact device association and fresh survival query');
  client.end('integration QA complete');
  await until(()=>ended,'normal client close');
  result.normalClientDisconnect=true;result.passed=true;
}
main().catch(e=>{result.error=String(e.stack||e);process.exitCode=1;console.error(result.error)}).finally(async()=>{
  for(const c of clients)c.end('QA cleanup');
  await pause(250);
  result.packetCounts=packetCounts;result.chunkReceipts=chunkReceipts;
  fs.writeFileSync(path.join(folder,'protocol-result.json'),JSON.stringify(result,null,2)+'\n');
});
'''


def policy(directory):
    path = directory / "config/qizhangverdict/guard.properties"
    values = dict(line.split("=", 1) for line in path.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#"))
    if values != EXPECTED_POLICY:
        raise ValueError("Complete strict defaults changed")
    return {**record(path), "values": values, "matchesCompleteStrictDefaults": True}


def send(process, command):
    if process.poll() is not None:
        raise RuntimeError("Server exited before command: " + command)
    process.stdin.write((command + "\n").encode("utf-8"))
    process.stdin.flush()


def wait_log(process, log, fragment, offset=0, seconds=120):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if fragment in log.read_text(encoding="utf-8", errors="replace")[offset:]:
            return
        if process.poll() is not None:
            raise RuntimeError("Server exited before " + fragment)
        time.sleep(0.1)
    raise TimeoutError("Server log timeout: " + fragment)


def start_server(directory, phase, port):
    available = memory_available_gib()
    gate = {"phase": phase, "availableGiB": round(available, 4), "requiredGiB": 3.5, "passed": available >= 3.5}
    with (directory / "resource-gate.jsonl").open("a", encoding="utf-8") as out:
        out.write(json.dumps(gate) + "\n")
    if not gate["passed"]:
        raise RuntimeError("Insufficient physical memory; did not start Java")
    with socket.socket() as check:
        check.bind(("127.0.0.1", port))
    log = directory / f"{phase}-console.log"
    output = log.open("xb")
    args = [str(JAVA), "-Xms256M", "-Xmx1536M", "-jar", "fabric-server-launch.jar", "nogui"]
    try:
        process = subprocess.Popen(args, cwd=directory, stdin=subprocess.PIPE, stdout=output, stderr=subprocess.STDOUT,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception:
        output.close()
        raise
    return process, output, log, {"pid": process.pid, "args": args, "resourceGate": gate}


def stop_server(process, output):
    if process.poll() is None:
        try:
            send(process, "stop")
            process.wait(timeout=60)
        except Exception:
            process.terminate()
            process.wait(timeout=20)
    output.close()
    return process.returncode


def run(args):
    directory = isolated_directory(args.directory)
    marker = get_json(directory / MARKER)
    if marker.get("profile") != "fabric-1.16.5-antixray-1.1.0-java17":
        raise ValueError("Wrong fixture")
    if (directory / "result.json").exists() or (directory / "bootstrap-console.log").exists():
        raise ValueError("Do not rerun a used fixture; preserve failures in a new stage directory")
    for item in marker["copiedInputs"]:
        if digest(item["path"]) != item["sha256"]:
            raise ValueError("Staged input changed")
    for package, version in [("minecraft-protocol", "1.66.2"), ("prismarine-chunk", "1.41.0")]:
        if get_json(MODULES / package / "package.json")["version"] != version:
            raise ValueError("Unexpected protocol dependency")
    assert digest(ROOT / "scripts/legacy-protocol-qa/package-lock.json") == digest(MODULES.parent / "package-lock.json")
    assert not (directory / "config").exists(), "Fresh generated policy required"
    result = {"schemaVersion": 1, "passed": False, "profile": marker["profile"], "harness": record(__file__),
              "guardSha256": GUARD_SHA, "antiXraySha256": marker.get("antiXraySha256", ANTI_SHA),
              "antiXrayVersion": marker.get("antiXrayVersion", "1.1.0"), "independentCompatFork": marker.get("independentCompatFork", False),
              "java": str(JAVA), "phaseResults": []}
    shutil.copyfile(__file__, directory / "evidence/harness.py")
    process = output = protocol = None
    try:
        process, output, log, phase = start_server(directory, "bootstrap", marker["port"])
        result["phaseResults"].append(phase)
        wait_log(process, log, 'Done (', seconds=180)
        offset = len(log.read_text(encoding="utf-8", errors="replace"))
        send(process, "qzverdict status")
        wait_log(process, log, "QiZhangVerdict sessions=", offset, 15)
        result["policyBefore"] = policy(directory)
        config = directory / "config/antixray.toml"
        expected = (directory / "evidence/upstream-default-antixray.toml").read_bytes()
        if config.read_bytes() != expected:
            raise ValueError("Generated AntiXray config differs from fixed artifact resource")
        checked_copy(config, directory / "evidence/generated-default-antixray.toml")
        phase["exitCode"] = stop_server(process, output)
        process = output = None
        if phase["exitCode"] != 0:
            raise RuntimeError("Bootstrap did not exit normally")
        text = expected.decode("utf-8")
        assert text.count("engineMode = 2") == 1
        config.write_bytes(text.replace("engineMode = 2", "engineMode = 1").encode("utf-8"))
        result["configurationChange"] = {"onlyChange": "overworld.engineMode: 2 -> 1", "default": record(directory / "evidence/generated-default-antixray.toml"),
                                         "selected": checked_copy(config, directory / "evidence/selected-antixray.toml")}
        checked_copy(directory / "config/qizhangverdict/guard.properties", directory / "evidence/strict-guard.properties")
        process, output, log, phase = start_server(directory, "integration", marker["port"])
        result["phaseResults"].append(phase)
        wait_log(process, log, 'Done (', seconds=180)
        result["policyBeforeProtocol"] = policy(directory)
        assert result["policyBefore"]["sha256"] == result["policyBeforeProtocol"]["sha256"]
        (directory / "commands.queue").write_text("", encoding="utf-8")
        protocol_file = directory / "evidence/protocol.cjs"
        protocol_file.write_text(PROTOCOL_JS, encoding="utf-8")
        env = os.environ.copy()
        env["NODE_PATH"] = str(MODULES)
        env["TEMP"] = env["TMP"] = str(directory)
        with (directory / "protocol-console.log").open("xb") as out:
            protocol = subprocess.Popen([str(NODE), str(protocol_file), str(directory), str(marker["port"])],
                                        cwd=directory, env=env, stdout=out, stderr=subprocess.STDOUT,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            deadline = time.monotonic() + 180
            sent_lines = 0
            while protocol.poll() is None:
                lines = (directory / "commands.queue").read_text(encoding="utf-8").splitlines()
                for line in lines[sent_lines:]:
                    send(process, line)
                sent_lines = len(lines)
                if time.monotonic() > deadline:
                    raise TimeoutError("Protocol QA deadline")
                if process.poll() is not None:
                    raise RuntimeError("Server exited during protocol QA")
                time.sleep(0.05)
            result["protocolExitCode"] = protocol.returncode
        result["protocol"] = get_json(directory / "protocol-result.json")
        if not result["protocol"].get("passed"):
            result["error"] = result["protocol"].get("error", "Protocol assertions failed")
        result["policyAfter"] = policy(directory)
        result["strictPolicyUnchanged"] = result["policyBefore"]["sha256"] == result["policyAfter"]["sha256"]
        phase["exitCode"] = stop_server(process, output)
        process = output = None
        startup = log.read_text(encoding="utf-8", errors="replace")
        result["loadedComponents"] = {"antixray": "antixray " + result["antiXrayVersion"] in startup, "verdict": "qizhangverdict 0.2.0-dev" in startup,
                                      "fabric": "fabric 0.42.0+1.16" in startup, "loader": "Fabric Loader 0.16.14" in startup}
        with socket.socket() as check:
            check.bind(("127.0.0.1", marker["port"]))
        result["portReleased"] = True
        result["passed"] = (result["protocolExitCode"] == 0 and result["protocol"]["passed"] and result["strictPolicyUnchanged"]
                            and all(p["exitCode"] == 0 for p in result["phaseResults"]) and all(result["loadedComponents"].values()))
    except Exception as failure:
        result["error"] = str(failure)
    finally:
        if protocol is not None and protocol.poll() is None:
            protocol.terminate()
            protocol.wait(timeout=20)
            result["protocolForcedTermination"] = True
        if process is not None:
            result["cleanupServerExitCode"] = stop_server(process, output)
        result["artifacts"] = [record(p) for p in [directory / "bootstrap-console.log", directory / "integration-console.log",
                                                  directory / "protocol-console.log", directory / "protocol-result.json"] if p.exists()]
        write_json(directory / "result.json", result)
    print(json.dumps({"passed": result["passed"], "result": str(directory / "result.json"), "error": result.get("error")}, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("stage", help="Files only; never starts Java")
    prepare.add_argument("--directory", required=True)
    prepare.add_argument("--port", type=int, default=25673)
    prepare.add_argument("--accept-eula", action="store_true")
    prepare.add_argument("--compat-jar", help="Explicit opt-in to fixed independent 1.1.0-qzcompat.1 JAR; never replaces the official input")
    execute = sub.add_parser("run", help="Requires an allocated Java window; hard memory gate before each start")
    execute.add_argument("--directory", required=True)
    args = parser.parse_args()
    (stage if args.action == "stage" else run)(args)


if __name__ == "__main__":
    main()
