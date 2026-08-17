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

    def test_multiple_entries_per_role_ok(self) -> None:
        """AC5: a role may carry several entries (e.g. two raw files)."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            roles = ['raw', 'inputs', 'logs', 'manifest', 'spec', 'analyzer',
                     'verifier', 'structured_result', 'renderer', 'report',
                     'inventory', 'receipt']
            args = []
            for r in roles:
                p = td / f'{r}.bin'
                p.write_text(f'content-{r}', encoding='utf-8')
                args += [str(p), r]
            # second raw entry with distinct content
            extra = td / 'raw-extra.csv'
            extra.write_text('extra-raw', encoding='utf-8')
            args += [str(extra), 'raw']
            out = td / 'bundle.yaml'
            proc = subprocess.run(
                [sys.executable, str(BUNDLER), str(out)] + args,
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            import yaml
            entries = yaml.safe_load(out.read_text())['entries']
            raws = [e for e in entries if e['role'] == 'raw']
            self.assertEqual(len(raws), 2,
                             'two raw entries must be recorded')
            self.assertTrue(
                {e['path'] for e in raws} == {str(extra), str(td / 'raw.bin')},
                f'unexpected raw paths: {raws}')

    def test_directory_recursive_expansion(self) -> None:
        """AC5: a directory argument expands to its whole recursive file
        path-set (nested files included), one entry per file."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            rawdir = td / 'raws'
            (rawdir / 'sub').mkdir(parents=True)
            (rawdir / 'a.csv').write_text('a', encoding='utf-8')
            (rawdir / 'b.csv').write_text('b', encoding='utf-8')
            (rawdir / 'sub' / 'c.csv').write_text('c', encoding='utf-8')
            args = []
            for r in [x for x in ROLES if x != 'raw']:
                p = td / f'{r}.bin'
                p.write_text(f'content-{r}', encoding='utf-8')
                args += [str(p), r]
            args += [str(rawdir), 'raw']
            out = td / 'bundle.yaml'
            proc = subprocess.run(
                [sys.executable, str(BUNDLER), str(out)] + args,
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            import yaml
            entries = yaml.safe_load(out.read_text())['entries']
            raw_paths = {e['path'] for e in entries if e['role'] == 'raw'}
            self.assertEqual(
                raw_paths,
                {str(rawdir / 'a.csv'), str(rawdir / 'b.csv'),
                 str(rawdir / 'sub' / 'c.csv')},
                f'recursive path-set must be exact: {raw_paths}')

    def test_tampered_file_detected_mechanically(self) -> None:
        """AC5: exact SHA-256 and byte-size recomputation detects a
        tampered source file after the bundle was written."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            code, out = run_bundle(td, ROLES)
            self.assertEqual(code, 0, out)
            import yaml
            bundle = yaml.safe_load((td / 'bundle.yaml').read_text())
            target = pathlib.Path(bundle['entries'][0]['path'])
            target.write_text('tampered', encoding='utf-8')
            import hashlib
            for entry in bundle['entries']:
                p = pathlib.Path(entry['path'])
                actual_sha = hashlib.sha256(p.read_bytes()).hexdigest()
                actual_bytes = p.stat().st_size
                if p == target:
                    self.assertNotEqual(actual_sha, entry['sha256'],
                                        'tampered file must change its hash')
                    self.assertNotEqual(actual_bytes, entry['bytes'],
                                        'tampered file must change its size')
                else:
                    self.assertEqual(actual_sha, entry['sha256'],
                                     f'{p} hash must be unchanged')
                    self.assertEqual(actual_bytes, entry['bytes'],
                                     f'{p} size must be unchanged')


if __name__ == '__main__':
    unittest.main()
