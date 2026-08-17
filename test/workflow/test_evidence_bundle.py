#!/usr/bin/env python3
"""Regression tests for build_evidence_bundle (AC7).

Valid bundle: all 12 required roles present -> OK.  Missing raw, missing
log, and missing script must be rejected.  Minimal synthetic files only.
"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
BUNDLER = REPO / 'scripts/build_evidence_bundle.py'
ROLES = ['raw', 'inputs', 'logs', 'manifest', 'spec', 'analyzer', 'verifier',
         'structured_result', 'renderer', 'report', 'inventory', 'receipt']


def make_files(td: pathlib.Path, roles: list[str]) -> list[str]:
    args = []
    for r in roles:
        p = td / f'{r}.bin'
        p.write_text(f'content-{r}', encoding='utf-8')
        args += [str(p), r]
    return args


def run_bundle(td: pathlib.Path, roles: list[str]) -> tuple[int, str]:
    out = td / 'bundle.yaml'
    args = [sys.executable, str(BUNDLER), str(out)] + make_files(td, roles)
    proc = subprocess.run(args, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


class BundleTests(unittest.TestCase):
    def test_complete_bundle_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            code, out = run_bundle(pathlib.Path(td), ROLES)
            self.assertEqual(code, 0, out)

    def test_missing_raw_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            code, out = run_bundle(pathlib.Path(td),
                                   [r for r in ROLES if r != 'raw'])
            self.assertNotEqual(code, 0, 'missing raw must fail')
            self.assertIn('raw', out)

    def test_missing_log_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            code, out = run_bundle(pathlib.Path(td),
                                   [r for r in ROLES if r != 'logs'])
            self.assertNotEqual(code, 0, 'missing logs must fail')
            self.assertIn('logs', out)

    def test_missing_script_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            code, out = run_bundle(pathlib.Path(td),
                                   [r for r in ROLES if r != 'analyzer'])
            self.assertNotEqual(code, 0, 'missing analyzer must fail')
            self.assertIn('analyzer', out)


if __name__ == '__main__':
    unittest.main()
