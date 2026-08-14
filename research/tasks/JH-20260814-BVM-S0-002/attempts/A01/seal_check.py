#!/usr/bin/env python3
"""seal_check -- independent verification of evidence-seal.yaml (S0-002 A01).

Verifies per AC2:
  - exact case x timestep identifier set (4 cases x 3 steps = 12),
  - per-category counts (12 CSV / 12 stdout / 12 stderr / 14 inputs /
    4 root artifacts / 5 predecessor),
  - path-set equality between the seal and disk (no missing, no added),
  - every listed SHA-256 against disk.

Fails (exit 1) on any missing, added, or hash-mismatched evidence item.
Pure stdlib; never executes JoSIM and never modifies files.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys
import yaml  # type: ignore

REPO = pathlib.Path('/home/howard/JoSIM')
SEAL = pathlib.Path(__file__).resolve().parent / 'evidence-seal.yaml'

CASES = ('init_positive_read', 'init_positive_control',
         'init_negative_read', 'init_negative_control')
STEPS = ('0.1ps', '0.05ps', '0.025ps')
EXPECT_COUNTS = {'raw_csv': 12, 'stdout': 12, 'stderr': 12,
                 'inputs': 14, 'root_artifacts': 4, 'predecessor': 5}


def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    errors: list[str] = []
    seal = yaml.safe_load(SEAL.read_text(encoding='utf-8'))

    # 1) identifier set: derive from raw_csv paths
    ids = set()
    for item in seal['raw_csv']:
        parts = pathlib.PurePosixPath(item['path']).parts
        # .../raw/<case>/<step>/run-01.csv
        ids.add((parts[-3], parts[-2]))
    expected_ids = {(c, s) for c in CASES for s in STEPS}
    if ids != expected_ids:
        errors.append(f'case x step set mismatch: got {len(ids)}, '
                      f'expected {len(expected_ids)}')
        errors.append(f'  missing: {sorted(expected_ids - ids)}')
        errors.append(f'  extra:   {sorted(ids - expected_ids)}')

    # 2) counts
    for key, exp in EXPECT_COUNTS.items():
        got = len(seal[key])
        if got != exp:
            errors.append(f'count {key}: seal has {got}, expected {exp}')

    # 3) path-set equality with disk + hashes
    for key in ('raw_csv', 'stdout', 'stderr', 'inputs',
                'root_artifacts', 'predecessor'):
        for item in seal[key]:
            p = REPO / item['path']
            if not p.is_file():
                errors.append(f'missing on disk: {item["path"]}')
                continue
            live = sha256_of(p)
            if live != item['sha256']:
                errors.append(f'hash mismatch: {item["path"]}')

    # 4) no extra files on disk inside the evidence package roots
    raw_root = REPO / 'test/final/bvm/runs/bvm-s0-canonical-20260814-01/raw'
    sealed_raw = {i['path'] for i in seal['raw_csv'] + seal['stdout'] + seal['stderr']}
    for p in raw_root.rglob('*'):
        if p.is_file():
            rel = p.relative_to(REPO).as_posix()
            if rel not in sealed_raw:
                errors.append(f'unsealed file in raw root: {rel}')
    inp_root = REPO / 'test/final/bvm/runs/bvm-s0-canonical-20260814-01/inputs'
    sealed_inp = {i['path'] for i in seal['inputs']}
    for p in inp_root.iterdir():
        rel = p.relative_to(REPO).as_posix()
        if rel not in sealed_inp:
            errors.append(f'unsealed file in inputs root: {rel}')

    if errors:
        print('SEAL CHECK FAILED:')
        for e in errors:
            print('  -', e)
        return 1
    print('SEAL CHECK PASSED: evidence-seal.yaml matches disk '
          f'({sum(len(seal[k]) for k in EXPECT_COUNTS)} entries, '
          'no missing/added/hash-mismatched items)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
