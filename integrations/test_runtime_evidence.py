"""Regression: our diagnostic text must not prove third-party initialization."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
script = Path(__file__).resolve().parents[1] / "scripts/mod_runtime_smoke.py"
spec = importlib.util.spec_from_file_location("runtime_smoke_under_test", script)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class EvidenceTests(unittest.TestCase):
    def parse(self, text, loader="neoforge", grim=False):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            keys = ["antixray-" + loader] + (["grim-fabric"] if grim else [])
            (directory / "integration-receipt.json").write_text(json.dumps({"artifacts": [{"key": key} for key in keys]}), encoding="utf-8")
            console = directory / "console.log"
            console.write_text(text, encoding="utf-8")
            evidence = {"started": True, "exit_code": 0, "timed_out": False, "console_status_verified": True}
            runtime.parse_console_evidence(evidence, {"loader": loader}, directory, console)
            return evidence

    def test_presence_diagnostic_is_not_success(self):
        result = self.parse("External mod presence only: grimac=false, antixray=false\nQiZhangVerdict sessions=0\n")
        self.assertFalse(result["grim_loaded"])
        self.assertFalse(result["grim_command_framework_available"])
        self.assertFalse(result["antixray_loaded"])
        self.assertFalse(result["passed_startup_only"])

    def test_real_initialization_respects_receipt(self):
        result = self.parse("External mod presence only: grimac=false, antixray=true\nSuccessfully initialized antixray for neoforge\nQiZhangVerdict sessions=0\n")
        self.assertFalse(result["grim_loaded"])
        self.assertFalse(result["expected_integrations"]["grim"])
        self.assertTrue(result["antixray_loaded"])
        self.assertTrue(result["passed_startup_only"])

    def test_startup_banner_is_not_console_response(self):
        result = self.parse("Grim Version: 2.3.73\nSuccessfully initialized antixray for fabric\nQiZhangGuard started: QiZhangVerdict sessions=0\n", loader="fabric", grim=True)
        self.assertTrue(result["grim_loaded"])
        self.assertTrue(result["expected_integrations"]["grim"])
        self.assertFalse(result["guard_status_observed"])
        self.assertFalse(result["passed_startup_only"])


if __name__ == "__main__":
    unittest.main()
