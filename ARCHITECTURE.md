# QiZhangVerdict implementation contract (七章的裁决 / QiZhang's Verdict)

Priority: Bukkit-compatible plugin + Fabric 1.20.1/1.21.1 + Forge 1.20.1/NeoForge 1.21.1 mods. All original code. Java 8 platform-neutral core. Platform builds may use Java 17/21. Only real builds/runtime checks count as verified.

Package `cn.qizhang.guard.core`, class `GuardService(Path directory)` with `reload()` transactional validation and `save()` atomic state persistence. Constructor loads configuration/default blacklist/state. Public methods (thread-safe):

* `Decision openSession(UUID player, String literalIp, long nowMillis)` checks CIDR allow/deny, rolling unique-account limit, simultaneous session limit, join-rate limit, reserves a session. No duplicate UUID overwrite; reject duplicate session. IP literals only; never DNS.
* `void confirmSession(UUID player, long nowMillis)` records a successful join in rolling account history, persistence marked dirty. Rejected prelogin attempts do not consume unique-account history.
* `void closeSession(UUID player)` releases session/challenge.
* `byte[] challenge(UUID player, long nowMillis)` creates a fresh bounded-lifetime nonce, invalidates previous, marks awaiting report.
* `Decision acceptReport(UUID player, byte[] payload, long nowMillis)` validates version, nonce, limits, completeness and policy; consumes nonce. No secret embedded in client; report is explicitly self-reported, not trusted attestation.
* `List<UUID> expiredReports(long nowMillis)` returns and consumes expired required reports; optional report timeout does not kick. Also expires unconfirmed reservations.
* `Decision checkBrand(String brand)` exact normalized blacklist policy.
* `String status()` concise policy/session status, no raw IPs.
* `boolean requiresCompanion()` and `int reportTimeoutSeconds()`.
* `boolean isDirty()` for async persistence.

`Decision` exposes `boolean allowed()`, `String code()`, `String message()`.

`Wire` exposes `byte[] encodeChallenge(String nonce)`, `String decodeChallenge(byte[] payload)`, `byte[] encodeReport(String nonce, ClientReport report)`, `ReportEnvelope decodeReport(byte[] payload)`.
`ClientReport` public constructors `(List<String> modIds, List<String> resourcePacks, List<String> vmSignals, boolean complete)` and the five-argument overload adding `String deviceId`; getters return immutable data. Wire version 2 includes a 64-hex device ID and persistent public server scope in the challenge. `ReportEnvelope` getters `nonce()` and `report()`.
Network channel: `qzguard:main` (legacy Bukkit pre-1.13 `QZGuard`). All wire messages binary and bounded <= 30,000 bytes. Nonce generated with SecureRandom, no client HMAC claims. Core validates fields/counts/trailing bytes, rejects malformed packets. Adapter rate-limits unsolicited/large packets; core never holds a client-owned mutable list.

Defaults in `guard.properties`: limits.max-online-per-ip=3; limits.max-online-per-ip-device=1; limits.max-accounts-per-ip=5; limits.account-window-hours=720; limits.attempts-per-minute=20; ip.allow= (empty allows all); ip.deny=; companion.required=true; device.required=true; companion.timeout-seconds=20; vm.action=DENY (OFF/ALERT/DENY); blacklist.action=DENY; sanctions.on-deny=BAN. `DENY` VM policy requires companion.required=true so absent reporting cannot silently bypass it. Explicit blacklist/known-VM denials can automatically persist associated account/device bans; quota, malformed/missing reports and IP denials cannot. `blacklist.tsv` has kind, exact normalized value, action, source URL; distinguish cheat identifiers from optional automation rules. This release does not scan JAR files or claim hash-based file recognition.

Adapters: actual join confirms session, disconnect releases, once per second checks timeouts and challenge resends only if needed. Bukkit reserves in PlayerLoginEvent, confirms at PlayerJoinEvent and sends challenge after channel registration/two ticks; mods open and confirm on JOIN and disconnect immediately on deny. Save runs on dedicated background executor; shutdown flushes. Normal users cannot run admin commands. No commands accept arbitrary shell or arbitrary server-command templates.

Client inventory limited to loaded mod IDs, selected pack IDs/file names, coarse VM indicator names and a server-scoped installation hash. No user files/process lists/MAC/hardware serials, no remote telemetry. VM probe is explicitly best-effort; do not treat `java.vm.name` (JVM) as OS virtualization. Client disclosure and privacy are documented. VM detection may use OS manufacturer/model (bounded local query) and Linux DMI with timeout; reports only indicator category. Client-side check happens only when server requests it.

Behavior anti-cheat: companion to separately installed GrimAC on supported platforms; integration status must never imply it is bundled or functioning when absent. Anti-Xray is server chunk obfuscation (Paper/Orebfuscator/external supported mods), cannot be achieved by names blacklist alone. Provide concrete versioned configuration and dependency installer with provenance/hashes; do not mutate other server installations.

Final extensions: managed EXACT/GLOB BLACK/WHITE rules for MOD/PACK/BRAND/PLAYER/DEVICE; automatic account/device association bans; independent unban; same IP/device online limit 1, total IP online limit 3. Device and companion reports are required by default. server-id.txt defines stable per-server hashing scope. Source code and tests define the current API; see README.md, platforms/README.md and docs/security-review.md.
