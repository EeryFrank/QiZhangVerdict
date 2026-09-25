#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Verify or package an explicit committed preview manifest; never publish."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_DIRS = {".git", ".gradle", "__pycache__", ".idea", "build", "run",
                  "runtime", "cache", "world", "worlds", "playerdata", "logs"}
FORBIDDEN_FILES = {"accounts.state", "server-id.txt", "installation-id.txt",
                   "usercache.json", "ops.json", "banned-players.json", "banned-ips.json"}
RESERVED = {"con", "prn", "aux", "nul"} | {
    prefix + str(number) for prefix in ("com", "lpt") for number in range(1, 10)
}
SHA256 = re.compile(r"[a-f0-9]{64}")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class Rejected(ValueError):
    """A reviewable input changed or a packaging boundary was violated."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Rejected("Manifest contains a duplicate JSON key")
        result[key] = value
    return result


def relative_path(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise Rejected("Paths must be nonempty repository-relative POSIX paths")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        raise Rejected("Absolute paths, empty components and dot traversal are forbidden")
    for part in path.parts:
        if part.rstrip(" .") != part or part.split(".")[0].casefold() in RESERVED:
            raise Rejected("Path has a Windows reserved component")
        if any(ord(char) < 32 for char in part):
            raise Rejected("Path has control characters")
    return path


def check_no_links(path):
    """Inspect every existing lexical ancestor before resolving or opening it."""
    path = Path(os.path.abspath(path))
    for current in reversed((path, *path.parents)):
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise Rejected("Symbolic links and Windows reparse points are forbidden: " + str(current))
    return path


def local_path(repository, value):
    relative = relative_path(value)
    candidate = check_no_links(repository.joinpath(*relative.parts))
    if not candidate.is_relative_to(repository):
        raise Rejected("Path escaped the repository")
    if not candidate.is_file():
        raise Rejected("Missing input file: " + value)
    return candidate


def source_allowed(value):
    path = relative_path(value)
    parts = [part.casefold() for part in path.parts]
    if any(part in FORBIDDEN_DIRS for part in parts[:-1]):
        raise Rejected("Tracked source tree contains a runtime/cache directory: " + value)
    if parts[-1] in FORBIDDEN_FILES or parts[-1].startswith(".env"):
        raise Rejected("Tracked source tree contains private runtime/configuration data: " + value)
    if parts[-1].endswith((".pyc", ".pyo")):
        raise Rejected("Tracked bytecode cache is forbidden: " + value)


def git(repository, *arguments, data=None):
    environment = dict(os.environ, GIT_NO_REPLACE_OBJECTS="1", GIT_TERMINAL_PROMPT="0")
    process = subprocess.run(
        ["git", "-C", str(repository), *arguments], input=data, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=environment, creationflags=NO_WINDOW, timeout=120)
    if process.returncode:
        # Do not print Git stderr: unusual remotes/configuration may contain secrets.
        raise Rejected("Git operation failed: " + arguments[0])
    return process.stdout


def tree_and_blobs(repository, commit):
    if not re.fullmatch(r"(?:[a-f0-9]{40}|[a-f0-9]{64})", commit):
        raise Rejected("Use a full lowercase commit object ID, not a branch or abbreviated ref")
    resolved = git(repository, "rev-parse", "--verify", commit + "^{commit}").decode().strip()
    if resolved != commit:
        raise Rejected("Commit does not identify the requested commit object")
    tree = {}
    casefolded = set()
    for raw in git(repository, "ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0"):
        if not raw:
            continue
        prefix, name = raw.split(b"\t", 1)
        mode, kind, object_id = prefix.decode("ascii").split()
        name = name.decode("utf-8")
        source_allowed(name)
        if mode not in ("100644", "100755") or kind != "blob":
            raise Rejected("Source commit contains a symlink/submodule or unsupported mode: " + name)
        if name.casefold() in casefolded:
            raise Rejected("Source paths collide on Windows: " + name)
        casefolded.add(name.casefold())
        tree[name] = (mode, object_id)
    object_ids = list(dict.fromkeys(object_id for _, object_id in tree.values()))
    result = git(repository, "cat-file", "--batch",
                 data=("\n".join(object_ids) + "\n").encode("ascii"))
    objects = {}
    position = 0
    for requested in object_ids:
        end = result.index(b"\n", position)
        object_id, kind, length = result[position:end].decode("ascii").split()
        if object_id != requested or kind != "blob":
            raise Rejected("Unexpected Git object response")
        length = int(length)
        position = end + 1
        payload = result[position:position + length]
        if len(payload) != length or result[position + length:position + length + 1] != b"\n":
            raise Rejected("Truncated Git blob")
        objects[requested] = payload
        position += length + 1
    if position != len(result):
        raise Rejected("Unexpected trailing Git object data")
    return tree, {name: objects[object_id] for name, (_, object_id) in tree.items()}


def worktree_matches(path, committed, allow_text_eol=False):
    current = path.read_bytes()
    if current == committed:
        return
    if allow_text_eol and b"\0" not in current and b"\0" not in committed:
        try:
            current.decode("utf-8")
            committed.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            if current.replace(b"\r\n", b"\n") == committed.replace(b"\r\n", b"\n"):
                return
    raise Rejected("Working file differs from the selected commit: " + str(path))


def verify_reference(entry, data):
    if set(entry) != {"path", "sha256", "bytes"}:
        raise Rejected("Each manifest reference requires exactly path, sha256 and bytes")
    if not isinstance(entry["sha256"], str) or not SHA256.fullmatch(entry["sha256"]):
        raise Rejected("Reference SHA-256 must contain 64 lowercase hexadecimal characters")
    if type(entry["bytes"]) is not int or entry["bytes"] < 0:
        raise Rejected("Reference size must be a nonnegative integer")
    if len(data) != entry["bytes"] or digest(data) != entry["sha256"]:
        raise Rejected("Manifest reference hash/size drift: " + entry["path"])


def check_jar(data, license_bytes, notice_bytes):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(names) != len(set(names)):
                raise Rejected("JAR has duplicate ZIP entries")
            for entry in entries:
                relative_path(entry.filename.rstrip("/"))
                if (entry.external_attr >> 16) & 0o170000 == stat.S_IFLNK:
                    raise Rejected("JAR contains a symlink")
            if sum(entry.file_size for entry in entries) > 256 * 1024**2:
                raise Rejected("First-party preview JAR expands beyond 256 MiB")
            if archive.testzip() is not None:
                raise Rejected("JAR CRC verification failed")
            if not any(name.endswith(".class") for name in names):
                raise Rejected("Preview artifact is not a compiled runtime JAR")
            if archive.read("LICENSE") != license_bytes or archive.read("NOTICE") != notice_bytes:
                raise Rejected("Embedded LICENSE/NOTICE differs from the selected commit")
            text = archive.read("META-INF/MANIFEST.MF").decode("utf-8")
            text = re.sub(r"\r?\n ", "", text)
            attributes = {}
            for line in text.splitlines():
                if ": " in line:
                    key, value = line.split(": ", 1)
                    if key in attributes:
                        raise Rejected("Duplicate JAR manifest attribute")
                    attributes[key] = value
            if attributes.get("License") != "GPL-3.0-only":
                raise Rejected("JAR does not declare GPL-3.0-only")
    except (zipfile.BadZipFile, KeyError, UnicodeDecodeError) as error:
        raise Rejected("Invalid JAR or required licensing entry missing") from error


@dataclass
class Plan:
    repository: Path
    commit: str
    manifest_path: str
    manifest_bytes: bytes
    package_name: str
    tree: dict
    source_blobs: dict
    files: dict
    roles: dict
    output_root: Path

    @property
    def destinations(self):
        return [self.output_root / self.package_name,
                self.output_root / (self.package_name + ".zip"),
                self.output_root / (self.package_name + "-sources.zip"),
                self.output_root / (self.package_name + "-packaging.json")]


def verify(repository, manifest_path, commit, output_root):
    repository = check_no_links(repository)
    if not repository.is_dir():
        raise Rejected("Repository does not exist")
    tree, blobs = tree_and_blobs(repository, commit)
    relative_path(manifest_path)
    if manifest_path not in blobs:
        raise Rejected("Preview manifest is not tracked at the selected commit")
    worktree_matches(local_path(repository, manifest_path), blobs[manifest_path], True)
    try:
        manifest = json.loads(blobs[manifest_path], object_pairs_hook=unique_json_object)
    except (ValueError, UnicodeDecodeError) as error:
        raise Rejected("Invalid committed manifest JSON") from error
    if not isinstance(manifest, dict):
        raise Rejected("Manifest must be a JSON object")
    if set(manifest) != {"schemaVersion", "packageName", "artifacts", "documents", "evidence"}:
        raise Rejected("Unexpected manifest fields")
    if type(manifest["schemaVersion"]) is not int or manifest["schemaVersion"] != 1:
        raise Rejected("Unsupported preview manifest schema")
    name = manifest["packageName"]
    if not isinstance(name, str) or not re.fullmatch(r"QiZhangVerdict-[A-Za-z0-9][A-Za-z0-9._-]{0,100}", name) or name.endswith("."):
        raise Rejected("Invalid preview packageName")
    for key in ("artifacts", "documents", "evidence"):
        if not isinstance(manifest[key], list):
            raise Rejected(key + " must be an explicit array")
    if not manifest["artifacts"]:
        raise Rejected("At least one original built JAR is required")
    documents = {item.get("path") for item in manifest["documents"] if isinstance(item, dict)}
    if not {"LICENSE", "NOTICE"} <= documents:
        raise Rejected("documents must explicitly include LICENSE and NOTICE")
    if "LICENSE" not in blobs or "NOTICE" not in blobs:
        raise Rejected("Selected commit lacks licensing files")
    if b"GNU GENERAL PUBLIC LICENSE" not in blobs["LICENSE"] or b"Version 3," not in blobs["LICENSE"]:
        raise Rejected("Selected LICENSE is not GNU GPL version 3")
    files, roles, sources = {}, {}, set()
    for role in ("artifacts", "documents", "evidence"):
        for entry in manifest[role]:
            if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "bytes"}:
                raise Rejected("Each manifest reference requires exactly path, sha256 and bytes")
            source = entry["path"]
            path = relative_path(source)
            if source.casefold() in sources:
                raise Rejected("Duplicate input reference: " + source)
            sources.add(source.casefold())
            local = local_path(repository, source)
            if role == "artifacts":
                if path.suffix != ".jar" or not source.startswith(("platforms/", "bukkit/")) or list(path.parts[-3:-1]) != ["build", "libs"]:
                    raise Rejected("Artifact must be an original platforms/ or bukkit/ build/libs JAR")
                payload = local.read_bytes()
                target = path.name
                verify_reference(entry, payload)
                check_jar(payload, blobs["LICENSE"], blobs["NOTICE"])
            else:
                source_allowed(source)
                if source not in blobs:
                    raise Rejected("Whitelisted document/evidence is not in the selected commit: " + source)
                if role == "evidence" and not source.startswith("outputs/"):
                    raise Rejected("Evidence must be under outputs/")
                payload = blobs[source]
                worktree_matches(local, payload, role == "documents")
                verify_reference(entry, payload)
                target = source
            if target.casefold() in {value.casefold() for value in files} or target.casefold() in {
                    "preview-manifest.json", "packaging-summary.json", "sha256sums.txt"}:
                raise Rejected("Package destination collision: " + target)
            files[target], roles[target] = payload, role
    output_root = check_no_links(output_root)
    if output_root.exists() and not output_root.is_dir():
        raise Rejected("Output root is not a directory")
    plan = Plan(repository, commit, manifest_path, blobs[manifest_path], name,
                tree, blobs, files, roles, output_root)
    for destination in plan.destinations:
        check_no_links(destination)
        if destination.exists():
            raise Rejected("Refusing existing package directory/archive/receipt: " + str(destination))
    return plan


def zip_bytes(path, prefix, files, modes=None):
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            entry = zipfile.ZipInfo(prefix + "/" + name, (1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            mode = 0o755 if modes and modes[name][0] == "100755" else 0o644
            entry.external_attr = (stat.S_IFREG | mode) << 16
            archive.writestr(entry, files[name])


def package(plan):
    # Recheck all destinations immediately before exclusive creation. Snapshot
    # bytes verified above are used throughout, never copied from a drifting file.
    check_no_links(plan.output_root)
    for destination in plan.destinations:
        check_no_links(destination)
        if destination.exists():
            raise Rejected("Refusing to overwrite an existing packaging output")
    plan.output_root.mkdir(parents=True, exist_ok=True)
    release, binary_zip, source_zip, receipt = plan.destinations
    release.mkdir(exist_ok=False)
    files = dict(plan.files)
    files["preview-manifest.json"] = plan.manifest_bytes
    rows = [{"file": name, "bytes": len(data), "sha256": digest(data),
             "role": plan.roles.get(name, "manifest")} for name, data in sorted(files.items())]
    summary = {"schemaVersion": 1, "packageName": plan.package_name, "sourceCommit": plan.commit,
               "manifestPath": plan.manifest_path, "manifestSha256": digest(plan.manifest_bytes),
               "sourceTrackedFiles": len(plan.source_blobs), "binaryFiles": rows,
               "publishingPerformed": False,
               "scope": "Verified manifest packaging only; runtime acceptance is supplied by the committed evidence."}
    files["packaging-summary.json"] = (json.dumps(summary, indent=2) + "\n").encode()
    files["SHA256SUMS.txt"] = "".join(
        digest(data) + "  " + name + "\n" for name, data in sorted(files.items())).encode()
    for name, data in files.items():
        target = release.joinpath(*relative_path(name).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        check_no_links(target)
        with target.open("xb") as output:
            output.write(data)
    zip_bytes(binary_zip, plan.package_name, files)
    zip_bytes(source_zip, plan.package_name + "-sources", plan.source_blobs, plan.tree)
    summary["archives"] = [{"file": path.name, "bytes": path.stat().st_size,
                            "sha256": digest(path.read_bytes())} for path in (binary_zip, source_zip)]
    with receipt.open("x", encoding="utf-8") as output:
        json.dump(summary, output, indent=2)
        output.write("\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "package"))
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--manifest", required=True, help="Committed repository-relative manifest path")
    parser.add_argument("--commit", required=True, help="Full lowercase commit object ID")
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        plan = verify(args.repository, args.manifest, args.commit, args.output_root)
        result = package(plan) if args.action == "package" else {
            "verified": True, "sourceCommit": plan.commit, "packageName": plan.package_name,
            "sourceTrackedFiles": len(plan.source_blobs), "whitelistedBinaryFiles": len(plan.files),
            "outputsCreated": False, "publishingPerformed": False}
        print(json.dumps(result, indent=2))
    except (Rejected, OSError, subprocess.SubprocessError) as error:
        print("Packaging rejected: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
