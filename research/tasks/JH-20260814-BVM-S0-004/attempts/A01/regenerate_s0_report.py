#!/usr/bin/env python3
"""regenerate_s0_report -- deterministic corrected S0 report generator/verifier.

JH-20260814-BVM-S0-004 A01.  From the twelve frozen CSVs, using the CSV's
actual time axis and the registered windows/directions, independently
reconstructs every phase-area and pre/post platform value printed in
corrected-analysis.md, compares them with frozen analysis.json (fail nonzero
on any discrepancy, including the previously reported 0.1-ps positive/
negative read values), deterministically renders corrected-analysis.json and
corrected-analysis.md from the reconstructed data, and performs a
byte-for-byte re-render check.

Preserves numerical_status=INCONCLUSIVE and evidence_quality=INCONCLUSIVE
(frozen S0 convergence rule).  Never executes JoSIM; never modifies source
evidence.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib
import sys

REPO = pathlib.Path('/home/howard/JoSIM')
RUN = REPO / 'test/final/bvm/runs/bvm-s0-canonical-20260814-01'
FROZEN_JSON = RUN / 'analysis.json'
OUT_JSON = pathlib.Path(__file__).resolve().parent / 'corrected-analysis.json'
OUT_MD = pathlib.Path(__file__).resolve().parent / 'corrected-analysis.md'
PHI0 = 2.067833848e-15

CASES = ('init_positive_read', 'init_positive_control',
         'init_negative_read', 'init_negative_control')
STEPS = ('0.1ps', '0.05ps', '0.025ps')
P_COLS = {'JM1': 'P(B_JM1|XBVM1)', 'JM2': 'P(B_JM2|XBVM1)'}
V_COLS = {'JM1': 'V(B_JM1|XBVM1)', 'JM2': 'V(B_JM2|XBVM1)'}
PRE = (80e-12, 90e-12)
ACT = (94e-12, 108e-12)
POST = (140e-12, 150e-12)
SRC_WIN = (94e-12, 130e-12)
SRC = {'V_SL1': 'V(SL1)', 'I_LSL': 'I(L_SL|XBVM1)'}


def load(case: str, step: str):
    with open(RUN / 'raw' / case / step / 'run-01.csv', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    hdr = [h.strip().strip('"') for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    t: list[float] = []
    cols: dict[str, list[float]] = {}
    for r in rows[1:]:
        t.append(float(r[0]))
        for h in idx:
            cols.setdefault(h, []).append(float(r[idx[h]]))
    return t, cols


def win_idx(t, lo, hi):
    return [i for i, tv in enumerate(t) if lo <= tv < hi]


def trapezoid(y, t):
    if len(y) < 2:
        raise ValueError('trapezoid requires >=2 samples')
    return sum(0.5 * (y[i] + y[i + 1]) * (t[i + 1] - t[i])
               for i in range(len(y) - 1))


def main() -> int:
    errors: list[str] = []

    # ---- reconstruct from raw CSV (actual time, registered windows) ----
    recon = {}
    for c in CASES:
        recon[c] = {}
        for s in STEPS:
            t, cols = load(c, s)
            act = win_idx(t, *ACT)
            pre = win_idx(t, *PRE)
            post = win_idx(t, *POST)
            src = win_idx(t, *SRC_WIN)
            pa = {}
            for jj in ('JM1', 'JM2'):
                p = [cols[P_COLS[jj]][i] for i in act]
                v = [cols[V_COLS[jj]][i] for i in act]
                tt = [t[i] for i in act]
                pd = p[-1] - p[0]
                pa[jj] = {
                    'phase_delta_rad': pd,
                    'phase_delta_turns': pd / (2 * math.pi),
                    'area_trapezoid_vs': trapezoid(v, tt),
                    'area_turns': trapezoid(v, tt) / PHI0,
                    'residual_turns': pd / (2 * math.pi)
                    - trapezoid(v, tt) / PHI0,
                }
            plat = {
                'pre': {jj: sum(cols[P_COLS[jj]][i] for i in pre) / len(pre)
                        for jj in ('JM1', 'JM2')},
                'post': {jj: sum(cols[P_COLS[jj]][i] for i in post) / len(post)
                         for jj in ('JM1', 'JM2')},
            }
            srcw = {}
            for key, col in SRC.items():
                y = [cols[col][i] for i in src]
                tt = [t[i] for i in src]
                base = sum(y[:5]) / 5
                sub = [v - base for v in y]
                im = max(range(len(sub)), key=lambda i: abs(sub[i]))
                srcw[key] = {
                    'baseline': base,
                    'peak_baseline_subtracted': sub[im],
                    'abs_peak': abs(sub[im]),
                    'peak_time_s': tt[im],
                    'latency_from_96ps_s': tt[im] - 96e-12,
                }
            recon[c][s] = {'phase_area': pa, 'platform': plat,
                           'source': srcw}

    # ---- compare with frozen analysis.json ----
    frozen = json.loads(FROZEN_JSON.read_text(encoding='utf-8'))
    for c in CASES:
        for s in STEPS:
            for jj in ('JM1', 'JM2'):
                fpa = frozen['phase_area'][jj][f'{c}/{s}']
                rpa = recon[c][s]['phase_area'][jj]
                for k in ('phase_delta_rad', 'phase_delta_turns',
                          'area_trapezoid_vs', 'area_turns', 'residual_turns'):
                    if abs(fpa[k] - rpa[k]) > 1e-12:
                        errors.append(
                            f'{c}/{s}/{jj}/{k}: recon {rpa[k]!r} != '
                            f'frozen {fpa[k]!r}')
            for w in ('pre', 'post'):
                for jj in ('JM1', 'JM2'):
                    fv = frozen['platform'][c][s][w][jj]
                    rv = recon[c][s]['platform'][w][jj]
                    if abs(fv - rv) > 1e-12:
                        errors.append(
                            f'{c}/{s}/{w}/{jj}: recon {rv!r} != frozen {fv!r}')
            for key in ('V_SL1', 'I_LSL'):
                fo = frozen['source_port'][c][s][key]
                ro = recon[c][s]['source'][key]
                for k in ('baseline', 'peak_baseline_subtracted', 'abs_peak',
                          'peak_time_s', 'latency_from_96ps_s'):
                    if abs(fo[k] - ro[k]) > 1e-12:
                        errors.append(
                            f'{c}/{s}/{key}/{k}: recon {ro[k]!r} != '
                            f'frozen {fo[k]!r}')

    # ---- build corrected-analysis.json ----
    corrected = {
        'run': 'bvm-s0-canonical-20260814-01',
        'task': 'JH-20260814-BVM-S0-004',
        'supersedes_report': {
            'path': 'test/final/bvm/runs/bvm-s0-canonical-20260814-01/analysis.md',
            'status': 'retained_but_superseded_for_human_readable_numeric_tables'},
        'numerical_status': 'INCONCLUSIVE',
        'evidence_quality': {'conclusion': 'INCONCLUSIVE',
                             'meaning': ('source-side calibration facts under '
                                         'the fixed fixture; no receiver/Gate/'
                                         'logical conclusion')},
        'frozen_source': {
            'analysis_json': 'test/final/bvm/runs/bvm-s0-canonical-20260814-01/analysis.json',
            'raw_root': 'test/final/bvm/runs/bvm-s0-canonical-20260814-01/raw/',
            'immutable': True},
        'reconstruction_matches_frozen_json': not errors,
        'cases': recon,
        'convergence_note': ('numerical_status INCONCLUSIVE because the '
                             'preregistered 0.1-to-0.05 ps control-latency '
                             'comparison (0.85 ps) exceeds its 0.5-ps '
                             'task-local band; frozen rule, not extended.'),
    }
    OUT_JSON.write_text(json.dumps(corrected, indent=2, sort_keys=True)
                        + '\n', encoding='utf-8')

    # ---- deterministically render corrected-analysis.md ----
    # If the file already exists from a previous run, the rendered bytes must
    # match it exactly (manual edits or non-determinism are rejected).
    render_target = OUT_MD.read_text(encoding='utf-8') if OUT_MD.is_file() else None
    md_lines = []
    md_lines.append('# Corrected analysis: `bvm-s0-canonical-20260814-01`\n')
    md_lines.append('> Correction note: the predecessor '
                    '`test/final/bvm/runs/bvm-s0-canonical-20260814-01/'
                    'analysis.md` (S0-001 A01 D5) is retained as immutable '
                    'evidence but is **superseded for human-readable numeric '
                    'tables** by this report; its "Observed" tables contained '
                    'values not present in any case x timestep of '
                    '`analysis.json`/raw. This corrected report is '
                    'deterministically rendered by '
                    '`regenerate_s0_report.py` from the twelve frozen CSVs '
                    'and byte-for-byte re-render checked.\n')
    md_lines.append('## Reconstruction consistency\n')
    md_lines.append(f'- reconstruction matches frozen analysis.json: '
                    f'{corrected["reconstruction_matches_frozen_json"]}\n')
    md_lines.append(f'- numerical_status: `{corrected["numerical_status"]}` '
                    f'(frozen rule; 0.1->0.05 ps control-latency 0.85 ps > '
                    f'0.5-ps band)\n')
    md_lines.append(f'- evidence_quality: '
                    f'`{corrected["evidence_quality"]["conclusion"]}`\n')
    md_lines.append('\n## Direct-JJ phase-area `[94,108) ps` '
                    '(reconstructed from raw, actual time)\n\n')
    md_lines.append('| case | step | JJ | phase_delta_rad | phase_delta_turns '
                    '| area_turns | residual_turns |\n')
    md_lines.append('|---|---|---|---|---|---|---|\n')
    for c in CASES:
        for s in STEPS:
            for jj in ('JM1', 'JM2'):
                a = recon[c][s]['phase_area'][jj]
                md_lines.append(
                    f'| {c} | {s} | {jj} | {a["phase_delta_rad"]:.6f} | '
                    f'{a["phase_delta_turns"]:.6f} | {a["area_turns"]:.6f} | '
                    f'{a["residual_turns"]:.6f} |\n')
    md_lines.append('\n## Pre/post storage signature (JM1/JM2 P means, rad)\n\n')
    md_lines.append('| case | step | pre JM1 | post JM1 | pre JM2 | post JM2 |\n')
    md_lines.append('|---|---|---|---|---|---|\n')
    for c in CASES:
        for s in STEPS:
            p = recon[c][s]['platform']
            md_lines.append(
                f'| {c} | {s} | {p["pre"]["JM1"]:.6f} | {p["post"]["JM1"]:.6f} '
                f'| {p["pre"]["JM2"]:.6f} | {p["post"]["JM2"]:.6f} |\n')
    md_lines.append('\n## Source-port waveform `[94,130) ps` (reconstructed)\n\n')
    md_lines.append('| case | step | key | abs_peak | latency_from_96ps_s |\n')
    md_lines.append('|---|---|---|---|---|\n')
    for c in CASES:
        for s in STEPS:
            for key in ('V_SL1', 'I_LSL'):
                o = recon[c][s]['source'][key]
                md_lines.append(
                    f'| {c} | {s} | {key} | {o["abs_peak"]:.6e} | '
                    f'{o["latency_from_96ps_s"]:.6e} |\n')
    md_lines.append('\n## Controls\n')
    md_lines.append('- init_positive_control / init_negative_control: identical '
                    'netlist/model/load/timestep/stop/PWL knots; only the two '
                    'read-pulse amplitudes are zero.\n')
    md_lines.append('\n## Provenance\n')
    md_lines.append('- Raw root (frozen): '
                    '`test/final/bvm/runs/bvm-s0-canonical-20260814-01/raw/`\n')
    md_lines.append('- Frozen analysis.json: '
                    '`test/final/bvm/runs/bvm-s0-canonical-20260814-01/'
                    'analysis.json`\n')
    md_lines.append('- Generator: '
                    '`research/tasks/JH-20260814-BVM-S0-004/attempts/A01/'
                    'regenerate_s0_report.py`\n')
    md_lines.append('- Source-evidence manifest: '
                    '`research/tasks/JH-20260814-BVM-S0-004/attempts/A01/'
                    'source-evidence-manifest.sha256`\n')
    md_lines.append('- This report is deterministic output of the generator; '
                    'no manual edits.\n')
    rendered = ''.join(md_lines)
    if render_target is not None and render_target != rendered:
        errors.append('corrected-analysis.md exists and differs from '
                      'deterministic render (manual edit or '
                      'non-determinism)')
    else:
        OUT_MD.write_text(rendered, encoding='utf-8')

    # ---- byte-for-byte re-render check ----
    # re-render from corrected JSON only (deterministic), compare bytes
    rj = json.loads(OUT_JSON.read_text(encoding='utf-8'))
    rr_lines = []
    rr_lines.append(f'# Corrected analysis: `{rj["run"]}`\n')
    rr_lines.append('> Correction note: the predecessor '
                    '`test/final/bvm/runs/bvm-s0-canonical-20260814-01/'
                    'analysis.md` (S0-001 A01 D5) is retained as immutable '
                    'evidence but is **superseded for human-readable numeric '
                    'tables** by this report; its "Observed" tables contained '
                    'values not present in any case x timestep of '
                    '`analysis.json`/raw. This corrected report is '
                    'deterministically rendered by '
                    '`regenerate_s0_report.py` from the twelve frozen CSVs '
                    'and byte-for-byte re-render checked.\n')
    rr_lines.append('## Reconstruction consistency\n')
    rr_lines.append(f'- reconstruction matches frozen analysis.json: '
                    f'{rj["reconstruction_matches_frozen_json"]}\n')
    rr_lines.append(f'- numerical_status: `{rj["numerical_status"]}` '
                    f'(frozen rule; 0.1->0.05 ps control-latency 0.85 ps > '
                    f'0.5-ps band)\n')
    rr_lines.append(f'- evidence_quality: '
                    f'`{rj["evidence_quality"]["conclusion"]}`\n')
    rr_lines.append('\n## Direct-JJ phase-area `[94,108) ps` '
                    '(reconstructed from raw, actual time)\n\n')
    rr_lines.append('| case | step | JJ | phase_delta_rad | phase_delta_turns '
                    '| area_turns | residual_turns |\n')
    rr_lines.append('|---|---|---|---|---|---|---|\n')
    for c in CASES:
        for s in STEPS:
            for jj in ('JM1', 'JM2'):
                a = rj['cases'][c][s]['phase_area'][jj]
                rr_lines.append(
                    f'| {c} | {s} | {jj} | {a["phase_delta_rad"]:.6f} | '
                    f'{a["phase_delta_turns"]:.6f} | {a["area_turns"]:.6f} | '
                    f'{a["residual_turns"]:.6f} |\n')
    rr_lines.append('\n## Pre/post storage signature (JM1/JM2 P means, rad)\n\n')
    rr_lines.append('| case | step | pre JM1 | post JM1 | pre JM2 | post JM2 |\n')
    rr_lines.append('|---|---|---|---|---|---|\n')
    for c in CASES:
        for s in STEPS:
            p = rj['cases'][c][s]['platform']
            rr_lines.append(
                f'| {c} | {s} | {p["pre"]["JM1"]:.6f} | {p["post"]["JM1"]:.6f} '
                f'| {p["pre"]["JM2"]:.6f} | {p["post"]["JM2"]:.6f} |\n')
    rr_lines.append('\n## Source-port waveform `[94,130) ps` (reconstructed)\n\n')
    rr_lines.append('| case | step | key | abs_peak | latency_from_96ps_s |\n')
    rr_lines.append('|---|---|---|---|---|\n')
    for c in CASES:
        for s in STEPS:
            for key in ('V_SL1', 'I_LSL'):
                o = rj['cases'][c][s]['source'][key]
                rr_lines.append(
                    f'| {c} | {s} | {key} | {o["abs_peak"]:.6e} | '
                    f'{o["latency_from_96ps_s"]:.6e} |\n')
    rr_lines.append('\n## Controls\n')
    rr_lines.append('- init_positive_control / init_negative_control: identical '
                    'netlist/model/load/timestep/stop/PWL knots; only the two '
                    'read-pulse amplitudes are zero.\n')
    rr_lines.append('\n## Provenance\n')
    rr_lines.append('- Raw root (frozen): '
                    '`test/final/bvm/runs/bvm-s0-canonical-20260814-01/raw/`\n')
    rr_lines.append('- Frozen analysis.json: '
                    '`test/final/bvm/runs/bvm-s0-canonical-20260814-01/'
                    'analysis.json`\n')
    rr_lines.append('- Generator: '
                    '`research/tasks/JH-20260814-BVM-S0-004/attempts/A01/'
                    'regenerate_s0_report.py`\n')
    rr_lines.append('- Source-evidence manifest: '
                    '`research/tasks/JH-20260814-BVM-S0-004/attempts/A01/'
                    'source-evidence-manifest.sha256`\n')
    rr_lines.append('- This report is deterministic output of the generator; '
                    'no manual edits.\n')
    rr = ''.join(rr_lines)
    if rr != OUT_MD.read_text(encoding='utf-8'):
        errors.append('byte-for-byte re-render check FAILED')

    if errors:
        print('REGENERATE/VERIFY FAILED:')
        for e in errors:
            print('  -', e)
        return 1
    print('REGENERATE/VERIFY PASSED: corrected-analysis.json/.md rendered, '
          'reconstruction matches frozen analysis.json, byte-for-byte '
          're-render consistent')
    return 0


if __name__ == '__main__':
    sys.exit(main())
