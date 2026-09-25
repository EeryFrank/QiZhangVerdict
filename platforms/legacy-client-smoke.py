#!/usr/bin/env python3
"""Production Minecraft 1.19.4 client QA, separate from the frozen 0.1.1 suite."""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "platforms/client-matrix-smoke.py"
SPEC = importlib.util.spec_from_file_location("verdict_matrix_helpers", HELPER)
matrix = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(matrix)
CACHE = Path(r"E:\CodexTemp\QiZhangVerdict\legacy-client-matrix")
SERVER_CACHE = Path(r"E:\CodexTemp\QiZhangVerdict\legacy-runtime")
PROFILES = {
    "fabric-1.19.4": {"loader": "fabric", "mc": "1.19.4", "version": "0.16.14", "port": 25611},
    "forge-1.19.4": {"loader": "forge", "mc": "1.19.4", "version": "45.4.5", "port": 25612},
}
matrix.PROFILES.update(PROFILES)


def prepare_base(name):
    """Download/copy official files only; this action never starts Java."""
    cfg = PROFILES[name]
    directory = CACHE / name / "client"
    directory.mkdir(parents=True, exist_ok=True)
    metadata = matrix.official_metadata(cfg["mc"])
    vanilla = directory / "versions" / cfg["mc"]
    matrix.save(vanilla / (cfg["mc"] + ".json"), metadata)
    candidates = [base / "caches/fabric-loom" / cfg["mc"] / "minecraft-client.jar" for base in matrix.GRADLES]
    client_jar = matrix.artifact(vanilla / (cfg["mc"] + ".jar"), metadata["downloads"]["client"], candidates)
    original = SERVER_CACHE / (name + "-guard-01")
    priors = [original / "libraries", matrix.PRIOR_FORGE / "libraries", matrix.PRIOR_FABRIC / "libraries"]
    libraries = {}
    natives = directory / "natives"
    natives.mkdir(exist_ok=True)

    def add_library(entry):
        library = matrix.get_library(directory, entry, priors)
        pieces = entry["name"].split(":")
        key = ":".join(pieces[:2]) + (":" + pieces[3] if len(pieces) > 3 else "")
        libraries[key] = str(library)
        if "natives-windows" in library.name and not any(arch in library.name for arch in ("natives-windows-arm64", "natives-windows-x86")):
            with zipfile.ZipFile(library) as archive:
                for member in archive.namelist():
                    if member.endswith(".dll"):
                        (natives / Path(member).name).write_bytes(archive.read(member))

    for entry in metadata["libraries"]:
        if matrix.allowed(entry):
            add_library(entry)
    asset_index = matrix.prepare_assets(directory, metadata)
    if cfg["loader"] == "fabric":
        profile = json.loads(matrix.fetch(f"https://meta.fabricmc.net/v2/versions/loader/{cfg['mc']}/{cfg['version']}/profile/json"))
    else:
        installer = SERVER_CACHE / "downloads/forge-1.19.4-45.4.5-installer.jar"
        with zipfile.ZipFile(installer) as archive:
            profile = json.loads(archive.read("version.json"))
    matrix.save(directory / "loader-profile.json", profile)
    for entry in profile["libraries"]:
        if matrix.allowed(entry):
            add_library(entry)
    if cfg["loader"] == "forge":
        alias = directory / "versions" / profile["id"] / (profile["id"] + ".jar")
        alias.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(client_jar, alias)
        client_jar = alias
    game = directory / "game"
    (game / "mods").mkdir(parents=True, exist_ok=True)
    (game / "options.txt").write_text("fullscreen:false\nrenderDistance:2\nsimulationDistance:5\nmaxFps:30\npauseOnLostFocus:false\njoinedFirstServer:true\nskipMultiplayerWarning:true\n", encoding="utf-8")
    matrix.save(directory / "base-plan.json", {"profile": name, "minecraft": cfg["mc"], "loader_version": cfg["version"],
                "main": profile["mainClass"], "classpath": list(libraries.values()) + [str(client_jar)],
                "loader_arguments": profile.get("arguments", {}), "loader_id": profile["id"], "game": str(game),
                "assets": str(directory / "assets"), "natives": str(natives), "libraries": str(directory / "libraries"),
                "asset_index": asset_index, "vanilla_sha1": matrix.digest(client_jar, "sha1"),
                "shared_harness_sha256": matrix.digest(HELPER)})
    print("Prepared official files without executing Java:", name, flush=True)


