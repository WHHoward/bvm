# R2-F near-critical dwell-time threshold — recovered artifact package

**Tier:** Exploration / EXPLORATORY
**Parent exploration:** `test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821` (checkpoint `51ae2c5c7340f70cb4021463edaad156d6c35c41`)
**Runs commit:** `830f56897b783432c4f38fc6d950693c20d3d48c`
**Solver:** `build/josim-cli` v2.7.2837d13, SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`, `.tran 0.0125p 170p`, PHASE analysis.

## Recovery note

The runs commit `830f568` contained raw/inputs/logs/manifest but omitted the declared analysis artifacts. This package is regenerated **from the committed raw CSVs only; JoSIM was not re-run**. Raw SHA-256 values match the committed `sha256sums.txt` exactly (h00 `62ba0dd1…`, h05 `8c1d5eed…`, h10 `d1ee259b…`, h20 `d5623fac…`), so the raw evidence is intact.

## Verdict

**`DWELL_THRESHOLD_FOUND` — first qualifying hold = 20 ps (the last point of the preregistered matrix).**

At fixed 4.5 µA direct-drive trapezoid, increasing only the flat-top hold from 0 → 20 ps grows the largest monotonic B_OUT segment from 0.1235 to **1.0039 turn**, and the h20 run contains the R-series' first qualifying complete 2π transition: |Δφ|/(2π) = 1.0039 ≥ 1 with same-segment V-area residual +3.1e-08 turn.

Bounded claim only: under the current 4.5 µA direct drive, current output-stage topology, and this pulse shape, the flat-top dwell threshold lies within this matrix (between 10 and 20 ps hold). This is **not** exactly-one SFQ delivery; no JTL/T1 compatibility is claimed.

## Per-point results

| Point | hold (ps) | largest segment (turns) | same-segment V-area (turns) | qualifying complete segments | peak I(B_OUT) (µA) | plateau I(B_OUT) (µA) | plateau V(B_OUT) (µV) |
|---|---:|---:|---:|---:|---:|---:|---:|
| h00 | 0 | 0.123538 | −0.123538 | 0 | 9.9820 | n/a (triangle) | n/a |
| h05 | 5 | 0.169740 | −0.169740 | 0 | 10.0102 | 9.9911 | +16.12 |
| h10 | 10 | 0.970565 | +0.970565 | 0 | 10.0102 | 9.9625 | +16.47 |
| h20 | 20 | **1.003894** | **+1.003894** | **1** | 10.0102 | 9.4480* | +22.34 |

*h20 plateau median is pulled down because the switching event itself occurs inside the nominal hold window; pre-switch plateau current is ~9.98–10.01 µA like h05/h10.

### Phase velocity and dwell times

| Point | hold phase velocity (turn/ns) | time > 0.99 Ic (ps) | time > 0.999 Ic (ps) |
|---|---:|---:|---:|
| h00 | n/a | 10.99 | 0.00 |
| h05 | 0.0079 | 9.45 | 2.54 |
| h10 | 0.0084 | 6.01 | 2.60 |
| h20 | 0.0231 | 6.01 | 2.60 |

The >0.999·Ic dwell (~2.6 ps) appears already at h05/h10 yet does not switch them; what differs at h20 is that the drive *stays on* while the phase creeps through the last degrees, so the creep is not cut off by the falling edge. The h20 hold-window phase velocity is ~3× the h05/h10 value because the junction enters its voltage-state run inside the window.

## First complete transition (h20)

- **First transition time:** unwrapped phase crosses equilibrium+2π at t ≈ **132.4 ps** (during the drive fall, after the 124.51 ps fall knee);
- **First transition phase change:** Δφ = **1.0039 turn** over the monotonic segment 94.0–138.5 ps;
- **V-area:** +1.0039 turn-equivalent, residual +3.1e-08 turn (consistency criterion ≤0.05 met by orders of magnitude);
- **Pulse state at transition:** no longer on the flat top — the fall had begun at 124.5 ps; the crossing happens during the fall, i.e., the creep that started on the flat top completes as the drive decays;
- **Complete slips in one pulse:** exactly **one** (n_complete_2pi_segments = 1);
- **Retrap after pulse:** yes — settled phase at 160–170 ps = 1.1236 turn = equilibrium (0.1234) + 1.0002, V decaying to −0.04 µV;
- **Multi-turn:** none; **free-running:** none; **ringing:** bounded transient during the event (V peak 228.5 µV in 115–140 ps), no sustained oscillation;
- **POST phase stable:** yes (POST-window phase range ≤ 0.0033 turn class; net whole-run drift +1.1235 turn = equilibrium establishment + exactly one slip).

h10 is the near-miss: largest segment 0.9706 turn (creep cut off by the fall before π/2 completion), but its event-window V already peaked at 132.9 µV — the junction locally entered the running state and fell back.

## Stop-rule compliance

Sequential ascending execution h00 → h05 → h10 → h20 with per-run qualifying checks. No point before h20 qualified, so all four points were required; h20 is the matrix's last point, so no post-threshold run exists. **No stop-rule violation.**

## Guards

Storage preserved in every run (JM1 post median = +5.911 rad, JM2 ≈ +0.31 rad class). Background identical across points (logical1 init, no READ). Controls: h00 reproduces the R2-E a45u0 triangle result exactly (0.123538 turn).

## Observed

1. Monotonic, strongly nonlinear growth of the response with hold: 0.1235 / 0.1697 / 0.9706 / 1.0039 turn.
2. First qualifying complete 2π transition occurs at 20 ps hold; exactly one slip; clean retrap to equilibrium+1.
3. Near-critical dwell above 0.999·Ic (~2.6 ps) is necessary but not sufficient — the drive must still be present when the creep completes (h10 vs h20).
4. Peak junction current crosses Ic slightly (10.0102 µA) in h05–h20 during the rise overshoot, but only sustained near-critical drive produces a full slip.

## Derived

1. Dwell threshold bracket: first qualifying hold ∈ (10, 20] ps under this shape/topology/bias.
2. h20 event timing: crossing at ~132.4 ps, i.e., ~8 ps after the fall knee — the transition completes during drive decay.
3. Settled state = equilibrium + exactly one turn (1.1236 vs 1.1234 expected): single-slip character of the event.

## Inference (falsifiable)

B_OUT activation in this fixture requires holding the junction within ~1 % of Ic long enough for the near-critical creep to traverse the remaining angle (~3 ps at ≥0.999·Ic plus margin for the final degrees). Peak amplitude alone (R2-E) and short near-critical excursions (h05/h10) do not switch it. A viable receiver transfer chain must therefore deliver both amplitude (~4.5 µA-class effective junction drive) and near-critical dwell (≥~3 ps, with total high-drive envelope ≳15 ps) simultaneously.

## Unknown

1. Exact dwell threshold between 10 and 20 ps (bracketed, not localized).
2. Retrap/one-shot quality under repeated pulses — untested.
3. Robustness of the ~2.6 ps near-critical dwell requirement to parameter/timestep perturbation.
4. Whether the h10 near-miss (local running state, 132.9 µV) leaves any residual state change (storage guard says no at JM level).
5. Timestep convergence of the switching event (single dt setting).

## Next single most informative action (recommendation, not started)

**R2-G: double-pulse retrigger test at the h20 operating point.** Two identical 4.5 µA / 20 ps-hold trapezoids separated by ~40 ps. Question: does each pulse produce exactly one complete transition (repeatable single-slip generator), or does the second pulse fail/multi-fire? This tests the most basic prerequisite for "read 1 → exactly one SFQ" beyond the single-shot demonstration.

## Artifacts

- Runs commit: `830f56897b783432c4f38fc6d950693c20d3d48c`
- This recovery commit: analysis/r2f-summary.json, R2F_DWELL_REPORT.md, REVIEW.md, regenerated sha256sums.txt
- No raw, inputs, or manifest content changed; no JoSIM re-run performed.
