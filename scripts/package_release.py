"""Package original artifacts/docs only; third-party dependencies remain separately downloaded."""
import hashlib, json, os, pathlib, shutil, zipfile
root = pathlib.Path(__file__).resolve().parents[1]
out = root / 'outputs'
out.mkdir(exist_ok=True)
release = out / 'QiZhangVerdict-0.1.0'
if release.is_symlink() or release.is_junction(): raise SystemExit('Release directory must not be a link')
if release.exists() and any(release.iterdir()): raise SystemExit('Release directory must be absent or empty; refusing to mix in previous files')
release.mkdir(exist_ok=True)
artifacts = [root/'bukkit/build/libs/qizhangverdict-bukkit-0.1.0.jar']
for version, loader in [('1.20.1','fabric'),('1.20.1','forge'),('1.21.1','fabric'),('1.21.1','neoforge')]:
    artifacts.append(root/f'platforms/{version}/{loader}/build/libs/qizhangverdict-{loader}-{version}-0.1.0.jar')
manifest=[]
validation_path = out/'validation.json'
if not validation_path.is_file(): raise SystemExit('Missing outputs/validation.json; finish validation before packaging')
validation = json.loads(validation_path.read_text(encoding='utf-8'))
validated_hashes = {item['file']: item['sha256'].lower() for item in validation['artifacts']}
for item in validation.get('evidence', []):
    evidence = out/item['file']
    if not evidence.is_file() or hashlib.sha256(evidence.read_bytes()).hexdigest() != item['sha256']:
        raise SystemExit(f"Validation evidence missing or changed: {item['file']}")
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
if (out/'evidence').is_dir(): shutil.copytree(out/'evidence',release/'evidence',dirs_exist_ok=True)
for directory in ['docs','integrations']:
    shutil.copytree(root/directory,release/directory,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
(release/'SHA256SUMS.txt').write_text(''.join(f"{x['sha256']}  {x['file']}\n" for x in manifest),encoding='utf-8')
(out/'artifacts.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(release/'artifacts.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
with zipfile.ZipFile(out/'QiZhangVerdict-0.1.0.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for source in sorted(release.rglob('*')):
        if source.is_file(): archive.write(source,source.relative_to(out))
with zipfile.ZipFile(out/'QiZhangVerdict-0.1.0-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for directory, dirs, files in os.walk(root, topdown=True, followlinks=False):
        base=pathlib.Path(directory)
        dirs[:] = sorted(d for d in dirs if d not in {'build','.gradle','.git','outputs','__pycache__','.idea','logs','run','runtime','cache'} and not (base/d).is_symlink() and not (base/d).is_junction())
        for name in sorted(files):
            source=base/name
            if source.is_symlink() or name.endswith(('.log','.pyc')) or name.startswith('.env') or name in {'accounts.state','server-id.txt','installation-id.txt'}: continue
            archive.write(source,pathlib.Path('QiZhangVerdict')/source.relative_to(root))
print(json.dumps({'release':str(out/'QiZhangVerdict-0.1.0.zip'),'source':str(out/'QiZhangVerdict-0.1.0-sources.zip'),'artifacts':manifest},indent=2))
