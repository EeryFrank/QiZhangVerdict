"""Stage/download, install, then test isolated 1.16.5 / 1.18.2 / 1.19.4 servers.

The stage action does not invoke Java. Installer/runtime execution are separate
actions so constrained machines can schedule them after client/build runs end.
Uses the existing mod_runtime_smoke runner without changing its source.
"""
from __future__ import annotations
import argparse
import ctypes
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
import zipfile
import struct

sys.dont_write_bytecode = True
import mod_runtime_smoke as runner

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(r"E:\CodexTemp\QiZhangVerdict\legacy-runtime")
JAVA = Path(r"E:\CodexTemp\mods-danzi\java\jdk-17.0.20.1+1-jre\bin\java.exe")
JAVA8 = Path(r"E:\CodexTemp\QiZhangVerdict\toolchains\jdk8\jdk8u504-b01\bin\java.exe")
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


PINS_BY_MINECRAFT = {
    "1.19.4": PIN,
    "1.16.5": {
        "fabric": {
            "loaderVersion": "0.16.14", "port": 25651,
            "installer": PIN["fabric"]["installer"],
            "installerSha256": PIN["fabric"]["installerSha256"],
            "api": "https://github.com/FabricMC/fabric-api/releases/download/0.42.0%2B1.16/fabric-api-0.42.0%2B1.16.jar",
            "apiSha256": "3df8dd503f35aa0ac9fab8ad9f9a369fdfd0b1ab544af19a3d626d948fb4586c",
            "apiDownloadName": "fabric-api-0.42.0+1.16-distribution.jar",
            "apiReleaseMetadata": "https://api.modrinth.com/v2/version/IQ3UGSc2",
            "apiReleaseVersion": "0.42.0+1.16",
            "apiReleaseSha512": "20defa796ea605fbad3285a7216c3bf8ac88bffbd0eee997c77e49dd6fbcf86631ef4ab75ab571d3d402181d1aa5c2bd945985a5119b411ef014b31c4ee1a5fb",
        },
        "forge": {
            "loaderVersion": "1.16.5-36.2.42", "port": 25652,
            "installer": "https://maven.minecraftforge.net/net/minecraftforge/forge/1.16.5-36.2.42/forge-1.16.5-36.2.42-installer.jar",
            "installerSha256": "dfa90c681f30be2406548b6429bccb68d95af4f64ab19b8c58f6128fd50ff857",
        },
    },
    "1.18.2": {
        "fabric": {
            "loaderVersion": "0.16.14", "port": 25621,
            "installer": PIN["fabric"]["installer"],
            "installerSha256": PIN["fabric"]["installerSha256"],
            # The Maven aggregate for this old release has no nested modules.
            # Use FabricMC's complete release, cross-checked against the official
            # Fabric API project metadata, instead of the 4,877-byte Maven jar.
            "api": "https://github.com/FabricMC/fabric-api/releases/download/0.77.0%2B1.18.2/fabric-api-0.77.0%2B1.18.2.jar",
            "apiSha256": "6f822fb5aa481b4a6c1cfb8612bbfecc62a58e69d2c792f61a0eafa580e75999",
            "apiDownloadName": "fabric-api-0.77.0+1.18.2-distribution.jar",
            "apiReleaseMetadata": "https://api.modrinth.com/v2/version/qk28POfr",
            "apiReleaseSha512": "adb62b0d73e83cf9302a59a55ffe7ca2cf6f4ebb34312ec09e0f56b99ebc173e02dd4f0b8ec059d7262a14857dc1911645b090e460f20fd8e2d48aa5f2fdbefa",
        },
        "forge": {
            "loaderVersion": "1.18.2-40.3.12", "port": 25622,
            "installer": "https://maven.minecraftforge.net/net/minecraftforge/forge/1.18.2-40.3.12/forge-1.18.2-40.3.12-installer.jar",
            "installerSha256": "dcff493f6c2212bdf6ae087f98029cd317a79759ab1009dce23e63e7dba0e216",
        },
    },
}
MIXIN_FLAGS = ["-Dmixin.debug.verbose=true", "-Dmixin.debug.export=true", "-Dmixin.debug.countInjections=true"]


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "QiZhangVerdict-compatibility-validation/0.2"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def verified_download(url, expected, release_metadata=None, release_sha512=None, download_name=None, release_version="0.77.0+1.18.2"):
    downloads = CACHE / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    official_release = None
    if release_metadata:
        metadata = json.loads(fetch(release_metadata))
        if metadata.get("project_id") != "P7dR8mSH" or metadata.get("version_number") != release_version or MC not in metadata.get("game_versions", []):
            raise ValueError("Unexpected official Fabric API release metadata")
        # Old Fabric API releases may mark every file primary=false. Select the
        # unique reviewed SHA-512 instead of mistaking that metadata for no jar.
        candidates = [f for f in metadata["files"] if f.get("hashes", {}).get("sha512") == release_sha512]
        if len(candidates) != 1:
            raise ValueError("Expected exactly one officially hashed Fabric API distribution")
        official_release = candidates[0]
        if official_release["hashes"]["sha512"] != release_sha512:
            raise ValueError("Official release checksum differs from reviewed pin")
    else:
        official = fetch(url + ".sha256").decode("ascii").strip().split()[0].lower()
        if official != expected:
            raise ValueError("Official checksum differs from reviewed pin: " + url)
    target = downloads / (download_name or url.rsplit("/", 1)[1])
    if not target.exists():
        with target.open("xb") as output:
            output.write(fetch(url))
    if runner.digest(target) != expected:
        raise ValueError("Cached artifact checksum mismatch: " + str(target))
    record = {"url": url, "checksumUrl": release_metadata or url + ".sha256", "sha256": expected,
              "path": str(target), "bytes": target.stat().st_size}
    if official_release:
        if hashlib.sha512(target.read_bytes()).hexdigest() != release_sha512 or target.stat().st_size != official_release["size"]:
            raise ValueError("Official Fabric API release size/SHA-512 mismatch")
        record["officialSha512"] = release_sha512
    return record


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
        raise ValueError("Not this tool's isolated " + MC + " test directory")
    return directory, metadata


