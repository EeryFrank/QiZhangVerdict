from pathlib import Path
import argparse, datetime, hashlib, json, os, subprocess, time

ROOT = Path('E:/Codex_work/QiZhangVerdict')
CACHE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sources():
    rows = {}
    for prefix in ('core/src', 'client-common/src', 'platforms/1.21.11'):
        for path in (ROOT / prefix).rglob('*'):
            relative = path.relative_to(ROOT)
            if path.is_file() and not {'build', '.gradle'} & set(relative.parts):
                rows[relative.as_posix()] = sha(path)
    for name in ('LICENSE', 'NOTICE', 'gradle/license-resources.gradle'):
        rows[name] = sha(ROOT / name)
    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('target', choices=['fabric', 'neoforge', 'all'])
    parser.add_argument('attempt')
    args = parser.parse_args()
    assert args.attempt and all(c.isalnum() or c in '-_' for c in args.attempt)
    out = CACHE / 'builds' / args.attempt
    out.mkdir(parents=True, exist_ok=False)
    (out / 'temp').mkdir()
    before = sources()
    prior = json.loads((ROOT / 'outputs/preview-manifest-0.3.0-dev-preview.1.json').read_bytes())['artifacts']
    assert all(sha(ROOT / row['path']) == row['sha256'] for row in prior)
    env = os.environ.copy()
    env.update(JAVA_HOME='D:/Java/jdk-21', GRADLE_USER_HOME='E:/CodexTemp/Gradle/QiZhang_Games',
               CI='true', TEMP=str(out / 'temp'), TMP=str(out / 'temp'))
    env['PATH'] = env['JAVA_HOME'] + '/bin;' + env['PATH']
    env['JAVA_TOOL_OPTIONS'] = ('-Djava.io.tmpdir=' + (out / 'temp').as_posix()
        + ' -Dqzguard.testDir=' + (out / 'core-tests').as_posix()
        + ' -Djavax.net.ssl.trustStoreType=Windows-ROOT -Djavax.net.ssl.trustStore=NONE')
    env['GRADLE_OPTS'] = '-Dorg.gradle.internal.http.connectionTimeout=20000 -Dorg.gradle.internal.http.socketTimeout=20000'
    cmd = [str(ROOT / 'platforms/1.21.11/gradlew.bat'), '--no-daemon', '--max-workers=1', '--console=plain',
           '--stacktrace', '--project-cache-dir', str(out / 'project-cache'),
           '-Dorg.gradle.jvmargs=-Xmx1536m -Dfile.encoding=UTF-8',
           '-PqzRuntimeRoot=' + (out / 'runtime').as_posix()]
    cmd.extend(['build', ':fabric:commandParserSmoke'] if args.target == 'all' else [':' + args.target + ':build'])
    plan = {'schemaVersion': 1, 'target': args.target, 'attempt': args.attempt,
            'startedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'command': cmd,
            'environment': {k: env[k] for k in ['JAVA_HOME', 'GRADLE_USER_HOME', 'CI', 'TEMP', 'TMP', 'JAVA_TOOL_OPTIONS', 'GRADLE_OPTS']},
            'sourceSha256': before, 'previousArtifacts': prior}
    (out / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    start = time.monotonic()
    with (out / 'console.log').open('wb') as log:
        process = subprocess.run(cmd, cwd=ROOT / 'platforms/1.21.11', env=env,
                                 stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    unchanged = sources() == before
    old_unchanged = all(sha(ROOT / row['path']) == row['sha256'] for row in prior)
    loaders = ['fabric', 'neoforge'] if args.target == 'all' else [args.target]
    artifacts = [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p), 'bytes': p.stat().st_size}
                 for loader in loaders for p in sorted((ROOT / 'platforms/1.21.11' / loader / 'build/libs').glob('*.jar'))]
    result = {**plan, 'exitCode': process.returncode, 'elapsedSeconds': time.monotonic() - start,
              'sourcesUnchanged': unchanged, 'previousArtifactsUnchanged': old_unchanged,
              'logSha256': sha(out / 'console.log'), 'artifacts': artifacts}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['target','attempt','exitCode','elapsedSeconds','sourcesUnchanged','previousArtifactsUnchanged','artifacts']}), flush=True)
    return process.returncode or (0 if unchanged and old_unchanged else 2)

if __name__ == '__main__':
    raise SystemExit(main())
