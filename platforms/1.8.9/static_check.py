"""GPL-3.0-only. Offline source checks only; never invokes Java, Gradle or Minecraft."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-dir", type=Path)
    parser.add_argument("--java-parser-path", type=Path)
    args = parser.parse_args()
    passed, generated, inputs = [], {}, {}
    for entry in json.loads((ROOT / "gradle/adaptations.json").read_text(encoding="utf-8")):
        source = (ROOT / entry["input"]).resolve()
        text = source.read_text(encoding="utf-8")
        inputs[source.relative_to(PROJECT).as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
        for change in entry["changes"]:
            require(text.count(change["before"]) == change["count"], "Shared-source bridge drift: " + change["before"])
            text = text.replace(change["before"], change["after"])
        generated[entry["output"]] = text
    passed.append("All three generated Java bridges match each reviewed occurrence count")
    java = {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8")
            for p in ROOT.rglob("*.java") if "build" not in p.parts and ".gradle" not in p.parts}
    java.update(generated)
    forbidden = re.compile(r"\bvar\s+\w+\s*=|\.readNBytes\(|Files\.writeString\(|Redirect\.DISCARD|\.repeat\(|\.toList\(\)\s*;")
    for name, text in java.items():
        require(not forbidden.search(text.replace("Collectors.toList()", "JAVA8_COLLECTOR")), "Modern syntax/API remains: " + name)
    passed.append("No known Java 9+ reporter API or local syntax remains")
    guard = generated["main/cn/qizhang/guard/minecraft/MinecraftGuard.java"]
    for token in ("owners.get(id) != player", '"STALE_REPORT"', "service.acceptReport", "service.requiresCompanion()",
                  "GameType.SPECTATOR", "service.bannedSessions()", "service.recheckSession", "service.save()",
                  "getServerForPlayer().getMinecraftServer().isDedicatedServer()", "getGameProfile().getName().equals"):
        require(token in guard, "Guard policy/ownership contract absent: " + token)
    for token in ("net.minecraft.server.level", "net.minecraft.network.chat", ".connection", ".serverLevel()", ".setGameMode(", "Component.literal"):
        require(token not in guard, "Unadapted Minecraft API: " + token)
    reporter = generated["main/cn/qizhang/guard/client/ClientReporter.java"]
    for token in ("generation != request.generation", "Wire.decodeServerScope", "new ArrayBlockingQueue<Runnable>(1)",
                  "request.clientThread.accept", "StandardOpenOption.CREATE_NEW", "1800, TimeUnit.MILLISECONDS", "1500, TimeUnit.MILLISECONDS"):
        require(token in reporter, "Reporter isolation contract absent: " + token)
    require(reporter.count("LegacyJava8.readBounded(") == 5, "Read bounds not fully bridged")
    passed.append("Strict isolation, device/VM policies, fixed scope, stale report and connection ownership retained")
    base = "forge/src/main/java/cn/qizhang/guard/forge189/"
    server, client, command = (java[base + name] for name in ("GuardForge189.java", "ClientProxy.java", "LegacyGuardCommand.java"))
    for token in ('CHANNEL = "QZGuard"', 'acceptedMinecraftVersions = "[1.8.9]"', "ServerCustomPacketEvent",
                  "event.handler", "event.packet", "playerEntity", "EventPriority.HIGHEST", "event.setCanceled(true)",
                  "MinecraftGuard.isWaiting", "event.sender", "getWorldThread(event.handler)", "30000"):
        require(token in server, "Server bridge missing: " + token)
    for token in ('C17PacketCustomPayload("REGISTER"', "client.getNetHandler()", "client.thePlayer", "client.theWorld",
                  "connection.getNetworkManager() != origin", "client.getNetHandler() == connection",
                  "event.manager", "getRepositoryEntries()", "getActiveModList()", "30000"):
        require(token in client, "Client bridge missing: " + token)
    require("getRepositoryEntriesAll" not in client and "getConnection()" not in client, "Wrong old client API")
    require(server.count("MinecraftForge.EVENT_BUS.register(this)") == 1 and ".bus().register" not in server, "Double server event registration")
    require(client.count("MinecraftForge.EVENT_BUS.register(this)") == 1 and ".bus().register" not in client, "Double client event registration")
    for token in ("getCommandName()", "getCommandUsage(", "getRequiredPermissionLevel() { return 3; }", "processCommand(ICommandSender sender, String[] args)"):
        require(token in command, "Wrong 1.8 CommandBase interface: " + token)
    test = java["forge/src/test/java/cn/qizhang/guard/forge189/LegacyCommandSmoke.java"]
    require("canCommandSenderUseCommand(sender(2))" in test and '"canCommandSenderUseCommand"' in test, "Permission test not adapted")
    passed.append("Native Forge receiver-side event fields, QZGuard/REGISTER and OP command cancellation are wired")
    build = (ROOT / "build.gradle").read_text(encoding="utf-8")
    for token in ("2.1-20211118.174922-42", "JavaVersion.VERSION_1_8", "1.8.9-11.15.1.2318-1.8.9", "stable_22",
                  "sourceMainJava", "sourceTestJava", "check.dependsOn checks.keySet()", "boundedIoSmoke", "legacyCommandSmoke"):
        require(token in build, "Required build/check configuration absent: " + token)
    require("configureEach" not in build and "tasks.register" not in build and "layout." not in build, "Modern Gradle DSL remains")
    license_script = (ROOT / "gradle/license-resources-legacy.gradle").read_text(encoding="utf-8")
    for token in ("org.gradle.api.tasks.bundling.Jar", "tasks.withType(Jar)", "'LICENSE'", "'NOTICE'", "GPL-3.0-only"):
        require(token in license_script, "Legacy license packaging absent: " + token)
    metadata = json.loads((ROOT / "forge/src/main/resources/mcmod.info").read_text(encoding="utf-8"))[0]
    require(metadata["license"] == "GPL-3.0-only" and metadata["mcversion"] == "1.8.9", "Wrong metadata target/license")
    require("gradle-2.7-bin.zip" in (ROOT / "gradle/wrapper/gradle-wrapper.properties").read_text(), "Wrong official wrapper target")
    require("cde43b90945b5304c43ee36e58aab4cc6fb3a3d5f9bd9449bb1709a68371cb06" in (ROOT / "prepare_gradle.py").read_text(), "Missing independent Gradle integrity check")
    passed.append("Gradle 2.7 build, native Java 8 checks, license resources and independent ZIP integrity preflight configured")
    if args.java_parser_path:
        sys.path.insert(0, str(args.java_parser_path))
        import javalang
        for text in java.values():
            javalang.parse.parse(text)
        passed.append("javalang parsed all local/generated Java 8 source files; no type resolution performed")
    if args.preview_dir:
        preview = args.preview_dir.resolve()
        require(preview != PROJECT and PROJECT not in preview.parents, "Previews must be outside the project tree")
        for name, text in generated.items():
            destination = preview / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text, encoding="utf-8")
    files = {}
    for current, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".gradle", "build", "__pycache__")]
        for name in names:
            if name == "static-checks.json":
                continue
            path = Path(current) / name
            files[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    print(json.dumps({"status": "SOURCE_STATIC_ONLY_NOT_COMPILED", "checkedAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      "passed": passed, "java8SyntaxFilesParsed": len(java) if args.java_parser_path else 0,
                      "javaProcessesLaunched": 0, "gradleProcessesLaunched": 0, "compiled": False, "runtimeTested": False,
                      "adaptationInputsSHA256": inputs, "filesSHA256": files}, indent=2))


if __name__ == "__main__":
    main()
