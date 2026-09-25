import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(r'E:\Codex_work\QiZhangVerdict')
CACHE = Path(__file__).resolve().parent
JDK = Path(r'E:\CodexTemp\QiZhangVerdict\toolchains\jdk8\jdk8u504-b01\bin')
BLACKLIST = 'core/src/main/java/cn/qizhang/guard/core/Blacklist.java'
CATALOG = 'catalog/blacklist-extension.tsv'
TESTS = ['core/src/test/java/cn/qizhang/guard/core/SecurityRegressionTest.java',
         'core/src/test/java/cn/qizhang/guard/core/CatalogCompatibilityTest.java']

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
    assert not (CACHE / 'result.json').exists(), 'Refusing to overwrite validation'
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    files = sorted((ROOT / 'core/src/main/java').rglob('*.java')) + [ROOT / t for t in TESTS]
    snapshot = [(p.relative_to(ROOT).as_posix(), p.read_bytes()) for p in files]
    catalog = (ROOT / CATALOG).read_bytes()
    rows = [s.split('\t') for s in catalog.decode('utf-8').splitlines() if s and not s.startswith('#')]
    assert len(rows) == 37 and sum(r[2] == 'DENY' for r in rows) == 33 and sum(r[2] == 'ALERT' for r in rows) == 4
    result = {'baseCommit': commit, 'kind': 'core-source-and-catalog-not-product-runtime',
              'harnessSha256': sha(Path(__file__).read_bytes()),
              'sourceFiles': [{'path': path, 'sha256': sha(data), 'bytes': len(data)} for path, data in snapshot],
              'catalog': {'path': CATALOG, 'sha256': sha(catalog), 'bytes': len(catalog), 'rules': 37, 'deny': 33, 'alert': 4},
              'runs': {}}
    for label, args in [('java-version', [str(JDK / 'java.exe'), '-Xmx128m', '-version']),
                        ('javac-version', [str(JDK / 'javac.exe'), '-J-Xmx128m', '-version'])]:
        record, _ = run(label, args)
        result['runs'][label] = record
        assert record['exitCode'] == 0
    for case in ['fixed', 'old-defaults-control']:
        stage = CACHE / case
        stage.mkdir(exist_ok=False)
        classes = stage / 'classes'; classes.mkdir()
        staged = []
        for path, content in snapshot:
            if case == 'old-defaults-control' and path == BLACKLIST:
                content = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)
                result['oldBlacklistSha256'] = sha(content)
            target = stage / path
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)
            staged.append(str(target))
        catalog_copy = stage / 'blacklist-extension.tsv'; catalog_copy.write_bytes(catalog)
        command = [str(JDK / 'javac.exe'), '-J-Xmx128m', '-J-XX:MaxMetaspaceSize=64m',
                   '-encoding', 'UTF-8', '-d', str(classes)] + staged
        record, _ = run(case + '-compile', command)
        result['runs'][case + '-compile'] = record
        assert record['exitCode'] == 0, 'Compilation failed'
        suites = ['SecurityRegressionTest', 'CatalogCompatibilityTest'] if case == 'fixed' else ['CatalogCompatibilityTest']
        for suite in suites:
            command = [str(JDK / 'java.exe'), '-Xmx128m', '-XX:MaxMetaspaceSize=64m',
                       '-Dqzguard.testDir=' + str(stage / ('private-state-' + suite)),
                       '-cp', str(classes), 'cn.qizhang.guard.core.' + suite]
            if suite == 'CatalogCompatibilityTest': command.append(str(catalog_copy))
            record, output = run(case + '-' + suite, command)
            result['runs'][case + '-' + suite] = record
            if case == 'old-defaults-control':
                assert record['exitCode'] != 0 and 'Fresh defaults must preserve every catalog kind, ID, action and pinned source without extra entries' in output
                record['expectedFailureObserved'] = True
            elif suite == 'SecurityRegressionTest':
                count = len(re.findall(r'^PASS \d+:', output, re.M))
                assert record['exitCode'] == 0 and count == 57 and 'PASS: 57 security regression tests' in output
                record['passedCases'] = count
            else:
                rules = len(re.findall(r'^PASS rule \d+:', output, re.M))
                controls = len(re.findall(r'^PASS control \d+:', output, re.M))
                assert record['exitCode'] == 0 and rules == 37 and controls == 3
                assert '37 exact catalog rules (33 DENY, 4 ALERT)' in output
                record['passedRules'] = rules; record['passedControls'] = controls
    result['passed'] = True
    (CACHE / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': True, 'securityTests': 57, 'catalogRules': 37, 'policyControls': 3,
                      'oldDefaultsRejected': True, 'cache': str(CACHE)}))

if __name__ == '__main__':
    main()
