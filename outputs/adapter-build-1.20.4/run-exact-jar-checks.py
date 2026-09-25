#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Explicitly gated exact-JAR core regression runner; default is a no-Java plan."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
JDK17 = Path('E:/CodexTemp/mods-danzi/minecraft/runtime/java-runtime-gamma/windows-x64/java-runtime-gamma')
PINS = {
    'fabric': 'b8d1d1ad6e2afd41acd15aeb2fb93221b9b5a8803da5e8be0c2da86805c571e4',
    'forge': '9e8ad322c83469b686671bda0e6d86207cd8a2e838085dcf53b0c65253a7b9cf',
    'neoforge': 'c3e742892ef723d035b81e165eed3ef4a560aa249349183298dd0f9b45e48f66',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact(loader):
    return ROOT / ('platforms/1.20.4/' + loader + '/build/libs/qizhangverdict-' + loader + '-1.20.4-0.3.0-dev.jar')


def run_one(loader, output, source_pins):
    jar = artifact(loader)
    if sha(jar) != PINS[loader]:
        raise ValueError('Exact artifact changed: ' + loader)
    output.mkdir(parents=True, exist_ok=False)
    classes = output / 'runner-classes'; classes.mkdir()
    temp = output / 'temp'; temp.mkdir()
    tests = [ROOT / ('core/src/test/java/cn/qizhang/guard/core/' + name + '.java')
             for name in ('SecurityRegressionTest', 'CatalogCompatibilityTest')]
    for rel, expected in source_pins.items():
        if sha(ROOT / rel) != expected:
            raise ValueError('Regression input changed after plan: ' + rel)
    origin = output / 'ArtifactOriginCheck.java'
    origin.write_text('import java.nio.file.Paths;\npublic final class ArtifactOriginCheck {\n'
        ' public static void main(String[] args) throws Exception {\n'
        '  java.net.URI actual = cn.qizhang.guard.core.GuardService.class.getProtectionDomain().getCodeSource().getLocation().toURI();\n'
        '  if (!Paths.get(actual).toRealPath().equals(Paths.get(args[0]).toRealPath())) throw new AssertionError("Wrong core source");\n'
        '  System.out.println("PASS: exact packaged core origin");\n }}\n', encoding='utf-8')
    environment = dict(os.environ, TEMP=str(temp), TMP=str(temp))
    for key in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS'):
        environment.pop(key, None)
    result = {'loader': loader, 'artifact': str(jar.relative_to(ROOT)), 'sha256': PINS[loader],
              'scope': 'Only packaged core regressions on Java17; no Minecraft loader, server or rendered client execution.',
              'java': str(JDK17 / 'bin/java.exe'), 'javac': str(JDK17 / 'bin/javac.exe'),
              'passed': False, 'checks': [], 'sourceSha256': source_pins,
              'runnerSha256': sha(__file__), 'gameStarted': False}

    def command(label, argv, required=None):
        log = output / (label + '.log')
        with log.open('xb') as stream:
            proc = subprocess.run([str(x) for x in argv], cwd=output, env=environment,
                                  stdout=stream, stderr=subprocess.STDOUT, timeout=120,
                                  creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        text = log.read_text('utf-8', errors='replace')
        okay = proc.returncode == 0 and (required is None or required in text)
        result['checks'].append({'name': label, 'argv': [str(x) for x in argv], 'exitCode': proc.returncode,
                                'passed': okay, 'log': log.name, 'bytes': log.stat().st_size, 'sha256': sha(log)})
        if not okay:
            raise AssertionError(label + ' failed; retain ' + str(log))
        return text

    try:
        with zipfile.ZipFile(jar) as archive:
            assert archive.testzip() is None
            for name in ('LICENSE', 'NOTICE'):
                assert archive.read(name) == (ROOT / name).read_bytes()
        command('java-version', [JDK17 / 'bin/java.exe', '-version'])
        command('compile-runners', [JDK17 / 'bin/javac.exe', '-J-Xmx256m', '--release', '8', '-encoding', 'UTF-8',
                '-sourcepath', '', '-cp', jar, '-d', classes, *tests, origin])
        compiled = sorted(p.relative_to(classes).as_posix() for p in classes.rglob('*.class'))
        assert compiled and all(n == 'ArtifactOriginCheck.class' or
            re.fullmatch(r'cn/qizhang/guard/core/(SecurityRegressionTest|CatalogCompatibilityTest)(\$[^/]+)?\.class', n)
            for n in compiled), 'Production source was compiled into regression classpath'
        result['runnerClassFiles'] = compiled
        base = [JDK17 / 'bin/java.exe', '-Xmx128M', '-XX:MaxMetaspaceSize=64M',
                '-Djava.io.tmpdir=' + str(temp), '-Dqzguard.testDir=' + str(output / 'test-data'),
                '-cp', str(classes) + os.pathsep + str(jar)]
        command('artifact-origin', base + ['ArtifactOriginCheck', jar], 'PASS: exact packaged core origin')
        security = command('security', base + ['cn.qizhang.guard.core.SecurityRegressionTest'])
        catalog = command('catalog', base + ['cn.qizhang.guard.core.CatalogCompatibilityTest', ROOT / 'catalog/blacklist-extension.tsv'])
        for text, pattern, count in [(security, r'^PASS (\d+):', 57),
                                     (catalog, r'^PASS rule (\d+):', 37),
                                     (catalog, r'^PASS control (\d+):', 3)]:
            assert list(map(int, re.findall(pattern, text, re.M))) == list(range(1, count + 1))
        assert sha(jar) == PINS[loader]
        for rel, expected in source_pins.items():
            assert sha(ROOT / rel) == expected
        result.update(passed=True, securityCount=57, catalogRuleCount=37, catalogControlCount=3)
    except Exception as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        result['artifactUnchanged'] = sha(jar) == PINS[loader]
        with (output / 'result.json').open('x', encoding='utf-8') as f:
            f.write(json.dumps(result, indent=2) + '\n')
    if not result['passed']:
        raise RuntimeError(result.get('error', 'Exact artifact regression failed'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, default=Path('E:/CodexTemp/QiZhangVerdict/next-platforms/1.20.4/artifact-core/01'))
    parser.add_argument('--execute', action='store_true', help='Run Java only after the shared QA slot has been released')
    args = parser.parse_args()
    output = args.output_root.resolve()
    output.relative_to(Path('E:/CodexTemp/QiZhangVerdict/next-platforms/1.20.4').resolve())
    if output.exists():
        raise ValueError('Use a new output directory; earlier results must be preserved')
    for loader, expected in PINS.items():
        assert sha(artifact(loader)) == expected
    for file in ('java.exe', 'javac.exe'):
        assert (JDK17 / 'bin' / file).is_file()
    sources = ['core/src/test/java/cn/qizhang/guard/core/SecurityRegressionTest.java',
               'core/src/test/java/cn/qizhang/guard/core/CatalogCompatibilityTest.java',
               'catalog/blacklist-extension.tsv', 'LICENSE', 'NOTICE']
    source_pins = {p: sha(ROOT / p) for p in sources}
    print(json.dumps({'mode': 'EXECUTE' if args.execute else 'PLAN_ONLY_NO_JAVA', 'pins': PINS,
                      'outputRoot': str(output), 'java': str(JDK17), 'sourceSha256': source_pins}), flush=True)
    if not args.execute:
        return
    output.mkdir(parents=True, exist_ok=False)
    results = [run_one(loader, output / loader, source_pins) for loader in PINS]
    summary = {'schemaVersion': 1, 'minecraft': '1.20.4', 'version': '0.3.0-dev',
               'completedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'passed': all(x['passed'] for x in results), 'checksPerJar': 97, 'totalChecks': 291,
               'scope': 'Exact packaged core tests only; no Minecraft runtime acceptance.',
               'artifacts': results, 'runnerSha256': sha(__file__), 'gameStarted': False}
    with (output / 'summary.json').open('x', encoding='utf-8') as f:
        f.write(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({'passed': summary['passed'], 'totalChecks': 291, 'summary': str(output / 'summary.json')}), flush=True)


if __name__ == '__main__':
    main()
