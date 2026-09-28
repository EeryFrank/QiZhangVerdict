from pathlib import Path
import argparse, datetime, hashlib, json, os, subprocess, time

ROOT = Path('E:/Codex_work/QiZhangVerdict')
CACHE = Path(__file__).resolve().parent
PROJECT = ROOT / 'platforms/1.17.1'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sources():
    rows = {}
    for prefix in ('catalog', 'core/src', 'client-common/src', 'platforms/shared/src', 'platforms/1.17.1'):
        for directory, children, files in os.walk(ROOT / prefix, followlinks=False):
            children[:] = [name for name in children if name not in {'build', '.gradle', '__pycache__'}]
            for name in files:
                path = Path(directory) / name
                rows[path.relative_to(ROOT).as_posix()] = digest(path)
    for name in ('LICENSE', 'NOTICE', 'gradle/license-resources.gradle'):
        rows[name] = digest(ROOT / name)
    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('target', choices=['fabric', 'forge', 'all'])
    parser.add_argument('attempt')
    parser.add_argument('--jdk16', type=Path, required=True)
    parser.add_argument('--configure-only', action='store_true')
    args = parser.parse_args()
    if not args.attempt or not all(c.isalnum() or c in '-_' for c in args.attempt):
        raise ValueError('Expected a simple unique attempt name')
    out = CACHE / 'builds' / args.attempt
    out.mkdir(parents=True, exist_ok=False)
    (out / 'temp').mkdir()
    if not (args.jdk16 / 'bin/javac.exe').is_file():
        raise ValueError('Complete Java 16 toolchain required')
    def observed_sources():
        rows = sources()
        if args.configure_only:
            rows = {key: value for key, value in rows.items() if key.startswith('platforms/1.17.1/') and (key.endswith(('.gradle', '.properties', 'gradlew', 'gradlew.bat', 'gradle-wrapper.jar')))}
        return rows
    before = observed_sources()
    prior = json.loads((ROOT / 'outputs/preview-manifest-0.5.0-dev-preview.1.json').read_bytes())['artifacts']
    def original_artifacts():
        return len(prior) == 23 and all(digest(ROOT / row['path']) == row['sha256']
            and (ROOT / row['path']).stat().st_size == row['bytes'] for row in prior)
    if not original_artifacts():
        raise ValueError('Published twenty-three-artifact pins differ')
    env = os.environ.copy()
    env.update(JAVA_HOME='D:/Java/jdk-21', GRADLE_USER_HOME='E:/CodexTemp/Gradle/QiZhang_Games',
               CI='true', TEMP=str(out / 'temp'), TMP=str(out / 'temp'))
    env['PATH'] = env['JAVA_HOME'] + '/bin;' + env['PATH']
    env['JAVA_TOOL_OPTIONS'] = ('-Djava.io.tmpdir=' + (out / 'temp').as_posix()
        + ' -Dqzguard.testDir=' + (out / 'core-tests').as_posix()
        + ' -Djavax.net.ssl.trustStoreType=Windows-ROOT -Djavax.net.ssl.trustStore=NONE')
    env['GRADLE_OPTS'] = '-Dorg.gradle.internal.http.connectionTimeout=20000 -Dorg.gradle.internal.http.socketTimeout=20000'
    cmd = [str(PROJECT / 'gradlew.bat'), '--no-daemon', '--max-workers=1', '--console=plain',
           '--stacktrace', '--project-cache-dir', str(out / 'project-cache'),
           '-Dorg.gradle.jvmargs=-Xmx1536m -Dfile.encoding=UTF-8',
           '-PqzRuntimeRoot=' + (out / 'runtime').as_posix(),
           '-Porg.gradle.java.installations.paths=' + args.jdk16.as_posix(),
           '-Porg.gradle.java.installations.auto-download=false']
    cmd.extend(['help'] if args.configure_only else (['build', ':fabric:commandParserSmoke'] if args.target == 'all' else [':' + args.target + ':build']))
    plan = {'schemaVersion': 1, 'target': args.target, 'attempt': args.attempt, 'configureOnly': args.configure_only,
            'startedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'command': cmd,
            'environment': {k: env[k] for k in ['JAVA_HOME', 'GRADLE_USER_HOME', 'CI', 'TEMP', 'TMP', 'JAVA_TOOL_OPTIONS', 'GRADLE_OPTS']},
            'sourceSha256': before, 'previousArtifacts': prior}
    (out / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    (out / 'executed-build_target.py').write_bytes(Path(__file__).read_bytes())
    for label, home in [('daemon', Path(env['JAVA_HOME'])), ('target', args.jdk16)]:
        with (out / (label + '-java-version.log')).open('wb') as version_log:
            subprocess.run([str(home / 'bin/java.exe'), '-version'], cwd=out, env=env, stdout=version_log, stderr=subprocess.STDOUT, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    start = time.monotonic()
    with (out / 'console.log').open('wb') as log:
        process = subprocess.run(cmd, cwd=PROJECT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
    unchanged, old_unchanged = observed_sources() == before, original_artifacts()
    loaders = [] if args.configure_only else (['fabric', 'forge'] if args.target == 'all' else [args.target])
    artifacts = [{'path': p.relative_to(ROOT).as_posix(), 'sha256': digest(p), 'bytes': p.stat().st_size}
                 for loader in loaders for p in sorted((PROJECT / loader / 'build/libs').glob('*.jar'))]
    result = {**plan, 'exitCode': process.returncode, 'elapsedSeconds': time.monotonic() - start,
              'sourcesUnchanged': unchanged, 'previousArtifactsUnchanged': old_unchanged,
              'logSha256': digest(out / 'console.log'), 'artifacts': artifacts}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['target', 'attempt', 'exitCode', 'elapsedSeconds',
                                           'sourcesUnchanged', 'previousArtifactsUnchanged', 'artifacts']}), flush=True)
    return process.returncode or (0 if unchanged and old_unchanged else 2)

if __name__ == '__main__':
    raise SystemExit(main())
