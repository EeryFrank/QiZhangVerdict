"""Offline, standard-library regression tests for catalog and administrator-rule safety."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

import catalog_tool as tool


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = tool.load_json(tool.DEFAULT_CATALOG)

    def setUp(self):
        self.data = copy.deepcopy(self.catalog)
        root = os.environ.get("QV_CATALOG_TEST_TEMP")
        if root:
            Path(root).mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="qzverdict-catalog-", dir=root)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def entry(self, key):
        return next(e for e in self.data["entries"] if e["key"] == key)

    def test_reviewed_catalog(self):
        result = tool.validate(self.data)
        self.assertEqual(37, result["exactIds"])
        self.assertEqual(51, sum(len(e["identifierProofs"]) for e in self.data["entries"]))

    def test_duplicate_conflicting_identity_rejected(self):
        duplicate = copy.deepcopy(self.entry("meteor-client"))
        duplicate["key"] = "conflicting-copy"
        duplicate["recommendedAction"] = "ALERT"
        self.data["entries"].append(duplicate)
        with self.assertRaisesRegex(tool.CatalogError, "duplicate/conflicting identity"):
            tool.validate(self.data)

    def test_deny_without_identifier_proof_rejected(self):
        self.entry("meteor-client")["identifierProofs"] = []
        with self.assertRaisesRegex(tool.CatalogError, "every ID"):
            tool.validate(self.data)

    def test_deny_without_purpose_rejected(self):
        self.entry("meteor-client")["purpose"]["sources"] = []
        with self.assertRaisesRegex(tool.CatalogError, "purpose evidence"):
            tool.validate(self.data)

    def test_unknown_source_rejected(self):
        self.entry("meteor-client")["identifierProofs"][0]["source"] = "nonexistent"
        with self.assertRaisesRegex(tool.CatalogError, "missing descriptor source"):
            tool.validate(self.data)

    def test_unpinned_source_rejected(self):
        next(iter(self.data["sources"].values()))["revision"] = "main"
        with self.assertRaisesRegex(tool.CatalogError, "full commit"):
            tool.validate(self.data)

    def test_ambiguous_and_automation_ids_cannot_default_deny(self):
        for key in ("keystrokesmod", "baritone"):
            data = copy.deepcopy(self.catalog)
            next(e for e in data["entries"] if e["key"] == key)["recommendedAction"] = "DENY"
            with self.subTest(key=key), self.assertRaisesRegex(tool.CatalogError, "cannot default DENY"):
                tool.validate(data)

    def test_wildcard_and_tsv_injection_rejected(self):
        for identifier in ("*xray*", "meteor-client\tDENY", "XRay", "${mod_id}"):
            self.entry("meteor-client")["exactIds"] = [identifier]
            with self.subTest(identifier=identifier), self.assertRaises(tool.CatalogError):
                tool.validate(self.data)

    def test_pending_cannot_invent_id(self):
        self.data["pending"][0]["exactIds"] = ["guessed-name"]
        with self.assertRaisesRegex(tool.CatalogError, "must not invent IDs"):
            tool.validate(self.data)

    def test_source_cannot_be_a_binary(self):
        source = next(iter(self.data["sources"].values()))
        for path in ("LICENSE", "LICENSE.txt", "COPYING", "COPYING.txt"):
            source["path"] = path
            source["url"] = f"https://raw.githubusercontent.com/{source['repository']}/{source['revision']}/{path}"
            with self.subTest(allowed=path):
                tool.check_source(source)
        for path in ("client.jar", "LICENSE.jar", "COPYING.exe", "license.bin", "other.txt"):
            source["path"] = path
            source["url"] = f"https://raw.githubusercontent.com/{source['repository']}/{source['revision']}/{path}"
            with self.subTest(rejected=path), self.assertRaisesRegex(tool.CatalogError, "only text"):
                tool.check_source(source)

    def test_descriptor_value_is_checked(self):
        proof = {"source": "descriptor", "format": "json", "selector": "/id", "id": "real-id"}
        with self.assertRaisesRegex(tool.CatalogError, "descriptor mismatch"):
            tool.verify_proof(proof, {"descriptor": '{"id":"different-id"}'})

    def test_template_binding_read_without_execution(self):
        proof = {"source": "descriptor", "format": "json", "selector": "/id", "id": "lambda",
                 "bindings": [{"token": "$modId", "source": "props", "format": "properties", "key": "modId"}]}
        texts = {"descriptor": '{"id":"$modId"}', "props": "modId=lambda\n"}
        tool.verify_proof(proof, texts)
        texts["props"] = "modId=${evaluate_me}\n"
        with self.assertRaisesRegex(tool.CatalogError, "literal ID"):
            tool.verify_proof(proof, texts)

    def test_cached_hash_corruption_rejected(self):
        for source in self.data["sources"].values():
            (self.folder / (source["sha256"] + ".txt")).write_bytes(b"tampered")
        with self.assertRaisesRegex(tool.CatalogError, "cached SHA256 mismatch"):
            tool.verify_sources(self.data, self.folder, offline=True)

    def test_export_exact_only_and_deterministic(self):
        first, second = self.folder / "a.tsv", self.folder / "b.tsv"
        tool.export(self.data, first, "blacklist")
        tool.export(self.data, second, "blacklist")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        parsed = tool.parse_rules(first.read_text("utf-8"))
        self.assertIn(("mod", "xray"), parsed)
        self.assertNotIn(("mod", "antixray"), parsed)
        self.assertNotIn(("mod", "schematica"), parsed)
        self.assertNotIn(("brand", "future"), parsed)
        self.assertNotIn(("mod", "bigrat"), parsed)
        self.assertNotIn(("mod", "template"), parsed)
        for identifier in ("cheatutils", "gamesense", "nightx", "krs", "cigarette", "meteorplus"):
            self.assertEqual("DENY", parsed[("mod", identifier)][2])
        self.assertEqual("ALERT", parsed[("mod", "baritoe")][2])

    def test_export_refuses_existing_file(self):
        output = self.folder / "out.tsv"
        output.write_text("admin text", "utf-8")
        with self.assertRaises(FileExistsError):
            tool.export(self.data, output, "blacklist")
        self.assertEqual("admin text", output.read_text("utf-8"))

    def test_merge_preserves_admin_and_only_adds_explicit_selection(self):
        existing, output, report = [self.folder / name for name in ("existing.tsv", "candidate.tsv", "report.json")]
        text = "# administrator choices\nmod\tmeteor-client\tOFF\thttps://example.org/server-policy\n"
        existing.write_text(text, "utf-8")
        before = existing.read_bytes()
        result = tool.merge(self.data, existing, output, report, ["mod:meteor-client", "mod:forgehax"])
        self.assertEqual(before, existing.read_bytes())
        rows = tool.parse_rules(output.read_text("utf-8"))
        self.assertEqual({("mod", "meteor-client"), ("mod", "forgehax")}, set(rows))
        self.assertEqual(("OFF", "https://example.org/server-policy"), rows[("mod", "meteor-client")][2:])
        self.assertEqual(1, len(result["conflictsPreservingAdministratorRule"]))
        self.assertEqual(hashlib.sha256(before).hexdigest(), result["inputSHA256"])
        self.assertFalse(result["serverFilesModified"])

    def test_merge_rejects_implicit_all_existing_output_and_same_input(self):
        existing = self.folder / "existing.tsv"
        existing.write_text("# Empty administrator list\n", "utf-8")
        output, report = self.folder / "out.tsv", self.folder / "report.json"
        with self.assertRaisesRegex(tool.CatalogError, "select additions explicitly"):
            tool.merge(self.data, existing, output, report, [])
        with self.assertRaisesRegex(tool.CatalogError, "paths must differ"):
            tool.merge(self.data, existing, existing, report, ["mod:xray"])
        output.write_text("keep", "utf-8")
        with self.assertRaisesRegex(tool.CatalogError, "refusing to overwrite"):
            tool.merge(self.data, existing, output, report, ["mod:xray"])

    def test_duplicate_admin_rules_rejected(self):
        text = "mod\twurst\tOFF\thttps://example.org/a\nmod\twurst\tDENY\thttps://example.org/b\n"
        with self.assertRaisesRegex(tool.CatalogError, "duplicate/conflicting existing"):
            tool.parse_rules(text)

    def test_automation_and_mod_share_core_identity(self):
        existing, output, report = [self.folder / name for name in ("existing.tsv", "candidate.tsv", "report.json")]
        text = " MOD \t Baritone \t off \thttps://example.org/admin\n"
        existing.write_text(text, "utf-8")
        result = tool.merge(self.data, existing, output, report, [" Automation : BARITONE ", "mod:baritone"])
        self.assertEqual([], result["added"])
        self.assertEqual(1, len(result["conflictsPreservingAdministratorRule"]))
        self.assertEqual(text, existing.read_text("utf-8"))
        self.assertEqual(text, output.read_text("utf-8"))
        self.assertEqual({("mod", "baritone")}, set(tool.parse_rules(text)))

    def test_core_normalized_duplicate_rejected(self):
        text = "mod\tbaritone\tOFF\thttps://example.org/a\n AUTOMATION \t BARITONE \tALERT\thttps://example.org/b\n"
        with self.assertRaisesRegex(tool.CatalogError, "duplicate/conflicting"):
            tool.parse_rules(text)

    def test_invalid_urls_rejected(self):
        for url in ("javascript:alert(1)", "https://", " https://example.org", "https://example.org/a b", "https://bad_host.org/x", "https://example.org/%ZZ"):
            with self.subTest(url=url), self.assertRaisesRegex(tool.CatalogError, "source URL"):
                tool.parse_rules("mod\txray\tDENY\t" + url + "\n")

    def test_core_value_limits_and_control_characters(self):
        for kind, value in (("mod", "a" * 129), ("pack", "\u4e2d" * 86), ("pack", "bad\x7fvalue")):
            with self.subTest(kind=kind), self.assertRaises(tool.CatalogError):
                tool.parse_rules(f"{kind}\t{value}\tALERT\thttps://example.org\n")
        with self.assertRaisesRegex(tool.CatalogError, "4 MiB"):
            tool.parse_rules("#" + "a" * tool.MAX_RULE_BYTES)

    def test_core_rule_count_limit(self):
        text = "".join(f"mod\tm{i}\tALERT\thttps://example.org\n" for i in range(10001))
        with self.assertRaisesRegex(tool.CatalogError, "too many"):
            tool.parse_rules(text)

    def test_non_ascii_space_not_java_trimmed(self):
        # Java String.trim does not remove NBSP. Do not accept a mod key core will reject.
        with self.assertRaisesRegex(tool.CatalogError, "invalid mod identifier"):
            tool.parse_rules("mod\t\u00a0xray\tDENY\thttps://example.org\n")

    def test_duplicate_json_keys_rejected(self):
        path = self.folder / "duplicate.json"
        path.write_text('{"schemaVersion":1,"schemaVersion":2}', "utf-8")
        with self.assertRaisesRegex(tool.CatalogError, "duplicate JSON key"):
            tool.load_json(path)


if __name__ == "__main__":
    unittest.main()
