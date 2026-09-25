"""Package original artifacts/docs only; third-party dependencies remain separately downloaded."""
import argparse, hashlib, json, os, pathlib, re, shutil, zipfile
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', default='0.1.1')
parser.add_argument('--validation', help='Validation manifest relative to outputs, or an absolute path')
args = parser.parse_args()
if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?', args.version):
    raise SystemExit('Invalid release version')
release_version = args.version
root = pathlib.Path(__file__).resolve().parents[1]
out = root / 'outputs'
out.mkdir(exist_ok=True)
release = out / f'QiZhangVerdict-{release_version}'
binary_zip = out/f'QiZhangVerdict-{release_version}.zip'
source_zip = out/f'QiZhangVerdict-{release_version}-sources.zip'
artifact_receipt = out/f'artifacts-{release_version}.json'
if binary_zip.exists() or source_zip.exists() or artifact_receipt.exists(): raise SystemExit('Release archive or artifact receipt already exists; refusing to overwrite published bytes')
if release.is_symlink() or release.is_junction(): raise SystemExit('Release directory must not be a link')
if release.exists() and any(release.iterdir()): raise SystemExit('Release directory must be absent or empty; refusing to mix in previous files')
release.mkdir(exist_ok=True)
artifacts = [root/f'bukkit/build/libs/qizhangverdict-bukkit-{release_version}.jar']
for version, loader in [('1.20.1','fabric'),('1.20.1','forge'),('1.21.1','fabric'),('1.21.1','neoforge')]:
    artifacts.append(root/f'platforms/{version}/{loader}/build/libs/qizhangverdict-{loader}-{version}-{release_version}.jar')
manifest=[]
validation_path = out/(args.validation or f'validation-{release_version}.json')
if not validation_path.is_file(): raise SystemExit(f'Missing {validation_path}; finish validation before packaging')
validation = json.loads(validation_path.read_text(encoding='utf-8'))
validated_hashes = {item['file']: item['sha256'].lower() for item in validation['artifacts']}
evidence_files = []
for item in validation.get('evidence', []):
    relative = pathlib.PurePosixPath(item['file'])
    if relative.is_absolute() or '..' in relative.parts or '\\' in item['file'] or ':' in item['file']:
        raise SystemExit(f"Unsafe evidence path: {item['file']}")
    evidence = out/relative
    if evidence.is_symlink() or not evidence.resolve().is_relative_to(out.resolve()):
        raise SystemExit(f"Evidence path escaped outputs: {item['file']}")
    if not evidence.is_file() or hashlib.sha256(evidence.read_bytes()).hexdigest() != item['sha256']:
        raise SystemExit(f"Validation evidence missing or changed: {item['file']}")
    evidence_files.append((evidence, relative))
for source in artifacts:
    if not source.is_file(): raise SystemExit(f'Missing artifact: {source}')
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if validated_hashes.get(source.name) != source_hash: raise SystemExit(f'Validation artifact drift: {source.name}')
    with zipfile.ZipFile(source) as archive:
        if archive.testzip(): raise SystemExit(f'Corrupt archive: {source}')
    target=release/source.name; shutil.copy2(source,target)
    manifest.append({'file':target.name,'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
for name in ['README.md','LICENSE','NOTICE']:
    shutil.copy2(root/name,release/name)
shutil.copy2(validation_path,release/'validation.json')
# Preserve repository-relative documentation links; only manifest-listed public evidence is included.
(release/'outputs').mkdir(exist_ok=True)
shutil.copy2(validation_path, release/'outputs'/validation_path.name)
for source, relative in evidence_files:
    target = release/'outputs'/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
for directory in ['docs','integrations','catalog']:
    if not (root/directory).is_dir(): continue
    shutil.copytree(root/directory,release/directory,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
(release/'SHA256SUMS.txt').write_text(''.join(f"{x['sha256']}  {x['file']}\n" for x in manifest),encoding='utf-8')
with artifact_receipt.open('x',encoding='utf-8') as receipt:
    receipt.write(json.dumps(manifest,indent=2))
(release/'artifacts.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
with zipfile.ZipFile(binary_zip,'x',zipfile.ZIP_DEFLATED) as archive:
    for source in sorted(release.rglob('*')):
        if source.is_file(): archive.write(source,source.relative_to(out))
with zipfile.ZipFile(source_zip,'x',zipfile.ZIP_DEFLATED) as archive:
    for directory, dirs, files in os.walk(root, topdown=True, followlinks=False):
        base=pathlib.Path(directory)
        dirs[:] = sorted(d for d in dirs if d not in {'build','.gradle','.git','outputs','__pycache__','.idea','logs','run','runtime','cache'} and not (base/d).is_symlink() and not (base/d).is_junction())
        for name in sorted(files):
            source=base/name
            if source.is_symlink() or name.endswith(('.log','.pyc')) or name.startswith('.env') or name in {'accounts.state','server-id.txt','installation-id.txt'}: continue
            archive.write(source,pathlib.Path('QiZhangVerdict')/source.relative_to(root))
print(json.dumps({'release':str(binary_zip),'source':str(source_zip),'artifacts':manifest},indent=2))
