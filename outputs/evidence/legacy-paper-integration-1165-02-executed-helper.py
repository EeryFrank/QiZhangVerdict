"""Fixed-input legacy Paper/Grim/Anti-Xray QA in new loopback fixtures only.

The shipped GPL Bukkit binary is kept unchanged. Third-party configurations are
applied only to this new fixture; installed servers and published evidence are
never modified. Normal stop is required after each of the two JVM phases.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import grim_link_smoke as common

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    '1.8.8': (445, '7ff6d2cec671ef0d95b3723b5c92890118fb882d73b7f8fa0a2cd31d97c55f86'),
    '1.12.2': (1620, '3a2041807f492dcdc34ebb324a287414946e3e05ec3df6fd03f5b5f7d9afc210'),
    '1.16.5': (794, 'e67da4851d08cde378ab2b89be58849238c303351ed2482181a99c2c2b489276'),
}
GRIM_SHA = 'd1f897c629668fc950cc318f8f049be2a2a80bb970aec6bbb19e1dd5f7cb9620'


def prepare(args):
    sys.path.insert(0, str(ROOT/'integrations'))
    from manage_integrations import fresh_directory, obtain, verify
    folder = fresh_directory(args.output)
    build, server_sha = SOURCES[args.version]
    filename = f'paper-{args.version}-{build}.jar'
    cached = args.server_cache/filename
    if not cached.is_file() or common.digest(cached) != server_sha:
        raise ValueError('Fixed official Paper input missing or checksum differs: ' + filename)
    shutil.copyfile(cached, folder/'server.jar')
    plugin = ROOT/'bukkit/build/libs/qizhangverdict-bukkit-0.1.1.jar'
    if common.digest(plugin) != common.GUARD_SHA:
        raise ValueError('Published Bukkit product bytes changed')
    plugins = folder/'plugins'; plugins.mkdir()
    shutil.copyfile(plugin, plugins/plugin.name)
    lock_path = ROOT/'integrations/legacy-dependencies.lock.json'
    lock = json.loads(lock_path.read_text('utf-8'))
    grim = next(a for a in lock['artifacts'] if a['key']=='legacy-grim-bukkit-2.3.67')
    if grim['hashes']['sha256'] != GRIM_SHA:
        raise ValueError('Legacy lock differs from reviewed Grim input')
    source = obtain(grim, args.integration_cache)
    shutil.copyfile(source, plugins/grim['filename']); verify(plugins/grim['filename'], grim)
    grim_folder = plugins/'GrimAC'; grim_folder.mkdir()
    template = ROOT/'integrations/grim-legacy-2.3.67-verdict.example.yml'
    shutil.copyfile(template, grim_folder/'punishments.yml')
    (folder/'eula.txt').write_text('eula=true\n', encoding='ascii')
    if args.version=='1.16.5':
        # Use the stock flat generator and explicitly construct the test volume.
        # The 1.16 worldgen codec does not accept the older flat JSON shape.
        generator = '{}'
    else:
        generator = '3;minecraft:bedrock,60*minecraft:stone,2*minecraft:dirt,minecraft:grass;1;'
    (folder/'server.properties').write_text(f'server-ip=127.0.0.1\nserver-port={args.port}\nonline-mode=false\n'
        'network-compression-threshold=256\nspawn-protection=0\nview-distance=3\nmax-players=10\n'
        f'level-type=flat\ngenerator-settings={generator}\ngenerate-structures=false\nlevel-seed=12955\n'
        'spawn-monsters=false\nspawn-animals=false\ndifficulty=peaceful\n', encoding='utf-8')
    if args.version=='1.8.8':
        config_name='spigot.yml'
        anti='config-version: 8\nworld-settings:\n  default:\n    anti-xray:\n      enabled: true\n      engine-mode: 1\n      hide-blocks: [14, 15, 16, 21, 56, 73, 74, 129]\n      replace-blocks: [1, 5]\n'
    else:
        config_name='paper.yml'
        config_version=13 if args.version=='1.12.2' else 20
        anti=f'config-version: {config_version}\nworld-settings:\n  default:\n    anti-xray:\n      enabled: true\n      engine-mode: 1\n      max-chunk-section-index: 3\n      update-radius: 2\n      hidden-blocks: [gold_ore, iron_ore, coal_ore, lapis_ore, diamond_ore, redstone_ore, emerald_ore]\n      replacement-blocks: [stone]\n'
    (folder/config_name).write_text(anti, encoding='utf-8')
    shutil.copyfile(folder/config_name, folder/'anti-xray-input.yml')
    java_version = subprocess.run([args.java, '-version'], capture_output=True, text=True, check=True).stderr.strip()
    node_version = subprocess.run([args.node, '--version'], capture_output=True, text=True, check=True).stdout.strip()
    metadata = {'version':args.version, 'server':'Paper', 'build':build, 'serverSha256':server_sha,
        'serverSourceUrl':f'https://fill-data.papermc.io/v1/objects/{server_sha}/{filename}',
        'guardSha256':common.GUARD_SHA, 'grimSha256':GRIM_SHA, 'grimVersion':'2.3.67',
        'legacyLockSha256':common.digest(lock_path), 'punishmentsTemplateSha256':common.digest(template),
        'antiXrayInputSha256':common.digest(folder/'anti-xray-input.yml'), 'antiXrayConfigurationFile':config_name,
        'javaExecutable':args.java, 'javaVersion':java_version, 'nodeExecutable':args.node, 'nodeVersion':node_version,
        'helperSha256':common.digest(__file__), 'sharedHelperSha256':common.digest(common.__file__),
        'protocolSha256':common.digest(args.protocol), 'qaDependencyLockSha256':common.digest(ROOT/'scripts/legacy-protocol-qa/package-lock.json'),
        'expectedDefaultPolicySha256':common.DEFAULT_POLICY_SHA,
        'host':'127.0.0.1', 'port':args.port, 'onlineMode':False,
        'scene':{'hidden':[8,32,8], 'exposed':[12,32,8], 'exposedAirNeighbor':[13,32,8], 'stoneControl':[9,32,8], 'actualTargetBlock':'minecraft:diamond_ore', 'engineMode':1},
        'scope':'Published GPL Bukkit and fixed old Grim/Paper; strict Verdict defaults, synthetic offline TCP reports, controlled ore positions and real upstream BadPacketsA. Not current core source build, genuine VM/hardware or general cheat accuracy.'}
    common.save(folder/'fixture.json',metadata)
    for source,name in [(Path(__file__),'executed-helper.py'), (Path(common.__file__),'executed-shared-helper.py'),
                        (args.protocol,'executed-protocol.cjs'), (ROOT/'scripts/legacy-protocol-qa/package-lock.json','executed-package-lock.json')]:
        shutil.copyfile(source,folder/name)
    return folder,metadata


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('version',choices=SOURCES)
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--java',required=True)
    ap.add_argument('--node',required=True)
    ap.add_argument('--port',type=int,default=25674)
    ap.add_argument('--server-cache',type=Path,default=Path('E:/CodexTemp/QiZhangVerdict/legacy-runtime/downloads'))
    ap.add_argument('--integration-cache',type=Path,default=Path('E:/CodexTemp/QiZhangVerdict/legacy-integration-research/binary-audit-01/jars'))
    ap.add_argument('--node-modules',type=Path,default=Path('E:/CodexTemp/QiZhangVerdict/legacy-protocol-qa/node_modules'))
    args=ap.parse_args()
    args.protocol=ROOT/'scripts/legacy_paper_integration_protocol.cjs'
    args.server_nogui='nogui'
    args.expected_cases={'trigger':8,'restart':6}
    args.setup_commands=['setworldspawn 0 64 0','gamerule doDaylightCycle false',
        'setblock 8 32 8 minecraft:diamond_ore','setblock 12 32 8 minecraft:diamond_ore','setblock 13 32 8 minecraft:air']
    if args.version=='1.16.5':
        args.setup_commands=['forceload add 0 0','fill 0 16 0 15 48 15 minecraft:stone'] + args.setup_commands
        args.setup_command_pause=1
    os.environ['NODE_PATH']=str(args.node_modules)
    folder,metadata=prepare(args)
    print(json.dumps({'starting':args.version,'folder':str(folder),'guardSha256':common.GUARD_SHA}),flush=True)
    results=[]
    for phase in ('trigger','restart'):
        result=common.run_phase(args,folder,phase)
        config=folder/metadata['antiXrayConfigurationFile']
        shutil.copyfile(config,folder/('anti-xray-after-'+phase+'.yml'))
        results.append(result)
        print(json.dumps({'phase':phase,'passed':result['passed'],'groups':result['protocol']['caseCount'],
            'serverExit':result['serverExit'],'elapsedSeconds':result['elapsedSeconds']}),flush=True)
    common.save(folder/'acceptance.json',{**metadata,'passed':True,'phases':results,
        'assertionGroups':sum(x['protocol']['caseCount'] for x in results), 'normalStops':all(x['normalStop'] for x in results)})


if __name__=='__main__':
    main()
