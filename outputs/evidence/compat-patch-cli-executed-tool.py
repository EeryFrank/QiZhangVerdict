#!/usr/bin/env python3
"""Create an explicitly identified MIT AntiXray compatibility fork, without Java.

This patches one fixed official artifact. It is not a QiZhangVerdict GPL mod,
an official Drex release, an updater, or a general-purpose JAR patcher.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

INPUT_SHA256 = "7c8d22a2e9c8d0f88a33ce76cdb7bade18c63bb2a5cc9b3a11991bd28c742f43"
VERSION = "1.1.0-qzcompat.1"
OUTPUT_NAME = "anti-xray-mc1.16.5-1.1.0-qzcompat.1.jar"
REFMAP = "anti-xray-mc1.16.5-refmap.json"
MIXIN = "me/drex/antixray/mixin/ChunkMapMixin"
SELECTOR = "lambda$scheduleChunkLoad$14"
TARGET = "Lnet/minecraft/class_3898;method_17256(Lnet/minecraft/class_1923;)Lcom/mojang/datafixers/util/Either;"
LICENSE_NAME = "LICENSE_anti-xray-mc1.16.5"
LICENSE_SHA256 = "109d6d2b31d28899e2a4e017341ab1ea5f5cf670a866e2bac538e8a5683e2f00"
NOTICE_NAME = "NOTICE_QIZHANG_COMPAT.txt"
NOTICE = """AntiXray 1.1.0-qzcompat.1 - independently maintained compatibility fork

This is NOT an official DrexHD release and is NOT the QiZhangVerdict GPL plugin
or mod. Original AntiXray copyright and MIT license are preserved verbatim in
LICENSE_anti-xray-mc1.16.5. Compatibility metadata/mapping changes are provided
under the same MIT license; copyright (c) 2026 QiZhangVerdict contributors.

Original project: https://github.com/DrexHD/AntiXray
Reviewed source commit: a113ce0b0616052de80ca8719986a09849348ce0
Original official release: https://modrinth.com/mod/anti-xray/version/RI3CvrQa
Original artifact: anti-xray-mc1.16.5-1.1.0.jar
Original SHA256: 7c8d22a2e9c8d0f88a33ce76cdb7bade18c63bb2a5cc9b3a11991bd28c742f43
Reported upstream failure: https://github.com/DrexHD/AntiXray/issues/48

Changes:
1. Add lambda$scheduleChunkLoad$14 to the ChunkMapMixin entry in both mappings
   and data.named:intermediary in anti-xray-mc1.16.5-refmap.json. Both map to:
   Lnet/minecraft/class_3898;method_17256(Lnet/minecraft/class_1923;)Lcom/mojang/datafixers/util/Either;
2. Identify this fork by version 1.1.0-qzcompat.1 and its display name; retain
   mod ID antixray, so the official and compatibility JAR must not coexist.
3. Add this change notice. Preserve every class, nested JAR, Mixin requirement
   and algorithm byte-for-byte. Deterministic ZIP storage changes packaging.

Mapping basis: Minecraft 1.16.5 official server mappings identify
ChunkMap.lambda$scheduleChunkLoad$14(ChunkPos) as zs.l(Lbrd;)Either. Fabric's
intermediary 1.16.5 maps it to class_3898.method_17256. The actual dedicated
runtime has the corresponding ProtoChunk constructor call in this method.

License discrepancy in the ORIGINAL release: its fabric.mod.json says
CC0-1.0, while its embedded LICENSE and the exact source commit LICENSE are
MIT. This fork retains the original descriptor license field rather than
silently rewriting that historical claim. The embedded MIT terms and this
notice must accompany redistribution; no upstream endorsement is implied.

