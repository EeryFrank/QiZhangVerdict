#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Compile only regression runners, then execute the core embedded in one exact JAR."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jar', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--java', type=Path, required=True)
    parser.add_argument('--javac', type=Path, required=True, help='JDK 21 compiler can read every supported platform JAR')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    jar = args.jar.resolve()
    if not re.fullmatch('[0-9a-f]{64}', args.sha256) or sha(jar) != args.sha256:
        parser.error('Expected immutable candidate SHA256')
    sys.path.insert(0, str(ROOT/'integrations'))
    from manage_integrations import fresh_directory
    folder = fresh_directory(args.output)
    classes = folder/'runner-classes'; classes.mkdir()
    sources = [ROOT/'core/src/test/java/cn/qizhang/guard/core'/f'{name}.java'
               for name in ('SecurityRegressionTest', 'CatalogCompatibilityTest')]
    origin = folder/'ArtifactOriginCheck.java'
    origin.write_text('import java.nio.file.Paths;\npublic final class ArtifactOriginCheck {\n'
        'public static void main(String[] args) throws Exception {\n'
        'java.net.URI uri = cn.qizhang.guard.core.GuardService.class.getProtectionDomain().getCodeSource().getLocation().toURI();\n'
        'if (!Paths.get(uri).toRealPath().equals(Paths.get(args[0]).toRealPath())) throw new AssertionError("Production class came from a different location");\n'
        'System.out.println("PASS: production GuardService loaded from the explicitly pinned artifact");\n}}\n',encoding='utf-8')
    result = {'artifact':str(jar),'sha256':args.sha256,'bytes':jar.stat().st_size,
              'scope':'Core from the packaged JAR, not source classes; no Minecraft loader or player runtime acceptance.',
              'java':str(args.java),'javac':str(args.javac),'checks':[],
              'sourceFiles':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in sources],
              'toolSha256':sha(__file__),'passed':False}
    environment = os.environ.copy()
    for key in ('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS'): environment.pop(key,None)
    def run(label, command, required=None):
        log = folder/(label+'.log')
        with log.open('xb') as out:
            completed = subprocess.run([str(x) for x in command],cwd=folder,env=environment,stdout=out,
                stderr=subprocess.STDOUT,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        text = log.read_text('utf-8',errors='replace')
        okay = completed.returncode==0 and (required is None or required in text)
        result['checks'].append({'name':label,'command':[str(x) for x in command],'exitCode':completed.returncode,
                                'passed':okay,'log':log.name,'sha256':sha(log),'bytes':log.stat().st_size})
        if not okay: raise RuntimeError(label+' failed; see '+str(log))
    try:
        with zipfile.ZipFile(jar) as archive:
            assert archive.testzip() is None
            for filename in ('LICENSE','NOTICE'):
                assert archive.read(filename)==(ROOT/filename).read_bytes(),filename+' differs'
            result['embeddedCoreClassCount'] = sum(n.startswith('cn/qizhang/guard/core/') and n.endswith('.class') for n in archive.namelist())
            assert result['embeddedCoreClassCount']>0
        run('java-version',[args.java,'-version'])
        run('compile-runners',[args.javac,'--release','8','-encoding','UTF-8','-sourcepath','','-cp',jar,'-d',classes,*sources,origin])
        # Test compilation must not silently compile any production source.
        compiled=[p.relative_to(classes).as_posix() for p in classes.rglob('*.class')]
        assert compiled and all(p=='ArtifactOriginCheck.class' or re.fullmatch(r'cn/qizhang/guard/core/(SecurityRegressionTest|CatalogCompatibilityTest)(\$[^/]+)?\.class',p) for p in compiled)
        result['runnerClassFiles']=compiled
        command=[args.java,'-Xmx128M','-XX:MaxMetaspaceSize=64M','-Dqzguard.testDir='+str(folder/'test-data'),'-cp',str(classes)+os.pathsep+str(jar)]
        run('artifact-origin',command+['ArtifactOriginCheck',jar],'PASS: production GuardService')
        run('security',command+['cn.qizhang.guard.core.SecurityRegressionTest'],'PASS 57:')
        run('catalog',command+['cn.qizhang.guard.core.CatalogCompatibilityTest',ROOT/'catalog/blacklist-extension.tsv'],'37')
        assert sha(jar)==args.sha256
        result['passed']=True
    except Exception as error:
        result['error']=str(error)
    finally:
        result['artifactUnchanged']=sha(jar)==args.sha256
        (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'artifact':jar.name,'passed':result['passed'],'output':str(folder),'error':result.get('error')}))
    if not result['passed']: raise SystemExit(1)


if __name__=='__main__':
    main()