def stage(args):
    directory = safe_directory(args.directory)
    if directory.exists():
        raise ValueError("Stage requires a NEW directory")
    pin = PIN[args.loader]
    installer = verified_download(pin["installer"], pin["installerSha256"])
    api = verified_download(pin["api"], pin["apiSha256"], pin.get("apiReleaseMetadata"),
                            pin.get("apiReleaseSha512"), pin.get("apiDownloadName"), pin.get("apiReleaseVersion", "0.77.0+1.18.2")) if args.loader == "fabric" else None
    if api:
        with zipfile.ZipFile(api["path"]) as artifact:
            api_descriptor = json.loads(artifact.read("fabric.mod.json"))
            modules = api_descriptor.get("jars", [])
            if not modules or any(module["file"] not in artifact.namelist() for module in modules):
                raise ValueError("Fabric API deployment needs a full distribution with embedded modules")
            api["nestedModules"] = len(modules)
            api["fullDistributionVerified"] = True
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
                "mixinAuditRequested": bool(getattr(args, "mixin_audit", False)),
                "stageExecutedJava": False, "stagedOn": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    runner.json_write(directory / runner.MARKER, metadata)
    runner.json_write(directory / "integration-receipt.json", {
        "product": "QiZhangVerdict", "profile": metadata["profile"],
        "coverage": "Guard adapter only; no Grim or AntiXray in this fixture",
        "artifacts": [{"key": "fabric-api-" + MC, "filename": Path(api["path"]).name,
                       "hashes": {"sha256": api["sha256"]}}] if api else []})
    print(json.dumps({"staged": str(directory), "loader": args.loader, "javaExecuted": False,
                      "installerSha256": installer["sha256"], "fabricApiSha256": api["sha256"] if api else None}), flush=True)


def require_memory_for_116():
    """Keep legacy Java runs within the shared QA machine's agreed budget."""
    if MC != "1.16.5":
        return
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(name, ctypes.c_ulonglong) for name in ("totalPhys", "availPhys", "totalPage", "availPage", "totalVirtual", "availVirtual", "extended")]
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)) or status.availPhys < 4 * 1024**3:
        raise RuntimeError("Java deferred: fewer than 4 GiB free physical memory")


def install(args):
    directory, metadata = read_marker(args.directory)
    if metadata["prepared"]:
        raise ValueError("Installer already completed; preserve existing evidence")
    if not args.accept_eula:
        raise ValueError("Test setup requires --accept-eula before writing eula=true")
    installer = directory / "loader-installer.jar"
    if runner.digest(installer) != metadata["installer"]["sha256"]:
        raise ValueError("Installer changed since staging")
    require_memory_for_116()
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
    elif MC == "1.16.5":
        entry = directory / ("forge-" + metadata["loader_version"] + ".jar")
        if not entry.is_file():
            raise ValueError("Expected the official legacy Forge executable jar")
        metadata["runtime_args"] = ["-jar", entry.name, "nogui"]
    else:
        files = list((directory / "libraries").rglob("win_args.txt" if os.name == "nt" else "unix_args.txt"))
        if len(files) != 1:
            raise ValueError("Expected exactly one Forge runtime argument file")
        metadata["runtime_args"] = ["@" + str(files[0].relative_to(directory)), "nogui"]
    if metadata.get("mixinAuditRequested"):
        metadata["runtime_args"] = MIXIN_FLAGS + metadata["runtime_args"]
    if MC == "1.16.5":
        # The frozen shared runner supplies -Xmx2G first. Java uses the last
        # repeated heap option, so this profile explicitly caps itself at 1.5 GiB.
        metadata["runtime_args"] = ["-Xmx1536M"] + metadata["runtime_args"]
        metadata["effectiveMaximumHeapMiB"] = 1536
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


