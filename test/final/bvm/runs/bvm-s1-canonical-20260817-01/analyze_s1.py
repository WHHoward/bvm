#!/usr/bin/env python3
"""analyze_s1 -- S1-002 canonical convergence analysis (frozen procedure only).

Implements the registered S1 procedure from
research/tasks/JH-20260817-BVM-S1-001/design/s1-canonical-source-convergence.md:
- readiness: pre-window [80,90) p2p <= 0.020 rad on JM1/JM2; pos/neg mean-vector
  L-infinity separation >= 0.100 rad (comparability only, never a Gate).
- ladder: 0.05->0.025->0.0125 ps; exact-decimal (string) timestamp match in
  source [94,130) ps, zero tolerance; no interpolation/resampling/alignment.
- control hierarchy: rctrl = Actrl/max(Aread, Afloor), Afloor 5 uV / 0.5 uA.
- observables: baseline-subtracted peaks, latency from 96 ps, FWHM, pointwise
  and RMS differences on exact common timestamps.
- bands: peak/pointwise <= max(Afloor, 1%*Aref); RMS <= max(0.2%*Aref,
  0.2*Afloor); latency/applicable-FWHM <= 0.25 ps; control max <= 1% of
  paired-read scale; control RMS/L1 <= 0.2%.
- platforms: pre/post means (rad + turns), activity-window endpoint deltas,
  same-JJ actual-time area (turns) + signed residual (descriptive, no band).
- verdict: CONVERGED / INCONCLUSIVE / INVALID per AC6.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).parent
RAW = ROOT / 'raw'
CASES = ['init_positive_read', 'init_positive_control',
         'init_negative_read', 'init_negative_control']
STEPS = ['0.05ps', '0.025ps', '0.0125ps']
PRE, ACT, SRC, POST = (80, 90), (94, 108), (94, 130), (140, 150)
AFL_V, AFL_I = 5e-6, 0.5e-6
FLOOR = {'V_SL1': AFL_V, 'I_LSL': AFL_I}
TAU = 2 * math.pi


def load(case: str, step: str) -> dict:
    p = RAW / case / step / 'run-01.csv'
    with open(p, encoding='utf-8') as f:
        rows = list(csv.reader(f))
    hdr = [h.strip().strip('"') for h in rows[0]]
    out = {'time': [], 'V_SL1': [], 'I_LSL': [], 'P_JM1': [], 'P_JM2': [],
           'V_JM1': [], 'V_JM2': []}
    idx = {h: i for i, h in enumerate(hdr)}
    for r in rows[1:]:
        out['time'].append(float(r[0]))
        out['V_SL1'].append(float(r[idx['V(SL1)']]))
        out['I_LSL'].append(float(r[idx['I(L_SL|XBVM1)']]))
        out['P_JM1'].append(float(r[idx['P(B_JM1|XBVM1)']]))
        out['V_JM1'].append(float(r[idx['V(B_JM1|XBVM1)']]))
        out['P_JM2'].append(float(r[idx['P(B_JM2|XBVM1)']]))
        out['V_JM2'].append(float(r[idx['V(B_JM2|XBVM1)']]))
    return out


def window(d: dict, col: str, w: tuple[float, float]) -> list[tuple[float, float]]:
    lo, hi = w
    return [(d['time'][i], d[col][i]) for i in range(len(d['time']))
            if lo * 1e-12 <= d['time'][i] < hi * 1e-12]


def tokens(d: dict, w: tuple[float, float]) -> set[str]:
    lo, hi = w
    return {f'{d["time"][i]:.6e}' for i in range(len(d['time']))
            if lo * 1e-12 <= d['time'][i] < hi * 1e-12}


def baseline_sub(d: dict, col: str, w: tuple[float, float]) -> dict:
    pts = window(d, col, w)
    m = sum(v for _, v in pts) / len(pts)
    out = {k: [x - m for x in d[k]] for k in ['time', col]}
    out['time'] = d['time']
    out[col] = [v - m for v in d[col]]
    return out


def peak_latency_fwhm(d: dict, col: str, w: tuple[float, float]) -> dict:
    lo, hi = w
    pts = [(d['time'][i], d[col][i]) for i in range(len(d['time']))
           if lo * 1e-12 <= d['time'][i] < hi * 1e-12]
    pk = max(pts, key=lambda p: abs(p[1]))
    lat = (pk[0] - 96e-12) * 1e12
    cross = []
    for j in range(1, len(pts)):
        a, b = pts[j - 1], pts[j]
        if (a[1] - pk[1] / 2) * (b[1] - pk[1] / 2) <= 0 and \
           (a[1] - pk[1] / 2) * (pk[1] - a[1]) >= 0:
            cross.append(a[0] + (b[0] - a[0]) * (pk[1] / 2 - a[1]) / (b[1] - a[1]))
    fwhm = None
    if len(cross) >= 2:
        fwhm = (max(cross) - min(cross)) * 1e12
    return {'peak': pk[1], 'abs_peak': abs(pk[1]), 't_peak_s': pk[0],
            'latency_ps': lat, 'fwhm_ps': fwhm}


def main() -> None:
    data = {case: {step: load(case, step) for step in STEPS} for case in CASES}
    res: dict = {}

    # ---- readiness (AC4) ----
    read = {}
    for step in STEPS:
        for case in CASES:
            for col in ['P_JM1', 'P_JM2']:
                pts = window(data[case][step], col, PRE)
                p2p = max(v for _, v in pts) - min(v for _, v in pts)
                read.setdefault(step, {}).setdefault(case, {})[f'{col}_p2p_rad'] = p2p
        def wmean(step, case, col):
            pts = window(data[case][step], col, PRE)
            return sum(v for _, v in pts) / len(pts)
        vp = [wmean(step, 'init_positive_read', 'P_JM1'),
              wmean(step, 'init_positive_read', 'P_JM2')]
        vn = [wmean(step, 'init_negative_read', 'P_JM1'),
              wmean(step, 'init_negative_read', 'P_JM2')]
        read[step]['Linf_sep_rad'] = max(abs(a - b) for a, b in zip(vp, vn))
    res['readiness'] = read

    # ---- exact-decimal ladder match (zero tolerance) ----
    match = {}
    for pair, (c, f) in {'05_to_025': ('0.05ps', '0.025ps'),
                         '025_to_0125': ('0.025ps', '0.0125ps')}.items():
        for case in CASES:
            coarse = tokens(data[case][c], SRC)
            fine = tokens(data[case][f], SRC)
            missing = sorted(coarse - fine)
            match.setdefault(pair, {})[case] = {
                'coarse_n': len(coarse), 'fine_n': len(fine),
                'missing_n': len(missing), 'missing_tokens': missing[:5]}
    res['exact_timestamp_match'] = match
    ts_ok = all(match[p][c]['missing_n'] == 0 for p in match for c in CASES)

    # ---- control hierarchy + read observables ----
    obs = {}
    for step in STEPS:
        for case in ['init_positive_read', 'init_negative_read']:
            for col in ['V_SL1', 'I_LSL']:
                rd = baseline_sub(data[case][step], col, PRE)
                ctrl = baseline_sub(
                    data[case.replace('read', 'control')][step], col, PRE)
                p_r = peak_latency_fwhm(rd, col, SRC)
                p_c = peak_latency_fwhm(ctrl, col, SRC)
                afloor = FLOOR[col]
                rctrl = p_c['abs_peak'] / max(p_r['abs_peak'], afloor)
                if rctrl <= 0.01:
                    hclass, lat_app = 'PASS', False
                elif rctrl < 0.05:
                    hclass, lat_app = 'NOT_MET_NA', False
                else:
                    hclass, lat_app = 'NOT_MET_APPLICABLE', True
                obs.setdefault(step, {}).setdefault(case, {})[col] = {
                    'rctrl': rctrl, 'hierarchy': hclass,
                    'read': p_r, 'control_max': p_c['abs_peak'],
                    'latency_applicable': lat_app}
    res['control_and_read_observables'] = obs

    # ---- adjacent-pair comparisons on exact common timestamps ----
    cmp_res = {}
    for pair, (c, f) in {'05_to_025': ('0.05ps', '0.025ps'),
                         '025_to_0125': ('0.025ps', '0.0125ps')}.items():
        for case in ['init_positive_read', 'init_negative_read']:
            for col in ['V_SL1', 'I_LSL']:
                afloor = FLOOR[col]
                cts = sorted(tokens(data[case][c], SRC) & tokens(data[case][f], SRC))
                idx_c = {f'{data[case][c]["time"][i]:.6e}': i
                         for i in range(len(data[case][c]['time']))}
                idx_f = {f'{data[case][f]["time"][i]:.6e}': i
                         for i in range(len(data[case][f]['time']))}
                pts_c = [(data[case][c]['time'][idx_c[t]], data[case][c][col][idx_c[t]])
                         for t in cts if t in idx_c and t in idx_f]
                pts_f = [(data[case][f]['time'][idx_f[t]], data[case][f][col][idx_f[t]])
                         for t in cts if t in idx_c and t in idx_f]
                pts_c.sort(); pts_f.sort()
                p_c = peak_latency_fwhm(data[case][c], col, SRC)
                p_f = peak_latency_fwhm(data[case][f], col, SRC)
                aref = max(p_c['abs_peak'], p_f['abs_peak'])
                pw = [abs(a[1] - b[1]) for a, b in zip(pts_c, pts_f)]
                pw_max = max(pw)
                rms = math.sqrt(sum(x * x for x in pw) / len(pw))
                chk_peak = pw_max <= max(afloor, 0.01 * aref)
                chk_rms = rms <= max(0.002 * aref, 0.2 * afloor)
                chk_lat = abs(p_c['latency_ps'] - p_f['latency_ps']) <= 0.25
                chk_fwhm = True
                if p_c['fwhm_ps'] and p_f['fwhm_ps']:
                    chk_fwhm = abs(p_c['fwhm_ps'] - p_f['fwhm_ps']) <= 0.25
                cmp_res.setdefault(pair, {})[f'{case}:{col}'] = {
                    'common_n': len(cts), 'Aref': aref,
                    'pointwise_max': pw_max, 'rms': rms,
                    'chk_peak_pointwise': chk_peak, 'chk_rms': chk_rms,
                    'chk_latency': chk_lat, 'chk_fwhm': chk_fwhm,
                    'latencies': [p_c['latency_ps'], p_f['latency_ps']],
                    'fwhms': [p_c['fwhm_ps'], p_f['fwhm_ps']],
                    'peaks': [p_c['peak'], p_f['peak']]}
    res['adjacent_pair_comparisons'] = cmp_res

    # ---- platforms, activity deltas, same-JJ area/residual ----
    plat = {}
    for step in STEPS:
        for case in CASES:
            d = data[case][step]
            plat.setdefault(step, {})[case] = {}
            for col in ['P_JM1', 'P_JM2']:
                for w, label in [(PRE, 'pre'), (POST, 'post')]:
                    pts = window(d, col, w)
                    m = sum(v for _, v in pts) / len(pts)
                    plat[step][case][f'{label}_{col}_mean_rad'] = m
                    plat[step][case][f'{label}_{col}_mean_turns'] = m / TAU
                a = window(d, col, ACT)
                dlt = a[-1][1] - a[0][1]
                plat[step][case][f'act_{col}_endpoint_delta_rad'] = dlt
                plat[step][case][f'act_{col}_endpoint_delta_turns'] = dlt / TAU
                vcol = 'V_JM1' if col == 'P_JM1' else 'V_JM2'
                a = [(d['time'][i], d[vcol][i]) for i in range(len(d['time']))
                     if ACT[0] * 1e-12 <= d['time'][i] < ACT[1] * 1e-12]
                area = (sum((a[j][0] - a[j - 1][0]) * (a[j][1] + a[j - 1][1]) / 2
                            for j in range(1, len(a)))) / 2.067833831e-15
                plat[step][case][f'act_{vcol}_area_turns'] = area
                plat[step][case][f'act_{vcol}_residual_turns'] = area - dlt / TAU
    res['platforms_deltas_areas'] = plat

    # ---- verdict ----
    fails = []
    for step in STEPS:
        for case in CASES:
            for col in ['P_JM1_p2p_rad', 'P_JM2_p2p_rad']:
                if read[step][case][col] > 0.020:
                    fails.append(f'readiness p2p {step} {case} {col}')
    for step in STEPS:
        if read[step]['Linf_sep_rad'] < 0.100:
            fails.append(f'readiness Linf sep {step}')
    if not ts_ok:
        fails.append('exact timestamp match failed')
    for pair in cmp_res:
        for k, v in cmp_res[pair].items():
            if not (v['chk_peak_pointwise'] and v['chk_rms'] and v['chk_latency']
                    and v['chk_fwhm']):
                fails.append(f'band {pair} {k}')
    res['verdict'] = {'status': 'INVALID' if not ts_ok else
                      ('CONVERGED' if not fails else 'INCONCLUSIVE'),
                      'fails': fails}
    with open(ROOT / 'analysis.json', 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1, default=str)
    print(json.dumps({'verdict': res['verdict']}, indent=1))
    print(f'wrote {ROOT / "analysis.json"}')


if __name__ == '__main__':
    main()
