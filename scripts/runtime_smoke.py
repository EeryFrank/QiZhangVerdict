"""Isolated private test servers; never starts or edits an existing production server."""
import argparse, hashlib, json, os, pathlib, re, shutil, subprocess, time

PROJECT = pathlib.Path(__file__).resolve().parents[1]
CACHE = pathlib.Path(r"E:\CodexTemp\QiZhangGuard")
JAVA = pathlib.Path(r"D:\Java\jdk-21\bin\java.exe")
JAVA17 = pathlib.Path(r"E:\CodexTemp\mods-danzi\java\jdk-17.0.20.1+1-jre\bin\java.exe")
NODE = pathlib.Path(r"E:\CodexTemp\Codex\RuntimeCache\codex-primary-runtime\dependencies\node\bin\node.exe")

def wait_for(path, marker, process, timeout=240):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        data = path.read_text("utf-8", errors="replace") if path.exists() else ""
        if marker in data: return
        if process.poll() is not None: raise RuntimeError(f"Server exited {process.returncode}: {data[-6000:]}")
        time.sleep(.5)
    raise TimeoutError(f"Server did not reach {marker}: {data[-6000:]}")

def run(version, mode, grim_path=None, compression=256):
    servers = json.loads((CACHE / "downloads/servers.json").read_text())
    source = next(x for x in servers if x["version"] == version)
    folder = CACHE / "runtime" / (version + "-" + mode + ("-" + time.strftime("%Y%m%d-%H%M%S") if mode != "startup" else ""))
    folder.mkdir(parents=True, exist_ok=True)
    plugin = PROJECT / "bukkit/build/libs/qizhangverdict-bukkit-0.1.0.jar"
    (folder / "plugins").mkdir(exist_ok=True)
    shutil.copy2(plugin, folder / "plugins" / plugin.name)
    shutil.copy2(source["path"], folder / "server.jar")
    bootstrap_cache = CACHE / "runtime" / (version + "-startup") / "cache"
    if mode != "startup" and bootstrap_cache.exists(): shutil.copytree(bootstrap_cache, folder / "cache", dirs_exist_ok=True)
    if mode == "integrated":
        grim_name = "grimac-2.3.71.jar" if version == "1.20.1" else "grimac-bukkit-2.3.73.jar"
        grim = pathlib.Path(grim_path) if grim_path else CACHE / "downloads/integrations" / grim_name
        shutil.copy2(grim, folder / "plugins" / grim.name)
        fragments = PROJECT / "integrations/configs" / ("paper-" + version)
        for source_name, target_name in [("paper-world-defaults.fragment.yml", "config/paper-world-defaults.yml"), ("nether-paper-world.fragment.yml", "world_nether/paper-world.yml"), ("end-paper-world.fragment.yml", "world_the_end/paper-world.yml")]:
            target = folder / target_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text((fragments / source_name).read_text(encoding="utf-8"), encoding="utf-8")
    (folder / "eula.txt").write_text("eula=true\n")
    port = 25581 if version == "1.20.1" else 25582
    generator = json.dumps({"layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:stone","height":60},{"block":"minecraft:dirt","height":2},{"block":"minecraft:grass_block","height":1}],"biome":"minecraft:plains"}, separators=(",", ":"))
    (folder / "server.properties").write_text(f"server-ip=127.0.0.1\nserver-port={port}\nonline-mode=false\nenforce-secure-profile=false\nnetwork-compression-threshold={compression}\nspawn-protection=0\nview-distance=2\nsimulation-distance=2\nmax-players=20\nlevel-type=minecraft:flat\ngenerator-settings={generator}\ngenerate-structures=false\nlevel-seed=12955\n")
    log = folder / "console.log"
    started = time.time()
    result = {"version": version, "distribution": "Purpur", "build": source["build"], "serverSha256": source["sha256"], "pluginSha256": hashlib.sha256(plugin.read_bytes()).hexdigest(), "log": str(log), "mode": mode}
    result["networkCompressionThreshold"] = compression
    with log.open("w", encoding="utf-8") as output:
        java = JAVA17 if version == "1.20.1" else JAVA
        result["javaExecutable"] = str(java)
        process = subprocess.Popen([str(java), "-Xms256M", "-Xmx1536M", "-jar", "server.jar", "--nogui"], cwd=folder, stdin=subprocess.PIPE, stdout=output, stderr=subprocess.STDOUT, text=True)
        try:
            wait_for(log, 'Done (', process)
            data = log.read_text("utf-8", errors="replace")
            if "Enabling QiZhangVerdict" not in data or "QiZhangVerdict sessions=" not in data:
                raise AssertionError("QiZhangVerdict was not successfully enabled")
            process.stdin.write("qzverdict status\nqzverdict integrations\n"); process.stdin.flush()
            if mode != "startup":
                env = dict(os.environ, NODE_PATH=str(CACHE / "bot/node_modules"), QV_TEST_ANTIXRAY="1" if mode == "integrated" else "0", QV_TEST_COMMAND_GATE="1")
                queue = folder / "commands.queue"
                queue.write_text("")
                with (folder / "protocol-results.log").open("w", encoding="utf-8") as test_log:
                    tests = subprocess.Popen([str(NODE), str(PROJECT / "scripts/protocol_smoke.cjs"), version, str(port), str(folder)], env=env, stdout=test_log, stderr=subprocess.STDOUT)
                    consumed, end = 0, time.monotonic() + 240
                    while tests.poll() is None:
                        commands = queue.read_text().splitlines()
                        for line in commands[consumed:]: process.stdin.write(line + "\n"); process.stdin.flush()
                        consumed = len(commands)
                        if time.monotonic() > end: tests.kill(); tests.wait(); raise TimeoutError("Protocol tests timed out")
                        time.sleep(.1)
                result["protocolExit"] = tests.returncode
                if tests.returncode: raise AssertionError((folder / "protocol-results.log").read_text())
                result["protocol"] = json.loads((folder / "protocol-result.json").read_text())
                if mode == "integrated":
                    final_log = log.read_text("utf-8", errors="replace")
                    grim_enabled = re.search(r"GrimAC=(\S+) enabled", final_log)
                    if not grim_enabled: raise AssertionError("GrimAC integration was not enabled")
                    result["grimVersion"] = grim_enabled.group(1)
                    result["grimSha256"] = hashlib.sha256(grim.read_bytes()).hexdigest()
            result["startup"] = "passed"
        finally:
            if process.poll() is None:
                process.stdin.write("stop\n"); process.stdin.flush()
                try: process.wait(timeout=90)
                except subprocess.TimeoutExpired: process.kill(); process.wait(); result["forcedStop"] = True
            result["exitCode"] = process.returncode
            result["elapsedSeconds"] = round(time.time() - started, 2)
            (folder / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result), flush=True)
    if result["exitCode"] != 0: raise AssertionError("Nonzero server exit")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("version", choices=["1.20.1", "1.21.1"])
    parser.add_argument("--mode", choices=["startup", "full", "integrated"], default="startup")
    parser.add_argument("--grim", help="Explicit already verified candidate JAR for isolated integration testing")
    parser.add_argument("--compression", type=int, default=256, help="Explicit network compression threshold; recorded in evidence")
    args = parser.parse_args()
    run(args.version, args.mode, args.grim, args.compression)
