#!/usr/bin/env python3
"""decode_hist_viz -- recover historical test_bvm_final.cir waveforms from the
Jul-17 self-contained viz HTML into a plain JoSIM-style CSV.

WHY THIS FILE EXISTS
====================
The historical raw CSV for test/final/bvm/test_bvm_final.cir no longer exists
in the repo (only the netlist and the self-contained HTML viewer remain).
test/final/bvm/bvm_final_viz.html (2026-07-17) embeds the actual run output as
base64 float64 arrays in the old p2j/npyjs trace format. This script decodes
those arrays back into a standard JoSIM CSV so the repository's native
josim-plot2 tool can plot history and current data with the same pipeline.

PROVENANCE / INTEGRITY
======================
- Input : test/final/bvm/bvm_final_viz.html (git-tracked, unmodified)
- Output: hist_test_bvm_final.csv (DERIVED data -- not raw evidence)
- The embedded x arrays are asserted byte-identical across all 7 traces,
  monotonic, and consistent with a 160 ps window at 0.5 ps (320 samples).
- Channel names come from the traces themselves; no name is invented.
- No JoSIM run; frozen evidence untouched.

PHASE-UNIT CORRECTION (turns -> rad)
====================================
The Jul-17 HTML embeds phase traces already divided by 2pi (TURNS) while
labelling them P(...): the layout axes carry no unit label, and the values
match the current-era state in turns, not rad:
  - same bvm_cell.cir + jjmit.cir (byte-identical, git-verified),
    same +100 uA / 10-20 ps WL+BL write
  - current S0 (0.025 ps, frozen) and P2-era runs (12-JJ load):
    JM1 plateau = +5.913 rad = +0.9411 turns
  - this HTML: embedded 0.9415 -> as turns, 5.9156 rad (0.04% from S0);
    as rad it would be 0.15 turns, i.e. a 6.28x different physical state
    from the identical write -- impossible (read current matches too:
    75.7 uA vs S0 75.3 uA)
Therefore P-columns are multiplied by 2pi here so the derived CSV stores
TRUE raw rad (the JoSIM P() convention). Every consumer must treat these
values as rad. The multiplication is documented and asserted below.

The unit schema mirrors plots/_viz_data.py: t_s is SECONDS (JoSIM raw).
"""
from __future__ import annotations

import base64
import csv
import json
import pathlib
import re
import struct

HTML = pathlib.Path(__file__).parent.parent / 'bvm_final_viz.html'
OUT = pathlib.Path(__file__).parent / 'hist_test_bvm_final.csv'

TRACE_RE = re.compile(
    r'\{"mode":"lines","name":"([^"]*)","x":(\{[^{}]*\}),"y":(\{[^{}]*\})')


def decode_arr(obj: str) -> list[float]:
    d = json.loads(obj)
    assert d['dtype'] == 'f8', f'unexpected dtype {d["dtype"]}'
    raw = base64.b64decode(d['bdata'])
    assert len(raw) % 8 == 0, 'f8 bdata length not a multiple of 8'
    return [struct.unpack('<d', raw[i:i + 8])[0] for i in range(0, len(raw), 8)]


def main() -> None:
    text = HTML.read_text(encoding='utf-8')
    traces = TRACE_RE.findall(text)
    assert len(traces) == 7, f'expected 7 embedded traces, found {len(traces)}'
    names = [t[0] for t in traces]
    print('decoded trace names:')
    for n in names:
        print(f'  {n}')

    x0 = decode_arr(traces[0][1])
    n = len(x0)
    print(f'samples per trace: {n}')

    # integrity: all traces share one time axis
    for t in traces[1:]:
        xi = decode_arr(t[1])
        assert xi == x0, 'embedded x arrays are not identical across traces'
    assert all(x0[i] <= x0[i + 1] for i in range(n - 1)), 'time not monotonic'

    # embedded axis: 160 ps window, 0.5 ps step (320 pts) -- the HTML generator
    # (or its run) used a coarser grid than the netlist's .tran 0.25p 160p
    tmin, tmax = x0[0], x0[-1]
    print(f'time range: {tmin:.3e} .. {tmax:.3e} s')
    assert abs(tmin) < 1e-18, f'time does not start at 0: {tmin}'
    assert 159e-12 <= tmax <= 160e-12, f'time end outside 160 ps: {tmax}'
    step = x0[1] - x0[0]
    assert abs(step - 0.5e-12) < 1e-16, f'step != 0.5 ps: {step}'
    print(f'step: {step:.3e} s = 0.5 ps  (embedded grid, 320 samples)')

    # ---- phase-unit correction: embedded phase traces are TURNS, store rad ----
    ys = [decode_arr(t[2]) for t in traces]
    for j, nm in enumerate(names):
        if nm.startswith('P('):
            ys[j] = [v * 2 * 3.141592653589793 for v in ys[j]]
    # assertion: +100 uA write plateau must land on the S0 state (~5.91 rad)
    jm1 = [v for i, v in enumerate(ys[0]) if 24 <= x0[i] * 1e12 <= 30]
    plateau = sum(jm1) / len(jm1)
    assert abs(plateau - 5.9130) < 0.06, f'JM1 plateau {plateau:.4f} rad != S0 state 5.913'
    print(f'JM1 +100uA-write plateau after turns->rad: {plateau:.4f} rad '
          f'(S0: 5.9130; delta {1000*abs(plateau-5.9130):.2f} mrad)')

    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['time'] + names)
        for i in range(n):
            w.writerow([f'{x0[i]:.15e}'] + [f'{y[i]:.9e}' for y in ys])
    print(f'wrote {OUT} ({OUT.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
