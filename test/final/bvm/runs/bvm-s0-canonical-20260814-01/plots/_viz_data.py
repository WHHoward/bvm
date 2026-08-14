#!/usr/bin/env python3
"""_viz_data -- shared visualization data preparation for BVM-S0 generators.

Single source of truth for reading the frozen raw CSVs into generator data
with an EXPLICIT unit schema, so no consumer has to guess whether a time
column is seconds or picoseconds.

Schema (see README-figure-index.md "Legend / conventions"):
  load_dataset(case, step) -> {
      't_s':  list[float]  seconds  (CSV actual time axis, raw)
      't_ps': list[float]  picoseconds (t_s * 1e12; the ONLY time axis the
                                        interactive HTML may consume)
      'c':   {key: list[float]}  raw values, keyed by COL_MAP names
  }

All unit/data-integrity assertions live here so every generator gets them:
  - t_ps in [0, 180], covers the 170 ps window;
  - each registered window contains samples;
  - column lengths all equal len(t_ps);
  - no NaN/Inf anywhere;
  - waveform visibility smoke: source V(SL1) and I(L_SL) are not flat lines
    in the source window (max-min > 0).

These are visualization-data integrity checks, NOT scientific acceptance
criteria.  No JoSIM run; raw CSVs are never modified.
"""
from __future__ import annotations

import csv
import math
import pathlib

REPO = pathlib.Path('/home/howard/JoSIM')
RUN = REPO / 'test/final/bvm/runs/bvm-s0-canonical-20260814-01'

COL_MAP = {
    'I_WL1': 'I(I_WL1)', 'I_SE1': 'I(I_SE1)',
    'P_JM1': 'P(B_JM1|XBVM1)', 'P_JM2': 'P(B_JM2|XBVM1)',
    'V_JM1': 'V(B_JM1|XBVM1)', 'V_JM2': 'V(B_JM2|XBVM1)',
    'V_SL1': 'V(SL1)', 'I_LSL': 'I(L_SL|XBVM1)',
}
# registered windows in ps (half-open) for sample-presence checks
WINDOWS_PS = {'pre': (80, 90), 'activity': (94, 108),
              'source': (94, 130), 'post': (140, 150)}


def load_dataset(case: str, step: str) -> dict:
    """Read one frozen raw CSV with explicit unit schema + integrity checks."""
    path = RUN / 'raw' / case / step / 'run-01.csv'
    with open(path, encoding='utf-8') as f:
        rows = list(csv.reader(f))
    hdr = [h.strip().strip('"') for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    t_s: list[float] = []
    t_ps: list[float] = []
    cols: dict[str, list[float]] = {k: [] for k in COL_MAP}
    for r in rows[1:]:
        ts = float(r[0])
        t_s.append(round(ts, 15))
        t_ps.append(round(ts * 1e12, 9))
        for key, col in COL_MAP.items():
            cols[key].append(round(float(r[idx[col]]), 9))

    # ---- P2 unit sanity checks (visualization-data integrity only) ----
    assert t_ps and min(t_ps) >= 0, f'{case}/{step}: t_ps below 0'
    assert max(t_ps) <= 180, f'{case}/{step}: t_ps exceeds 180 ps'
    assert 160 <= max(t_ps) <= 180, (
        f'{case}/{step}: simulation end {max(t_ps):.1f} ps not in [160,180]')
    for wname, (lo, hi) in WINDOWS_PS.items():
        assert any(lo <= t < hi for t in t_ps), (
            f'{case}/{step}: no samples in {wname} window [{lo},{hi}) ps')
    n = len(t_ps)
    for key, col in COL_MAP.items():
        assert len(cols[key]) == n, (
            f'{case}/{step}: {key} length {len(cols[key])} != time {n}')
        assert all(math.isfinite(v) for v in cols[key]), (
            f'{case}/{step}: non-finite value in {key}')
    # waveform visibility smoke: source window not flat
    src = [(t, cols['V_SL1'][i]) for i, t in enumerate(t_ps)
           if WINDOWS_PS['source'][0] <= t < WINDOWS_PS['source'][1]]
    assert max(v for _, v in src) - min(v for _, v in src) > 0, (
        f'{case}/{step}: V(SL1) flat in source window (broken mapping)')
    srci = [(t, cols['I_LSL'][i]) for i, t in enumerate(t_ps)
            if WINDOWS_PS['source'][0] <= t < WINDOWS_PS['source'][1]]
    assert max(v for _, v in srci) - min(v for _, v in srci) > 0, (
        f'{case}/{step}: I(L_SL) flat in source window (broken mapping)')

    return {'t_s': t_s, 't_ps': t_ps, 'c': cols}


def load_all_datasets(cases, steps) -> dict:
    """Load every case x step dataset, keyed '<case>/<step>'."""
    out = {}
    for case in cases:
        for step in steps:
            out[f'{case}/{step}'] = load_dataset(case, step)
    return out
