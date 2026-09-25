"""Real Bukkit fail-closed login test in a new localhost-only, disposable server directory."""
import hashlib
import json
import os
import pathlib
import shutil
import socket
import subprocess
import time

PROJECT = pathlib.Path(__file__).resolve().parents[1]
CACHE = pathlib.Path(r"E:\CodexTemp\QiZhangGuard")
SOURCE = CACHE / "runtime/1.21.1-startup"
JAVA = pathlib.Path(r"D:\Java\jdk-21\bin\java.exe")
NODE = pathlib.Path(r"E:\CodexTemp\Codex\RuntimeCache\codex-primary-runtime\dependencies\node\bin\node.exe")
PORT = 25589

CLIENT = r"""
const mc = require('minecraft-protocol');
const fs = require('fs');
const resultPath = process.argv[2];
const result = {version: '1.21.1', server: '127.0.0.1', port: 25589, enteredPlay: false, kick: null};
let finished = false;
function finish(error) {
  if (finished) return;
  finished = true;
  clearTimeout(timeout);
  if (error) result.error = String(error);
  const passed = !result.enteredPlay && result.kick && JSON.stringify(result.kick).toLowerCase().includes('unavailable');
  result.passed = Boolean(passed);
  fs.writeFileSync(resultPath, JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  client.end('test complete');
  setTimeout(() => process.exit(passed ? 0 : 1), 100);
}
const client = mc.createClient({host:'127.0.0.1', port:25589, username:'QVFailClosed', version:'1.21.1', auth:'offline'});
const timeout = setTimeout(() => finish('No matching rejection within 25 seconds'), 25000);
client.on('packet', (data, meta) => {
  if (meta.name === 'login' && meta.state === 'play') result.enteredPlay = true;
  if (meta.name === 'disconnect' || meta.name === 'kick_disconnect') result.kick = data;
});
client.on('end', () => finish());
client.on('error', error => { result.networkError = String(error); });
"""


def wait_for(log, text, process, timeout=240):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        contents = log.read_text("utf-8", errors="replace") if log.exists() else ""
        if text in contents:
            return contents
        if process.poll() is not None:
            raise RuntimeError(f"Server exited {process.returncode}: {contents[-6000:]}")
        time.sleep(0.25)
    raise TimeoutError(f"Missing server marker {text!r}")


def run():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", PORT))
    folder = CACHE / "runtime" / ("failclosed-1.21.1-" + time.strftime("%Y%m%d-%H%M%S"))
    folder.mkdir(parents=True, exist_ok=False)
    for name in ("cache", "libraries", "versions"):
        if (SOURCE / name).exists():
            shutil.copytree(SOURCE / name, folder / name)
    shutil.copy2(SOURCE / "server.jar", folder / "server.jar")
    plugin_data = (PROJECT / "bukkit/build/libs/qizhangverdict-bukkit-0.1.0.jar").read_bytes()
    plugin_dir = folder / "plugins/QiZhangVerdict"
    plugin_dir.mkdir(parents=True)
    (folder / "plugins/qizhangverdict-bukkit-0.1.0.jar").write_bytes(plugin_data)
    (plugin_dir / "guard.properties").write_text("limits.max-online-per-ip=-1\n", encoding="utf-8")
    (folder / "eula.txt").write_text("eula=true\n", encoding="ascii")
    (folder / "server.properties").write_text(
        f"server-ip=127.0.0.1\nserver-port={PORT}\nonline-mode=false\nenforce-secure-profile=false\n"
        "spawn-protection=0\nview-distance=2\nsimulation-distance=2\nmax-players=5\n"
        "level-type=minecraft:flat\ngenerate-structures=false\nlevel-seed=12955\n",
        encoding="utf-8",
    )
    client_script = folder / "failclosed-client.cjs"
    client_script.write_text(CLIENT, encoding="utf-8")
    log = folder / "console.log"
    started = time.time()
    result = {
        "test": "Bukkit invalid-config fail-closed admission",
        "serverVersion": "1.21.1",
        "serverSha256": hashlib.sha256((folder / "server.jar").read_bytes()).hexdigest(),
        "pluginSha256": hashlib.sha256(plugin_data).hexdigest(),
        "javaExecutable": str(JAVA),
        "directory": str(folder),
        "log": str(log),
        "invalidConfiguration": "limits.max-online-per-ip=-1",
        "port": PORT,
    }
    with log.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [str(JAVA), "-Xms256M", "-Xmx1536M", "-jar", "server.jar", "--nogui"],
            cwd=folder, stdin=subprocess.PIPE, stdout=output, stderr=subprocess.STDOUT,
            text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            contents = wait_for(log, "Done (", process)
            if "ALL LOGINS BLOCKED" not in contents or "Enabling QiZhangVerdict" not in contents:
                raise AssertionError("Plugin did not retain fail-closed admission policy")
            if "Disabling QiZhangVerdict" in contents:
                raise AssertionError("Bukkit disabled the failed policy plugin")
            process.stdin.write("plugins\nqzverdict status\n")
            process.stdin.flush()
            wait_for(log, "Logins remain blocked.", process, 15)
            env = dict(os.environ, NODE_PATH=str(CACHE / "bot/node_modules"))
            client = subprocess.run(
                [str(NODE), str(client_script), str(folder / "client-result.json")],
                env=env, capture_output=True, text=True, timeout=35,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            (folder / "client-console.log").write_text(client.stdout + client.stderr, encoding="utf-8")
            result["clientExitCode"] = client.returncode
            result["client"] = json.loads((folder / "client-result.json").read_text("utf-8"))
            if client.returncode != 0:
                raise AssertionError("Real protocol client did not receive expected policy failure rejection")
            result["passed"] = True
        except Exception as failure:
            result["passed"] = False
            result["error"] = str(failure)
        finally:
            if process.poll() is None:
                process.stdin.write("stop\n")
                process.stdin.flush()
                try:
                    process.wait(timeout=90)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    result["forcedStop"] = True
            result["serverExitCode"] = process.returncode
            result["elapsedSeconds"] = round(time.time() - started, 2)
            if process.returncode != 0 or result.get("forcedStop"):
                result["passed"] = False
            (folder / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
