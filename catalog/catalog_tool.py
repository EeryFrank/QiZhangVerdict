#!/usr/bin/env python3
"""Read-only source verification and explicit, non-destructive rule candidates. Python 3.11+."""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import sys
import tomllib
import urllib.parse
import urllib.request

DEFAULT_CATALOG = Path(__file__).with_name("identifiers.json")
ID_RE = re.compile(r"[a-z][a-z0-9_.-]{1,127}\Z")
KEY_RE = re.compile(r"[a-z0-9][a-z0-9_.-]*\Z")
KINDS = {"mod", "automation", "pack", "brand"}
# Ambiguous/common identities and ordinary support mods cannot become default DENY.
ALERT_ONLY = {"keystrokesmod", "baritone", "baritoe", "examplemod", "client",
              "sodium", "iris", "optifine", "jei", "rei", "litematica", "schematica",
              "lunatriuscore", "antixray", "fabric-api", "minecraft"}
MAX_SOURCE_BYTES = 1024 * 1024
MAX_RULE_BYTES = 4 * 1024 * 1024
MAX_RULE_COUNT = 10000


class CatalogError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise CatalogError(message)


def safe_text(value):
    return isinstance(value, str) and bool(value) and all(ord(c) >= 32 for c in value)


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=unique)


def check_source(source):
    require(isinstance(source, dict), "source must be an object")
    for key in ("repository", "revision", "path", "url", "sha256", "retrievedAt"):
        require(safe_text(source.get(key)), f"invalid source {key}")
    require(re.fullmatch(r"[0-9a-f]{40}", source["revision"]), "source must pin a full commit SHA")
    require(re.fullmatch(r"[0-9a-f]{64}", source["sha256"]), "source SHA256 missing")
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", source["repository"]), "invalid repository")
    path = source["path"]
    require(not path.startswith("/") and not any(p in ("", ".", "..") for p in path.split("/")), "unsafe source path")
    require("\\" not in path and "%" not in path and "?" not in path and "#" not in path, "unsafe source path")
    standard_license = path.rsplit("/", 1)[-1] in {"LICENSE", "LICENSE.txt", "COPYING", "COPYING.txt"}
    require(standard_license or path.endswith((".json", ".toml", ".properties", ".md", ".java", ".kt", ".gradle", ".kts", ".info")), "only text metadata/source is allowed")
    expected = f"https://raw.githubusercontent.com/{source['repository']}/{source['revision']}/{path}"
    require(source["url"] == expected, "source URL must match the pinned official repository path")
    dt.date.fromisoformat(source["retrievedAt"])


