# R2-F numerical and adversarial review (recovered package)

## Recovery scope

Runs commit `830f568` shipped raw evidence without the declared analysis artifacts. This package regenerates them strictly from the committed raw CSVs. Pre-regeneration verification:

1. Raw integrity: SHA-256 of all four committed CSVs matches the committed `sha256sums.txt` line-for-line; 13,599 rows each. No corruption → no JoSIM re-run, per the recovery constraint.
2. No raw, inputs, or manifest science content modified.

## Numerical checks

1. Event oracle identical across R2-B…R2-F: continuous adjacent-sample unwrapped P(B_OUT|XTRIG), monotonic segment ≥1.0 turn with start ≤130 ps and same-segment direct V(B_OUT|XTRIG) trapezoid area within 0.05 turn on actual timestamps.
2. h20 qualifying segment: 1.003894 turn over 94.0–138.5 ps with area residual +3.08e-08 turn — the first and only complete transition in the matrix.
3. Exactly-one-slip check performed independently of the segment code: unwrapped phase crosses equilibrium+2π at t≈132.4 ps and settles at 1.1236 turn (= equilibrium 0.1234 + 1.0002) by 160–170 ps. No second slip anywhere in the run.
4. h00 control reproduces the R2-E a45u0 triangle result exactly (0.123538 turn, same residual −3.85e-08): the fixture family is consistent.
5. Dwell-time integrals use actual adjacent-sample intervals above absolute current thresholds (9.9 µA / 9.99 µA); no fixed-step assumption.
6. All CSVs artifact-valid: 13,599 rows, finite, strictly increasing time, no missing columns; single timestep setting, no convergence claim.

## Adversarial checks

1. **Could the h20 "transition" be an analysis artifact?** No: it satisfies the preregistered phase+area oracle independently, the Josephson consistency residual is +3e-08 turn, and the settled state equals equilibrium+exactly one turn — three mutually consistent signatures.
2. **Could the crossing have occurred during the flat top (contradicting the "creep cut off" story)?** Checked: crossing at ~132.4 ps is after the 124.51 ps fall knee. The report states this honestly — the creep that started on the flat top completes during drive decay.
3. **Is "dwell ≥0.999 Ic for ~2.6 ps" sufficient?** No — h05/h10 also show ~2.5–2.6 ps above 0.999·Ic without switching. The discriminating factor at h20 is drive presence while the creep completes. The report records dwell as necessary-but-not-sufficient rather than overclaiming a simple threshold.
4. **Stop-rule audit:** ascending order with per-run checks; no pre-h20 point qualified; h20 is the last matrix point → no violation possible. Recorded in summary JSON.
5. **Free-running / multi-turn hunt:** POST window stable (phase range ≤0.0033 turn class, V → −0.04 µV); whole-run drift = equilibrium + exactly one turn; no sustained rotation or repeated slips.
6. **Storage guard:** JM signs preserved in all runs despite the output-stage switching event — the receiver event did not corrupt BVM state.
7. **Interpretation discipline:** verdict bounded to shape/topology/bias; explicitly not exactly-one SFQ delivery, no JTL/T1 claim; Unknown lists five gaps including the untested retrigger dimension and single-timestep limitation.

## Disposition

Artifact package restored as declared: `r2f-summary.json`, `R2F_DWELL_REPORT.md`, `REVIEW.md`, regenerated `sha256sums.txt`. Bounded verdict **`DWELL_THRESHOLD_FOUND`** with first qualifying hold = 20 ps (matrix boundary), exactly one complete slip, clean retrap, storage preserved. The dwell hypothesis from R2-E is confirmed within this fixture; the next open question is per-pulse repeatability (retrigger), which remains untested.
