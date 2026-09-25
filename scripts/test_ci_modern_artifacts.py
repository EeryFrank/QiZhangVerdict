# SPDX-License-Identifier: GPL-3.0-only
"""Acceptance boundary tests for exact CI delivery names and checksum collection."""
from pathlib import Path
import tempfile
import unittest

import ci_modern_artifacts as artifacts


class ModernArtifactsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='qizhang-ci-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        for target in artifacts.TARGETS:
            for path in artifacts.artifact_paths(target):
                item = self.source / path
                item.parent.mkdir(parents=True, exist_ok=True)
                item.write_bytes(('fixture:' + path).encode('ascii'))

    def staged(self, layout='gitlab'):
        folder = self.root / 'inputs'
        for target in artifacts.TARGETS:
            name = 'qizhang-ci-' + target if layout == 'github' else target
            artifacts.stage(self.source, target, folder / name)
        return folder

    def rejected(self, inputs, layout='gitlab'):
        with self.assertRaises(ValueError):
            artifacts.collect(inputs, self.root / 'out', layout)
        self.assertFalse((self.root / 'out').exists())

    def test_versions_and_exact_ten_production_paths(self):
        paths = [p for t in artifacts.TARGETS for p in artifacts.artifact_paths(t)]
        self.assertEqual(10, len(paths))
        self.assertEqual(10, len(set(paths)))
        self.assertIn('bukkit/build/libs/qizhangverdict-bukkit-0.2.1-dev.jar', paths)
        self.assertEqual(3, len(artifacts.artifact_paths('mods-1.20.4')))
        self.assertTrue(all('-sources' not in p for p in paths))

    def test_gitlab_valid_collection(self):
        inputs = self.staged()
        artifacts.collect(inputs, self.root / 'out', 'gitlab')
        self.assertEqual(10, len(list((self.root / 'out').glob('*.jar'))))

    def test_github_valid_collection(self):
        inputs = self.staged('github')
        artifacts.collect(inputs, self.root / 'out', 'github')
        self.assertEqual(10, len((self.root / 'out/SHA256SUMS').read_text().splitlines()))

    def test_missing_loader_rejected(self):
        inputs = self.staged()
        next((inputs / 'mods-1.20.4').glob('*neoforge*.jar')).unlink()
        self.rejected(inputs)

    def test_old_version_same_count_rejected(self):
        inputs = self.staged()
        jar = next((inputs / 'core-bukkit').glob('*.jar'))
        jar.rename(jar.with_name('qizhangverdict-bukkit-0.2.0-test.1.jar'))
        self.rejected(inputs)

    def test_sources_jar_rejected(self):
        inputs = self.staged()
        (inputs / 'mods-1.19.2/qizhangverdict-fabric-1.19.2-0.3.0-dev-sources.jar').write_bytes(b'extra')
        self.rejected(inputs)

    def test_legacy_folder_rejected(self):
        inputs = self.staged()
        (inputs / 'legacy-1.19.4').mkdir()
        self.rejected(inputs)

    def test_payload_change_rejected(self):
        inputs = self.staged()
        next((inputs / 'mods-1.20.1').glob('*.jar')).write_bytes(b'changed')
        self.rejected(inputs)

    def test_duplicate_checksum_rejected(self):
        inputs = self.staged()
        checksum = inputs / 'core-bukkit/SHA256SUMS'
        checksum.write_bytes(checksum.read_bytes() * 2)
        self.rejected(inputs)

    def test_missing_checksum_rejected(self):
        inputs = self.staged()
        (inputs / 'core-bukkit/SHA256SUMS').unlink()
        self.rejected(inputs)

    def test_checksum_path_traversal_rejected(self):
        inputs = self.staged()
        (inputs / 'core-bukkit/SHA256SUMS').write_text('0' * 64 + '  ../payload.jar\n')
        self.rejected(inputs)

    def test_stage_requires_exact_version_even_when_old_exists(self):
        jar = self.source / artifacts.artifact_paths('core-bukkit')[0]
        jar.rename(jar.with_name('qizhangverdict-bukkit-0.2.0-test.1.jar'))
        with self.assertRaises(ValueError):
            artifacts.stage(self.source, 'core-bukkit', self.root / 'out')
        self.assertFalse((self.root / 'out').exists())

    def test_stage_ignores_unlisted_prior_jars(self):
        jar = self.source / artifacts.artifact_paths('core-bukkit')[0]
        jar.with_name('qizhangverdict-bukkit-0.2.0-test.1.jar').write_bytes(b'old')
        artifacts.stage(self.source, 'core-bukkit', self.root / 'out')
        self.assertEqual({jar.name, 'SHA256SUMS'}, {p.name for p in (self.root / 'out').iterdir()})


if __name__ == '__main__':
    unittest.main()
