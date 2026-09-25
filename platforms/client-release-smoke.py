#!/usr/bin/env python3
"""Prepare/run the actual released Fabric 1.21.1 companion in an isolated Windows client.

Official Mojang/Fabric metadata is used; downloaded Minecraft files are hash checked.
This is an opt-in integration harness, never included in the mod or server artifacts.
"""
import argparse
import concurrent.futures
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(r"E:\CodexTemp\QiZhangGuard\client-release-smoke")
JAVA = Path(r"D:\Java\jdk-21\bin\java.exe")
MODULES = [Path(r"E:\CodexTemp\Gradle\QiZhang_Games\caches\modules-2\files-2.1"), Path(r"E:\CodexTemp\Gradle\XiuXianZhuan\caches\modules-2\files-2.1")]


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "QiZhangVerdict-companion-smoke/0.1"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha1(path):
    return hashlib.sha1(path.read_bytes()).hexdigest()


def artifact(path, url, expected, group=None, artifact_name=None, version=None):
    if path.exists() and (not expected or sha1(path) == expected):
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    if group:
        for cache in MODULES:
            prefix = cache / group / artifact_name / version
            if prefix.exists():
                for cached in prefix.glob("*/" + path.name):
                    if not expected or sha1(cached) == expected:
                        shutil.copy2(cached, path)
                        return path
    data = fetch(url)
    if expected and hashlib.sha1(data).hexdigest() != expected:
        raise ValueError("Download SHA-1 mismatch for " + path.name)
    path.write_bytes(data)
    return path


def allowed(library):
    if not library.get("rules"):
        return True
    decision = False
    for rule in library["rules"]:
        os_rule = rule.get("os", {})
        if os_rule.get("name", "windows") != "windows":
            continue
        if os_rule.get("arch", "x86_64") not in ("x86_64", "amd64"):
            continue
        decision = rule["action"] == "allow"
    return decision


def prepare():
    CACHE.mkdir(parents=True, exist_ok=True)
    game = CACHE / "game"
    (game / "mods").mkdir(parents=True, exist_ok=True)
    metadata = json.loads(Path(r"E:\CodexTemp\Gradle\QiZhang_Games\caches\fabric-loom\1.21.1\mojang_minecraft_info.json").read_text(encoding="utf-8"))
    profile = json.loads(fetch("https://meta.fabricmc.net/v2/versions/loader/1.21.1/0.16.14/profile/json"))
    save_json(CACHE / "fabric-profile.json", profile)
    client_meta = metadata["downloads"]["client"]
    client_jar = Path(r"E:\CodexTemp\Gradle\QiZhang_Games\caches\fabric-loom\1.21.1\minecraft-client.jar")
    if sha1(client_jar) != client_meta["sha1"]:
        raise ValueError("Cached Minecraft client does not match Mojang metadata")
    libraries = []
    natives = CACHE / "natives"
    natives.mkdir(exist_ok=True)
    for item in metadata["libraries"]:
        if not allowed(item):
            continue
        detail = item["downloads"]["artifact"]
        group, name, version, *classifier = item["name"].split(":")
        target = artifact(CACHE / "libraries" / detail["path"], detail["url"], detail["sha1"], group, name, version)
        libraries.append(target)
        if "natives-windows" in item["name"]:
            with zipfile.ZipFile(target) as archive:
                for member in archive.namelist():
                    if member.endswith(".dll"):
                        (natives / Path(member).name).write_bytes(archive.read(member))
    for item in profile["libraries"]:
        group, name, version = item["name"].split(":")
        relative = group.replace(".", "/") + "/" + name + "/" + version + "/" + name + "-" + version + ".jar"
        url = item["url"].rstrip("/") + "/" + relative
        expected = fetch(url + ".sha1").decode("ascii").split()[0]
        libraries.append(artifact(CACHE / "libraries" / relative, url, expected, group, name, version))
    assets = CACHE / "assets"
    (assets / "indexes").mkdir(parents=True, exist_ok=True)
    detail = metadata["assetIndex"]
    index = artifact(assets / "indexes" / (detail["id"] + ".json"), detail["url"], detail["sha1"])
    objects = json.loads(index.read_text(encoding="utf-8"))["objects"]
    prior = Path(r"E:\CodexTemp\Gradle\XiuXianZhuan\caches\neoformruntime\assets\objects")

    def asset(record):
        digest = record["hash"]
        relative = Path(digest[:2]) / digest
        target = assets / "objects" / relative
        if target.exists() and target.stat().st_size == record["size"]:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        old = prior / relative
        if old.exists() and old.stat().st_size == record["size"]:
            try:
                os.link(old, target)
            except OSError:
                shutil.copy2(old, target)
        else:
            artifact(target, "https://resources.download.minecraft.net/" + str(relative).replace("\\", "/"), digest)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(asset, objects.values()))
    guard = ROOT / "platforms/1.21.1/fabric/build/libs/qizhangverdict-fabric-1.21.1-0.1.0.jar"
    shutil.copy2(guard, game / "mods" / guard.name)
    fabric_api = next((MODULES[0] / "net.fabricmc.fabric-api/fabric-api/0.116.15+1.21.1").glob("*/fabric-api-0.116.15+1.21.1.jar"))
    shutil.copy2(fabric_api, game / "mods" / fabric_api.name)
    (game / "options.txt").write_text("fullscreen:false\nrenderDistance:2\nsimulationDistance:5\nmaxFps:30\npauseOnLostFocus:false\njoinedFirstServer:true\nskipMultiplayerWarning:true\n", encoding="utf-8")
    plan = {"main": profile["mainClass"], "classpath": [str(p) for p in libraries] + [str(client_jar)],
            "game": str(game), "assets": str(assets), "natives": str(natives), "asset_index": detail["id"],
            "guard_sha256": hashlib.sha256(guard.read_bytes()).hexdigest(), "asset_count": len(objects),
            "scope": "actual released Fabric companion JAR with official Minecraft/Fabric production launcher"}
    save_json(CACHE / "launch-plan.json", plan)
    print("Prepared production Fabric companion; assets:", len(objects), "guard SHA-256:", plan["guard_sha256"], flush=True)


