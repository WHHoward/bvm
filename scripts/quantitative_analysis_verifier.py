#!/usr/bin/env python3
"""quantitative_analysis_verifier -- independent quantitative analysis verifier.

Reads ONLY the raw CSV and the frozen analysis-spec (JSON), recomputes every
declared metric independently, and compares against the executor's structured
analysis (JSON).  NEVER imports or calls the executor analyzer.  Interpolation,
resampling and time alignment are prohibited by spec; affine endpoint
comparisons use linear-between-endpoints only.

Usage:
  python3 quantitative_analysis_verifier.py raw.csv spec.json structured.json
Exit 0 = all metrics match within declared tolerances; exit 1 otherwise.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import sys

TAU = 2 * math.pi


def load_raw(path: pathlib.Path) -> dict:
    rows = list(csv.reader(open(path, encoding='utf-8')))
    hdr = [h.strip().strip('"') for h in rows[0]]
    out = {'time': [float(r[0]) for r in rows[1:]]}
    for j, col in enumerate(hdr[1:], start=1):
        out[col] = [float(r[j]) for r in rows[1:]]
    return out


def in_win(t: float, w: tuple[float, float]) -> bool:
    lo, hi = w
    return lo * 1e-12 <= t < hi * 1e-12


def window(d: dict, col: str, w: tuple[float, float]) -> list[tuple[float, float]]:
    return [(d['time'][i], d[col][i]) for i in range(len(d['time']))
            if in_win(d['time'][i], w)]


def metric(d: dict, m: dict, wins: dict) -> float:
    col = m['column']
    w = tuple(wins[m.get('window', 'source')])
    bw = tuple(wins[m['baseline_window']]) if m.get('baseline_window') else (0, 0)
    kind = m['kind']
    if kind == 'window_mean':
        pts = window(d, col, w)
        return sum(v for _, v in pts) / len(pts)
    if kind == 'baseline_subtracted_peak':
        pts = window(d, col, bw)
        base = sum(v for _, v in pts) / len(pts)
        pts = window(d, col, w)
        pk = max(((t, v - base) for t, v in pts), key=lambda p: abs(p[1]))
        return pk[1]
    if kind == 'latency_from':
        pts = window(d, col, bw)
        base = sum(v for _, v in pts) / len(pts)
        pts = window(d, col, w)
        pk = max(((t, v - base) for t, v in pts), key=lambda p: abs(p[1]))
        return (pk[0] - m['latency_from_ps'] * 1e-12) * 1e12
    if kind == 'fwhm':
        pts = window(d, col, bw)
        base = sum(v for _, v in pts) / len(pts)
        pts = window(d, col, w)
        pk = max(((t, v - base) for t, v in pts), key=lambda p: abs(p[1]))
        half = pk[1] / 2
        cross = []
        for j in range(1, len(pts)):
            a, b = pts[j - 1], pts[j]
            if (a[1] - base - half) * (b[1] - base - half) <= 0:
                cross.append(a[0] + (b[0] - a[0]) *
                             (half + base - a[1]) / (b[1] - a[1]))
        if len(cross) < 2:
            return float('nan')
        return (max(cross) - min(cross)) * 1e12
    if kind == 'phase_area':
        sj = m['same_jj']
        pcol, vcol = sj['phase_column'], sj['voltage_column']
        wact = tuple(wins[sj['window']])
        a = window(d, pcol, wact)
        dlt = (a[-1][1] - a[0][1]) * sj['reporting_direction'] / TAU
        av = window(d, vcol, wact)
        area = sum((av[j][0] - av[j - 1][0]) * (av[j][1] + av[j - 1][1]) / 2
                   for j in range(1, len(av))) / m['integration']['phi0_wb']
        area *= sj['voltage_to_phase_sign'] * sj['reporting_direction']
        return dlt - area
    if kind == 'affine_residual':
        ae = m['affine_endpoint']
        cols = m['columns']
        lo_l, hi_l = ae['endpoint_loads']
        lo_c, hi_c = cols[str(lo_l)], cols[str(hi_l)]
        i_l = m['interior_load']
        i_c = cols[str(i_l)]
        pts_lo = window(d, lo_c, w)
        pts_hi = window(d, hi_c, w)
        pts_i = window(d, i_c, w)
        n = min(len(pts_lo), len(pts_hi), len(pts_i))
        worst = 0.0
        for j in range(n):
            a, b, x = pts_lo[j][1], pts_hi[j][1], pts_i[j][1]
            ref = a + (b - a) * (i_l - lo_l) / (hi_l - lo_l)
            worst = max(worst, abs(x - ref))
        return worst
    raise ValueError(f'unknown metric kind {kind}')


def main() -> None:
    if len(sys.argv) != 4:
        print('usage: quantitative_analysis_verifier.py raw.csv spec.json '
              'structured.json')
        sys.exit(2)
    raw_path, spec_path, struct_path = map(pathlib.Path, sys.argv[1:])
    spec = json.load(open(spec_path, encoding='utf-8'))
    structured = json.load(open(struct_path, encoding='utf-8'))

    import jsonschema
    schema = json.load(open(
        pathlib.Path(__file__).resolve().parents[1] /
        'research/schemas/quantitative-analysis-spec.schema.json'))
    jsonschema.validate(spec, schema)
    if spec.get('interpolation') != 'prohibited':
        print('FAIL: interpolation must be prohibited in spec')
        sys.exit(1)

    d = load_raw(raw_path)
    wins = spec['windows']
    fails = []
    checked = 0
    for m in spec['metrics']:
        if m['kind'] == 'phase_area':
            m = {**m, 'same_jj': spec['same_jj'],
                 'integration': spec['integration']}
        if m['kind'] == 'affine_residual':
            m = {**m, 'affine_endpoint': spec['affine_endpoint'],
                 'columns': spec['columns']}
        got = metric(d, m, wins)
        key = m['id']
        want = structured.get('metrics', {}).get(key)
        if want is None:
            fails.append(f'{key}: missing in structured analysis')
            continue
        tol = m.get('compare_tolerance', 0.0)
        if math.isnan(got):
            fails.append(f'{key}: NOT_APPLICABLE (no finite result)')
            continue
        if abs(got - want) > tol:
            fails.append(f'{key}: got {got:.6e} != structured {want:.6e} '
                         f'(tol {tol})')
        else:
            checked += 1
    if fails:
        print('VERIFIER FAIL:')
        for f in fails:
            print(f'  - {f}')
        sys.exit(1)
    print(f'VERIFIER PASS: {checked} metrics independently recomputed '
          f'from raw+spec match structured analysis')


if __name__ == '__main__':
    main()
