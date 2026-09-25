#!/usr/bin/env python3
"""Launch frozen release JARs with production loaders in isolated Windows fixtures.

This optional QA runner never edits source, release bundles, user instances or saves.
Official metadata hashes authenticate downloads; cached immutable files may be linked.
"""
from __future__ import annotations
import argparse
import concurrent.futures
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
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(r"E:\CodexTemp\QiZhangVerdict\client-matrix")
OLD = Path(r"E:\CodexTemp\QiZhangGuard")
JAVA21 = Path(r"D:\Java\jdk-21\bin\java.exe")
JAVA17 = Path(r"E:\CodexTemp\mods-danzi\java\jdk-17.0.20.1+1-jre\bin\java.exe")
PRIOR_FORGE = Path(r"E:\CodexTemp\mods-danzi\minecraft")
PRIOR_FABRIC = OLD / "client-release-smoke"
GRADLES = [Path(r"E:\CodexTemp\Gradle\QiZhang_Games"), Path(r"E:\CodexTemp\Gradle\XiuXianZhuan")]
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
PROFILES = {
    "fabric-1.20.1": {"loader": "fabric", "mc": "1.20.1", "version": "0.16.14", "port": 25594,
                      "sha256": "5162552b204b5487ffaecc88c5a796de8d558fdb40988cb2a6a76e369cc2fe60", "prior": "fabric-1.20.1-final-03"},
    "fabric-1.21.1": {"loader": "fabric", "mc": "1.21.1", "version": "0.16.14", "port": 25597,
                      "sha256": "c878c510bfb0c0cc1815f34ef327b73cb4ce45eddeeb2d9e7bcac1b476fda182", "prior": "fabric-1.21.1-final-06"},
    "forge-1.20.1": {"loader": "forge", "mc": "1.20.1", "version": "47.4.23", "port": 25595,
                     "sha256": "78e056b90b39483dfce5487cb76dfa8671ea8fe21e27182a735498f9a5be059a", "prior": "forge-1.20.1-final-02"},
    "neoforge-1.21.1": {"loader": "neoforge", "mc": "1.21.1", "version": "21.1.244", "port": 25596,
                        "sha256": "c9f53e0d0540e90900ef2277f24af88813dd4d5a12c16e64a7a1a6459dcaa932", "prior": "neoforge-1.21.1-final-02"},
}
EXPECTED_POLICY = {
    "limits.max-online-per-ip": "3", "limits.max-online-per-ip-device": "1", "limits.max-accounts-per-ip": "5",
    "limits.account-window-hours": "720", "limits.attempts-per-minute": "20", "ip.allow": "", "ip.deny": "",
    "companion.required": "true", "companion.timeout-seconds": "20", "vm.action": "DENY",
    "blacklist.action": "DENY", "sanctions.on-deny": "BAN", "device.required": "true",
}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def runtime_environment(directory):
    temporary = directory / "tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["TEMP"] = environment["TMP"] = str(temporary)
    return environment


