#!/usr/bin/env python3
"""seal_check -- SEAL-004 evidence seal generator + independent validator.

SEAL-004 supersedes SEAL-003 because analyze_s1.py was omitted.  The
completeness rule is now DYNAMIC: seal_check recursively enumerates every
regular file under the run root and FAILS unless that exact relative-path
set equals the run-root entries in evidence-seal.yaml (missing/extra paths
reported).  closure-hashes.txt is NOT used as the completeness oracle.

Authority layers:
  A01_RAW_EXECUTION  : run-root execution/input-generation files (raw CSVs,
                       stdout/stderr, inputs, manifest, closure-hashes,
                       gen_inputs.py, run_all.sh, logs-tmp-gen.txt)
  A01_HISTORICAL     : A01 analysis.json/md + analyze_s1.py (analysis-
                       generation provenance) + A01 ack/receipt/REVIEW/logs
  A02_CORRECTED      : analysis-corrected.json/md + gen/verify + A02 ack/logs
  SEAL002_HISTORICAL : SEAL-002 accepted seal files
  SEAL003_HISTORICAL : SEAL-003 delivered seal files
Read-only on all sealed sources; writes only this attempts/A01/ directory.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

REPO = pathlib.Path('/home/howard/JoSIM')
ROOT = REPO / 'test/final/bvm/runs/bvm-s1-canonical-20260817-01'
TASK = REPO / 'research/tasks/JH-20260817-BVM-S1-002'
SEAL2 = REPO / 'research/tasks/JH-20260817-BVM-S1-SEAL-002'
SEAL3 = REPO / 'research/tasks/JH-20260817-BVM-S1-SEAL-003'
OUT = pathlib.Path(__file__).parent / 'evidence-seal.yaml'

CASES = ['init_positive_read', 'init_positive_control',
         'init_negative_read', 'init_negative_control']
STEPS = ['0.05ps', '0.025ps', '0.0125ps']

RUN_ROOT_A01_RAW = {'gen_inputs.py', 'run_all.sh', 'manifest.yaml',
                    'closure-hashes.txt', 'logs-tmp-gen.txt'}
RUN_ROOT_A01_HIST = {'analysis.json', 'analysis.md', 'analyze_s1.py'}
RUN_ROOT_A02 = {'analysis-corrected.json', 'analysis-corrected.md',
                'gen_analysis_corrected.py', 'verify_analysis_corrected.py'}


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def live_run_root() -> set[str]:
    """RECURSIVE enumeration of every regular file under the run root."""
    out = set()
    for p in ROOT.rglob('*'):
        if p.is_file():
            out.add(p.relative_to(ROOT).as_posix())
    return out


def entries() -> dict[str, str]:
    e: dict[str, str] = {}
    for case in CASES:
        for step in STEPS:
            d = ROOT / 'raw' / case / step
            e[f'raw/{case}/{step}/run-01.csv'] = 'A01_RAW_EXECUTION'
            e[f'raw/{case}/{step}/stdout.txt'] = 'A01_RAW_EXECUTION'
            e[f'raw/{case}/{step}/stderr.txt'] = 'A01_RAW_EXECUTION'
    for f in sorted((ROOT / 'inputs').glob('*.cir')):
        e[f'inputs/{f.name}'] = 'A01_RAW_EXECUTION'
    for f in sorted(RUN_ROOT_A01_RAW):
        e[f] = 'A01_RAW_EXECUTION'
    for f in sorted(RUN_ROOT_A01_HIST):
        e[f] = 'A01_HISTORICAL'
    for f in sorted(RUN_ROOT_A02):
        e[f] = 'A02_CORRECTED'
    for f in sorted((TASK / 'attempts/A01').rglob('*')):
        if f.is_file():
            e[f'research/tasks/JH-20260817-BVM-S1-002/attempts/A01/{f.relative_to(TASK / "attempts/A01")}'] = \
                'A01_HISTORICAL'
    for f in sorted((TASK / 'attempts/A02').rglob('*')):
        if f.is_file():
            e[f'research/tasks/JH-20260817-BVM-S1-002/attempts/A02/{f.relative_to(TASK / "attempts/A02")}'] = \
                'A02_CORRECTED'
    for f in sorted((SEAL2 / 'attempts/A01').rglob('*')):
        if f.is_file():
            e[f'research/tasks/JH-20260817-BVM-S1-SEAL-002/attempts/A01/{f.relative_to(SEAL2 / "attempts/A01")}'] = \
                'SEAL002_HISTORICAL'
    for f in sorted((SEAL3 / 'attempts/A01').rglob('*')):
        if f.is_file():
            e[f'research/tasks/JH-20260817-BVM-S1-SEAL-003/attempts/A01/{f.relative_to(SEAL3 / "attempts/A01")}'] = \
                'SEAL003_HISTORICAL'
    return e


def resolve(rel: str) -> pathlib.Path:
    if rel.startswith('raw/') or rel.startswith('inputs/') or rel in (
            RUN_ROOT_A01_RAW | RUN_ROOT_A01_HIST | RUN_ROOT_A02):
        return ROOT / rel
    return REPO / rel


def main() -> None:
    live = live_run_root()
    ent = entries()
    run_root_entries = {rel for rel in ent if resolve(rel).is_relative_to(ROOT)}
    missing = sorted(live - run_root_entries)
    extra = sorted(run_root_entries - live)
    if missing or extra:
        print(f'FAIL: run-root coverage mismatch — live {len(live)}, '
              f'sealed {len(run_root_entries)}')
        if missing:
            print('  MISSING from seal (live but not sealed):')
            for m in missing:
                print(f'    {m}')
        if extra:
            print('  EXTRA in seal (not live):')
            for x in extra:
                print(f'    {x}')
        sys.exit(1)
    print(f'run-root completeness: {len(live)} live == {len(run_root_entries)} '
          f'sealed (dynamic enumeration; closure-hashes NOT the oracle)')

    hashes = {}
    missing_files = []
    for rel in ent:
        p = resolve(rel)
        if not p.is_file():
            missing_files.append(rel)
            continue
        hashes[rel] = sha(p)
    if missing_files:
        print('MISSING FILES:', *missing_files, sep='\n  ')
        sys.exit(1)

    # closure cross-check (integrity only, NOT completeness)
    ch_lines = [l.split('  ', 1) for l in (ROOT / 'closure-hashes.txt')
                .read_text().splitlines()]
    ch = {p.strip(): h for h, p in ch_lines}
    cross_fail = []
    for rel, h in hashes.items():
        if rel in ch and ch[rel] != h:
            cross_fail.append(f'{rel}: seal {h[:12]} != closure {ch[rel][:12]}')
    if cross_fail:
        print('CROSS-CHECK FAIL (closure-hashes.txt):', *cross_fail, sep='\n  ')
        sys.exit(1)

    lines = [
        '# SEAL-004 evidence seal for JH-20260817-BVM-S1-002 (supersedes',
        '# SEAL-003: adds analyze_s1.py as A01_HISTORICAL analysis-generation',
        '# provenance; generated by seal_check.py with DYNAMIC recursive',
        '# run-root coverage; no JoSIM run; no S1/SEAL file modified).',
        '# Authority layers:',
        '#   A01_RAW_EXECUTION  - run-root execution/input-generation files',
        '#                       (raw, stdout/stderr, inputs, manifest,',
        '#                       closure-hashes, gen_inputs, run_all,',
        '#                       logs-tmp-gen.txt)',
        '#   A01_HISTORICAL     - A01 analysis.json/md + analyze_s1.py',
        '#                       (analysis-generation provenance) + A01',
        '#                       ack/receipt/REVIEW/logs',
        '#   A02_CORRECTED      - corrected analysis + generator/verifier + A02',
        '#   SEAL002_HISTORICAL - SEAL-002 accepted seal files',
        '#   SEAL003_HISTORICAL - SEAL-003 delivered seal files',
        'entries:',
    ]
    for rel in sorted(ent):
        lines.append(f'  - {{path: {rel}, sha256: "{hashes[rel]}", authority: {ent[rel]}}}')
    OUT.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    import yaml
    back = yaml.safe_load(OUT.read_text())
    n = len(back['entries'])
    fails = []
    for it in back['entries']:
        p = resolve(it['path'])
        if not p.is_file():
            fails.append(f'{it["path"]}: missing after write')
            continue
        if sha(p) != it['sha256']:
            fails.append(f'{it["path"]}: hash mismatch after write')
        if it['authority'] not in ('A01_RAW_EXECUTION', 'A01_HISTORICAL',
                                   'A02_CORRECTED', 'SEAL002_HISTORICAL',
                                   'SEAL003_HISTORICAL'):
            fails.append(f'{it["path"]}: bad authority {it["authority"]}')
    if fails:
        print('POST-WRITE VALIDATION FAIL:', *fails, sep='\n  ')
        sys.exit(1)
    seal_run_root = {it['path'] for it in back['entries']
                     if resolve(it['path']).is_relative_to(ROOT)}
    if seal_run_root != live:
        print('FAIL: written seal run-root set != live set '
              f'({len(seal_run_root)} vs {len(live)})')
        sys.exit(1)
    counts = {a: sum(1 for i in back['entries'] if i['authority'] == a)
              for a in ('A01_RAW_EXECUTION', 'A01_HISTORICAL', 'A02_CORRECTED',
                        'SEAL002_HISTORICAL', 'SEAL003_HISTORICAL')}
    print(f'SEAL OK: {n} entries {counts}; run-root {len(live)}/dynamic OK; '
          f'closure integrity {len(ch)} OK; analyze_s1.py tagged '
          f'A01_HISTORICAL; post-write OK')


if __name__ == '__main__':
    main()
