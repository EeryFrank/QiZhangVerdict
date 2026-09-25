#!/usr/bin/env python3
"""Prepare isolated mod servers and record real startup/clean-stop evidence.

The directory must be NEW on prepare and carry this tool's marker on run.
No graphical client, multiplayer gameplay or anti-cheat accuracy is claimed.
"""
from __future__ import annotations
import argparse
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

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations"))
import manage_integrations as integrations

VERSIONS = {"fabric": "0.16.14", "neoforge": "21.1.244", "forge": "1.20.1-47.4.23"}
MARKER = ".qizhang-verdict-smoke.json"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_write(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def status_responses(text):
    # Forge can log its guard initialization after vanilla's Done line. Do not
    # count that startup banner as a reply to the actual console command.
    return [line for line in text.splitlines() if "QiZhangVerdict sessions=" in line and "started:" not in line]


def download(url, path):
    if Path(path).exists():
        raise ValueError("Download target exists")
    req = urllib.request.Request(url, headers={"User-Agent": "QiZhangVerdict/0.1 integration smoke"})
    with urllib.request.urlopen(req, timeout=60) as response, Path(path).open("xb") as out:
        shutil.copyfileobj(response, out)


def prepare(args):
    directory = Path(args.directory).absolute()
    if directory.exists():
        raise ValueError("Prepare requires a NEW directory")
    profile = integrations.read_json(ROOT / "integrations/dependencies.lock.json")["profiles"][args.profile]
    loader, mc = profile["loader"], profile["minecraft"]
    if loader not in VERSIONS:
        raise ValueError("Only Fabric/Forge/NeoForge profiles supported")
    if not args.accept_eula:
        raise ValueError("An explicit --accept-eula is required before writing eula=true")
    integrations.stage(argparse.Namespace(lock=ROOT / "integrations/dependencies.lock.json", profile=args.profile, cache=args.cache, output=directory))
    metadata = {"product": "QiZhangVerdict", "profile": args.profile, "loader": loader, "minecraft": mc,
                "loader_version": VERSIONS[loader], "java": str(Path(args.runtime_java or args.java).resolve()),
                "installer_java": str(Path(args.java).resolve()), "prepared": False}
    json_write(directory / MARKER, metadata)
    if loader == "fabric":
        url = "https://maven.fabricmc.net/net/fabricmc/fabric-installer/1.1.1/fabric-installer-1.1.1.jar"
        install_args = ["server", "-mcversion", mc, "-loader", VERSIONS[loader], "-downloadMinecraft", "-dir", str(directory)]
    elif loader == "neoforge":
        version = VERSIONS[loader]
        url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{version}/neoforge-{version}-installer.jar"
        install_args = ["--installServer", str(directory)]
    else:
        version = VERSIONS[loader]
        url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{version}/forge-{version}-installer.jar"
        install_args = ["--installServer", str(directory)]
    installer = directory / "loader-installer.jar"
    download(url, installer)
    metadata["installer"] = {"url": url, "sha256": digest(installer)}
    java_command = [args.java, "-Djava.awt.headless=true", "-jar", str(installer), *install_args]
    with (directory / "install-console.log").open("wb") as log:
        done = subprocess.run(java_command, cwd=directory, stdout=log, stderr=subprocess.STDOUT, timeout=900, creationflags=NO_WINDOW)
    metadata["install_exit_code"] = done.returncode
    if done.returncode != 0:
        json_write(directory / MARKER, metadata)
        raise RuntimeError("Loader install failed; see " + str(directory / "install-console.log"))
    if loader == "fabric":
        runtime_args = ["-jar", "fabric-server-launch.jar", "nogui"]
    else:
        argument_files = list((directory / "libraries").rglob("win_args.txt" if os.name == "nt" else "unix_args.txt"))
        if len(argument_files) != 1:
            raise ValueError("Expected one installed loader args file")
        runtime_args = ["@" + str(argument_files[0].relative_to(directory)), "nogui"]
    config = directory / "config"
    config.mkdir(exist_ok=True)
    for path in (directory / "config-fragments").glob("*.toml"):
        shutil.copy2(path, config / path.name)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (directory / "eula.txt").write_text("eula=true\n", encoding="ascii")
    (directory / "server.properties").write_text("server-ip=127.0.0.1\nserver-port=" + str(port) + "\nonline-mode=true\nview-distance=2\nsimulation-distance=2\nmax-players=2\nspawn-protection=0\nallow-flight=false\nenable-rcon=false\nenable-query=false\nlevel-name=smoke-world\nlevel-seed=547462\n", encoding="ascii")
    metadata.update({"prepared": True, "runtime_args": runtime_args, "port": port})
    json_write(directory / MARKER, metadata)
    print("Prepared " + args.profile + " at " + str(directory), flush=True)


def run(args):
    directory = Path(args.directory).resolve()
    marker = directory / MARKER
    metadata = integrations.read_json(marker)
    if not metadata["prepared"] or metadata["product"] != "QiZhangVerdict":
        raise ValueError("Not a prepared smoke directory")
    source = Path(args.guard_jar).resolve()
    if not source.name.startswith("qizhangverdict-") or source.suffix != ".jar":
        raise ValueError("Unexpected guard artifact")
    if metadata["loader"] not in source.name or metadata["minecraft"] not in source.name:
        raise ValueError("Guard artifact does not match prepared profile")
    old = list((directory / "mods").glob("qizhangverdict-*.jar"))
    if old:
        raise ValueError("Smoke directory already has a guard jar; prepare a fresh run")
    target = directory / "mods" / source.name
    source_hash = digest(source)
    with source.open("rb") as inp, target.open("xb") as out:
        shutil.copyfileobj(inp, out)
    if source_hash != digest(source) or source_hash != digest(target):
        raise ValueError("Build artifact changed while copying")
    evidence = {"product": "QiZhangVerdict", "profile": metadata["profile"], "java": metadata["java"],
                "guard_source": str(source), "guard_sha256": source_hash, "guard_target": str(target),
                "scope": "Dedicated server startup + console status + clean shutdown, no player/client gameplay",
                "mods": [{"filename": p.name, "sha256": digest(p)} for p in sorted((directory / "mods").glob("*.jar"))],
                "started": False, "console_status_verified": False, "timed_out": False,
                "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if args.protocol_node:
        properties = directory / "server.properties"
        settings = properties.read_text(encoding="ascii")
        settings = re.sub(r"(?m)^online-mode=.*$", "online-mode=false", settings)
        settings = re.sub(r"(?m)^max-players=.*$", "max-players=20", settings)
        properties.write_text(settings, encoding="ascii")
        evidence["scope"] += "; real loopback TCP protocol clients with synthetic self-reports, not rendered mod clients"
        evidence["offline_mode_for_isolated_protocol_test"] = True
    console = directory / ("console.log" if args.protocol_node else "smoke-console.log")
    evidence["console_path"] = str(console)
    command = [metadata["java"], "-Xms512M", "-Xmx2G", "-Djava.awt.headless=true", "-Dfile.encoding=UTF-8", *metadata["runtime_args"]]
    start = time.monotonic()
    process = None
    with console.open("xb") as output:
        try:
            process = subprocess.Popen(command, cwd=directory, stdin=subprocess.PIPE, stdout=output, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
            while process.poll() is None and time.monotonic() - start < args.timeout:
                text = console.read_text(encoding="utf-8", errors="replace")
                if re.search(r'Done \([\d.,]+s\)! For help', text):
                    evidence["started"] = True
                    break
                time.sleep(0.5)
            if evidence["started"]:
                startup_status_count = len(status_responses(text))
                process.stdin.write(b"qzverdict status\n")
                process.stdin.flush()
                for _ in range(20):
                    time.sleep(0.5)
                    reply = console.read_text(encoding="utf-8", errors="replace")
                    if len(status_responses(reply)) > startup_status_count:
                        evidence["console_status_verified"] = True
                        break
                if args.protocol_node:
                    protocol_check(args, directory, metadata, process, evidence)
                process.stdin.write(b"stop\n")
                process.stdin.flush()
                try:
                    process.wait(timeout=90)
                except subprocess.TimeoutExpired:
                    evidence["timed_out"] = True
                    process.kill()
                    process.wait(timeout=30)
            elif process.poll() is None:
                evidence["timed_out"] = True
                process.kill()
                process.wait(timeout=30)
        except Exception as exc:
            evidence["runner_error"] = type(exc).__name__ + ": " + str(exc)
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=30)
            evidence["exit_code"] = process.returncode if process is not None else None
    evidence["elapsed_seconds"] = round(time.monotonic() - start, 2)
    parse_console_evidence(evidence, metadata, directory, console)
    json_write(directory / "smoke-result.json", evidence)
    print(json.dumps({k: evidence[k] for k in ("profile", "started", "exit_code", "elapsed_seconds", "passed_startup_only", "guard_sha256")}), flush=True)
    return 0 if evidence["all_requested_checks_passed"] else 1


def parse_console_evidence(evidence, metadata, directory, console):
    text = console.read_text(encoding="utf-8", errors="replace")
    receipt = integrations.read_json(directory / "integration-receipt.json")
    expected_keys = [artifact["key"] for artifact in receipt["artifacts"]]
    evidence["parser_version"] = 2
    evidence["expected_integrations"] = {
        "grim": any(key.startswith("grim-") for key in expected_keys),
        "antixray": any(key.startswith("antixray-") for key in expected_keys)}
    evidence["console_sha256"] = digest(console)
    evidence["guard_log_lines"] = [line for line in text.splitlines() if "qizhang" in line.lower() or "七章" in line]
    evidence["antixray_log_lines"] = [line for line in text.splitlines() if "antixray" in line.lower() or "anti-xray" in line.lower()]
    evidence["grim_log_lines"] = [line for line in text.splitlines() if "grim" in line.lower()]
    evidence["error_lines"] = [line for line in text.splitlines() if "ERROR" in line or "Exception" in line]
    evidence["nonfatal_upstream_notices"] = [line for line in text.splitlines()
        if "Failed reading REFMAP JSON" in line or "Reference map '' for packetevents-" in line
        or "Grim will run without commands enabled" in line
        or ("Mixin config antixray." in line and 'does not specify "minVersion"' in line)]
    evidence["pass_definition"] = "Done + QiZhangVerdict console status + dependency initialization + clean stop; not an error-free log or anticheat accuracy claim"
    evidence["integration_startup_errors"] = [line for line in text.splitlines() if "Could not load SQLite driver" in line or "Failed to load mods" in line]
    evidence["status_response_lines"] = status_responses(text)
    evidence["guard_status_observed"] = bool(evidence["status_response_lines"])
    evidence["antixray_loaded"] = bool(re.search(r"Successfully initialized antixray for " + re.escape(metadata["loader"]) + r"\b", text))
    evidence["grim_loaded"] = bool(re.search(r"Grim Version: \d+\.\d+", text))
    evidence["grim_command_framework_available"] = evidence["grim_loaded"] and "Grim will run without commands enabled" not in text
    evidence["passed_startup_only"] = (evidence["started"] and evidence["exit_code"] == 0
                                      and not evidence["timed_out"] and evidence["guard_status_observed"] and evidence["console_status_verified"]
                                      and (not evidence["expected_integrations"]["antixray"] or evidence["antixray_loaded"])
                                      and not evidence["integration_startup_errors"]
                                      and "runner_error" not in evidence
                                      and (not evidence["expected_integrations"]["grim"] or evidence["grim_loaded"]))
    evidence["all_requested_checks_passed"] = evidence["passed_startup_only"] and ("protocol_script_sha256" not in evidence or evidence.get("protocol_exit_code") == 0)
    protocol_console = directory / "protocol-console.log"
    if protocol_console.is_file():
        protocol_text = protocol_console.read_text(encoding="utf-8", errors="replace")
        decoder_errors = [line for line in protocol_text.splitlines() if line.startswith("PartialReadError:")]
        evidence["protocol_client_decoder_error_count"] = len(decoder_errors)
        evidence["protocol_client_decoder_error_examples"] = list(dict.fromkeys(decoder_errors))[:3]


def refresh(args):
    """Correct a parser result from immutable server logs without rerunning Java."""
    directory = Path(args.directory).resolve()
    metadata = integrations.read_json(directory / MARKER)
    path = directory / "smoke-result.json"
    evidence = integrations.read_json(path)
    console = Path(evidence.get("console_path", directory / "smoke-console.log"))
    original_console_hash = evidence["console_sha256"]
    if digest(console) != original_console_hash:
        raise ValueError("Console changed after original run; cannot refresh evidence")
    if evidence.get("parser_version") == 2:
        raise ValueError("Already parsed with version 2; retain existing evidence")
    original = directory / "smoke-result.pre-parser-v2.json"
    with original.open("xb") as out:
        out.write(path.read_bytes())
    parse_console_evidence(evidence, metadata, directory, console)
    evidence["parser_refresh"] = {"method": "mod_runtime_smoke.py refresh; no new server execution",
        "previous_report": str(original), "previous_report_sha256": digest(original),
        "unchanged_console_sha256": original_console_hash, "parser_script_sha256": digest(__file__)}
    json_write(path, evidence)
    print(json.dumps({k: evidence[k] for k in ("profile", "grim_loaded", "antixray_loaded", "passed_startup_only")}), flush=True)
    return 0


def protocol_check(args, directory, metadata, server, evidence):
    """Forward this NEW runtime's console queue while running root's protocol suite."""
    script = ROOT / "scripts/protocol_smoke.cjs"
    environment = os.environ.copy()
    environment.update({"NODE_PATH": args.protocol_node_modules,
                        "QV_DATA_DIR": str(directory / "config/qizhangverdict"),
                        "QV_TEST_COMMAND_GATE": "1", "QV_TEST_ANTIXRAY": "0"})
    evidence["protocol_script_sha256"] = digest(script)
    evidence["protocol_data_directory"] = environment["QV_DATA_DIR"]
    queue = directory / "commands.queue"
    queue.touch(exist_ok=False)
    forwarded = 0
    start = time.monotonic()
    with (directory / "protocol-console.log").open("xb") as output:
        bot = subprocess.Popen([args.protocol_node, str(script), metadata["minecraft"], str(metadata["port"]), str(directory)],
                               cwd=directory, env=environment, stdout=output, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
        try:
            while bot.poll() is None and server.poll() is None and time.monotonic() - start < args.protocol_timeout:
                lines = queue.read_text(encoding="utf-8").splitlines(keepends=True)
                complete = [line for line in lines if line.endswith("\n")]
                for line in complete[forwarded:]:
                    server.stdin.write(line.encode("utf-8"))
                    server.stdin.flush()
                    forwarded += 1
                time.sleep(0.1)
        finally:
            if bot.poll() is None:
                evidence["protocol_timed_out"] = time.monotonic() - start >= args.protocol_timeout
                bot.kill()
            bot.wait(timeout=30)
    evidence["protocol_exit_code"] = bot.returncode
    evidence["protocol_elapsed_seconds"] = round(time.monotonic() - start, 2)
    evidence["protocol_forwarded_commands"] = forwarded
    evidence["protocol_console_sha256"] = digest(directory / "protocol-console.log")
    result = directory / "protocol-result.json"
    if result.exists():
        evidence["protocol_result"] = integrations.read_json(result)
        evidence["protocol_result_sha256"] = digest(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--profile", required=True)
    p.add_argument("--directory", required=True)
    p.add_argument("--cache", required=True)
    p.add_argument("--java", required=True)
    p.add_argument("--runtime-java", help="Optional runtime JVM; installer still uses --java")
    p.add_argument("--accept-eula", action="store_true")
    p.set_defaults(func=prepare)
    r = commands.add_parser("run")
    r.add_argument("--directory", required=True)
    r.add_argument("--guard-jar", required=True)
    r.add_argument("--timeout", type=int, default=240)
    r.add_argument("--protocol-node", help="Optional Node executable for isolated offline-mode TCP tests")
    r.add_argument("--protocol-node-modules", default=r"E:\CodexTemp\QiZhangGuard\bot\node_modules")
    r.add_argument("--protocol-timeout", type=int, default=240)
    r.set_defaults(func=run)
    f = commands.add_parser("refresh", help="Reparse an existing result with verified unchanged console bytes")
    f.add_argument("--directory", required=True)
    f.set_defaults(func=refresh)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