def digest(path, algorithm="sha256"):
    return hashlib.new(algorithm, path.read_bytes()).hexdigest()


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "QiZhangVerdict-client-matrix/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def link_copy(source, target):
    """Only immutable libraries/assets are hardlinked; editable runtime files are copied."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        try:
            os.link(source, target)
        except FileExistsError:
            pass  # Multiple logical assets can share one content hash.
        except OSError:
            shutil.copy2(source, target)
    return str(target)


def artifact(target, detail, candidates=()):
    target.parent.mkdir(parents=True, exist_ok=True)
    expected = detail.get("sha1")
    if target.exists() and (not expected or digest(target, "sha1") == expected):
        return target
    for candidate in candidates:
        if candidate.exists() and (not expected or digest(candidate, "sha1") == expected):
            shutil.copy2(candidate, target)
            return target
    raw = fetch(detail["url"])
    if expected and hashlib.sha1(raw).hexdigest() != expected:
        raise ValueError("SHA-1 mismatch: " + target.name)
    target.write_bytes(raw)
    return target


def allowed(entry):
    if not entry.get("rules"):
        return True
    result = False
    for rule in entry["rules"]:
        if rule.get("features"):
            continue
        platform = rule.get("os", {})
        if platform.get("name", "windows") != "windows":
            continue
        if platform.get("arch", "amd64") not in ("amd64", "x86_64"):
            continue
        result = rule["action"] == "allow"
    return result


def official_metadata(mc):
    candidates = [base / "caches/fabric-loom" / mc / "mojang_minecraft_info.json" for base in GRADLES]
    candidates.append(PRIOR_FORGE / "versions" / mc / (mc + ".json"))
    for candidate in candidates:
        if candidate.exists():
            return read(candidate)
    manifest = json.loads(fetch("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"))
    entry = next(item for item in manifest["versions"] if item["id"] == mc)
    raw = fetch(entry["url"])
    if hashlib.sha1(raw).hexdigest() != entry["sha1"]:
        raise ValueError("Mojang version metadata hash mismatch")
    return json.loads(raw)


def get_library(directory, item, prior_libraries):
    group, name, version, *classifier = item["name"].split(":")
    detail = item.get("downloads", {}).get("artifact")
    if not detail:
        relative = group.replace(".", "/") + "/" + name + "/" + version + "/" + name + "-" + version
        relative += ("-" + classifier[0] if classifier else "") + ".jar"
        url = item["url"].rstrip("/") + "/" + relative
        detail = {"path": relative, "url": url, "sha1": fetch(url + ".sha1").decode("ascii").split()[0]}
    relative = detail["path"]
    target = directory / "libraries" / relative
    candidates = [folder / relative for folder in prior_libraries]
    for base in GRADLES:
        parent = base / "caches/modules-2/files-2.1" / group / name / version
        if parent.exists():
            candidates.extend(parent.glob("*/" + target.name))
    return artifact(target, detail, candidates)


def prepare_assets(directory, metadata):
    assets = directory / "assets"
    entry = metadata["assetIndex"]
    index = artifact(assets / "indexes" / (entry["id"] + ".json"), entry,
                     [PRIOR_FORGE / "assets/indexes" / (entry["id"] + ".json"), PRIOR_FABRIC / "assets/indexes" / (entry["id"] + ".json")])
    objects = read(index)["objects"]
    previous = [PRIOR_FORGE / "assets/objects", PRIOR_FABRIC / "assets/objects",
                GRADLES[1] / "caches/neoformruntime/assets/objects"]

    def get_asset(record):
        sha = record["hash"]
        relative = Path(sha[:2]) / sha
        target = assets / "objects" / relative
        if target.exists() and target.stat().st_size == record["size"]:
            return
        for folder in previous:
            candidate = folder / relative
            if candidate.exists() and candidate.stat().st_size == record["size"]:
                link_copy(candidate, target)
                return
        artifact(target, {"url": "https://resources.download.minecraft.net/" + relative.as_posix(), "sha1": sha})

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(get_asset, objects.values()))
    return entry["id"]


def prepare(name, guard_jar=None, guard_sha256=None):
    cfg = PROFILES[name]
    directory = CACHE / name / "client"
    directory.mkdir(parents=True, exist_ok=True)
    mc = cfg["mc"]
    metadata = official_metadata(mc)
    vanilla_dir = directory / "versions" / mc
    save(vanilla_dir / (mc + ".json"), metadata)
    client_candidates = [base / "caches/fabric-loom" / mc / "minecraft-client.jar" for base in GRADLES]
    client_candidates.append(PRIOR_FORGE / "versions" / mc / (mc + ".jar"))
    client_jar = artifact(vanilla_dir / (mc + ".jar"), metadata["downloads"]["client"], client_candidates)
    prior_server = OLD / "runtime-smoke" / cfg["prior"]
    priors = [PRIOR_FORGE / "libraries", PRIOR_FABRIC / "libraries", prior_server / "libraries"]
    libraries = {}
    natives = directory / "natives"
    natives.mkdir(exist_ok=True)
    for item in metadata["libraries"]:
        if not allowed(item):
            continue
        library = get_library(directory, item, priors)
        libraries[":".join(item["name"].split(":")[:2]) + (":" + item["name"].split(":")[3] if len(item["name"].split(":")) > 3 else "")] = str(library)
        # Current Mojang metadata lists all Windows architectures; extract x64 only.
        if "natives-windows" in library.name and "natives-windows-arm64" not in library.name and "natives-windows-x86" not in library.name:
            with zipfile.ZipFile(library) as archive:
                for member in archive.namelist():
                    if member.endswith(".dll"):
                        (natives / Path(member).name).write_bytes(archive.read(member))
    asset_index = prepare_assets(directory, metadata)
    if cfg["loader"] == "fabric":
        profile = json.loads(fetch(f"https://meta.fabricmc.net/v2/versions/loader/{mc}/{cfg['version']}/profile/json"))
    elif cfg["loader"] == "forge":
        profile = read(PRIOR_FORGE / "versions/1.20.1-forge-47.4.23/1.20.1-forge-47.4.23.json")
        # Installer-generated patched client and split Minecraft artifacts.
        for relative in ("net/minecraftforge", "net/minecraft/client"):
            shutil.copytree(PRIOR_FORGE / "libraries" / relative, directory / "libraries" / relative,
                            dirs_exist_ok=True, copy_function=link_copy)
    else:
        version_json = directory / "versions" / ("neoforge-" + cfg["version"]) / ("neoforge-" + cfg["version"] + ".json")
        if not version_json.exists():
            # Copy instead of hardlink here: the installer is allowed to rewrite its own files.
            shutil.copytree(prior_server / "libraries", directory / "libraries", dirs_exist_ok=True)
            save(directory / "launcher_profiles.json", {"profiles": {}})
            installer = prior_server / "loader-installer.jar"
            with (directory / "install-console.log").open("wb") as output:
                process = subprocess.run([str(JAVA21), "-Djava.awt.headless=true", "-Djavax.net.ssl.trustStoreType=Windows-ROOT",
                                          "-Djavax.net.ssl.trustStore=NONE", "-jar", str(installer), "--installClient", str(directory)],
                                         cwd=directory, stdout=output, stderr=subprocess.STDOUT, timeout=900, creationflags=NO_WINDOW,
                                         env=runtime_environment(directory))
            if process.returncode != 0:
                raise RuntimeError("NeoForge client install failed; see " + str(directory / "install-console.log"))
        profile = read(version_json)
    save(directory / "loader-profile.json", profile)
    if cfg["loader"] != "fabric":
        # The official loader profile excludes ${version_name}.jar from its
        # transforming module layer. Give the inherited vanilla JAR that exact
        # launch-version filename; otherwise ModLauncher sees duplicate packages.
        aliased_client = directory / "versions" / profile["id"] / (profile["id"] + ".jar")
        aliased_client.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(client_jar, aliased_client)
        client_jar = aliased_client
    for item in profile["libraries"]:
        if allowed(item):
            library = get_library(directory, item, priors)
            key = ":".join(item["name"].split(":")[:2]) + (":" + item["name"].split(":")[3] if len(item["name"].split(":")) > 3 else "")
            libraries[key] = str(library)
    game = directory / "game"
    (game / "mods").mkdir(parents=True, exist_ok=True)
    if bool(guard_jar) != bool(guard_sha256):
        raise ValueError("Custom artifacts require both --guard-jar and --guard-sha256")
    jar = Path(guard_jar).resolve() if guard_jar else ROOT / "outputs/QiZhangVerdict-0.1.0" / ("qizhangverdict-" + name + "-0.1.0.jar")
    expected_guard_sha = guard_sha256.lower() if guard_sha256 else cfg["sha256"]
    assert digest(jar) == expected_guard_sha, "Expected release artifact hash changed"
    if not jar.name.startswith("qizhangverdict-" + name + "-") or jar.suffix != ".jar":
        raise ValueError("Guard artifact does not match the selected platform")
    for previous_guard in (game / "mods").glob("qizhangverdict-*.jar"):
        previous_guard.resolve().relative_to(CACHE.resolve())
        if previous_guard.resolve() != jar.resolve():
            previous_guard.unlink()
    if jar.resolve() != (game / "mods" / jar.name).resolve():
        shutil.copy2(jar, game / "mods" / jar.name)
    if cfg["loader"] == "fabric":
        api_name = "fabric-api-0.92.12+1.20.1.jar" if mc == "1.20.1" else "fabric-api-0.116.17+1.21.1.jar"
        api = OLD / "downloads/integrations" / api_name
        shutil.copy2(api, game / "mods" / api.name)
    (game / "options.txt").write_text("fullscreen:false\nrenderDistance:2\nsimulationDistance:5\nmaxFps:30\npauseOnLostFocus:false\njoinedFirstServer:true\nskipMultiplayerWarning:true\n", encoding="utf-8")
    save(directory / "launch-plan.json", {"profile": name, "minecraft": mc, "loader_version": cfg["version"],
         "main": profile["mainClass"], "classpath": list(libraries.values()) + [str(client_jar)],
         "loader_arguments": profile.get("arguments", {}), "loader_id": profile["id"], "game": str(game),
         "assets": str(directory / "assets"), "natives": str(natives), "libraries": str(directory / "libraries"),
         "asset_index": asset_index, "guard_sha256": expected_guard_sha, "guard_source": str(jar),
         "vanilla_sha1": digest(client_jar, "sha1")})
    print("Prepared production client", name, expected_guard_sha, flush=True)


def windows(pid, close=False, screenshot=False):
    user32 = ctypes.windll.user32
    kind = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def callback(handle, _):
        owner = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(owner))
        if owner.value == pid:
            if screenshot:
                user32.PostMessageW(handle, 0x0100, 0x71, 0x003C0001)
                user32.PostMessageW(handle, 0x0101, 0x71, 0xC03C0001)
            elif close:
                user32.PostMessageW(handle, 0x0010, 0, 0)
            else:
                user32.ShowWindow(handle, 0)
        return True
    user32.EnumWindows(kind(callback), 0)


def prepare_server(name, run_name, plan):
    cfg = PROFILES[name]
    original = OLD / "runtime-smoke" / cfg["prior"]
    target = CACHE / name / run_name / "server"
    if target.exists():
        raise ValueError("Run directories cannot be reused: " + str(target))
    target.mkdir(parents=True)
    for child in original.iterdir():
        if child.is_dir() and child.name in ("libraries", "mods", "config", "defaultconfigs", "smoke-world", ".fabric"):
            ignored = shutil.ignore_patterns("qizhangverdict", "playerdata", "advancements", "stats", "session.lock")
            shutil.copytree(child, target / child.name, ignore=ignored)
        elif child.is_file() and (child.suffix == ".jar" or child.name == ".qizhang-verdict-smoke.json"):
            shutil.copy2(child, target / child.name)
    public_jar = Path(plan.get("guard_source", ROOT / "outputs/QiZhangVerdict-0.1.0" / ("qizhangverdict-" + name + "-0.1.0.jar")))
    assert digest(public_jar) == plan["guard_sha256"]
    for previous_guard in (target / "mods").glob("qizhangverdict-*.jar"):
        previous_guard.resolve().relative_to(CACHE.resolve())
        previous_guard.unlink()
    shutil.copy2(public_jar, target / "mods" / public_jar.name)
    (target / "eula.txt").write_text("eula=true\n", encoding="ascii")
    (target / "server.properties").write_text(f"server-ip=127.0.0.1\nserver-port={cfg['port']}\nonline-mode=false\nview-distance=2\nsimulation-distance=2\nmax-players=5\nspawn-protection=0\nallow-flight=false\nenable-rcon=false\nenable-query=false\nlevel-name=smoke-world\ndifficulty=peaceful\ngamemode=survival\n", encoding="ascii")
    return target, read(original / ".qizhang-verdict-smoke.json")["runtime_args"]


def client_command(name, plan):
    cfg = PROFILES[name]
    library_directory = plan["libraries"].replace("\\", "/")
    substitutions = {"library_directory": library_directory, "classpath_separator": os.pathsep,
                     "version_name": plan["loader_id"], "natives_directory": plan["natives"],
                     "launcher_name": "QiZhangVerdict-QA", "launcher_version": "1", "classpath": os.pathsep.join(plan["classpath"])}
    def expand(value):
        for key, replacement in substitutions.items():
            value = value.replace("${" + key + "}", replacement)
        if "${" in value:
            raise ValueError("Unknown launch placeholder: " + value)
        return value
    jvm = [expand(value) for value in plan["loader_arguments"].get("jvm", []) if isinstance(value, str)]
    identity = bytearray(hashlib.md5(b"OfflinePlayer:VerdictClient").digest())
    identity[6] = (identity[6] & 15) | 48
    identity[8] = (identity[8] & 63) | 128
    java = JAVA17 if cfg["mc"] == "1.20.1" else JAVA21
    command = [str(java), "-Xms512M", "-Xmx2G", "-Dfile.encoding=UTF-8", "-Djava.library.path=" + plan["natives"], *jvm,
               "-cp", os.pathsep.join(plan["classpath"]), plan["main"], "--username", "VerdictClient", "--version", plan["loader_id"],
               "--gameDir", plan["game"], "--assetsDir", plan["assets"], "--assetIndex", plan["asset_index"],
               "--uuid", str(uuid.UUID(bytes=bytes(identity))), "--accessToken", "0", "--userType", "legacy", "--versionType", "release",
               "--width", "640", "--height", "360", "--quickPlayMultiplayer", "127.0.0.1:" + str(cfg["port"])]
    command += [expand(value) for value in plan["loader_arguments"].get("game", []) if isinstance(value, str)]
    return command


def text_log(path):
    return re.sub(r"\x1b\[[0-9;]*m", "", path.read_text(encoding="utf-8", errors="replace")) if path.exists() else ""


def artifact_record(path):
    return {"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size}


def policy_record(server_dir):
    path = server_dir / "config/qizhangverdict/guard.properties"
    values = dict(line.split("=", 1) for line in path.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#"))
    return {**artifact_record(path), "values": values, "matches_strict_defaults": values == EXPECTED_POLICY}


def run(name, run_name):
    cfg = PROFILES[name]
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", cfg["port"]))
    plan = read(CACHE / name / "client/launch-plan.json")
    server_dir, server_args = prepare_server(name, run_name, plan)
    directory = server_dir.parent
    server_log, client_log = directory / "server-console.log", directory / "client-console.log"
    server = client = None
    result = {"profile": name, "guard_sha256": plan["guard_sha256"], "guard_source": plan.get("guard_source"),
              "minecraft": plan["minecraft"], "loader_version": plan["loader_version"],
              "launch_main": plan["main"], "vanilla_client_sha1": plan["vanilla_sha1"],
              "scope": "Production rendered loader client and matching dedicated server using explicitly hash-pinned JARs", "passed": False}
    begun = time.monotonic()
    try:
        with server_log.open("xb") as server_out, client_log.open("xb") as client_out:
            java = JAVA17 if cfg["mc"] == "1.20.1" else JAVA21
            server = subprocess.Popen([str(java), "-Xms512M", "-Xmx2G", "-Djava.awt.headless=true", "-Dfile.encoding=UTF-8", *server_args],
                                      cwd=server_dir, stdin=subprocess.PIPE, stdout=server_out, stderr=subprocess.STDOUT, creationflags=NO_WINDOW,
                                      env=runtime_environment(server_dir))
            def console(command):
                if server.poll() is None:
                    server.stdin.write((command + "\n").encode("utf-8")); server.stdin.flush()
            while server.poll() is None and time.monotonic() - begun < 240:
                if re.search(r'Done \([\d.,]+s\)!', text_log(server_log)):
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError("Server failed to reach ready")
            console("difficulty peaceful"); console("gamerule doMobSpawning false")
            console("qzverdict status")
            policy_deadline = time.monotonic() + 5
            while not (server_dir / "config/qizhangverdict/guard.properties").exists() and time.monotonic() < policy_deadline:
                time.sleep(0.1)
            policy_before = policy_record(server_dir)
            result["policy_before_client"] = policy_before
            if not policy_before["matches_strict_defaults"]:
                raise RuntimeError("Fixture policy does not match unmodified strict defaults")
            client = subprocess.Popen(client_command(name, plan), cwd=plan["game"], stdout=client_out, stderr=subprocess.STDOUT, creationflags=NO_WINDOW,
                                      env=runtime_environment(Path(plan["game"])))
            print("Running", name, "server", server.pid, "client", client.pid, flush=True)
            client_start = time.monotonic()
            client_wall_start = time.time()
            screenshot_requested = False
            joined = last_query = None
            while client.poll() is None and time.monotonic() - client_start < 240:
                windows(client.pid)
                now = time.monotonic()
                if joined is None and "VerdictClient joined the game" in text_log(server_log):
                    joined = now
                    print("Real client joined", name, flush=True)
                if joined is not None and now - joined >= 30 and (last_query is None or now - last_query >= 15):
                    console("list"); console("qzverdict status"); console("data get entity VerdictClient playerGameType")
                    last_query = now
                    if not screenshot_requested:
                        windows(client.pid, screenshot=True); screenshot_requested = True
                if joined is None and now - client_start >= 60 and not screenshot_requested:
                    windows(client.pid, screenshot=True); screenshot_requested = True
                if joined is not None and now - joined >= 65:
                    break
                time.sleep(0.25)
            result["observed_join_elapsed_seconds"] = None if joined is None else round(joined - client_start, 2)
            if client.poll() is None:
                windows(client.pid, close=True)
                try:
                    client.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    client.terminate(); client.wait(timeout=15)
            result["client_exit_code"] = client.returncode
            console("stop")
            server.wait(timeout=90)
            result["server_exit_code"] = server.returncode
        log = text_log(server_log)
        client_text = text_log(client_log)
        excerpts = [line for line in log.splitlines() if any(key in line for key in ("VerdictClient joined", "There are 1 of", "following entity data:", "QiZhangVerdict sessions=1", "Report decision", "lost connection"))]
        policy_after = policy_record(server_dir)
        result["policy_after_client"] = policy_after
        result["policy_unchanged"] = policy_before["sha256"] == policy_after["sha256"]
        strict = "companion=required" in log and "deviceRequired=true" in log and "vm=DENY" in log and policy_after["matches_strict_defaults"] and result["policy_unchanged"]
        survival = "following entity data: 0" in log
        online = "There are 1 of" in log
        state = server_dir / "config/qizhangverdict/accounts.state"
        associated = any(re.fullmatch(r"D\t[0-9a-f-]{36}\t[0-9a-f]{64}", line) for line in state.read_text(encoding="utf-8").splitlines()) if state.exists() else False
        join_line = next((line for line in excerpts if "joined the game" in line), None)
        queries = [line for line in excerpts if "There are 1 of" in line]
        def clock_seconds(line):
            stamp = re.search(r"\[(\d\d):(\d\d):(\d\d)", line)
            return int(stamp[1]) * 3600 + int(stamp[2]) * 60 + int(stamp[3])
        confirmed_seconds = clock_seconds(queries[-1]) - clock_seconds(join_line) if join_line and queries else 0
        result.update({"strict_defaults": strict, "restored_survival": survival, "persisted_device_association": associated,
                       "rendered_client_confirmed": "textures/atlas/" in client_text and "OpenAL" in client_text,
                       "resource_pack_metadata_warning": "Missing metadata in pack mod:qizhangverdict" in client_text,
                       "confirmed_online_after_join_seconds": confirmed_seconds, "required_report_window_seconds": 20,
                       "excerpts": excerpts, "elapsed_seconds": round(time.monotonic() - begun, 2)})
        result["passed"] = strict and survival and online and associated and confirmed_seconds > 20 and result["rendered_client_confirmed"] and not result["resource_pack_metadata_warning"] and client.returncode == 0 and server.returncode == 0
    except Exception as exception:
        result["error"] = type(exception).__name__ + ": " + str(exception)
    finally:
        if client is not None and client.poll() is None:
            windows(client.pid, close=True)
            try:
                client.wait(timeout=20)
            except subprocess.TimeoutExpired:
                client.terminate(); client.wait(timeout=10)
        if server is not None and server.poll() is None:
            try:
                server.stdin.write(b"stop\n"); server.stdin.flush(); server.wait(timeout=90)
            except (OSError, subprocess.TimeoutExpired):
                server.terminate(); server.wait(timeout=15)
        if client is not None:
            result["client_exit_code"] = client.returncode
        if server is not None:
            result["server_exit_code"] = server.returncode
        result["raw_evidence"] = [artifact_record(path) for path in (server_log, client_log) if path.exists()]
        if client is not None:
            for screenshot in (Path(plan["game"]) / "screenshots").glob("*.png"):
                if screenshot.stat().st_mtime >= client_wall_start:
                    destination = directory / "screenshots" / screenshot.name
                    destination.parent.mkdir(exist_ok=True)
                    shutil.copy2(screenshot, destination)
                    result["raw_evidence"].append(artifact_record(destination))
        save(directory / "result.json", result)
    print(json.dumps({"profile": name, "passed": result["passed"], "result": str(directory / "result.json"), "error": result.get("error")}), flush=True)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("profile", choices=PROFILES)
    parser.add_argument("--run-name", default="run-01")
    parser.add_argument("--guard-jar")
    parser.add_argument("--guard-sha256")
    args = parser.parse_args()
    prepare(args.profile, args.guard_jar, args.guard_sha256) if args.action == "prepare" else run(args.profile, args.run_name)
