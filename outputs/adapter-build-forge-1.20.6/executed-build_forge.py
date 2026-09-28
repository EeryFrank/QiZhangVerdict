from pathlib import Path
import argparse, ctypes, datetime, hashlib, json, os, subprocess, time

ROOT = Path('E:/Codex_work/QiZhangVerdict')
CACHE = Path(__file__).resolve().parent
PROJECT = ROOT / 'platforms/1.20.6/forge'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def sources():
    rows = {}
    for prefix in ('core/src', 'client-common/src', 'platforms/1.20.6/common', 'platforms/1.20.6/forge'):
        for directory, children, files in os.walk(ROOT / prefix, followlinks=False):
            children[:] = [x for x in children if x not in {'build', '.gradle', '__pycache__'}]
            for name in files:
                path = Path(directory) / name
                rows[path.relative_to(ROOT).as_posix()] = digest(path)
    for name in ('LICENSE', 'NOTICE', 'gradle/license-resources.gradle'):
        rows[name] = digest(ROOT / name)
    return rows

def memory_gate():
    class Mem(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(n, ctypes.c_ulonglong) for n in ('totalPhysical', 'availablePhysical', 'totalPageFile', 'availablePageFile', 'totalVirtual', 'availableVirtual', 'availableExtendedVirtual')]
    value = Mem(); value.length = ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
        raise OSError('Cannot read physical memory')
    free = value.availablePhysical / 1024 ** 3
    if free < 5: raise RuntimeError('Need 5 GiB available before Java')
    return free

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('attempt')
    args = parser.parse_args()
    if not args.attempt or not all(c.isalnum() or c in '-_' for c in args.attempt):
        raise ValueError('Expected a unique simple attempt name')
    free = memory_gate()
    out = CACHE / 'builds' / args.attempt
    out.mkdir(parents=True, exist_ok=False); (out / 'temp').mkdir()
    before = sources()
    old = json.loads((ROOT / 'outputs/preview-manifest-0.4.0-dev-preview.1.json').read_bytes())['artifacts']
    modern = json.loads((CACHE / 'builds/all-42-01/result.json').read_bytes())['artifacts']
    if len(old) != 20 or len(modern) != 4: raise ValueError('Unexpected prior artifact inventory')
    prior = old + modern
    def preserved():
        return all((ROOT / p['path']).stat().st_size == p['bytes'] and digest(ROOT / p['path']) == p['sha256'] for p in prior)
    if not preserved(): raise ValueError('Previous artifact bytes changed')
    env = os.environ.copy()
    for name in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS', 'GRADLE_OPTS'):
        env.pop(name, None)
    env.update(JAVA_HOME='D:/Java/jdk-21', GRADLE_USER_HOME='E:/CodexTemp/Gradle/QiZhang_Games',
               CI='true', TEMP=str(out / 'temp'), TMP=str(out / 'temp'))
    env['PATH'] = env['JAVA_HOME'] + '/bin;' + env['PATH']
    env['JAVA_TOOL_OPTIONS'] = ('-Djava.io.tmpdir=' + (out / 'temp').as_posix()
        + ' -Dqzguard.testDir=' + (out / 'core-tests').as_posix()
        + ' -Djavax.net.ssl.trustStoreType=Windows-ROOT -Djavax.net.ssl.trustStore=NONE')
    env['GRADLE_OPTS'] = '-Dorg.gradle.internal.http.connectionTimeout=20000 -Dorg.gradle.internal.http.socketTimeout=20000'
    command = [str(PROJECT / 'gradlew.bat'), '--no-daemon', '--max-workers=1', '--console=plain', '--stacktrace',
        '--project-cache-dir', str(out / 'project-cache'), '-Dorg.gradle.jvmargs=-Xmx1536m -Dfile.encoding=UTF-8',
        '-PqzRuntimeRoot=' + (out / 'runtime').as_posix(), 'build']
    plan = {'schemaVersion': 1, 'target': 'forge', 'attempt': args.attempt, 'gradle': '8.12.1',
        'forgeGradle': '6.0.54', 'forge': '50.2.0', 'minecraft': '1.20.6', 'availablePhysicalGiB': free,
        'startedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'command': command,
        'environment': {k: env[k] for k in ('JAVA_HOME', 'GRADLE_USER_HOME', 'CI', 'TEMP', 'TMP', 'JAVA_TOOL_OPTIONS', 'GRADLE_OPTS')},
        'sourceSha256': before, 'previousArtifacts': prior}
    (out / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    (out / 'executed-build_forge.py').write_bytes(Path(__file__).read_bytes())
    started = time.monotonic()
    with (out / 'console.log').open('xb') as output:
        process = subprocess.run(command, cwd=PROJECT, env=env, stdout=output, stderr=subprocess.STDOUT,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
    artifacts = [{'path': p.relative_to(ROOT).as_posix(), 'sha256': digest(p), 'bytes': p.stat().st_size}
                 for p in sorted((PROJECT / 'build/libs').glob('*.jar'))]
    result = {**plan, 'exitCode': process.returncode, 'elapsedSeconds': time.monotonic() - started,
        'sourcesUnchanged': sources() == before, 'previousArtifactsUnchanged': preserved(),
        'logSha256': digest(out / 'console.log'), 'artifacts': artifacts}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('target', 'attempt', 'exitCode', 'elapsedSeconds', 'sourcesUnchanged', 'previousArtifactsUnchanged', 'artifacts')}), flush=True)
    return process.returncode or (0 if result['sourcesUnchanged'] and result['previousArtifactsUnchanged'] else 2)

if __name__ == '__main__': raise SystemExit(main())