def validate(data):
    require(data.get("schemaVersion") == 1, "unsupported schemaVersion")
    dt.date.fromisoformat(data["reviewedAt"])
    sources = data.get("sources")
    require(isinstance(sources, dict) and sources, "sources required")
    for key, source in sources.items():
        require(KEY_RE.fullmatch(key), "invalid source key")
        check_source(source)
    entries = data.get("entries")
    require(isinstance(entries, list) and entries, "entries required")
    seen_keys, seen_ids = set(), set()
    for entry in entries:
        key = entry.get("key")
        require(isinstance(key, str) and KEY_RE.fullmatch(key) and key not in seen_keys, f"duplicate/invalid entry: {key}")
        seen_keys.add(key)
        require(safe_text(entry.get("canonicalName")), f"{key}: canonicalName required")
        require(entry.get("type") in {"MOD", "PACK", "BRAND"}, f"{key}: invalid type")
        require(entry["type"] == "MOD", f"{key}: this schema only verifies loader mod IDs; PACK/BRAND remain pending")
        require(entry.get("category") in {"CHEAT_CLIENT", "CHEAT_ADDON", "XRAY", "AUTOMATION", "AMBIGUOUS"}, f"{key}: invalid category")
        require(entry.get("recommendedAction") in {"DENY", "ALERT"}, f"{key}: invalid action")
        require(entry.get("confidence") in {"HIGH", "MEDIUM", "LOW"}, f"{key}: invalid confidence")
        require(entry.get("status") == "VERIFIED", f"{key}: unverified entries belong in pending")
        ids = entry.get("exactIds")
        require(isinstance(ids, list) and ids and len(set(ids)) == len(ids), f"{key}: unique exact IDs required")
        for identifier in ids:
            require(isinstance(identifier, str) and ID_RE.fullmatch(identifier), f"{key}: literal normalized ID required")
            identity = (entry["type"], identifier)
            require(identity not in seen_ids, f"duplicate/conflicting identity: {identity}")
            seen_ids.add(identity)
            require(entry["recommendedAction"] != "DENY" or identifier not in ALERT_ONLY, f"{key}: ambiguous/ordinary identity cannot default DENY")
        purpose = entry.get("purpose", {})
        require(safe_text(purpose.get("summary")) and purpose.get("sources"), f"{key}: purpose evidence required")
        require(all(s in sources for s in purpose["sources"]), f"{key}: unknown purpose source")
        proofs = entry.get("identifierProofs", [])
        require({p.get("id") for p in proofs} == set(ids), f"{key}: every ID needs an exact descriptor proof")
        for proof in proofs:
            require(proof.get("source") in sources, f"{key}: missing descriptor source")
            source = sources[proof["source"]]
            require(source["path"].endswith(("fabric.mod.json", "quilt.mod.json", "mcmod.info", "mods.toml")), f"{key}: ID proof must reference a loader descriptor")
            require(proof.get("format") in {"json", "toml"}, f"{key}: invalid descriptor format")
            require(isinstance(proof.get("selector"), str) and proof["selector"].startswith("/"), f"{key}: selector required")
            for binding in proof.get("bindings", []):
                require(binding.get("source") in sources and binding.get("format") == "properties", f"{key}: invalid binding source")
                require(re.fullmatch(r"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?", binding.get("token", "")), f"{key}: invalid template token")
                bound = sources[binding["source"]]
                require(bound["repository"] == source["repository"] and bound["revision"] == source["revision"], f"{key}: binding must use the same repository commit")
            for token in proof.get("jsonBareTokens", []):
                require(re.fullmatch(r"\$[A-Za-z_][A-Za-z0-9_]*", token), f"{key}: invalid bare token")
        scopes = entry.get("compatibility", [])
        require(scopes, f"{key}: source compatibility scope required")
        for scope in scopes:
            require(scope.get("loader") in {"Fabric", "Forge", "NeoForge", "Quilt", "Standalone", "ResourcePack"}, f"{key}: invalid loader")
            require(safe_text(scope.get("sourceBuildTarget")) and safe_text(scope.get("descriptorRange")), f"{key}: declared compatibility required")
            require(scope.get("sources") and all(s in sources for s in scope["sources"]), f"{key}: compatibility sources required")
        if entry["recommendedAction"] == "DENY":
            require(entry["confidence"] == "HIGH", f"{key}: DENY needs HIGH confidence")
            require(entry.get("category") in {"CHEAT_CLIENT", "CHEAT_ADDON", "XRAY"}, f"{key}: inappropriate default DENY category")
    pending_keys = set()
    for entry in data.get("pending", []):
        require(entry.get("key") not in seen_keys | pending_keys, "duplicate pending key")
        pending_keys.add(entry["key"])
        require(entry.get("status") == "PENDING" and entry.get("exactIds") == [], "pending entries must not invent IDs")
        require(entry.get("recommendedAction") == "NONE", "pending entries cannot emit enforcement rules")
        require(entry.get("type") in {"MOD", "PACK", "BRAND"} and entry.get("sources"), "pending source required")
        for source in entry["sources"]:
            require(source.get("url", "").startswith("https://") and safe_text(source.get("reason")), "pending provenance required")
    return {"entries": len(entries), "exactIds": len(seen_ids), "pending": len(pending_keys), "sources": len(sources)}


def pointer(value, selector):
    for part in selector.strip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def properties(text):
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "!")) and "=" in line:
            key, value = line.split("=", 1)
            require(key.strip() not in result, "duplicate property in source")
            result[key.strip()] = value.strip()
    return result


def verify_proof(proof, texts):
    text = texts[proof["source"]]
    for binding in proof.get("bindings", []):
        value = properties(texts[binding["source"]])[binding["key"]]
        require(ID_RE.fullmatch(value), "template identity must resolve to a literal ID")
        require(binding["token"] in text, "binding token absent from descriptor")
        text = text.replace(binding["token"], value)
    for token in proof.get("jsonBareTokens", []):
        # Only stand-alone JSON values are replaced, never strings or executable expressions.
        text, count = re.subn(r"(:\s*)" + re.escape(token) + r"(?=\s*[,}])", r"\1null", text)
        require(count > 0, "declared JSON template token absent")
    parsed = json.loads(text) if proof["format"] == "json" else tomllib.loads(text)
    require(pointer(parsed, proof["selector"]) == proof["id"], f"descriptor mismatch: {proof['id']}")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CatalogError("redirect refused; review and pin the new source explicitly")


