#!/usr/bin/env python3
"""QiZhang's Verdict: pin and stage third-party server components; stdlib only.

This tool never modifies an existing server. Stage requires an absent/empty
directory and places configuration fragments separately for deliberate review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import stat
import sys
import urllib.parse
import urllib.request
import zipfile

BASE = Path(__file__).resolve().parent
USER_AGENT = "QiZhangVerdict/0.1 (pinned integration verifier)"
MAX_BYTES = 100 * 1024 * 1024


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_new_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as out:
        json.dump(value, out, indent=2, ensure_ascii=False)
        out.write("\n")


def request(url, host):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != host or parsed.username or parsed.password:
        raise ValueError("Unexpected download host or scheme")
    response = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=45)
    final = urllib.parse.urlsplit(response.url)
    if final.scheme != "https" or final.hostname != host:
        response.close()
        raise ValueError("Redirect escaped the approved HTTPS host")
    return response


def api(endpoint):
    with request("https://api.modrinth.com/v2/" + endpoint, "api.modrinth.com") as response:
        return json.load(response)


def leaf(name):
    # Windows drive paths, ADS, traversal and separators must all be rejected.
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+()-]*\.jar", name) or ".." in name:
        raise ValueError("Unsafe artifact filename: " + repr(name))
    return name


def hashes(path):
    sha256, sha512 = hashlib.sha256(), hashlib.sha512()
    size = 0
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError("Artifact exceeds 100 MiB")
            sha256.update(chunk)
            sha512.update(chunk)
    return {"sha256": sha256.hexdigest(), "sha512": sha512.hexdigest()}, size


def verify(path, artifact, require_sha256=True):
    actual, size = hashes(path)
    expected = artifact["hashes"]
    required = ("sha256", "sha512") if require_sha256 else ("sha512",)
    for algorithm in required:
        if not re.fullmatch(r"[0-9a-f]+", expected.get(algorithm, "")) or actual[algorithm] != expected[algorithm]:
            raise ValueError(algorithm + " mismatch for " + str(path))
    if size != artifact["size"]:
        raise ValueError("Size mismatch for " + str(path))
    return actual


def obtain(artifact, cache, require_sha256=True):
    cache = Path(cache).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / leaf(artifact["filename"])
    if path.is_symlink():
        raise ValueError("Refusing symlink artifact")
    if path.exists():
        verify(path, artifact, require_sha256)
        return path
    partial = path.with_name(path.name + ".partial")
    if partial.exists():
        raise ValueError("Partial file already exists; use a fresh cache directory: " + str(partial))
    created_partial = False
    try:
        with partial.open("xb") as out:
            created_partial = True
            with request(artifact["url"], "cdn.modrinth.com") as response:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > min(MAX_BYTES, artifact["size"]):
                        raise ValueError("Download larger than locked size")
                    out.write(chunk)
        verify(partial, artifact, require_sha256)
        # On Windows rename fails if destination exists. This never targets a server.
        if path.exists():
            raise ValueError("Artifact destination appeared during download")
        partial.rename(path)
    except Exception:
        if created_partial and partial.is_file():
            partial.unlink()
        raise
    return path


def descriptor_summary(path):
    with zipfile.ZipFile(path) as jar:
        if jar.testzip() is not None:
            raise ValueError("JAR CRC failure")
        found = {}
        for name in ("plugin.yml", "fabric.mod.json", "META-INF/mods.toml", "META-INF/neoforge.mods.toml"):
            if name in jar.namelist():
                if jar.getinfo(name).file_size > 1024 * 1024:
                    raise ValueError("Oversized mod descriptor")
                found[name] = jar.read(name).decode("utf-8")
        if not found:
            raise ValueError("No supported plugin/mod descriptor in " + path.name)
        return found


def make_lock(args):
    pins = read_json(args.pins)
    project_cache = {}
    artifacts = []
    for pin in pins["artifacts"]:
        project = project_cache.setdefault(pin["project"], None)
        if project is None:
            project = project_cache[pin["project"]] = api("project/" + pin["project"])
        version = api("version/" + pin["version_id"])
        if version["project_id"] != project["id"]:
            raise ValueError("Version does not belong to pinned project")
        primary = [item for item in version["files"] if item["primary"]]
        if len(primary) != 1:
            raise ValueError("Expected exactly one primary artifact")
        file = primary[0]
        artifact = {**pin, "project_id": project["id"], "project_url": "https://modrinth.com/project/" + project["id"],
                    "source_url": project["source_url"], "license": project["license"]["id"],
                    "version_number": version["version_number"], "version_type": version["version_type"],
                    "published": version["date_published"], "game_versions": version["game_versions"],
                    "loaders": version["loaders"], "dependencies": version["dependencies"],
                    "filename": leaf(file["filename"]), "url": file["url"], "size": file["size"],
                    "hashes": {"sha512": file["hashes"]["sha512"]}}
        path = obtain(artifact, args.cache, require_sha256=False)
        artifact["hashes"] = verify(path, artifact, require_sha256=False)
        artifact["descriptors"] = descriptor_summary(path)
        artifacts.append(artifact)
        print("Verified " + artifact["filename"])
    lookup = {a["key"]: a for a in artifacts}
    for name, profile in pins["profiles"].items():
        for key in profile["artifacts"]:
            artifact = lookup[key]
            if profile["minecraft"] not in artifact["game_versions"] or profile["loader"] not in artifact["loaders"]:
                raise ValueError("Unsupported profile artifact: " + name + " / " + key)
        required_projects = {d["project_id"] for key in profile["artifacts"] for d in lookup[key]["dependencies"] if d["dependency_type"] == "required"}
        included_projects = {lookup[key]["project_id"] for key in profile["artifacts"]}
        if not required_projects <= included_projects:
            raise ValueError("Unresolved required project dependency in " + name)
    write_new_json(args.output, {"schema": 1, "product": pins["product"], "reviewed_on": pins["reviewed_on"],
                              "verification": "Official API SHA512 checked against downloaded bytes; SHA256 computed; JAR CRC and descriptors inspected. Runtime testing is separate.",
                              "artifacts": artifacts, "profiles": pins["profiles"]})


def fresh_directory(value):
    candidate = Path(value).absolute()
    for part in (candidate, *candidate.parents):
        # Path.is_junction only exists on Python 3.12+. Check Windows reparse
        # attributes too so the supported Python 3.10/3.11 versions stay safe.
        try:
            reparse = bool(getattr(part.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
        except FileNotFoundError:
            reparse = False
        if part.is_symlink() or reparse:
            raise ValueError("Output path may not traverse symlinks or junctions")
    if candidate.exists() and (not candidate.is_dir() or any(candidate.iterdir())):
        raise ValueError("Output must be absent or empty; existing servers are never modified")
    candidate.mkdir(parents=True, exist_ok=True)
    with (candidate / ".qizhang-verdict-stage").open("x", encoding="utf-8") as marker:
        marker.write("Fresh staging directory owned by the integration installer.\n")
    return candidate.resolve()


def stage(args):
    lock = read_json(args.lock)
    if lock.get("schema") != 1:
        raise ValueError("Unsupported lock schema")
    profile = lock["profiles"][args.profile]
    lookup = {a["key"]: a for a in lock["artifacts"]}
    # Validate and download before creating a stage. Failure cannot partially mutate a server.
    files = []
    for key in profile["artifacts"]:
        artifact = lookup[key]
        if artifact["folder"] not in ("mods", "plugins"):
            raise ValueError("Invalid installation folder")
        if profile["minecraft"] not in artifact["game_versions"] or profile["loader"] not in artifact["loaders"]:
            raise ValueError("Artifact does not match profile")
        files.append((artifact, obtain(artifact, args.cache)))
    output = fresh_directory(args.output)
    for artifact, source in files:
        target = output / artifact["folder"] / leaf(artifact["filename"])
        target.parent.mkdir(exist_ok=True)
        with source.open("rb") as inp, target.open("xb") as out:
            shutil.copyfileobj(inp, out)
        verify(target, artifact)
    config_name = profile["configuration"]
    if not re.fullmatch(r"[a-z0-9.-]+", config_name):
        raise ValueError("Invalid configuration name")
    snippets = BASE / "configs" / config_name
    if snippets.is_dir():
        shutil.copytree(snippets, output / "config-fragments")
    if any(key.startswith("grim-") for key in profile["artifacts"]):
        optional = output / "config-fragments"
        optional.mkdir(exist_ok=True)
        shutil.copyfile(BASE / "grim-punishments-verdict.example.yml", optional / "grim-punishments-verdict.example.yml")
    write_new_json(output / "integration-receipt.json", {"product": lock["product"], "profile": args.profile,
                   "coverage": profile["coverage"], "configuration_action": "Review config-fragments; merge before starting a new server. No configuration was applied to an existing server.",
                   "artifacts": [{k:a[k] for k in ("key", "filename", "version_number", "hashes", "license", "license_url", "source_url")} for a,_ in files]})
    print("Staged " + args.profile + " at " + str(output))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("lock", help="Resolve explicit version IDs; download and produce a NEW locked manifest")
    generate.add_argument("--pins", type=Path, default=BASE / "pins.json")
    generate.add_argument("--cache", type=Path, required=True)
    generate.add_argument("--output", type=Path, required=True)
    generate.set_defaults(run=make_lock)
    install = sub.add_parser("stage", help="Stage a locked profile in an absent/empty directory, never an existing server")
    install.add_argument("--lock", type=Path, default=BASE / "dependencies.lock.json")
    install.add_argument("--profile", required=True)
    install.add_argument("--cache", type=Path, required=True)
    install.add_argument("--output", type=Path, required=True)
    install.set_defaults(run=stage)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        sys.exit(2)
