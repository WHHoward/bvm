# R15-D execution report

Verdict: **`JQ_CAUSAL_NEAR_THRESHOLD`**

This report audits the single preregistered split-node + independent J_Q bias + RL refractory compressor point. No J_OUT, DCSFQ, JTL, or T1 is present.

## Matched cases

| case | B_DET largest (turn) | B_SET largest (turn) | B_SET area (turn) | B_Q activity (turn) | B_Q largest (turn) | B_Q area (turn) | B_Q events | I_BSET activity min..max (uA) | I_LQ depletion (uA) | recovery 90% (ps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| logical1-read0-control | -8.43521e-05 | 0.000330565 | 0.000330562 | 0.00739162 | 0.00739162 | 0.00739162 | 0 | 5.57596..5.58869 | -0.120811 | None |
| logical1-read | 3.93404 | -0.153563 | -0.1536 | 0.11179 | 0.11179 | 0.111829 | 0 | 2.11826..9.14518 | 2.45299 | 0.5249999999999915 |
| logical0-read | 0.0299711 | -0.00420873 | -0.00421017 | 0.0104934 | 0.00818392 | 0.00818661 | 0 | 5.42702..5.73096 | 0.008546 | 0.10000000000000853 |
| logical0-read0-control | -8.43521e-05 | 0.000330565 | 0.000330562 | 0.00739162 | 0.00739162 | 0.00739162 | 0 | 5.57596..5.58869 | -0.120811 | None |

## Event boundary

A complete event requires a continuous monotonic unwrapped phase segment of at least one turn and same-segment voltage area consistency under the task-local 5%/0.02-turn rule. Current or voltage peaks alone are not used.

## R15-C comparison

Read1 B_SET current modulation p2p: 7.02692 uA; read0: 0.303935 uA; maximum control: 0.012733 uA; read1/read0 ratio: 23.1198.
The full per-window source comparison against matching R15-C raw cases is stored in `r15d-execution-metrics.json`. This is a differential guard; R15-C's accepted comparison to its canonical/no-receiver baseline remains unchanged.

### Absolute read1 post-window source comparison

The canonical column is the accepted no-receiver read1 post-window reference quoted in the R15-B report; R15-B/R15-C/R15-D are recomputed from their matching raw CSVs.

| quantity | canonical no receiver | R15-B | R15-C | R15-D |
|---|---:|---:|---:|---:|
| V(SL) p2p (uV) | 1.631 | 386.081 | 339.178 | 366.632 |
| V(N6) p2p (uV) | 3.271 | 385.803 | 341.081 | 366.317 |
| I(L_SL) p2p (uA) | 0.1359 | 0.396606 | 0.378862 | 0.396317 |
| P(JM2) p2p (rad) | 0.26827 | 0.396389 | 0.311348 | 0.41967 |
| P(JS1) p2p (rad) | 0.05604 | 0.50997 | 0.43472 | 0.46879 |
| P(JS2) p2p (rad) | 0.00554 | 0.59001 | 0.48916 | 0.5596 |

R15-D remains bounded and has no control running or storage-sign collapse, but its read1 post-window source ringing is still orders of magnitude above the canonical no-receiver reference and is higher than R15-C for the listed SL/N6/JM2/JS probes. The source guard is therefore a bounded extra-back-action disposition, not a pristine isolation pass.

## Settled operating point and refractory diagnostic

In the new READ=0 settled window, representative medians are I(B_SET)=5.57101 uA, I(L_Q)=1.63534 uA, I(R_Q)=0.664661 uA, and I(B_Q)=7.20635 uA. B_Q AREA=.10 has Ic=10 uA; this ratio is only an operating-point diagnostic, not event evidence.
For read1, I(L_Q) reaches -0.817646 uA at 111.2 ps from a pre median of 1.63534 uA, a derived depletion of 2.45299 uA; 90% recovery takes 0.525 ps and the post median is 2.18081 uA. This is an observed L_Q transient, but because B_Q never completes a phase event it is not refractory one-shot evidence.

## Stage disposition

- Stage 1 `UPSTREAM_CAUSAL_PRESERVED`: met for state selectivity; B_DET read1 remains multi-turn and read0/control remain sub-turn, while loaded B_SET current remains strongly read1 selective.
- Stage 2 `JQ_ONE_SHOT`: not met; read1 B_Q largest segment is 0.111790 turn with same-segment area 0.111829 turn, and all read0/control cases have zero complete candidates.
- Stage 3 `REFRACTORY_ESTABLISHED`: not met; L_Q depletion/recovery is visible but no first complete J_Q event exists from which to establish refractory suppression.
- Stage 4 `SOURCE_GUARD`: bounded but not pristine; no startup/free-running or control event, but loaded read1 source ringing remains materially above canonical and is not lower than R15-C on all probes.

## Observed / Derived / Inference / Unknown

- **Observed:** raw phase, same-JJ voltage, currents, node voltages, BVM guard probes, KCL residuals, and L_Q time behavior for each completed case are recorded in the metrics JSON.
- **Derived:** event candidates, phase/area residuals, read1/read0 J_SET modulation ratios, and L_Q depletion/recovery metrics are computed from the same raw run and preregistered windows.
- **Inference:** the verdict is limited to this frozen loaded fixture; it does not generalize to the broader active-stage family.
- **Unknown:** downstream output conversion and JTL transport were not tested by design.