No runtime compatibility is guaranteed by producing this artifact. Keep
separate acceptance evidence for the exact output hash and server profile.
"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def build(raw):
    if sha(raw) != INPUT_SHA256:
        raise ValueError("Only the exact reviewed official AntiXray 1.1.0 JAR is accepted")
    with zipfile.ZipFile(io.BytesIO(raw)) as source:
        if source.testzip() is not None:
            raise ValueError("Input CRC failure")
        names = source.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP entry")
        entries = {name: source.read(name) for name in names if not name.endswith("/")}
    if sha(entries[LICENSE_NAME]) != LICENSE_SHA256:
        raise ValueError("Unexpected upstream license")
    before = entries.copy()
    descriptor = json.loads(entries["fabric.mod.json"])
    if descriptor["id"] != "antixray" or descriptor["version"] != "1.1.0":
        raise ValueError("Unexpected original descriptor")
    descriptor["version"] = VERSION
    descriptor["name"] = "AntiXray (QiZhang 1.16.5 compatibility)"
    entries["fabric.mod.json"] = json_bytes(descriptor)
    refmap = json.loads(entries[REFMAP])
    for mapping in (refmap["mappings"][MIXIN], refmap["data"]["named:intermediary"][MIXIN]):
        if SELECTOR in mapping or mapping != {"net/minecraft/world/level/chunk/ProtoChunk": "net/minecraft/class_2839"}:
            raise ValueError("Refmap differs from reviewed missing-mapping input")
        mapping[SELECTOR] = TARGET
    entries[REFMAP] = json_bytes(refmap)
    entries[NOTICE_NAME] = NOTICE.encode("utf-8")
    modified = sorted(name for name, data in before.items() if entries[name] != data)
    if modified != sorted([REFMAP, "fabric.mod.json"]):
        raise AssertionError("Unexpected changed entries")
    classes = [name for name in before if name.endswith(".class")]
    if len(classes) != 32 or not all(before[n] == entries[n] for n in classes):
        raise AssertionError("All 32 class bytes must remain unchanged")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as jar:
        for name in sorted(entries):
            item = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            item.compress_type = zipfile.ZIP_STORED
            jar.writestr(item, entries[name])
    result = output.getvalue()
    with zipfile.ZipFile(io.BytesIO(result)) as jar:
        assert jar.testzip() is None
    proof = {"schemaVersion": 1, "kind": "independent-third-party-MIT-compatibility-fork", "officialRelease": False,
             "version": VERSION, "inputSha256": INPUT_SHA256, "outputSha256": sha(result), "outputBytes": len(result),
             "changedExistingEntries": modified, "newEntries": [NOTICE_NAME], "allClassBytesUnchanged": True,
             "unchangedClassCount": len(classes), "unchangedOtherFileCount": len(before)-len(modified),
             "nestedJarsUnchanged": all(before[n] == entries[n] for n in before if n.endswith(".jar")),
             "licenseSha256": LICENSE_SHA256, "zipStorage": "STORED", "zipEntryTimestamp": "1980-01-01T00:00:00",
             "entryDelta": [{"name": n, "beforeSha256": sha(before[n]) if n in before else None, "afterSha256": sha(entries[n])}
                            for n in sorted(modified+[NOTICE_NAME])], "runtimeVerified": False}
    return result, proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() == args.receipt.resolve():
        parser.error("Output and receipt must resolve to different paths")
    if args.output.name != OUTPUT_NAME:
        parser.error("Output filename must identify the compatibility fork: " + OUTPUT_NAME)
    if args.output.resolve() == args.input.resolve() or args.output.exists() or args.receipt.exists():
        parser.error("Use new output and receipt files; never overwrite the official input")
    raw = args.input.read_bytes()
    result, proof = build(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as out:
        out.write(result)
    proof.update({"inputPath": str(args.input.resolve()), "outputPath": str(args.output.resolve()),
                  "toolSha256": sha(Path(__file__).read_bytes())})
    with args.receipt.open("xb") as out:
        out.write(json_bytes(proof))
    print(json.dumps({"version": VERSION, "outputSha256": proof["outputSha256"], "allClassBytesUnchanged": True,
                      "runtimeVerified": False}, indent=2))


if __name__ == "__main__":
    main()