def class_name(raw):
    """Read this_class from an exported JVM class without starting another JVM."""
    if raw[:4] != bytes.fromhex("CAFEBABE"):
        raise ValueError("Not a JVM class file")
    count = struct.unpack_from(">H", raw, 8)[0]
    pos, index = 10, 1
    pool = [None] * count
    while index < count:
        tag = raw[pos]
        pos += 1
        if tag == 1:
            length = struct.unpack_from(">H", raw, pos)[0]
            pos += 2
            pool[index] = raw[pos:pos + length].decode("utf-8", errors="replace")
            pos += length
        elif tag in (7, 8, 16, 19, 20):
            pool[index] = struct.unpack_from(">H", raw, pos)[0]
            pos += 2
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            pos += 4
        elif tag in (5, 6):
            pos += 8
            index += 1
        elif tag == 15:
            pos += 3
        else:
            raise ValueError("Unknown constant-pool tag")
        index += 1
    this_class = struct.unpack_from(">H", raw, pos + 2)[0]
    return pool[pool[this_class]]


def audit_mixin(directory):
    found = []
    for path in (directory / ".mixin.out").rglob("*.class"):
        raw = path.read_bytes()
        if b"qizhangverdict$denyPendingCommand" not in raw:
            continue
        name = class_name(raw)
        if name not in ("net/minecraft/class_2170", "net/minecraft/commands/Commands", "net/minecraft/command/Commands"):
            continue
        references = b"cn/qizhang/guard/minecraft/MinecraftGuard" in raw and b"isWaiting" in raw
        found.append({"file": str(path), "class": name, "sha256": runner.digest(path),
                      "bytes": len(raw), "injectedGuardCallPresent": references})
    return {"scope": "Actual runtime-exported transformed command dispatch target, not source annotation inspection.",
            "flags": MIXIN_FLAGS, "exports": found,
            "passed": len(found) == 1 and found[0]["injectedGuardCallPresent"]}


def run(args):
    directory, metadata = read_marker(args.directory)
    require_memory_for_116()
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
    if metadata.get("mixinAuditRequested"):
        audit = audit_mixin(directory)
        audit_file = directory / "mixin-audit.json"
        runner.json_write(audit_file, audit)
        evidence["mixinAudit"] = str(audit_file)
        evidence["mixinAuditSha256"] = runner.digest(audit_file)
        evidence["mixinActualTargetExportVerified"] = audit["passed"]
        if not audit["passed"]:
            evidence["all_requested_checks_passed"] = False
            code = 1
    evidence["legacy_harness_sha256"] = runner.digest(__file__)
    evidence["runtime_harness_sha256"] = runner.digest(ROOT / "scripts/mod_runtime_smoke.py")
    runner.json_write(path, evidence)
    return code


def main():
    global MC, PIN
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    p = subs.add_parser("stage", help="Download and verify only; does not invoke Java")
    p.add_argument("--loader", choices=PIN, required=True)
    p.add_argument("--minecraft", choices=PINS_BY_MINECRAFT, default="1.19.4")
    p.add_argument("--mixin-audit", action="store_true", help="Export and verify the 1.16.5 / 1.18.2 command dispatch Mixin")
    p.add_argument("--directory", required=True)
    p.add_argument("--java", help="Default: Java 8 for 1.16.5, Java 17 otherwise")
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
    if args.action == "stage":
        MC = args.minecraft
        args.java = args.java or str(JAVA8 if MC == "1.16.5" else JAVA)
        if args.mixin_audit and MC not in ("1.16.5", "1.18.2"):
            parser.error("--mixin-audit currently verifies the 1.16.5 / 1.18.2 command dispatch target only")
    else:
        metadata = json.loads((safe_directory(args.directory) / runner.MARKER).read_text(encoding="utf-8"))
        MC = metadata.get("minecraft")
    if MC not in PINS_BY_MINECRAFT:
        parser.error("Unsupported Minecraft version in test directory metadata")
    PIN = PINS_BY_MINECRAFT[MC]
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
