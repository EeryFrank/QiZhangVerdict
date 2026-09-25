# 七章的裁决 / QiZhang's Verdict — mod adapters

Four independent installable adapters share the Java core and private client report implementation:

| Minecraft | Loader | Java target | Build |
| --- | --- | --- | --- |
| 1.20.1 | Fabric 0.16.14 + Fabric API 0.92.6 | 17 | `platforms/1.20.1/gradlew.bat :fabric:build` |
| 1.20.1 | Forge 47.4.23 | 17 | `platforms/1.20.1/gradlew.bat :forge:build` |
| 1.21.1 | Fabric 0.16.14 + Fabric API 0.116.15 | 21 | `platforms/1.21.1/gradlew.bat :fabric:build` |
| 1.21.1 | NeoForge 21.1.244 | 21 | `platforms/1.21.1/gradlew.bat :neoforge:build` |

Run the wrapper **from its version directory**. Gradle 8.14.1 is pinned for both version projects. Set `GRADLE_USER_HOME` and pass `--project-cache-dir` under `E:/CodexTemp`; `CI=true` skips expensive dependency source remapping. Install the ordinary JAR from each adapter's `build/libs`, not the sources/dev JAR. The same JAR runs on the client and dedicated server. Fabric API is an external prerequisite. No Architectury API runtime is required.

Server policy lives in `config/qizhangverdict`. Default policy requires the client companion and device report. The mod ID is `qizhangverdict`; the internal compatibility channel stays `qzguard:main`, with the same bounded wire payload as the Bukkit plugin. Proxy administrators must use a trusted forwarding configuration; the adapter uses Minecraft's server-side reported connection IP and cannot independently authenticate upstream proxies.

Only operators with permission level 3 can use `/qzverdict status`, `reload`, `rule list [page]`, `rule add <BLACK|WHITE> <MOD|PACK|BRAND|PLAYER|DEVICE> <EXACT|GLOB> <value>`, `rule remove <id>`, `ban <uuid|exact-online-name> [reason]`, `unban <uuid|device:sha256>`, or `bans [page]`. Rule edits and persistent admin actions use a background executor; a successful rule edit/reload rechecks online sessions and requests fresh reports. Old pending deadlines are not extended. BRAND rules require a brand-aware server adapter; the mod companion inventory is evaluated as MOD/PACK/DEVICE/PLAYER rules.

While a required report is pending the player is temporarily a spectator and is returned to the original position/dimension every server tick. This limits ordinary movement and interaction; it is **not** pre-join/configuration-phase isolation. Chunks are already transmitted. A required Mixin blocks the shared Minecraft command dispatcher for waiting players, covering signed and unsigned normal commands. Other mods' independent custom network actions may still need their own permission restrictions. Successful reports, disconnects, and orderly shutdown restore the original game mode. An abrupt server crash can persist the temporary spectator mode. This limitation is relevant when deploying alongside gameplay mods.

Client inspection happens only when a server asks. It reads loaded mod IDs, selected resource-pack IDs, coarse OS manufacturer/model/BIOS VM categories, and an OS installation ID (Windows MachineGuid or Linux machine-id). The installation ID is hashed with the server's persistent public scope from the challenge; raw IDs never leave the client. Other OSes or failed OS-ID queries use `config/qizhangverdict/installation-id.txt`, a random local ID, and log that fallback. The server receives a 64-character SHA-256 digest. Changing the server's scope or reinstalling/resetting an installation ID changes the digest.

No process list, personal files, MAC address, hardware serial number, or remote telemetry is collected. Windows probe commands are bounded and run on a daemon worker, not the render/server thread. JVM names and physical-host Hyper-V/VBS flags are not proof of a virtual machine. Missing probes report `unknown`. Client inventory, VM categories, and device digests are self-reported and forgeable; they are not hardware attestation. Name blacklists cannot detect all cheats or X-ray. External Grim and AntiXray presence is logged separately and does not prove their configuration or gameplay effectiveness.

Official API references: [Fabric networking](https://docs.fabricmc.net/develop/networking), [NeoForge 1.21.1 payload registration](https://docs.neoforged.net/docs/1.21.1/networking/payload/), [Forge 1.20.x networking](https://docs.minecraftforge.net/en/1.20.x/networking/).