def verify_sources(data, cache, offline=False):
    validate(data)
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    def read(item):
        key, source = item
        destination = cache / (source["sha256"] + ".txt")
        if destination.exists():
            content = destination.read_bytes()
        else:
            require(not offline, f"missing cached source: {key}")
            request = urllib.request.Request(source["url"], headers={"User-Agent": "QiZhangVerdict-IdentifierCatalog/1"})
            with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
                content = response.read(MAX_SOURCE_BYTES + 1)
            require(len(content) <= MAX_SOURCE_BYTES, f"source exceeds size limit: {key}")
            require(hashlib.sha256(content).hexdigest() == source["sha256"], f"SHA256 mismatch: {key}")
            try:
                with destination.open("xb") as stream:
                    stream.write(content)
            except FileExistsError:
                require(destination.read_bytes() == content, "cache changed concurrently")
        require(len(content) <= MAX_SOURCE_BYTES and hashlib.sha256(content).hexdigest() == source["sha256"], f"cached SHA256 mismatch: {key}")
        return key, content.decode("utf-8-sig")
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        texts = dict(pool.map(read, data["sources"].items()))
    proofs = [proof for entry in data["entries"] for proof in entry["identifierProofs"]]
    for proof in proofs:
        verify_proof(proof, texts)
    return {"verifiedSources": len(texts), "verifiedDescriptorProofs": len(proofs), "offline": offline}


def rule_rows(data):
    validate(data)
    result = []
    for entry in data["entries"]:
        kind = "automation" if entry["category"] == "AUTOMATION" else entry["type"].lower()
        for identifier in entry["exactIds"]:
            proof = next(p for p in entry["identifierProofs"] if p["id"] == identifier)
            result.append((kind, identifier, entry["recommendedAction"], data["sources"][proof["source"]]["url"]))
    return sorted(result, key=lambda row: row[:2])


def exclusive_text(path, text):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def export(data, path, format_name):
    if format_name == "blacklist":
        text = "# Reviewed extension candidates; exact IDs only. No server files are modified.\n"
        text += "\n".join("\t".join(row) for row in rule_rows(data)) + "\n"
    else:
        rows = ["type\texactId\taction\tcanonicalName\tloaders\tsourceBuildTargets\tdescriptorSource"]
        for entry in sorted(data["entries"], key=lambda x: x["key"]):
            for identifier in entry["exactIds"]:
                proof = next(p for p in entry["identifierProofs"] if p["id"] == identifier)
                rows.append("\t".join([entry["type"], identifier, entry["recommendedAction"], entry["canonicalName"],
                    ",".join(sorted({s["loader"] for s in entry["compatibility"]})),
                    ",".join(sorted({s["sourceBuildTarget"] for s in entry["compatibility"]})),
                    data["sources"][proof["source"]]["url"]]))
        text = "\n".join(rows) + "\n"
    exclusive_text(path, text)


def java_trim(text):
    """String.trim() removes <= U+0020, unlike Python's Unicode whitespace strip()."""
    return re.sub(r"^[\x00-\x20]+|[\x00-\x20]+$", "", text)


def rule_key(kind, identifier):
    kind, identifier = java_trim(kind).lower(), java_trim(identifier).lower()
    return ("mod" if kind == "automation" else kind, identifier)


def valid_rule_url(source):
    # Conservative subset of java.net.URI with a non-null host, matching core's scheme checks.
    if not source.startswith(("https://", "http://")) or re.search(r'[\x00-\x20\x7f-\x9f<>"{}|\\^`]', source):
        return False
    if re.search(r"%(?![0-9a-fA-F]{2})", source):
        return False
    try:
        parsed = urllib.parse.urlsplit(source)
        host = parsed.hostname
        if not host or parsed.scheme not in {"http", "https"}:
            return False
        _ = parsed.port  # Reject invalid/non-numeric ports and malformed IPv6 authority.
        if ":" in host:
            ipaddress.IPv6Address(host)
        elif not all(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label) for label in host.rstrip(".").split(".")):
            return False
        return True
    except ValueError:
        return False