def windows(pid, action):
    if os.name != "nt":
        return
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(handle, _):
        owner = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(owner))
        if owner.value == pid:
            if action == "hide":
                user32.ShowWindow(handle, 0)
            else:
                user32.PostMessageW(handle, 0x0010, 0, 0)
        return True

    user32.EnumWindows(callback_type(callback), 0)


def launch(server, duration, singleplayer=None):
    plan = json.loads((CACHE / "launch-plan.json").read_text(encoding="utf-8"))
    name = "VerdictClient"
    digest = bytearray(hashlib.md5(("OfflinePlayer:" + name).encode()).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30
    digest[8] = (digest[8] & 0x3F) | 0x80
    identity = str(uuid.UUID(bytes=bytes(digest)))
    command = [str(JAVA), "-Xms512M", "-Xmx2G", "-Dfile.encoding=UTF-8", "-Djava.library.path=" + plan["natives"],
               "-cp", os.pathsep.join(plan["classpath"]), plan["main"], "--username", name, "--version", "1.21.1",
               "--gameDir", plan["game"], "--assetsDir", plan["assets"], "--assetIndex", plan["asset_index"],
               "--uuid", identity, "--accessToken", "0", "--userType", "legacy", "--versionType", "release",
               "--width", "640", "--height", "360"]
    command.extend(["--quickPlaySingleplayer", singleplayer] if singleplayer else ["--quickPlayMultiplayer", server])
    log = CACHE / "client-console.log"
    started = time.time()
    with log.open("wb") as output:
        child = subprocess.Popen(command, cwd=plan["game"], stdout=output, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        print("Production Fabric client PID", child.pid, "target", singleplayer or server, flush=True)
        while child.poll() is None and time.time() - started < duration:
            windows(child.pid, "hide")
            time.sleep(0.25)
        if child.poll() is None:
            windows(child.pid, "close")
            try:
                child.wait(timeout=20)
            except subprocess.TimeoutExpired:
                child.terminate()
                child.wait(timeout=10)
        save_json(CACHE / "client-result.json", {**plan, "server": None if singleplayer else server, "singleplayer": singleplayer, "exit_code": child.returncode, "elapsed_seconds": round(time.time() - started, 2), "console": str(log), "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started))})
        print("Client exited", child.returncode, "log", log, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "launch"])
    parser.add_argument("--server", default="127.0.0.1:25590")
    parser.add_argument("--duration", type=int, default=100)
    parser.add_argument("--singleplayer")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        launch(args.server, args.duration, args.singleplayer)
