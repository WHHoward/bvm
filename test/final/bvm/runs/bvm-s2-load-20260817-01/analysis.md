# BVM-S2 load characterization — analysis

Run root: `test/final/bvm/runs/bvm-s2-load-20260817-01` (immutable, 16 runs)
Task: `JH-20260817-BVM-S2-001` (request SHA-256 `155f3db5…`)
Binary: `/home/howard/JoSIM/build/josim-cli` v2.7.2837d13 (SHA-256
`48655cb3…40b2`).  Closure: copied `bvm_cell.cir` + `jjmit.cir` (byte
identical); `XBVM1 WL1 BL1 SE1 SL1 BVM`; only variable `R_LD SL1 0
<1|12|25|50>`.  All runs 0.0125 ps / 170 ps.  **numerical_status:
NOT_APPLICABLE** (no S2 convergence procedure registered; S1 INCONCLUSIVE
unchanged).

## 1. QA (AC3) — PASS 16/16

Exact registered header (14 cols incl. P/V for JM1/JM2/JS1/JS2, V(SL1),
I(L_SL), I(WL1)/I(BL1)/I(SE1)); no NaN/Inf; strictly increasing nonduplicate
time; last sample 169.9875 ps covers all windows (pre/activity/source/
recovery/post).  Stderr clean (no ERROR/WARNING).

## 2. Readiness (AC4) — NOT_MET at every load

| load | JM1 pre p2p (rad) | JM2 pre p2p (rad) | L∞ sep (rad) | band |
|---|---:|---:|---:|---|
| 1 Ω | 0.00353 | 0.0585 | 11.822 | JM2 p2p 0.0585 > 0.020 ✗ |
| 12 Ω | 0.00352 | 0.0584 | 11.822 | ✗ |
| 25 Ω | 0.00352 | 0.0584 | 11.822 | ✗ |
| 50 Ω | 0.00352 | 0.0583 | 11.822 | ✗ |

L∞ sep ≥ 0.100 rad ✓.  JM1 p2p ≤ 0.020 ✓, but **JM2 pre-window p2p ≈
0.058 rad exceeds the registered 0.020 rad band at every load**: under the
S2 preregistered init PWL (0 at 0-9 ps, ±100 µA at 10-20 ps, 0 at 21 ps)
JM2 sustains a ~5 ps-period oscillation (≈0.29-0.35 rad) in pre [80,90) ps —
a comparability/readiness result, not a Gate.  (For reference the S1
init PWL, which ramps 1 ps later, yields JM2 p2p ≈ 0.0055 rad; S2 executed
exactly the preregistered stimulus.)

## 3. Control hierarchy (AC5) — all PASS_REGION

| load | init | V(SL1) rctrl | I(L_SL) rctrl | region |
|---|---|---:|---:|---|
| 1 Ω | pos/neg | 1.1e-4 / 2.1e-4 | 1.1e-4 / 2.1e-4 | PASS_REGION |
| 12 Ω | pos/neg | 1.0e-4 / 2.9e-4 | 1.0e-4 / 2.9e-4 | PASS_REGION |
| 25 Ω | pos/neg | 1.5e-4 / 4.4e-4 | 1.5e-4 / 4.4e-4 | PASS_REGION |
| 50 Ω | pos/neg | 1.6e-4 / 5.4e-4 | 1.6e-4 / 5.4e-4 | PASS_REGION |

rctrl ≤ 0.01 → peak latency / FWHM NOT_APPLICABLE at every load/init.

## 4. Source observables (AC5/AC8, baseline-subtracted)

| load | init | V(SL1) peak | latency (from 96 ps) | I(L_SL) peak | latency |
|---|---|---:|---:|---:|---:|
| 1 Ω | pos | +0.100 mV | 5.9 ps | +58.9 µA | 5.9 ps |
| 12 Ω | pos | +0.905 mV | 5.0 ps | +75.3 µA | 5.0 ps |
| 25 Ω | pos | +1.823 mV | 7.7 ps | +72.9 µA | 7.7 ps |
| 50 Ω | pos | +2.259 mV | 8.5 ps | +45.2 µA | 8.5 ps |
| 1 Ω | neg | −0.103 mV | 6.6 ps | −48.9 µA | 6.6 ps |
| 12 Ω | neg | −0.317 mV | 10.0 ps | −26.4 µA | 10.0 ps |
| 25 Ω | neg | −0.516 mV | 10.4 ps | −20.6 µA | 10.4 ps |
| 50 Ω | neg | −0.559 mV | 11.0 ps | −11.2 µA | 11.0 ps |

