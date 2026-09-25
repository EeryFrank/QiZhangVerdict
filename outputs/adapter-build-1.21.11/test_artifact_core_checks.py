# SPDX-License-Identifier: GPL-3.0-only
"""Pure Python regression checks; never compiles or launches Java."""
import os
from pathlib import Path
import tempfile
import unittest

import artifact_core_checks as checks


SOURCE = 'https://raw.githubusercontent.com/example/client/' + 'a' * 40 + '/mcmod.info'
CONTROLS = [
    'PASS control 1: ordinary and ambiguous identifiers remain allowed without bans',
    'PASS control 2: administrator OFF and API deletion survive reload and a new GuardService byte-for-byte',
    'PASS control 3: pre-existing sparse CRLF policy is never auto-expanded or normalized',
]


def transcript(rows):
    lines = [f'PASS rule {i}: {r[0]} {r[1]} {r[2]}; parser, fresh defaults, source and report'
             for i, r in enumerate(rows, 1)]
    deny = sum(row[2] == 'DENY' for row in rows)
    alert = sum(row[2] == 'ALERT' for row in rows)
    return lines + CONTROLS + [
        f'PASS: production Blacklist parser and fresh GuardService enforce {len(rows)} exact catalog rules '
        f'({deny} DENY, {alert} ALERT); 3 preservation and ordinary-ID controls passed']


class CatalogLogTests(unittest.TestCase):
    def setUp(self):
        folder = os.environ.get('QV_CATALOG_TEST_TEMP')
        if folder:
            Path(folder).mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix='artifact-catalog-', dir=folder)
        self.addCleanup(temp.cleanup)
        self.catalog = Path(temp.name) / 'catalog.tsv'
        self.rows = [('automation', 'baritone', 'ALERT', SOURCE), ('mod', 'fixture-client', 'DENY', SOURCE)]
        self.write_catalog(self.rows)
        # This literal success contract is independent of the production validator.
        self.lines = [
            'PASS rule 1: automation baritone ALERT; parser, fresh defaults, source and report',
            'PASS rule 2: mod fixture-client DENY; parser, fresh defaults, source and report',
            *CONTROLS,
            'PASS: production Blacklist parser and fresh GuardService enforce 2 exact catalog rules '
            '(1 DENY, 1 ALERT); 3 preservation and ordinary-ID controls passed',
        ]

    def write_catalog(self, rows):
        self.catalog.write_text('# reviewed catalog\n' + '\n'.join('\t'.join(r) for r in rows) + '\n', encoding='utf-8')

    def validate(self, lines):
        return checks.validate_catalog_log('\n'.join(lines) + '\n', self.catalog)

    def reject(self, lines):
        with self.assertRaises(ValueError):
            self.validate(lines)

    def test_counts_come_from_passed_tsv_not_a_fixed_version(self):
        result = self.validate(self.lines)
        self.assertEqual((2, 1, 1, 3), tuple(result[k] for k in ('rules', 'deny', 'alert', 'controls')))
        self.assertEqual(checks.sha(self.catalog), result['catalogSha256'])
        rows = [tuple(line.split('\t')) for line in (checks.ROOT/'catalog/blacklist-extension.tsv').read_text('utf-8').splitlines()
                if line and not line.startswith('#')]
        self.write_catalog(rows)
        result = self.validate(transcript(rows))
        self.assertEqual(len(rows), result['rules'])
        self.assertEqual(sum(r[2] == 'DENY' for r in rows), result['deny'])

    def test_old_37_rule_log_cannot_validate_a_39_rule_catalog(self):
        old = [('mod', 'fixture-' + str(i), 'ALERT' if i < 4 else 'DENY', SOURCE) for i in range(37)]
        self.write_catalog(old + [('mod', 'added-one', 'DENY', SOURCE), ('mod', 'added-two', 'DENY', SOURCE)])
        self.reject(transcript(old))

    def test_missing_summary_and_incidental_37_rejected(self):
        self.reject(self.lines[:-1])
        self.reject(['runner started with 37 inputs', *self.lines[:-1]])
        self.reject(['37', 'not a production success summary'])

    def test_duplicate_missing_or_out_of_order_rule_rejected(self):
        for altered in ([self.lines[0], *self.lines], self.lines[1:],
                        [self.lines[1], self.lines[0], *self.lines[2:]],
                        [self.lines[0], self.lines[0], *self.lines[2:]]):
            with self.subTest(log=altered[:2]):
                self.reject(altered)

    def test_wrong_rule_number_identity_kind_or_action_rejected(self):
        for replacement in ('PASS rule 0', 'PASS rule 01', 'PASS rule 37'):
            self.reject([self.lines[0].replace('PASS rule 1', replacement), *self.lines[1:]])
        for original, replacement in (('baritone', 'another-id'), ('automation', 'mod'), ('ALERT', 'DENY')):
            self.reject([self.lines[0].replace(original, replacement), *self.lines[1:]])

    def test_all_three_exact_controls_required_once(self):
        for index in range(2, 5):
            with self.subTest(control=index - 1):
                self.reject(self.lines[:index] + self.lines[index + 1:])
                self.reject(self.lines[:index] + [self.lines[index]] + self.lines[index:])
                changed = self.lines.copy()
                changed[index] = changed[index].split(':', 1)[0] + ': unrelated control'
                self.reject(changed)
        self.reject(self.lines[:2] + list(reversed(self.lines[2:5])) + self.lines[5:])

    def test_summary_counts_and_final_position_must_match(self):
        for old, new in (('2 exact', '37 exact'), ('1 DENY, 1 ALERT', '2 DENY, 0 ALERT'), ('3 preservation', '2 preservation')):
            self.reject(self.lines[:-1] + [self.lines[-1].replace(old, new)])
        self.reject(self.lines + [self.lines[-1]])
        self.reject(self.lines + ['later failure'])
        self.reject([self.lines[-1], *self.lines[:-1]])

    def test_crlf_and_non_result_jvm_diagnostics_allowed(self):
        log = '\r\n'.join(['JVM diagnostic before results', *self.lines, '', ''])
        self.assertEqual(2, checks.validate_catalog_log(log, self.catalog)['rules'])

    def test_invalid_or_duplicate_tsv_cannot_create_success_expectations(self):
        cases = [[], [self.rows[0], self.rows[0]],
                 [self.rows[0], ('mod', 'baritone', 'DENY', SOURCE)],
                 [('mod', 'fixture-client', 'OFF', SOURCE)],
                 [('mod', 'fixture-client', 'DENY')],
                 [('mod', 'fixture-client', 'DENY', 'https://example.org/unpinned')]]
        for rows in cases:
            with self.subTest(rows=rows):
                self.write_catalog(rows)
                self.reject(self.lines)


if __name__ == '__main__':
    unittest.main()