def install_client(name, guard_jar, expected_sha):
    cfg = PROFILES[name]
    directory = CACHE / name / "client"
    plan = matrix.read(directory / "base-plan.json")
    if cfg["loader"] == "forge":
        completed = directory / "client-install-result.json"
        if not completed.exists() or matrix.read(completed).get("exit_code") != 0:
            original = SERVER_CACHE / (name + "-guard-01")
            shutil.copytree(original / "libraries", directory / "libraries", dirs_exist_ok=True)
            matrix.save(directory / "launcher_profiles.json", {"profiles": {}})
            installer = SERVER_CACHE / "downloads/forge-1.19.4-45.4.5-installer.jar"
            installer_log = directory / "install-console.log"
            with installer_log.open("wb") as output:
                process = subprocess.run([str(matrix.JAVA17), "-Djava.awt.headless=true", "-Djavax.net.ssl.trustStoreType=Windows-ROOT",
                                          "-Djavax.net.ssl.trustStore=NONE", "-jar", str(installer), "--installClient", str(directory)],
                                         cwd=directory, stdout=output, stderr=subprocess.STDOUT, timeout=900,
                                         creationflags=matrix.NO_WINDOW, env=matrix.runtime_environment(directory))
            matrix.save(completed, {"exit_code": process.returncode, "installer_sha256": matrix.digest(installer),
                                    "console": matrix.artifact_record(installer_log)})
            if process.returncode:
                raise RuntimeError("Official Forge client installer failed")
    jar = Path(guard_jar).resolve()
    if not jar.name.startswith("qizhangverdict-" + name + "-") or matrix.digest(jar) != expected_sha.lower():
        raise ValueError("Guard filename/hash does not match requested candidate")
    mods = Path(plan["game"]) / "mods"
    for previous in mods.glob("qizhangverdict-*.jar"):
        previous.resolve().relative_to(CACHE.resolve())
        if previous.resolve() != jar:
            previous.unlink()
    if jar != (mods / jar.name).resolve():
        shutil.copy2(jar, mods / jar.name)
    if cfg["loader"] == "fabric":
        api = SERVER_CACHE / "downloads/fabric-api-0.87.2+1.19.4.jar"
        shutil.copy2(api, mods / api.name)
    plan.update({"guard_source": str(jar), "guard_sha256": expected_sha.lower(), "guard_filename": jar.name})
    matrix.save(directory / "launch-plan.json", plan)
    print("Prepared production client candidate:", name, expected_sha.lower(), flush=True)


def prepare_server(name, run_name, plan):
    cfg = PROFILES[name]
    source = SERVER_CACHE / (name + "-guard-01")
    target = CACHE / name / run_name / "server"
    if target.exists():
        raise ValueError("A run directory can only be created once")
    target.mkdir(parents=True)
    for child in source.iterdir():
        if child.is_dir() and child.name in ("libraries", "mods", "config", "defaultconfigs", "world", "versions", ".fabric"):
            shutil.copytree(child, target / child.name, ignore=shutil.ignore_patterns("qizhangverdict", "playerdata", "advancements", "stats", "session.lock"))
        elif child.is_file() and child.suffix == ".jar":
            shutil.copy2(child, target / child.name)
    jar = Path(plan["guard_source"])
    if matrix.digest(jar) != plan["guard_sha256"]:
        raise ValueError("Candidate changed after client preparation")
    for previous in (target / "mods").glob("qizhangverdict-*.jar"):
        previous.resolve().relative_to(CACHE.resolve()); previous.unlink()
    shutil.copy2(jar, target / "mods" / jar.name)
    (target / "eula.txt").write_text("eula=true\n", encoding="ascii")
    (target / "server.properties").write_text(f"server-ip=127.0.0.1\nserver-port={cfg['port']}\nonline-mode=false\nview-distance=2\nsimulation-distance=2\nmax-players=5\nspawn-protection=0\nallow-flight=false\nenable-rcon=false\nenable-query=false\nlevel-name=world\ndifficulty=peaceful\ngamemode=survival\n", encoding="ascii")
    metadata = matrix.read(source / ".qizhang-verdict-smoke.json")
    metadata.update({"port": cfg["port"], "cloned_from": str(source), "guard_sha256": plan["guard_sha256"]})
    matrix.save(target / ".qizhang-verdict-smoke.json", metadata)
    return target, metadata["runtime_args"]


