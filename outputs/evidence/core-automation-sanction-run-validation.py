import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(r'E:\Codex_work\QiZhangVerdict')
CACHE = Path(__file__).resolve().parent
JDK = Path(r'E:\CodexTemp\QiZhangVerdict\toolchains\jdk8\jdk8u504-b01\bin')
SERVICE = 'core/src/main/java/cn/qizhang/guard/core/GuardService.java'
TEST = 'core/src/test/java/cn/qizhang/guard/core/SecurityRegressionTest.java'
MAIN = 'cn.qizhang.guard.core.SecurityRegressionTest'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def run(label, command):
    start = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=180)
    output = CACHE / (label + '.log')
    output.write_bytes(result.stdout)
    return {'command': [str(s) for s in command], 'exitCode': result.returncode,
            'elapsedSeconds': round(time.monotonic() - start, 3),
            'log': str(output), 'logSha256': sha(result.stdout),
            'logBytes': len(result.stdout)}, result.stdout.decode('utf-8', errors='replace')

def main():
    if (CACHE / 'result.json').exists():
        raise RuntimeError('Refusing to overwrite completed validation')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    files = sorted((ROOT / 'core/src/main/java').rglob('*.java')) + [ROOT / TEST]
    snapshot = [(p.relative_to(ROOT).as_posix(), p.read_bytes()) for p in files]
    result = {'baseCommit': commit, 'kind': 'source-level-regression-not-product-runtime',
              'harnessSha256': sha(Path(__file__).read_bytes()),
              'sourceFiles': [{'path': path, 'sha256': sha(data), 'bytes': len(data)}
                              for path, data in snapshot], 'runs': {}}
    for label, args in [('java-version', [str(JDK / 'java.exe'), '-Xmx128m', '-version']),
                        ('javac-version', [str(JDK / 'javac.exe'), '-J-Xmx128m', '-version'])]:
        record, _ = run(label, args)
        result['runs'][label] = record
        assert record['exitCode'] == 0
    for case in ['fixed', 'pre-fix-control']:
        stage = CACHE / case
        stage.mkdir(exist_ok=False)
        classes = stage / 'classes'
        classes.mkdir()
        staged = []
        for path, content in snapshot:
            if case == 'pre-fix-control' and path == SERVICE:
                content = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)
                result['preFixGuardServiceSha256'] = sha(content)
            target = stage / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            staged.append(str(target))
        command = [str(JDK / 'javac.exe'), '-J-Xmx128m', '-J-XX:MaxMetaspaceSize=64m',
                   '-encoding', 'UTF-8', '-d', str(classes)] + staged
        record, _ = run(case + '-compile', command)
        result['runs'][case + '-compile'] = record
        assert record['exitCode'] == 0, 'Compilation failed'
        command = [str(JDK / 'java.exe'), '-Xmx128m', '-XX:MaxMetaspaceSize=64m',
                   '-Dqzguard.testDir=' + str(stage / 'private-test-state'),
                   '-cp', str(classes), MAIN]
        record, output = run(case + '-security', command)
        record['passedCasesBeforeExit'] = len(re.findall(r'^PASS \d+:', output, re.M))
        result['runs'][case + '-security'] = record
        if case == 'fixed':
            assert record['exitCode'] == 0 and record['passedCasesBeforeExit'] == 57
            assert 'PASS: 57 security regression tests' in output
        else:
            assert record['exitCode'] != 0 and record['passedCasesBeforeExit'] == 28
            assert 'Explicit automation denial must ban two accounts and one device' in output
    result['passed'] = True
    (CACHE / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': True, 'fixedSecurityTests': 57, 'preFixControlRejected': True,
                      'cache': str(CACHE)}))

if __name__ == '__main__':
    main()
