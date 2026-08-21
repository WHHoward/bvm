# R2-G numerical and adversarial review

## Review scope

Strongest bounded claim: "two identical h20 pulses each produce exactly one qualifying complete 2π slip with clean rearm between — `REPEATABLE_TWO_PULSE_SINGLE_SLIP`." This review tests that claim against the single two-pulse run. It does not claim SFQ receiver status, JTL/T1 compatibility, or robustness beyond this operating point and separation.

## Numerical checks

1. Event oracle identical to R2-B…R2-F, applied per pulse window: monotonic unwrapped segment ≥1.0 turn with same-segment direct V(B_OUT|XTRIG) area within 0.05 turn on actual timestamps.
2. Pulse 1: 1 complete segment (1.033314 turn, residual +3e-08); pulse 2: 1 complete segment (1.033315 turn, residual −6e-07). Total exactly 2 slips; no additional complete segments in gap or post windows.
3. Phase bookkeeping closes: final settled phase (2.1234 turn) = initial equilibrium (0.1234) + exactly 2 turns within 2e-04 turn.
4. Inter-pulse rearm verified quantitatively: phase at 200 ps = 1.1234 turn = initial + 2π·1; V(N_SEC) = −0.000 µV — the second pulse starts from the same local operating condition as the first (mod 2π).
5. Artifact QA: 23,999 rows, finite, strictly increasing time, no missing columns; stop time extended to 300 ps as declared in the manifest (recorded deviation), all other numerical settings unchanged.

## Adversarial checks

1. **Could the second "slip" be an echo/ringing artifact of the first?** No: it is driven by a physically distinct second PWL pulse (I_DIRECT knees at 204.51–264.51 ps), separated by a 60 ps quiet window containing zero segments >0.02 turn and |V| < 0.3 µV.
2. **Could the two events be one long running state miscounted?** No: segments are direction-monotonic pieces of a continuous unwrapped trace whose total is exactly +2 turns; a free-running state would show continued accumulation past 258.5 ps, but the post window is flat.
3. **Is the near-identical Δφ suspicious (copy-paste)?** The values differ in the 6th decimal (1.033314 vs 1.033315) and arise from independent integrations over different windows of the same deterministic simulation; exact equality is not expected because the second pulse starts from equilibrium+1 rather than equilibrium+0 (identical mod 2π).
4. **Stop-time deviation:** extending .tran to 300 ps is required by the two-event research question and is declared in the manifest; no accepted artifact relied on the 170 ps convention for this fixture family.
5. **Storage guard:** JM signs preserved at 280–295 ps despite two output-stage switching events — receiver activity did not corrupt BVM state.
6. **Interpretation discipline:** verdict limited to "repeatable local single-slip behavior under two-pulse direct drive"; explicitly not an SFQ receiver claim; Unknown lists separation/count/margin/convergence gaps.

## Disposition

Artifact set valid; preregistered analysis executed as registered; **bounded verdict `REPEATABLE_TWO_PULSE_SINGLE_SLIP`**. The single-slip primitive demonstrated in R2-F is shown to repeat across two pulses with exact phase bookkeeping and clean rearm. Per directive, no further direct-drive tuning follows; next work item is the receiver architecture comparison under its own preregistration.
