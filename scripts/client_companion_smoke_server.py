"""Temporary loopback Bukkit host for a real companion client; commands.queue controls stdin."""
import hashlib
import json
import pathlib
import shutil
import socket
import subprocess
import time
import argparse

PROJECT = pathlib.Path(__file__).resolve().parents[1]
CACHE = pathlib.Path(r"E:\CodexTemp\QiZhangGuard")
SOURCE = CACHE / "runtime/1.21.1-full-20260925-134742"
JAVA = pathlib.Path(r"D:\Java\jdk-21\bin\java.exe")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fabric-directory", type=pathlib.Path)
    args = parser.parse_args()
    fabric = args.fabric_directory is not None
    port = 25591 if fabric else 25590
    with socket.socket() as test:
        test.bind(("127.0.0.1", port))
    if fabric:
        folder = args.fabric_directory.resolve()
        folder.relative_to(CACHE.resolve())
        if not (folder / ".qizhang-verdict-stage").is_file() or not (folder / "fabric-server-launch.jar").is_file():
            raise ValueError("Expected an explicitly staged isolated Fabric test directory")
        plugin = (PROJECT / "platforms/1.21.1/fabric/build/libs/qizhangverdict-fabric-1.21.1-0.1.0.jar").read_bytes()
        (folder / "mods/qizhangverdict-fabric-1.21.1-0.1.0.jar").write_bytes(plugin)
    else:
        folder = CACHE / "runtime" / ("client-companion-bukkit-" + time.strftime("%Y%m%d-%H%M%S"))
        folder.mkdir(parents=True, exist_ok=False)
        for name in ("cache", "libraries", "versions"):
            if (SOURCE / name).exists():
                shutil.copytree(SOURCE / name, folder / name)
        shutil.copy2(SOURCE / "server.jar", folder / "server.jar")
        plugin = (PROJECT / "bukkit/build/libs/qizhangverdict-bukkit-0.1.0.jar").read_bytes()
        (folder / "plugins").mkdir()
        (folder / "plugins/qizhangverdict-bukkit-0.1.0.jar").write_bytes(plugin)
    (folder / "eula.txt").write_text("eula=true\n", encoding="ascii")
    (folder / "server.properties").write_text(
        f"server-ip=127.0.0.1\nserver-port={port}\nonline-mode=false\nenforce-secure-profile=false\n"
        "spawn-protection=0\nview-distance=2\nsimulation-distance=2\nmax-players=5\n"
        "level-type=minecraft:flat\ngenerate-structures=false\nlevel-seed=12955\n",
        encoding="utf-8",
    )
    queue = folder / "commands.queue"
    queue.write_text("", encoding="utf-8")
    result = {
        "directory": str(folder), "port": port, "host": "127.0.0.1", "javaExecutable": str(JAVA),
        "platform": "Fabric 1.21.1" if fabric else "Bukkit 1.21.1",
        "pluginSha256": hashlib.sha256(plugin).hexdigest(),
        "serverSha256": hashlib.sha256((folder / "server.jar").read_bytes()).hexdigest(),
        "commandsQueue": str(queue), "log": str(folder / "console.log"), "strictDefaults": True,
    }
    (folder / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result), flush=True)
    started = time.monotonic()
    with (folder / "console.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [str(JAVA), "-Xms256M", "-Xmx1536M", "-jar", "fabric-server-launch.jar" if fabric else "server.jar", "--nogui"],
            cwd=folder, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        consumed = 0
        try:
            while process.poll() is None:
                commands = queue.read_text("utf-8").splitlines()
                for command in commands[consumed:]:
                    if command.strip():
                        process.stdin.write(command + "\n")
                        process.stdin.flush()
                consumed = len(commands)
                if time.monotonic() - started > 900:
                    process.stdin.write("stop\n")
                    process.stdin.flush()
                    break
                time.sleep(0.1)
            process.wait(timeout=90)
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
            result["elapsedSeconds"] = round(time.monotonic() - started, 2)
            (folder / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
