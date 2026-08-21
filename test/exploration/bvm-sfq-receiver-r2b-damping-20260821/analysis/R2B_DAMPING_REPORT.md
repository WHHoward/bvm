# R2-B B_OUT local damping diagnostic

**Tier:** Exploration / EXPLORATORY
**Created:** 2026-08-21
**Parent exploration:** `test/exploration/bvm-sfq-receiver-r2a-coupling-20260821` (checkpoint `1a78d141e363466b6bc6841534ddaef87e99dd03`)
**Head before experiment:** `1a78d141e363466b6bc6841534ddaef87e99dd03`
**Solver:** `build/josim-cli` v2.7.2837d13, SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`, `.tran 0.0125p 170p`, PHASE analysis, same command for all 16 runs.

## Verdict

**R2-B verdict: Situation B — H2 rejected as the dominant bottleneck.**

Weakening only `R_OUT_DAMP` from 100 Ω to 330 Ω (βc = RN‖R_OUT_DAMP basis: 0.81 → 2.47, crossing the underdamped transition βc = 1) raises the read1 largest monotonic B_OUT segment only from **0.0261 to 0.0290 turn (+10.9 %)**. No tested point reaches a complete 2π transition; read0 stays at ~0.006–0.007 turn and both zero-READ controls stay at exactly zero activity. Per the preregistered interpretation plan, the damping sweep stops here, and no AREA/bias/C/K sweep is auto-started.

This is a bounded local receiver result at one timestep on one fixture. It does not claim that damping is irrelevant in other topologies, that all larger R_OUT_DAMP values fail, or that the receiver route is impossible. A local B_OUT phase response is never called downstream SFQ delivery; this fixture has no JTL.

## What R_OUT_DAMP is in the actual circuit

From `inputs/k095-rXXX-receiver.cir` (identical to the R2-A K=0.95 receiver except the damper value):

```
B_OUT         N_SEC       0             jjmit area=0.10
I_OUT_BIAS    0           N_SEC         pwl(0p 0 2p 7U ... 170p 7U)
R_OUT_DAMP    N_SEC       0            <varied>
```

`R_OUT_DAMP` is a linear resistor from N_SEC to ground, directly in parallel with the B_OUT junction (also N_SEC → ground). KCL at N_SEC: `i_BOUT = I_BIAS − i_LSEC − i_RDAMP`. At DC (V(N_SEC)=0) it carries no current, so it does not shift the pre-READ operating point; during transients it carries `V(N_SEC)/R_OUT_DAMP` and both steals junction drive and adds RCSJ damping. The AREA-scaled B_OUT model is Ic=10 µA, RN=160 Ω, R0=1600 Ω, C=7 fF; bias 7 µA (i_b = 0.7).

## Preregistered hypothesis

H2 (primary): local damping blocks evolution of the input transient into a complete phase slip. Prediction: read1 largest monotonic segment grows strongly with R_OUT_DAMP (0.026 → ≥0.1 → ~0.3 → approaching/reaching 1 turn) while read0/controls remain sub-turn.

## Damping matrix (frozen before runs)

| Point | R_OUT_DAMP (Ω) | Reff = RN‖Rd (Ω) | βc(Reff) |
|---|---:|---:|---:|
| k095-r100 | 100 | 61.538 | 0.8055 |
| k095-r150 | 150 | 77.419 | 1.2749 |
| k095-r220 | 220 | 92.632 | 1.8251 |
| k095-r330 | 330 | 107.755 | 2.4697 |

βc = 2π·Ic·Reff²·C/Φ0 with Ic=10 µA, C=7 fF. The ladder crosses βc=1 between 100 and 150 Ω and keeps Reff < RN (junction stays explicitly shunted). Everything else frozen: canonical BVM unchanged, SL route, R_IN=12 Ω, L_TX=0.20 pH, L_SEC=2.0 pH, K_TX=0.95 (M=0.6008327 pH), R_SEC_LOAD=12 Ω, B_TRIG area=0.50/bias=15 µA, B_OUT area=0.10/bias=7 µA.

## Results

All 16 raw CSVs artifact-valid (13,599 rows each, finite, strictly increasing time, no missing probe columns). The k095-r100 point reproduces the R2-A k095 raw matrix **byte-for-byte** (all four cases) — deterministic replay check of the parameterized runner.

### B_OUT primary metric (largest continuous monotonic unwrapped-phase segment, OUTPUT_ANALYSIS window 94–170 ps)

| Rdamp (Ω) | read1 (turns) | read0 (turns) | logical1 ctrl | logical0 ctrl |
|---:|---:|---:|---:|---:|
| 100 | 0.026122 | 0.006125 | 0.000000 | 0.000000 |
| 150 | 0.027411 | 0.006385 | 0.000000 | 0.000000 |
| 220 | 0.028297 | 0.006561 | 0.000000 | 0.000000 |
| 330 | 0.028961 | 0.006693 | 0.000000 | 0.000000 |

Same-segment direct `V(B_OUT|XTRIG)` trapezoid areas agree with phase deltas to ≤1.3e-05 turn everywhere (area-consistency criterion ≤0.05 turn met by orders of magnitude). No complete_2pi segment exists anywhere in the matrix; no qualifying event exists anywhere.

### Junction-drive diagnostics (read1, activity-window abs peaks)

| Rdamp (Ω) | \|I(B_OUT)\| peak (µA) | \|I(R_OUT_DAMP)\| peak (µA) | \|V(B_OUT)\|=‖V(N_SEC)‖ peak (µV) |
|---:|---:|---:|---:|
| 100 | 8.46 | 0.89 | 88.7 |
| 150 | 8.56 | 0.62 | 93.7 |
| 220 | 8.64 | 0.44 | 97.2 |
| 330 | 8.69 | 0.30 | 99.9 |

The junction current peak stays **below Ic = 10 µA at every point**, and the read1 V(N_SEC) excursion is negative-polarity throughout. Secondary loop return-current peaks are nearly constant (2.48 → 2.52 µA for a 3.3× damper change): the induced secondary current is set by the L_SEC/R_SEC_LOAD branch (12 Ω), which dominates the secondary loop impedance, not by the output-stage damper.

### Guards (all points)

- Secondary separation: read1/read0 V(N_SEC) deviation ratio 5.759 → 5.880 across the ladder; guard pass at every point.
- Storage: JM1/JM2 post medians keep logical-state signs at every point and case (read1 ≈ +5.915/+0.314 rad; read0 ≈ −5.911/−0.321 rad); storage guard pass.
- Trigger: B_TRIG read1 largest segment 3.916–3.919 turns vs read0 0.1849 turns at every point — R0b trigger behavior preserved; bounded back-action only.
- Source: SL ≈ ±1.88 mV/−0.44 mV, N6 ≈ ±2.12 mV/−0.72 mV, I(L_SL) ≈ 54.1/−22.2 µA (read1/read0) unchanged across points.
- Controls: zero READ produces zero secondary deviation and zero B_OUT activity at every point.
- No ringing burst, no free-running, no read0/control switching at any damping value (Situation C did not occur within this range).

Independent cross-check (`analysis/independent_crosscheck.py`, separate recomputation from raw CSVs): all comparisons pass for all 4 points × 4 cases (phase, area, completeness, secondary, storage pre/post, SHA match).

## Observed

1. read1 largest monotonic B_OUT segment grows monotonically but weakly with R_OUT_DAMP: 0.026122 → 0.027411 → 0.028297 → 0.028961 turn (+10.9 % total for 3.3× damper change and βc tripling across the underdamped transition).
2. read0 grows similarly weakly (0.006125 → 0.006693 turn); controls remain exactly zero.
3. Peak junction current stays below Ic at all points (8.46–8.69 µA vs 10 µA).
4. Secondary loop return-current peak is nearly independent of R_OUT_DAMP (2.48–2.52 µA); V(N_SEC) amplitude rises only ~13 % while the damper value triples.
5. Damper current falls as expected (0.89 → 0.30 µA) but the freed current does not reach the junction (I_BOUT peak rises only 0.23 µA).
6. All guards (secondary separation, storage signs, trigger, source, controls) pass at every point; artifacts valid; crosscheck passes; k095-r100 replays R2-A k095 byte-identically.

## Derived (arithmetic from observed values only)

1. Growth ratio read1 r330/r100 = 0.028961/0.026122 = 1.109.
2. Drive deficit at best point: Ic − max|I_BOUT| = 10 − 8.69 = 1.31 µA (≈13 % of Ic) below criticality; with bias fixed at 7 µA, the transient delivers ≈1.7 µA of additional junction drive where ≥3.0 µA would be needed to reach Ic.
3. Steady-state phase from bias alone: arcsin(0.7) ≈ 0.775 rad ≈ 0.123 turn; read1 adds ≈0.029 turn, keeping total supercurrent-driving phase well below π/2 — consistent with item 3 (subcritical at all times).
4. βc(Reff) spans 0.81–2.47 across the ladder (crossing βc=1); the near-absent response shows the bottleneck is not in this βc range.

## Inference (interpretation, falsifiable)

The binding constraint is the **amount of current the secondary can inject into the B_OUT branch**, not the local damping: the L_SEC/R_SEC_LOAD return path (12 Ω) takes most of the induced current, capping the junction drive at ~8.7 µA < Ic, so no damping value alone can produce a slip. Weakening damping cannot create drive that the injection mechanism never delivers. This explains why R2-A (K sweep) and R2-B (damper sweep) both show real-but-small monotonic margins: both scale the same insufficient injection by modest factors.

## Unknown

1. Whether any passive transformer-based variant of this topology can deliver ≥3 µA into the B_OUT branch without breaking storage or read0 silence (not bounded by this experiment).
2. The actual complete-switching threshold curve of the output stage (amplitude/duration of injected drive needed for one full 2π transition at the frozen operating point) — not measured here.
3. Timestep convergence of these small excursions (single dt=0.0125 ps setting; no convergence claim made).
4. Behavior beyond R_OUT_DAMP=330 Ω (untested; expected to trend toward Situation C but not demonstrated).
5. Whether JoSIM's reported I(B_OUT) decomposition (supercurrent vs normal component) matches the ideal-RCSJ reading used in the inference above at the ~100 µV level.

## Next single most informative experiment (recommendation, not started)

**R2-C: direct-drive B_OUT activation-threshold calibration.** Replace the transformer-induced drive with an ideal PWL current pulse injected directly into N_SEC (same negative polarity and ~ps-scale duration as the observed read1 transient), amplitude matrix around the predicted threshold (e.g., 3.0/3.5/4.0/5.0 µA added on top of the 7 µA bias), everything else frozen. Question: what injected drive amplitude/duration is actually required for one complete 2π B_OUT transition? This converts the deficit into a number and bounds every future transfer-chain design: any proposed topology must deliver at least that much. It also cleanly separates "output stage capability" from "transfer chain delivery".

Per the preregistered plan, no further damping points were run after the Situation-B signature was visible, and no AREA/bias/C/K sweep was started.

## Artifacts

- Manifest (preregistered before runs): `manifest.yaml`
- Inputs: `inputs/k095-r{100,150,220,330}-{receiver,read1,read0,logical1-read0-control,logical0-read0-control}.cir`
- Raw: `raw/<point>/<case>/run-01.csv` (16 files)
- Logs: `logs/`
- Primary analysis: `analyze_r2b.py`, `analysis/k095-rXXX-analysis.json`
- Independent crosscheck: `analysis/independent_crosscheck.py`, `analysis/k095-rXXX-crosscheck.json`
- Aggregate: `analysis/damping-summary.json`
- Hashes: `analysis/sha256sums.txt`