Terminal V depends strongly on load (positive: 0.10 → 2.26 mV across
1→50 Ω; negative: −0.10 → −0.56 mV).  I(L_SL) peaks at 12 Ω (75.3 µA pos)
and falls on both sides — a bounded observation, not an impedance model.
FWHM and following-opposite-lobe per lobe_rules in analysis.json (all
control-region NOT_APPLICABLE for latency/FWHM acceptance; lobe metrics are
descriptive).

## 5. Terminal affine diagnostics (AC8)

Corrected traces (read − matched control, exact decimal timestamps);
endpoints 1/50 Ω, interior 12/25 Ω; residual band
`abs(e) ≤ max(5 µV, 1%·|V50−V1|)` (voltage) / `max(0.5 µA, 1%·span)` (current):

- V(SL1) positive init: e12 max ≈ 30.9 µV, e25 max ≈ 92.4 µV, band ≈
  max(5 µV, 1%·2.16 mV) = 21.6 µV → **NOT_SUPPORTED_AT_NAMED_TIMESTAMP**
  at the peak region (non-affine at the working grid);
- V(SL1) negative init: e12 ≈ 15.5 µV / e25 ≈ 31.9 µV vs band 4.6 µV →
  NOT_SUPPORTED;
- I(L_SL) similar non-affine pattern; some far-tail timestamps are
  INCONCLUSIVE_ILL_CONDITIONED (span below the 5 µV / 0.5 µA floors).

Per preregistration, non-affine is `NOT_SUPPORTED_AT_NAMED_TIMESTAMP`, not a
physical circuit FAIL, and never a universal/internal Thevenin-Norton
impedance.  Peak envelope is reported separately.

## 6. Internal trajectory (AC9)

p-star/v-star/a-star (read − control, PRE-mean-corrected) computed for
JM1/JM2/JS1/JS2 at all loads on exact common timestamps; comparisons
load-to-12, adjacent pairs, full span; control envelopes included.
**Disposition: LOAD_EFFECT_ON_INITIALIZATION_OR_UNRESOLVED** — the
registered two-witness RESOLVED label requirements (5× envelope separation
on phase AND voltage, ≥ 0.25 ps contiguous interval, same-JJ direction
consistency) are not claimed here; the label is only assignable by the
preregistered criteria.  No state-preservation/SFQ/fluxoid interpretation.

## 7. Same-JJ cross-check (AC7, descriptive)

Per run/JJ: activity-window endpoint phase delta (turns) vs actual-time
V-area (turns), residual = phase − area, `Phi0 = 2.067833848e-15 Wb`;
reported in analysis.json `same_jj_cross_check`; descriptive only, no
global acceptance band.

## 8. Verdict

Artifact **VALID** (QA/closure/hash/probe integrity PASS).  Readiness
**NOT_MET** (JM2 pre p2p 0.058 rad > 0.020 band at all loads) — per the
registered inconclusive condition, the disposition is **INCONCLUSIVE**:
bounded per-load source and internal-trajectory observations remain
reportable, but comparability/readiness requirements are not met.
numerical_status **NOT_APPLICABLE** by design (no S2 ladder).  No converged
characterization, no universal impedance, no Gate/logical/SFQ/fluxoid
claim.  S1 INCONCLUSIVE unchanged.  After delivery: Copilot skeptical
review, then Codex audit.

## 9. Reproduction

```bash
cd test/final/bvm/runs/bvm-s2-load-20260817-01
python3 gen_inputs.py      # 16 netlists + closure copies
bash run_all.sh            # 16 runs -> raw/<case>/<load>ohm/
python3 analyze_s2.py      # -> analysis.json (schema-validated)
```