def parse_rules(text):
    require(len(text.encode("utf-8")) <= MAX_RULE_BYTES, "blacklist exceeds 4 MiB")
    parsed = {}
    for number, line in enumerate(text.splitlines(), 1):
        if not java_trim(line) or java_trim(line).startswith("#"):
            continue
        fields = line.split("\t")
        require(len(fields) == 4, f"line {number}: expected four TSV columns")
        original_kind, original_identifier, original_action, source = fields
        kind, identifier = java_trim(original_kind).lower(), java_trim(original_identifier).lower()
        action = java_trim(original_action).upper()
        require(kind in KINDS and action in {"OFF", "ALERT", "DENY"}, f"line {number}: invalid rule")
        require(identifier and len(identifier.encode("utf-8")) <= 256 and not any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in identifier), f"line {number}: invalid/oversized value")
        if kind in {"mod", "automation"}:
            require(re.fullmatch(r"[a-z0-9_.-]{1,128}", identifier), f"line {number}: invalid mod identifier")
        require(valid_rule_url(source), f"line {number}: invalid source URL")
        key = rule_key(kind, identifier)
        require(key not in parsed, f"line {number}: duplicate/conflicting existing key {key}")
        parsed[key] = tuple(fields)
        require(len(parsed) <= MAX_RULE_COUNT, "too many blacklist entries")
    return parsed


def merge(data, existing, output, report, selections):
    # No implicit full merge: only administrator-selected keys may be introduced.
    require(selections, "select additions explicitly with --add kind:exactid")
    source_path, output_path, report_path = map(lambda p: Path(p).resolve(), (existing, output, report))
    require(len({source_path, output_path, report_path}) == 3, "input, candidate and report paths must differ")
    require(not output_path.exists() and not report_path.exists(), "refusing to overwrite an existing output/report")
    original = source_path.read_text(encoding="utf-8-sig")
    current = parse_rules(original)
    available = {rule_key(row[0], row[1]): row for row in rule_rows(data)}
    added, conflicts, unchanged = [], [], []
    selected_keys = set()
    for selection in sorted(set(selections)):
        require(":" in selection, "selection must be kind:exactid")
        kind, identifier = selection.split(":", 1)
        require(java_trim(kind).lower() in KINDS, "unknown selected rule kind")
        key = rule_key(kind, identifier)
        require(key in available, f"unknown selected catalog rule: {selection}")
        if key in selected_keys:
            continue
        selected_keys.add(key)
        proposed = available[key]
        if key in current:
            if current[key][2:] != proposed[2:]:
                conflicts.append({"key": selection, "kept": list(current[key]), "catalogSuggestion": list(proposed)})
            else:
                unchanged.append(selection)
        else:
            added.append(proposed)
    candidate = original.rstrip("\r\n") + "\n"
    if added:
        candidate += "# Explicitly selected catalog additions; existing administrator rules preserved.\n"
        candidate += "\n".join("\t".join(row) for row in added) + "\n"
    parse_rules(candidate)  # Recheck combined size/count and normalized key uniqueness before any output.
    details = {"existing": str(source_path), "candidate": str(output_path), "inputSHA256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
               "selected": sorted(set(selections)), "added": [list(row) for row in added], "conflictsPreservingAdministratorRule": conflicts,
               "unchanged": unchanged, "serverFilesModified": False}
    exclusive_text(output_path, candidate)
    exclusive_text(report_path, json.dumps(details, ensure_ascii=False, indent=2) + "\n")
    return details


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    verify = sub.add_parser("verify-sources")
    verify.add_argument("--cache", required=True, type=Path)
    verify.add_argument("--offline", action="store_true")
    ex = sub.add_parser("export")
    ex.add_argument("--cache", required=True, type=Path, help="verified source cache; export is offline")
    ex.add_argument("--format", choices=("blacklist", "catalog"), default="blacklist")
    ex.add_argument("--output", required=True, type=Path)
    merge_parser = sub.add_parser("merge")
    merge_parser.add_argument("--cache", required=True, type=Path)
    merge_parser.add_argument("--existing", required=True, type=Path)
    merge_parser.add_argument("--output", required=True, type=Path)
    merge_parser.add_argument("--report", required=True, type=Path)
    merge_parser.add_argument("--add", action="append", required=True)
    args = parser.parse_args()
    try:
        data = load_json(args.catalog)
        result = validate(data)
        if args.command == "verify-sources":
            result.update(verify_sources(data, args.cache, args.offline))
        elif args.command == "export":
            result.update(verify_sources(data, args.cache, offline=True))
            export(data, args.output, args.format)
            result["output"] = str(args.output)
        elif args.command == "merge":
            verify_sources(data, args.cache, offline=True)
            result = merge(data, args.existing, args.output, args.report, args.add)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"catalog: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
