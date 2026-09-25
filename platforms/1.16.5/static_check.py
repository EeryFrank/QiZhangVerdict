"""Read-only source/metadata audit; optional previews/reports belong in the supplied temporary directory.

GPL-3.0-only. This does not invoke a JVM, Gradle, compiler, loader or game.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-dir", type=Path)
    parser.add_argument("--java-parser-path", type=Path, help="optional external javalang 0.13.0 directory")
    args = parser.parse_args()
    passed, inputs, generated = [], {}, {}
    script = (ROOT / "gradle/adapt-sources.gradle").read_text(encoding="utf-8")
    entries = re.findall(r"\[input: '([^']+)', output: '([^']+)', changes: \[(.*?)\n    \]\]", script, re.S)
    require(len(entries) == 5, "Expected five explicitly reviewed adaptation inputs")
    for source, output, raw_changes in entries:
        path = ROOT / source
        data = path.read_bytes()
        inputs[path.resolve().relative_to(PROJECT).as_posix()] = hashlib.sha256(data).hexdigest()
        text = data.decode("utf-8")
        changes = re.findall(r"\['([^']*)', '([^']*)', (\d+)\]", raw_changes)
        require(changes, "Missing anchored replacement list")
        for before, after, count in changes:
            require(text.count(before) == int(count), "Shared source drift: " + before)
            text = text.replace(before, after)
        generated[output] = text
    passed.append("Five generated-source bridges match every anchored occurrence count")
    java = {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8") for p in ROOT.rglob("*.java") if "build" not in p.parts}
    java.update(generated)
    modern = re.compile(r"\bvar\s+\w+\s*=|\.readNBytes\(|Files\.writeString\(|Redirect\.DISCARD|\.toList\(\)\s*;|\.repeat\(|instanceof\s+\w+\s+\w+\s*[&)]")
    # Collectors.toList is Java 8; strip that exact call before rejecting Stream.toList.
    for name, text in java.items():
        require(not modern.search(text.replace("Collectors.toList()", "JAVA8_COLLECTOR")), "Modern syntax/API remains: " + name)
    passed.append("Local/generated Java has no known Java 9+ bridge API or syntax remnants")
    guard = generated["shared/main/cn/qizhang/guard/minecraft/MinecraftGuard.java"]
    require(".serverLevel()" not in guard and "p.getYRot()" not in guard and "p.getXRot()" not in guard, "Modern entity access remains")
    require("p.yRot" in guard and "p.xRot" in guard and "LogManager.getLogger" in guard, "Legacy mapped entity/logging bridge absent")
    for critical in ("owners.get(id) != player", '"STALE_REPORT"', "requiresCompanion()", "GameType.SPECTATOR", "service.acceptReport", "service.bannedSessions()"):
        require(critical in guard, "Guard policy/ownership bridge lost: " + critical)
    reporter = generated["client/main/cn/qizhang/guard/client/ClientReporter.java"]
    for critical in ("generation != request.generation", "Wire.decodeServerScope", "new ArrayBlockingQueue<Runnable>(1)", "latest = null", "request.clientThread.accept", "StandardOpenOption.CREATE_NEW", "1800, TimeUnit.MILLISECONDS", "1500, TimeUnit.MILLISECONDS"):
        require(critical in reporter, "Reporter contract lost: " + critical)
    require(reporter.count("LegacyJava8.readBounded(") == 5, "Probe bound replacements missing")
    passed.append("Shared policy, isolation, scope, connection ownership and coalescing contracts retained")
    fabric = json.loads((ROOT / "fabric/src/main/resources/fabric.mod.json").read_text(encoding="utf-8"))
    forge = tomllib.loads((ROOT / "forge/src/main/resources/META-INF/mods.toml").read_text(encoding="utf-8"))
    require(fabric["depends"].get("fabric") == ">=0.42.0" and "fabric-api" not in fabric["depends"], "Wrong 1.16 Fabric API mod identity")
    require(fabric["depends"]["minecraft"] == "1.16.5" and fabric["depends"]["java"] == ">=8", "Wrong Fabric target")
    require(fabric["license"] == forge["license"] == "GPL-3.0-only", "License metadata mismatch")
    require(forge["loaderVersion"] == "[36,)" and forge["dependencies"]["qizhangverdict"][0]["versionRange"] == "[1.16.5]", "Wrong Forge target")
    passed.append("Fabric exact fabric ID and both Java 8/Minecraft 1.16.5/GPL metadata targets")
    for loader in ("fabric", "forge"):
        data = json.loads((ROOT / loader / "src/main/resources/qizhangverdict.mixins.json").read_text())
        require(data["required"] and data["injectors"]["defaultRequire"] == 1 and data["compatibilityLevel"] == "JAVA_8", "Strict gate weakened")
        require(data["mixins"] == ["CommandGate116Mixin"] and data["refmap"] == "qizhangverdict.refmap.json", "Wrong gate or missing refmap")
    gate = java["src/main/java/cn/qizhang/guard/minecraft/mixin/CommandGate116Mixin.java"]
    require("performCommand(Lnet/minecraft/commands/CommandSourceStack;Ljava/lang/String;)I" in gate and "require = 1" in gate, "Wrong dispatch descriptor")
    passed.append("Required loader Mixin configurations and exact 1.16.5 command method descriptor")
    forge_source = java["forge/src/main/java/cn/qizhang/guard/forge/GuardForge.java"]
    for critical in ("net.minecraftforge.fml.network.", "FMLServerStartingEvent", "FMLServerStoppingEvent", "NetworkEvent.ClientCustomPayloadEvent", "NetworkDirection.PLAY_TO_SERVER", "NetworkEvent.ServerCustomPayloadEvent", "NetworkDirection.PLAY_TO_CLIENT", "activeServer", "30000"):
        require(critical in forge_source, "Missing Forge 36 API/direction bridge: " + critical)
    require("event.getServer()" not in forge_source[forge_source.index("private void tick"):], "Old tick has no server accessor")
    passed.append("Forge 36 lifecycle, networking package and explicit PLAY direction checks")
    require(json.loads((ROOT / "forge/src/main/resources/pack.mcmeta").read_text())["pack"]["pack_format"] == 6, "Wrong resource pack version")
    build = (ROOT / "build.gradle").read_text()
    require("options.release = 8" in build and "JavaLanguageVersion.of(8)" in build and "':compat:check'" in build, "Java 8 compilation/checks not mandatory")
    require("gradle/license-resources.gradle" in build, "Embedded license script missing")
    passed.append("Pack format 6, shared license resources and mandatory Java 8 checks configured")
    syntax_count = 0
    if args.java_parser_path:
        sys.path.insert(0, str(args.java_parser_path))
        import javalang
        for text in java.values():
            javalang.parse.parse(text)
            syntax_count += 1
        passed.append("javalang parsed all local/generated Java 8 source files; no type resolution performed")
    if args.preview_dir:
        require(not args.preview_dir.resolve().is_relative_to(PROJECT.resolve()), "Previews must be outside the project tree")
        for name, text in generated.items():
            destination = args.preview_dir / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text, encoding="utf-8")
    files = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob("*")
             if p.is_file() and not any(part in {".gradle", "build", "__pycache__"} for part in p.parts) and p.name != "static-checks.json"}
    print(json.dumps({"status": "STATIC_ONLY_NOT_COMPILED", "checkedAtUTC": dt.datetime.now(dt.timezone.utc).isoformat(),
        "passed": passed, "java8SyntaxFilesParsed": syntax_count, "javaProcessesLaunched": 0, "gradleProcessesLaunched": 0,
        "compiled": False, "runtimeTested": False, "adaptationInputsSHA256": inputs, "filesSHA256": files}, indent=2))


if __name__ == "__main__":
    main()
