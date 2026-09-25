"""Stage/download, install, then test isolated 1.19.4 Fabric/Forge servers.

The stage action does not invoke Java. Installer/runtime execution are separate
actions so constrained machines can schedule them after client/build runs end.
Uses the existing mod_runtime_smoke runner without changing its source.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

sys.dont_write_bytecode = True
import mod_runtime_smoke as runner

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(r"E:\CodexTemp\QiZhangVerdict\legacy-runtime")
JAVA = Path(r"E:\CodexTemp\mods-danzi\java\jdk-17.0.20.1+1-jre\bin\java.exe")
NODE = Path(r"E:\CodexTemp\Codex\RuntimeCache\codex-primary-runtime\dependencies\node\bin\node.exe")
NODE_MODULES = Path(r"E:\CodexTemp\QiZhangGuard\bot\node_modules")
MC = "1.19.4"
PIN = {
    "fabric": {
        "loaderVersion": "0.16.14", "port": 25601,
        "installer": "https://maven.fabricmc.net/net/fabricmc/fabric-installer/1.1.1/fabric-installer-1.1.1.jar",
        "installerSha256": "2487a69dd6f9d9c2605265a7142d77c26ab62edc620e6bcf810d581d2ee31b79",
        "api": "https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/0.87.2+1.19.4/fabric-api-0.87.2+1.19.4.jar",
        "apiSha256": "a92650d48a9f672dc74e8b1eaefedb28dc83a13a80431215900181aa3a8675d8",
    },
    "forge": {
        "loaderVersion": "1.19.4-45.4.5", "port": 25602,
        "installer": "https://maven.minecraftforge.net/net/minecraftforge/forge/1.19.4-45.4.5/forge-1.19.4-45.4.5-installer.jar",
        "installerSha256": "1b4475d6ece01e7242855504fbe0fe37ac79efd7b3281bf42b8dcf390d421f35",
    },
}


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "QiZhangVerdict-compatibility-validation/0.2"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def verified_download(url, expected):
    downloads = CACHE / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    official = fetch(url + ".sha256").decode("ascii").strip().split()[0].lower()
    if official != expected:
        raise ValueError("Official checksum differs from reviewed pin: " + url)
    target = downloads / url.rsplit("/", 1)[1]
    if not target.exists():
        with target.open("xb") as output:
            output.write(fetch(url))
    if runner.digest(target) != expected:
        raise ValueError("Cached artifact checksum mismatch: " + str(target))
    return {"url": url, "checksumUrl": url + ".sha256", "sha256": expected, "path": str(target), "bytes": target.stat().st_size}


def safe_directory(value):
    directory = Path(value).resolve()
    directory.relative_to(CACHE.resolve())
    if directory == CACHE.resolve():
        raise ValueError("Use a NEW child directory, not the cache root")
    return directory


def read_marker(value):
    directory = safe_directory(value)
    metadata = json.loads((directory / runner.MARKER).read_text(encoding="utf-8"))
    if metadata.get("product") != "QiZhangVerdict" or metadata.get("minecraft") != MC or metadata.get("loader") not in PIN:
        raise ValueError("Not this tool's isolated 1.19.4 test directory")
    return directory, metadata


def stage(args):
    directory = safe_directory(args.directory)
    if directory.exists():
        raise ValueError("Stage requires a NEW directory")
    pin = PIN[args.loader]
    installer = verified_download(pin["installer"], pin["installerSha256"])
    api = verified_download(pin["api"], pin["apiSha256"]) if args.loader == "fabric" else None
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "mods").mkdir()
    (directory / "config").mkdir()
    shutil.copy2(installer["path"], directory / "loader-installer.jar")
    if api:
        shutil.copy2(api["path"], directory / "mods" / Path(api["path"]).name)
    metadata = {"product": "QiZhangVerdict", "profile": args.loader + "-" + MC,
                "loader": args.loader, "minecraft": MC, "loader_version": pin["loaderVersion"],
                "java": str(Path(args.java).resolve()), "installer_java": str(Path(args.java).resolve()),
                "prepared": False, "downloaded": True, "installer": installer, "fabric_api": api,
                "port": pin["port"], "thirdPartyAnticheatInstalled": False,
                "stageExecutedJava": False, "stagedOn": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    runner.json_write(directory / runner.MARKER, metadata)
    runner.json_write(directory / "integration-receipt.json", {
        "product": "QiZhangVerdict", "profile": metadata["profile"],
        "coverage": "Guard adapter only; no Grim or AntiXray in this fixture",
        "artifacts": [{"key": "fabric-api-1.19.4", "filename": Path(api["path"]).name,
                       "hashes": {"sha256": api["sha256"]}}] if api else []})
    print(json.dumps({"staged": str(directory), "loader": args.loader, "javaExecuted": False,
                      "installerSha256": installer["sha256"], "fabricApiSha256": api["sha256"] if api else None}), flush=True)


def install(args):
    directory, metadata = read_marker(args.directory)
    if metadata["prepared"]:
        raise ValueError("Installer already completed; preserve existing evidence")
    if not args.accept_eula:
        raise ValueError("Test setup requires --accept-eula before writing eula=true")
    installer = directory / "loader-installer.jar"
    if runner.digest(installer) != metadata["installer"]["sha256"]:
        raise ValueError("Installer changed since staging")
    if metadata["loader"] == "fabric":
        arguments = ["server", "-mcversion", MC, "-loader", metadata["loader_version"], "-downloadMinecraft", "-dir", str(directory)]
    else:
        arguments = ["--installServer", str(directory)]
    with (directory / "install-console.log").open("xb") as output:
        done = subprocess.run([metadata["installer_java"], "-Xmx768M", "-Djava.awt.headless=true", "-jar", str(installer), *arguments],
                              cwd=directory, stdout=output, stderr=subprocess.STDOUT, timeout=900,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    metadata["install_exit_code"] = done.returncode
    metadata["install_console_sha256"] = runner.digest(directory / "install-console.log")
    if done.returncode:
        runner.json_write(directory / runner.MARKER, metadata)
        raise RuntimeError("Installer failed; inspect its preserved log")
    if metadata["loader"] == "fabric":
        metadata["runtime_args"] = ["-jar", "fabric-server-launch.jar", "nogui"]
    else:
        files = list((directory / "libraries").rglob("win_args.txt" if os.name == "nt" else "unix_args.txt"))
        if len(files) != 1:
            raise ValueError("Expected exactly one Forge runtime argument file")
        metadata["runtime_args"] = ["@" + str(files[0].relative_to(directory)), "nogui"]
    metadata["javaVersion"] = subprocess.run([metadata["java"], "-version"], capture_output=True, text=True, check=True).stderr.strip()
    (directory / "eula.txt").write_text("eula=true\n", encoding="ascii")
    generator = json.dumps({"layers": [{"block": "minecraft:bedrock", "height": 1}, {"block": "minecraft:dirt", "height": 2},
                                        {"block": "minecraft:grass_block", "height": 1}], "biome": "minecraft:plains"}, separators=(",", ":"))
    (directory / "server.properties").write_text(
        f"server-ip=127.0.0.1\nserver-port={metadata['port']}\nonline-mode=true\nenforce-secure-profile=false\n"
        "view-distance=2\nsimulation-distance=2\nmax-players=5\nspawn-protection=0\n"
        "difficulty=peaceful\nspawn-monsters=false\nspawn-animals=false\nlevel-type=minecraft:flat\n"
        f"generator-settings={generator}\ngenerate-structures=false\nlevel-seed=547462\n", encoding="ascii")
    metadata["prepared"] = True
    runner.json_write(directory / runner.MARKER, metadata)
    print(json.dumps({"installed": str(directory), "loader": metadata["loader"], "exitCode": done.returncode}), flush=True)


def run(args):
    directory, metadata = read_marker(args.directory)
    with socket.socket() as test:
        test.bind(("127.0.0.1", metadata["port"]))
    if not metadata["prepared"]:
        raise ValueError("Run install after staging, before starting the server")
    source = Path(args.guard_jar).resolve()
    expected_name = f"qizhangverdict-{metadata['loader']}-{MC}-0.2.0-dev.jar"
    if source.name != expected_name:
        raise ValueError("Expected " + expected_name)
    if args.expected_guard_sha256 and runner.digest(source) != args.expected_guard_sha256.lower():
        raise ValueError("Product hash differs from requested test target")
    command = argparse.Namespace(directory=str(directory), guard_jar=str(source), timeout=240,
                                 protocol_node=str(NODE) if metadata["loader"] == "fabric" else None,
                                 protocol_node_modules=str(NODE_MODULES), protocol_timeout=240)
    code = runner.run(command)
    path = directory / "smoke-result.json"
    evidence = json.loads(path.read_text(encoding="utf-8"))
    evidence["loader_installation_metadata"] = str(directory / runner.MARKER)
    evidence["loader_installation_metadata_sha256"] = runner.digest(directory / runner.MARKER)
    evidence["guard_only_adapter_test"] = True
    evidence["grim_antixray_installed"] = False
    evidence["installer_url"] = metadata["installer"]["url"]
    evidence["installer_sha256"] = metadata["installer"]["sha256"]
    evidence["javaVersion"] = metadata["javaVersion"]
    if metadata["loader"] == "fabric":
        evidence["expected_protocol_case_count"] = 26
        if evidence.get("protocol_result", {}).get("passed") != 26:
            evidence["all_requested_checks_passed"] = False
            code = 1
    runner.json_write(path, evidence)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    p = subs.add_parser("stage", help="Download and verify only; does not invoke Java")
    p.add_argument("--loader", choices=PIN, required=True)
    p.add_argument("--directory", required=True)
    p.add_argument("--java", default=str(JAVA))
    p.set_defaults(func=stage)
    p = subs.add_parser("install", help="Run the official installer after memory-intensive tasks finish")
    p.add_argument("--directory", required=True)
    p.add_argument("--accept-eula", action="store_true")
    p.set_defaults(func=install)
    p = subs.add_parser("run", help="Test a built guard artifact with preserved actual process evidence")
    p.add_argument("--directory", required=True)
    p.add_argument("--guard-jar", required=True)
    p.add_argument("--expected-guard-sha256")
    p.set_defaults(func=run)
    args = parser.parse_args()
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
