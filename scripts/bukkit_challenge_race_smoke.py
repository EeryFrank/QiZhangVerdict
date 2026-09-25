"""Controlled Bukkit challenge-order QA. prepare never starts Java; run requires a reserved Java slot."""
# SPDX-License-Identifier: GPL-3.0-only
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE_FILE = ROOT / 'scripts/bukkit_catalog_smoke.py'
spec = importlib.util.spec_from_file_location('catalog_fixture_utils', BASE_FILE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
POLICY = base.DEFAULT_POLICY.encode('utf-8')
POLICY_SHA = '47310c31b47287ab805bfdbf8ddddf80e8169385bd9c862239a0a0075644da4e'
JAVA_SOURCE = r'''// SPDX-License-Identifier: GPL-3.0-only
package qa;
import java.nio.charset.StandardCharsets;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerRegisterChannelEvent;
import org.bukkit.plugin.java.JavaPlugin;

/** QA timing only: no reflection, replacement guard classes, or synthetic Bukkit events. */
public final class ChallengeRace extends JavaPlugin implements Listener {
    private static final String CONTROL = "qzqa:control";
    private long tick, joinedTick;
    private Player owner;
    private boolean reloaded, slow;
    public void onEnable() {
        getServer().getMessenger().registerOutgoingPluginChannel(this, CONTROL);
        getServer().getPluginManager().registerEvents(this, this);
        getServer().getScheduler().runTaskTimer(this, () -> tick++, 1L, 1L);
        getLogger().info("QA_READY no guard reflection or policy edits; one synthetic player only");
    }
    @EventHandler(priority = EventPriority.MONITOR)
    public void joined(PlayerJoinEvent event) {
        if (!event.getPlayer().getName().equals("QVRace")) return;
        if (owner != null) throw new IllegalStateException("Fixture permits only one join");
        owner = event.getPlayer(); joinedTick = tick;
        slow = Bukkit.dispatchCommand(Bukkit.getConsoleSender(), "tick rate 1");
        getLogger().info("QA_JOIN tick=" + tick + " slowCommand=" + slow);
        getServer().getScheduler().runTaskLater(this, () -> {
            boolean same = owner != null && Bukkit.getPlayer(owner.getUniqueId()) == owner && owner.isOnline();
            String marker = same && reloaded && slow ? "CHECKPOINT" : "TIMING_NOT_ESTABLISHED";
            if (same) control(marker);
            getLogger().info("QA_CHECKPOINT tick=" + tick + " joinTick=" + joinedTick + " reloaded=" + reloaded);
            restoreTicks();
        }, 4L);
    }
    @EventHandler(priority = EventPriority.MONITOR)
    public void registered(PlayerRegisterChannelEvent event) {
        if (event.getPlayer() != owner || !event.getChannel().equals("qzguard:main") || reloaded) return;
        // The fixture channel is registered first by the client. Guard NORMAL runs before this MONITOR.
        if (!owner.getListeningPluginChannels().contains(CONTROL) || tick - joinedTick >= 2L || !slow) {
            control("TIMING_NOT_ESTABLISHED");
            getLogger().warning("QA_TIMING_NOT_ESTABLISHED registerTick=" + tick + " joinTick=" + joinedTick);
            return;
        }
        control("BEFORE_RELOAD");
        boolean dispatched = Bukkit.dispatchCommand(Bukkit.getConsoleSender(), "qzverdict reload");
        control("AFTER_RELOAD");
        reloaded = dispatched;
        getLogger().info("QA_RELOADED registerTick=" + tick + " joinTick=" + joinedTick + " command=" + dispatched);
    }
    private void control(String stage) {
        owner.sendPluginMessage(this, CONTROL, (stage + "|" + tick + "|" + joinedTick).getBytes(StandardCharsets.US_ASCII));
    }
    private void restoreTicks() {
        if (slow) { Bukkit.dispatchCommand(Bukkit.getConsoleSender(), "tick rate 20"); slow = false; }
    }
    public void onDisable() { restoreTicks(); }
}
'''
PLUGIN_YML = '''name: QVChallengeRaceQA
version: '1'
main: qa.ChallengeRace
depend: [QiZhangVerdict]
description: Isolated timing instrumentation for the delayed challenge regression.
'''


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def prepare(args):
    assert hashlib.sha256(POLICY).hexdigest() == POLICY_SHA
    if not re.fullmatch('[a-fA-F0-9]{64}', args.guard_sha256 or ''):
        raise ValueError('An explicit expected product SHA256 is required')
    guard = args.guard_jar.resolve(strict=True)
    if digest(guard) != args.guard_sha256.lower():
        raise ValueError('Product JAR hash mismatch')
    source = args.server_fixture.resolve(strict=True)
    build, server_sha = base.SERVERS['1.21.1']
    if digest(source / 'server.jar') != server_sha:
        raise ValueError('Use the fixed Purpur 1.21.1 build 2329 fixture')
    for executable in [args.java, args.javac, args.node]:
        if not executable.is_file():
            raise ValueError('Explicit runtime/compiler executable is missing')
    if not args.spigot_api.is_file():
        raise ValueError('Spigot API compile input missing')
    package = json.loads((args.node_modules / 'minecraft-protocol/package.json').read_text())
    if package['version'] != '1.66.2':
        raise ValueError('Use the existing pinned minecraft-protocol 1.66.2 installation')
    sys_path = __import__('sys').path
    sys_path.insert(0, str(ROOT / 'integrations'))
    from manage_integrations import fresh_directory
    folder = fresh_directory(args.output)
    shutil.copyfile(source / 'server.jar', folder / 'server.jar')
    for name in ['cache', 'libraries', 'versions']:
        if (source / name).exists():
            base.no_reparse_tree(source / name)
            shutil.copytree(source / name, folder / name)
    plugins = folder / 'plugins'
    plugins.mkdir()
    shutil.copyfile(guard, plugins / guard.name)
    data = plugins / 'QiZhangVerdict'
    data.mkdir()
    (data / 'guard.properties').write_bytes(POLICY)
    (folder / 'default-policy-reference.properties').write_bytes(POLICY)
    qa = folder / 'qa-source'
    (qa / 'qa').mkdir(parents=True)
    (qa / 'qa/ChallengeRace.java').write_text(JAVA_SOURCE, encoding='utf-8')
    (qa / 'plugin.yml').write_text(PLUGIN_YML, encoding='utf-8')
    shutil.copyfile(ROOT / 'LICENSE', qa / 'LICENSE')
    for src, name in [(Path(__file__), 'executed-helper.py'), (BASE_FILE, 'executed-base-helper.py'),
                      (ROOT / 'scripts/bukkit_challenge_race_smoke.cjs', 'executed-protocol.cjs'),
                      (ROOT / 'scripts/legacy-protocol-qa/package-lock.json', 'executed-package-lock.json')]:
        shutil.copyfile(src, folder / name)
    (folder / 'eula.txt').write_text('eula=true\n', encoding='ascii')
    generator = json.dumps({'layers': [{'block': 'minecraft:bedrock', 'height': 1},
        {'block': 'minecraft:stone', 'height': 60}, {'block': 'minecraft:grass_block', 'height': 1}],
        'biome': 'minecraft:plains'}, separators=(',', ':'))
    (folder / 'server.properties').write_text(
        f'server-ip=127.0.0.1\nserver-port={args.port}\nonline-mode=false\nenforce-secure-profile=false\n'
        'network-compression-threshold=256\nspawn-protection=0\nview-distance=2\nsimulation-distance=2\n'
        f'max-players=3\nlevel-type=minecraft:flat\ngenerator-settings={generator}\ngenerate-structures=false\n'
        'spawn-monsters=false\nspawn-animals=false\ndifficulty=peaceful\n', encoding='utf-8')
    fixture = {'schemaVersion': 1, 'version': '1.21.1', 'build': build, 'serverSha256': server_sha,
        'serverSourceUrl': f'https://api.purpurmc.org/v2/purpur/1.21.1/{build}/download',
        'guardFile': guard.name, 'guardSha256': digest(guard), 'expectedOutcome': args.expect,
        'policySha256': POLICY_SHA, 'policyChanges': {},
        'timingControl': 'QA plugin uses vanilla tick rate 1 until join+4ticks, then restores 20; guard timeout/policy are unchanged.',
        'host': '127.0.0.1', 'port': args.port, 'java': str(args.java.resolve()), 'javac': str(args.javac.resolve()),
        'node': str(args.node.resolve()), 'nodeModules': str(args.node_modules.resolve()),
        'spigotApi': str(args.spigot_api.resolve()), 'spigotApiSha256': digest(args.spigot_api),
        'snapshots': {name: digest(folder / name) for name in ['executed-helper.py', 'executed-base-helper.py',
            'executed-protocol.cjs', 'executed-package-lock.json', 'qa-source/qa/ChallengeRace.java',
            'qa-source/plugin.yml', 'qa-source/LICENSE']}, 'javaStartedByPrepare': False,
        'scope': 'Actual frozen/new product JAR, real Bukkit lifecycle and TCP, synthetic companion reports; no actual ClientReporter probe or real hardware assertion.'}
    save(folder / 'fixture.json', fixture)
    print(json.dumps({'prepared': True, 'folder': str(folder), 'guardSha256': fixture['guardSha256'], 'javaStarted': False}))


def wait_log(log, text, process, timeout=240):
    end = time.monotonic() + timeout
    while text not in log.read_text('utf-8', errors='replace'):
        if process.poll() is not None:
            raise RuntimeError('Server exited before expected log marker: ' + text)
        if time.monotonic() >= end:
            raise TimeoutError('Missing log marker: ' + text)
        time.sleep(.1)


def run(args):
    folder = args.output.resolve(strict=True)
    fixture = json.loads((folder / 'fixture.json').read_text())
    if not (folder / '.qizhang-verdict-stage').is_file() or (folder / 'result.json').exists() or (folder / 'console.log').exists():
        raise ValueError('Fresh owned fixture required; refusing existing execution/output')
    for name, sha in fixture['snapshots'].items():
        if digest(folder / name) != sha:
            raise ValueError('Prepared snapshot drift: ' + name)
    if digest(__file__) != fixture['snapshots']['executed-helper.py'] or digest(BASE_FILE) != fixture['snapshots']['executed-base-helper.py']:
        raise ValueError('Runner/dependency drift after prepare')
    policy = folder / 'plugins/QiZhangVerdict/guard.properties'
    for path, sha in [(folder / 'server.jar', fixture['serverSha256']),
                      (folder / 'plugins' / fixture['guardFile'], fixture['guardSha256']),
                      (Path(fixture['spigotApi']), fixture['spigotApiSha256']), (policy, POLICY_SHA)]:
        if digest(path) != sha:
            raise ValueError('Pinned input mismatch: ' + str(path))
    result = {'passed': False, 'expectedOutcomeConfirmed': False, 'fixture': fixture}
    process = bot = None
    log = folder / 'console.log'
    try:
        memory = base.available_memory()
        result['availableBytesBeforeJava'] = memory
        if memory < 3.5 * 1024**3:
            raise RuntimeError('Resource gate: at least 3.5 GiB free is required')
        with socket.socket() as probe:
            if os.name != 'nt':
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind((fixture['host'], fixture['port'])); probe.listen(1)
        classes = folder / 'qa-classes'
        classes.mkdir()
        command = [fixture['javac'], '-J-Xmx128m', '-encoding', 'UTF-8', '-source', '8', '-target', '8',
                   '-cp', fixture['spigotApi'], '-d', str(classes), str(folder / 'qa-source/qa/ChallengeRace.java')]
        compiled = subprocess.run(command, capture_output=True, timeout=60,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        (folder / 'qa-compile.log').write_bytes(compiled.stdout + compiled.stderr)
        result['qaCompileExitCode'] = compiled.returncode
        if compiled.returncode:
            raise RuntimeError('QA plugin compilation failed')
        qa_jar = folder / 'plugins/QVChallengeRaceQA.jar'
        with zipfile.ZipFile(qa_jar, 'x', compression=zipfile.ZIP_DEFLATED) as jar:
            for p in sorted(classes.rglob('*.class')):
                jar.write(p, p.relative_to(classes).as_posix())
            for name in ['plugin.yml', 'LICENSE']:
                jar.write(folder / 'qa-source' / name, name)
        result['qaJarSha256'] = digest(qa_jar)
        queue = folder / 'commands.queue'
        queue.write_text('', encoding='utf-8')
        with log.open('w', encoding='utf-8') as output:
            server_cmd = [fixture['java'], '-Xms256m', '-Xmx1536m', '-jar', 'server.jar', '--nogui']
            result['serverCommand'] = server_cmd
            process = subprocess.Popen(server_cmd, cwd=folder, stdin=subprocess.PIPE, stdout=output,
                stderr=subprocess.STDOUT, text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            result['ownedServerPid'] = process.pid
            wait_log(log, 'Done (', process)
            wait_log(log, 'QA_READY', process)
            if digest(policy) != POLICY_SHA:
                raise AssertionError('Policy drift before TCP')
            result['started'] = True
            env = dict(os.environ, NODE_PATH=fixture['nodeModules'])
            with (folder / 'protocol.log').open('w', encoding='utf-8') as protocol_log:
                bot = subprocess.Popen([fixture['node'], str(folder / 'executed-protocol.cjs'), str(folder)],
                    env=env, stdout=protocol_log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                consumed = 0; deadline = time.monotonic() + 90
                while bot.poll() is None:
                    lines = queue.read_text('utf-8').splitlines()
                    for line in lines[consumed:]:
                        process.stdin.write(line + '\n'); process.stdin.flush()
                    consumed = len(lines)
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError('Server stopped or protocol exceeded 90 seconds')
                    time.sleep(.05)
            result['protocolExitCode'] = bot.returncode
            protocol = json.loads((folder / 'protocol-result.json').read_text())
            result['protocol'] = protocol
            if bot.returncode or not protocol['expectedOutcomeConfirmed']:
                raise AssertionError('Observed result did not confirm the requested outcome')
            result['expectedOutcomeConfirmed'] = True
    except Exception as exc:
        result['error'] = str(exc)
    finally:
        if bot is not None and bot.poll() is None:
            bot.kill(); bot.wait(); result['forcedProtocolStop'] = True
        if process is not None and process.poll() is None:
            try:
                process.stdin.write('tick rate 20\nstop\n'); process.stdin.flush()
            except (OSError, BrokenPipeError):
                result['stopWriteFailed'] = True
            try:
                process.wait(timeout=90)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(); result['forcedServerStop'] = True
        if process is not None:
            result['serverExitCode'] = process.poll()
            if process.stdin is not None:
                process.stdin.close()
        text = log.read_text('utf-8', errors='replace') if log.exists() else ''
        result['normalStop'] = result.get('serverExitCode') == 0 and 'Stopping server' in text and 'Saving chunks for level' in text and not result.get('forcedServerStop')
        result['policyAfterSha256'] = digest(policy)
        result['policyUnchanged'] = result['policyAfterSha256'] == POLICY_SHA
        result['expectedOutcomeConfirmed'] = bool(result['expectedOutcomeConfirmed'] and result['normalStop'] and result['policyUnchanged'] and not result.get('forcedProtocolStop'))
        result['passed'] = bool(fixture['expectedOutcome'] == 'fixed' and result['expectedOutcomeConfirmed'])
        result['knownBugReproduced'] = bool(fixture['expectedOutcome'] == 'old-bug' and result['expectedOutcomeConfirmed'])
        save(folder / 'result.json', result)
    print(json.dumps({'passed': result['passed'], 'knownBugReproduced': result['knownBugReproduced'], 'expectedOutcomeConfirmed': result['expectedOutcomeConfirmed']}))
    if not result['expectedOutcomeConfirmed']:
        raise RuntimeError(result.get('error', 'Shutdown or unchanged-policy verification failed'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--guard-jar', type=Path)
    parser.add_argument('--guard-sha256')
    parser.add_argument('--expect', choices=['fixed', 'old-bug'], default='fixed')
    parser.add_argument('--server-fixture', type=Path, default=Path('E:/CodexTemp/QiZhangGuard/runtime/1.21.1-startup'))
    parser.add_argument('--java', type=Path, default=Path('D:/Java/jdk-21/bin/java.exe'))
    parser.add_argument('--javac', type=Path, default=Path('E:/CodexTemp/QiZhangVerdict/toolchains/jdk8/jdk8u504-b01/bin/javac.exe'))
    parser.add_argument('--node', type=Path, default=Path('E:/CodexTemp/Codex/RuntimeCache/codex-primary-runtime/dependencies/node/bin/node.exe'))
    parser.add_argument('--node-modules', type=Path, default=Path('E:/CodexTemp/QiZhangVerdict/legacy-protocol-qa/node_modules'))
    parser.add_argument('--spigot-api', type=Path, default=Path('E:/CodexTemp/Gradle/QiZhang_Games/caches/modules-2/files-2.1/org.spigotmc/spigot-api/1.8.8-R0.1-SNAPSHOT/164ca9702b04d7ff5f655e507ceafd9b50e7fca7/spigot-api-1.8.8-R0.1-SNAPSHOT.jar'))
    parser.add_argument('--port', type=int, default=25679)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Use an unprivileged TCP port')
    if args.action == 'prepare' and args.guard_jar is None:
        parser.error('prepare requires --guard-jar and --guard-sha256')
    (prepare if args.action == 'prepare' else run)(args)


if __name__ == '__main__':
    main()
