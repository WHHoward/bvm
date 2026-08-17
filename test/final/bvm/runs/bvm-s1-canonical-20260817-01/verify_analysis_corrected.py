#!/usr/bin/env python3
"""verify_analysis_corrected -- INDEPENDENT recomputation checks for A02.

Does NOT import gen_analysis_corrected.py.  Recomputes the headline cells
directly from the sealed raw CSVs and asserts them against
analysis-corrected.json (and the A01 hashes stay untouched).  Exits non-zero
on any failure.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).parent
RAW = ROOT / 'raw'
PRE, SRC = (80, 90), (94, 130)


def load(case: str, step: str) -> tuple[list[float], dict]:
    rows = list(csv.reader(open(RAW / case / step / 'run-01.csv', encoding='utf-8')))
    hdr = [h.strip().strip('"') for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    t = [float(r[0]) for r in rows[1:]]
    d = {col: [float(r[idx[col]]) for r in rows[1:]] for col in
         ('V(SL1)', 'I(L_SL|XBVM1)')}
    return t, d


def pre_mean(t, d, col):
    v = [d[col][i] for i in range(len(t)) if PRE[0] * 1e-12 <= t[i] < PRE[1] * 1e-12]
    return sum(v) / len(v)


def pair_pw_rms(t_c, d_c, t_f, d_f, col):
    tc = {f'{t_c[i]:.6e}': i for i in range(len(t_c))}
    tf = {f'{t_f[i]:.6e}': i for i in range(len(t_f))}
    common = sorted(set(tc) & set(tf), key=float)
    pw = [abs(d_c[col][tc[k]] - d_f[col][tf[k]]) for k in common
          if SRC[0] * 1e-12 <= float(k) < SRC[1] * 1e-12]
    rms = math.sqrt(sum(x * x for x in pw) / len(pw))
    return max(pw), rms, len(pw)


def ctrl_l1(t_r, d_r, t_c, d_c, col, m_c, aref):
    tc = {f'{t_r[i]:.6e}': i for i in range(len(t_r))}
    tcc = {f'{t_c[i]:.6e}': i for i in range(len(t_c))}
    common = sorted(set(tc) & set(tcc), key=float)
    t = [(float(k) - 94e-12) for k in common
         if SRC[0] * 1e-12 <= float(k) < SRC[1] * 1e-12]
    c = [d_c[col][tcc[k]] - m_c for k in common
         if SRC[0] * 1e-12 <= float(k) < SRC[1] * 1e-12]
    l1 = sum(abs(c[j]) * (t[j] - t[j - 1]) for j in range(1, len(t)))
    span = t[-1] - t[0]
    return l1 / (aref * span)


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def main() -> None:
    j = json.load(open(ROOT / 'analysis-corrected.json', encoding='utf-8'))
    fails = []
    ok = lambda name, cond: (fails.append(name) if not cond else None)

    # 1. neg:I 05->025 pointwise is floor-limited PASS
    t_c, d_c = load('init_negative_read', '0.05ps')
    t_f, d_f = load('init_negative_read', '0.025ps')
    pw, rms, n = pair_pw_rms(t_c, d_c, t_f, d_f, 'I(L_SL|XBVM1)')
    aref = 2.639e-5  # from A01/Copilot independent recomputation
    band_pw = max(0.5e-6, 0.01 * aref)
    ok('neg:I pw PASS', pw <= band_pw and abs(pw - 0.4952e-6) < 1e-9)
    ok('neg:I json chk', j['adjacent_pair_comparisons']['05_to_025']
       ['init_negative_read:I_LSL']['chk_peak_pointwise'] is True)
    ok('neg:I band floor label', abs(j['adjacent_pair_comparisons']['05_to_025']
       ['init_negative_read:I_LSL']['band_pw'] - 0.5e-6) < 1e-12)
    ok('neg:I still FAIL overall (RMS)', j['adjacent_pair_comparisons']['05_to_025']
       ['init_negative_read:I_LSL']['chk_rms'] is False)

    # 2. negative-read FWHM has two crossings ~1.07 ps (json reports, not None)
    for step in ('0.05ps', '0.025ps', '0.0125ps'):
        fw = j['read_observables'][step]['init_negative_read']['V_SL1']['fwhm_ps']
        ok(f'neg FWHM {step} finite ~1.07', fw is not None and 1.0 <= fw <= 1.15)

    # 3. control L1/time-norm passes (baseline-subtracted, ~1e-5 scale)
    t_r, d_r = load('init_positive_read', '0.025ps')
    t_c2, d_c2 = load('init_positive_control', '0.025ps')
    m_c = pre_mean(t_c2, d_c2, 'V(SL1)')
    l1n = ctrl_l1(t_r, d_r, t_c2, d_c2, 'V(SL1)', m_c, 9.036e-4)
    ok('ctrl L1 ~1e-5 and <= 0.002', abs(l1n - j['control_observables']['0.025ps']
       ['init_positive_read']['V_SL1']['l1_time_norm']) < 1e-6 and l1n <= 0.002)

    # 4. verdict unchanged: INCONCLUSIVE with the 6 registered pair failures
    ok('verdict INCONCLUSIVE', j['verdict']['status'] == 'INCONCLUSIVE')
    ok('6 pair fails', len(j['verdict']['fails']) == 6)

    # 5. A01 artifacts untouched (hashes frozen at A01 delivery)
    ok('A01 analysis.json hash', sha(ROOT / 'analysis.json')
       == '5232a1425eae5e78494ee3b79cb74e287361b9a15364a434e18fd2d14c13b890')
    ok('A01 analysis.md hash', sha(ROOT / 'analysis.md')
       == '9b708265b8c4a24b81ab9ade188d7404bbac452f7412537a78e9ba0c45359aa7')
    ok('A01 closure-hashes hash', sha(ROOT / 'closure-hashes.txt')
       == 'bbb2c7f9520f2233c2e7beb3fca0e1f9ff19cdc6d1923d22689324e8daa334e5')

    if fails:
        print('FAIL:')
        for f in fails:
            print(f'  - {f}')
        raise SystemExit(1)
    print(f'ALL {13} INDEPENDENT CHECKS PASS (n_common={n})')


if __name__ == '__main__':
    main()
