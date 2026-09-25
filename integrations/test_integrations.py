"""Security regression tests for staging, hashes and filenames; no network."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import sys

sys.dont_write_bytecode = True
import manage_integrations as target


class IntegrationTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows junction case")
    def test_junction_ancestor_cannot_redirect_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "existing-server"
            real.mkdir()
            sentinel = real / "server.properties"
            sentinel.write_text("keep", encoding="utf-8")
            link = root / "redirect"
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(real)],
                                    capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode:
                self.skipTest("Junction creation unavailable")
            with self.assertRaises(ValueError):
                target.fresh_directory(link / "new-stage")
            self.assertEqual([sentinel], list(real.iterdir()))
            self.assertEqual("keep", sentinel.read_text(encoding="utf-8"))

    def test_existing_server_is_never_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            sentinel = path / "server.properties"
            sentinel.write_text("sentinel", encoding="utf-8")
            with self.assertRaises(ValueError):
                target.fresh_directory(path)
            self.assertEqual("sentinel", sentinel.read_text(encoding="utf-8"))
            self.assertEqual([sentinel], list(path.iterdir()))

    def test_staging_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "new"
            target.fresh_directory(path)
            with self.assertRaises(ValueError):
                target.fresh_directory(path)

    def test_hostile_file_names(self):
        for name in ("../evil.jar", "C:evil.jar", "../mods/evil.jar", "..\\evil.jar", "/evil.jar", "good.jar:stream", "good.jar/extra"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                target.leaf(name)

    def test_tampering_and_missing_hash_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.jar"
            path.write_bytes(b"good")
            info = {"size": 4, "hashes": {name: hashlib.new(name, b"good").hexdigest() for name in ("sha256", "sha512")}}
            target.verify(path, info)
            path.write_bytes(b"evil")
            with self.assertRaises(ValueError):
                target.verify(path, info)
            path.write_bytes(b"good")
            del info["hashes"]["sha256"]
            with self.assertRaises(ValueError):
                target.verify(path, info)

    def test_symlink_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real"
            real.mkdir()
            link = root / "link"
            try:
                link.symlink_to(real, target_is_directory=True)
            except OSError:
                self.skipTest("Symlink creation unavailable")
            with self.assertRaises(ValueError):
                target.fresh_directory(link / "child")
            self.assertEqual([], list(real.iterdir()))


if __name__ == "__main__":
    unittest.main()