def client_command(name, plan):
    # 1.19.4 Main uses the pre-QuickPlay --server / --port startup options.
    command = matrix.client_command(name, plan)
    command[0] = str(matrix.JAVA17)
    index = command.index("--quickPlayMultiplayer")
    command[index:index + 2] = ["--server", "127.0.0.1", "--port", str(PROFILES[name]["port"])]
    return command


def stamp(line):
    found = re.search(r"\[(\d\d):(\d\d):(\d\d)", line)
    return int(found[1]) * 3600 + int(found[2]) * 60 + int(found[3])


def run(name, run_name):
    cfg = PROFILES[name]
    with socket.socket() as port:
        port.bind(("127.0.0.1", cfg["port"]))
    plan = matrix.read(CACHE / name / "client/launch-plan.json")
    server_dir, arguments = prepare_server(name, run_name, plan)
    directory = server_dir.parent
    server_log, client_log = directory / "server-console.log", directory / "client-console.log"
    result = {"profile": name, "guard_source": plan["guard_source"], "guard_sha256": plan["guard_sha256"],
              "minecraft": cfg["mc"], "loader_version": cfg["version"], "launch_main": plan["main"],
              "vanilla_client_sha1": plan["vanilla_sha1"], "shared_harness_sha256": matrix.digest(HELPER),
              "scope": "Production rendered Minecraft 1.19.4 client and matching dedicated server; isolated loopback offline-auth fixture", "passed": False}
    server = client = None
    started = time.monotonic()
    client_wall_start = None
    try:
        with server_log.open("xb") as server_out, client_log.open("xb") as client_out:
            server = subprocess.Popen([str(matrix.JAVA17), "-Xms512M", "-Xmx2G", "-Djava.awt.headless=true", "-Dfile.encoding=UTF-8", *arguments],
                                      cwd=server_dir, stdin=subprocess.PIPE, stdout=server_out, stderr=subprocess.STDOUT,
                                      creationflags=matrix.NO_WINDOW, env=matrix.runtime_environment(server_dir))
            def console(value):
                if server.poll() is None:
                    server.stdin.write((value + "\n").encode("utf-8")); server.stdin.flush()
            while server.poll() is None and time.monotonic() - started < 240:
                log = matrix.text_log(server_log)
                if re.search(r'Done \([\d.,]+s\)!', log) and "deviceRequired=true" in log:
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError("Dedicated server did not become ready with the guard enabled")
            before = matrix.policy_record(server_dir)
            result["policy_before_client"] = before
            if not before["matches_strict_defaults"]:
                raise RuntimeError("Fixture does not have unmodified strict defaults")
            console("difficulty peaceful"); console("gamerule doMobSpawning false")
            console("qzverdict status")
            client_wall_start = time.time()
            client = subprocess.Popen(client_command(name, plan), cwd=plan["game"], stdout=client_out, stderr=subprocess.STDOUT,
                                      creationflags=matrix.NO_WINDOW, env=matrix.runtime_environment(Path(plan["game"])))
            print("Running real legacy client", name, "server", server.pid, "client", client.pid, flush=True)
            began_client = time.monotonic()
            joined = validated = last_query = None
            captured = False
            while client.poll() is None and time.monotonic() - began_client < 300:
                matrix.windows(client.pid)
                now = time.monotonic()
                log = matrix.text_log(server_log)
                if joined is None and "VerdictClient joined the game" in log:
                    joined = now; print("Joined", name, flush=True)
                if joined is not None and now - joined >= 10 and (last_query is None or now - last_query >= 10):
                    console("list"); console("qzverdict status"); console("data get entity VerdictClient playerGameType")
                    last_query = now
                if validated is None and "following entity data: 0" in log:
                    validated = now
                    print("Required report accepted and survival restored", name, flush=True)
                if validated is not None and not captured and now - validated >= 30:
                    matrix.windows(client.pid, screenshot=True); captured = True
                if validated is None and not captured and now - began_client >= 90:
                    matrix.windows(client.pid, screenshot=True); captured = True
                if validated is not None and now - validated >= 65:
                    console("list"); console("qzverdict status"); console("data get entity VerdictClient playerGameType")
                    time.sleep(2)
                    break
                if joined is not None and validated is None and now - joined > 45:
                    break
                time.sleep(0.25)
            if client.poll() is None:
                matrix.windows(client.pid, close=True)
                try:
                    client.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    client.terminate(); client.wait(timeout=15)
            console("stop"); server.wait(timeout=90)
        after = matrix.policy_record(server_dir)
        log = matrix.text_log(server_log)
        client_text = matrix.text_log(client_log)
        modes = [line for line in log.splitlines() if "following entity data: 0" in line]
        online = [line for line in log.splitlines() if "There are 1 of" in line and "VerdictClient" in line]
        elapsed_after_report = stamp(online[-1]) - stamp(modes[0]) if modes and online else 0
        state_path = server_dir / "config/qizhangverdict/accounts.state"
        association = any(re.fullmatch(r"D\t[0-9a-f-]{36}\t[0-9a-f]{64}", line) for line in state_path.read_text(encoding="utf-8").splitlines()) if state_path.exists() else False
        metadata_warning = "Missing metadata in pack mod:qizhangverdict" in client_text or "failed to load a valid ResourcePackInfo" in client_text
        unchanged = before["sha256"] == after["sha256"]
        strict = before["matches_strict_defaults"] and after["matches_strict_defaults"] and unchanged and "vm=DENY" in log
        rendered = "textures/atlas/" in client_text and "OpenAL" in client_text
        result.update({"policy_after_client": after, "policy_unchanged": unchanged, "strict_defaults": strict,
                       "restored_survival": bool(modes), "persisted_device_association": association,
                       "confirmed_online_seconds_after_first_restored_mode": elapsed_after_report,
                       "report_acceptance_basis": "Survival restoration while the strict required-report gate is active proves the report was accepted no later than this first mode query.",
                       "first_restored_mode_line": modes[0] if modes else None, "last_online_line": online[-1] if online else None,
                       "resource_pack_metadata_warning": metadata_warning, "rendered_client_confirmed": rendered,
                       "elapsed_seconds": round(time.monotonic() - started, 2),
                       "excerpts": [line for line in log.splitlines() if any(part in line for part in ("VerdictClient joined", "There are 1 of", "following entity data:", "Report decision", "lost connection"))]})
        result["passed"] = strict and rendered and not metadata_warning and association and elapsed_after_report >= 60 and client.returncode == 0 and server.returncode == 0
    except Exception as error:
        result["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if client is not None and client.poll() is None:
            matrix.windows(client.pid, close=True)
            try:
                client.wait(timeout=20)
            except subprocess.TimeoutExpired:
                client.terminate(); client.wait(timeout=10)
        if server is not None and server.poll() is None:
            try:
                server.stdin.write(b"stop\n"); server.stdin.flush(); server.wait(timeout=90)
            except (OSError, subprocess.TimeoutExpired):
                server.terminate(); server.wait(timeout=15)
        result["client_exit_code"] = client.returncode if client else None
        result["server_exit_code"] = server.returncode if server else None
        result["raw_evidence"] = [matrix.artifact_record(path) for path in (client_log, server_log) if path.exists()]
        if client_wall_start is not None:
            for path in (Path(plan["game"]) / "screenshots").glob("*.png"):
                if path.stat().st_mtime >= client_wall_start:
                    output = directory / "screenshots" / path.name
                    output.parent.mkdir(exist_ok=True); shutil.copy2(path, output)
                    result["raw_evidence"].append(matrix.artifact_record(output))
        matrix.save(directory / "result.json", result)
    print(json.dumps({"profile": name, "passed": result["passed"], "result": str(directory / "result.json"), "error": result.get("error")}), flush=True)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare-base", "install-client", "run"))
    parser.add_argument("profile", choices=PROFILES)
    parser.add_argument("--guard-jar")
    parser.add_argument("--guard-sha256")
    parser.add_argument("--run-name", default="run-01")
    args = parser.parse_args()
    if args.action == "prepare-base":
        prepare_base(args.profile)
    elif args.action == "install-client":
        if not args.guard_jar or not args.guard_sha256:
            parser.error("install-client requires --guard-jar and --guard-sha256")
        install_client(args.profile, args.guard_jar, args.guard_sha256)
    else:
        run(args.profile, args.run_name)
