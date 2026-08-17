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
    out = {'time': [float(r[0]) for r in rows[1:]],
           'time_str': [r[0] for r in rows[1:]]}
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
    raise ValueError(f'unknown metric kind {kind}')


def _exact_token_index(raw: dict, token_ps: float) -> int:
    """Exact-decimal timestamp lookup: the token time in seconds is
    represented as Decimal (never float equality, interpolation, or
    tolerance) and must equal one raw CSV time value exactly.  Returns the
    row index of the matching time."""
    from decimal import Decimal
    wanted = Decimal(str(token_ps)) * Decimal('1e-12')
    for idx, time_str in enumerate(raw['time_str']):
        if Decimal(time_str) == wanted:
            return idx
    raise ValueError(
        f'exact timestamp token {token_ps} ps not present in raw time axis')


def _agg(values: list[float], descriptor: str) -> float:
    if descriptor == 'max':
        return max(values)
    if descriptor == 'rms':
        return (sum(v * v for v in values) / len(values)) ** 0.5
    if descriptor == 'mean':
        return sum(values) / len(values)
    raise ValueError(f'unknown endpoint_vi descriptor {descriptor}')


def endpoint_vi(evi: dict, base_dir: pathlib.Path) -> dict:
    """Endpoint-VI affine fit from SIMULTANEOUS endpoint V/I samples.

    Every load run contributes one (I, V) value per preregistered exact
    timestamp token (same token, same raw row -> simultaneous).  For each
    token independently: Rhat(t) = (V_hi(t) - V_lo(t)) / (I_hi(t) - I_lo(t)),
    Vth(t) = V_lo(t) - Rhat(t) * I_lo(t) (signed-slope load line
    V = Vth + Rhat*I), and e_L(t) = max over loads of
    |V_l(t) - (Vth(t) + Rhat(t) * I_l(t))|.  NO pre-fit token averaging:
    the frozen descriptors (spec.endpoint_vi.descriptors, max/rms/mean)
    are applied per quantity ACROSS the per-token values afterwards.
    Timestamps are matched as exact decimals; no interpolation, resampling,
    float equality, or cross-run alignment.
    """
    raw_by_load: dict[str, dict] = {}
    for load, run in evi['runs'].items():
        raw = load_raw(base_dir / run['raw_path'])
        raw['v_col'] = run['v_column']
        raw['i_col'] = run['i_column']
        raw_by_load[load] = raw
    descriptors = evi.get('descriptors', {'rhat': 'max', 'vth': 'max',
                                          'e_L': 'rms'})
    lo, hi = str(evi['endpoint_loads'][0]), str(evi['endpoint_loads'][1])
    rhat_vals: list[float] = []
    vth_vals: list[float] = []
    e_l_vals: list[float] = []
    for token in evi['tokens_ps']:
        idx_by_load: dict[str, int] = {}
        for load, raw in raw_by_load.items():
            idx_by_load[load] = _exact_token_index(raw, token)
        def val(load: str, column: str) -> float:
            raw = raw_by_load[load]
            return raw[column][idx_by_load[load]]
        i_lo_t = val(lo, raw_by_load[lo]['i_col'])
        v_lo_t = val(lo, raw_by_load[lo]['v_col'])
        i_hi_t = val(hi, raw_by_load[hi]['i_col'])
        v_hi_t = val(hi, raw_by_load[hi]['v_col'])
        rhat_t = (v_hi_t - v_lo_t) / (i_hi_t - i_lo_t)
        vth_t = v_lo_t - rhat_t * i_lo_t
        e_l_t = max(
            abs(val(load, raw_by_load[load]['v_col'])
                - (vth_t + rhat_t * val(load, raw_by_load[load]['i_col'])))
            for load in raw_by_load)
        rhat_vals.append(rhat_t)
        vth_vals.append(vth_t)
        e_l_vals.append(e_l_t)
    result = {
        'rhat': _agg(rhat_vals, descriptors.get('rhat', 'max')),
        'vth': _agg(vth_vals, descriptors.get('vth', 'max')),
        'e_L': _agg(e_l_vals, descriptors.get('e_L', 'rms')),
        'token_count': len(e_l_vals),
    }
    return result


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
    base_dir = spec_path.resolve().parent
    for m in spec['metrics']:
        if m['kind'] == 'phase_area':
            m = {**m, 'same_jj': spec['same_jj'],
                 'integration': spec['integration']}
        if m['kind'] == 'endpoint_vi':
            got = endpoint_vi(spec['endpoint_vi'], base_dir)
        else:
            got = metric(d, m, wins)
        key = m['id']
        want = structured.get('metrics', {}).get(key)
        if want is None:
            fails.append(f'{key}: missing in structured analysis')
            continue
        tol = m.get('compare_tolerance', 0.0)
        if isinstance(got, dict):
            for field, got_value in got.items():
                want_value = want.get(field)
                if want_value is None:
                    fails.append(f'{key}.{field}: missing in structured')
                    continue
                if math.isnan(got_value) or abs(got_value - want_value) > tol:
                    fails.append(f'{key}.{field}: got {got_value:.6e} != '
                                 f'structured {want_value:.6e} (tol {tol})')
                else:
                    checked += 1
            continue
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
