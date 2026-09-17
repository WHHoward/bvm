# LS3 physicalization next-step comparison

This is a read-only, facts-only comparison of the three independently
registered experiments run from parent `1348140f17f0d9467dc42238eaa1e252e877e07a`.
It does not add a solve, alter canonical BVM/QB files, or assign a scientific
mechanism or route winner.

| route | intervention location | physical passive element? | N2 (`0011`) | N3 (`0111`) | N1 (`0001`) | N4 (`1111`) | recorded BVM/bridge trajectory change | main limitation | mechanism evidence status |
|---|---|---|---:|---:|---:|---:|---|---|---|
| A: LS3 ideal timing upper bound | Per-instance physical LS3 branch replaced by exact stored-grid ideal `I(L_S3)` replay; `R_S` retained; QB/JSL/JTL unchanged | No; ideal current replay counterfactual | `0.5 ps: 2`; `0.6 ps: 1` | `0.5 ps: 3`; `0.6 ps: 3` | Not run | Not run | At `0.5 ps`, N2 second response/re-arm gate passed; at `0.6 ps`, the recorded N2 ordered-chain count was 1. N3 fourth chain was absent in both delayed cases. Full branch/JJ/COMMON/JSL/QB/JTL raw metrics are in the experiment analysis. | Ideal replay is not a physical delay or passive-equivalence proof; only the registered 0.5/0.6 ps points were tested. | `NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED` |
| B: LS3 physical mutual-RL | Physical `L_S3=0.5 pH` and `R_S=3 ohm` retained inside per-case BVM clone; passive `L_AUX=10 pH`, `R_AUX=20 ohm`, `K_AUX` directly coupled to physical LS3; `M=0/0.25/0.50/0.75 pH` | Yes, within the simulated lumped passive model | `2` at every M point | `4` at every M point | Not run; no conditional M selected | Not run; no conditional M selected | M=0 no-op gate passed. N3 fourth BJ1 was `124.2 ps` at M=0/0.25 and `124.4 ps` at M=0.50/0.75; active phase and LS3 auxiliary records are retained per run. Mechanical labels for positive points were `LS3_MUTUAL_TOO_WEAK`. | Discrete four-point M matrix only; no additional L/R/C, polarity, split-LS3, or sentinel case. | `NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED` |
| C: current-QB transformer isolation | Direct galvanic `JSL8 -> QBIN` removed; frozen R6-A-scale passive interface `R_PRI=12 ohm`, `L_PRI=0.20 pH`, `L_SEC=2.00 pH`, `K=0.50` (`M=0.31622776601683794 pH`) inserted between JSL8 source side and QBIN; canonical QB/JTL retained | Yes, within the simulated lumped passive model | `0` ordered phase chains | `0` ordered phase chains | Not run | Not run | Transformer primary/secondary I/V, power/timing and upstream BVM/LS3/RS/COMMON/JSL records were captured. The fixed pair did not pass the registered N2/N3 conditional gate. | This is a galvanic-interface/topology isolation counterfactual at one frozen point; no R6-B or other isolation point was authorized. | `NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED` |

## Scope and evidence pointers

- A: `test/exploration/bvm-rloop-ls3-delay-upper-bound-v1-20260917/analysis/mechanical_analysis.json`
- B: `test/exploration/bvm-rloop-ls3-mutual-rl-v1-20260917/analysis/mechanical_analysis.json`
- C: `test/exploration/bvm-qb-transformer-isolation-current-qb-v1-20260917/analysis/mechanical_analysis.json`

All phase values remain raw radians. Any turns are navigation values derived
as `rad/(2*pi)`; they are not SFQ counts. A/B/C were mechanically QA-checked
and stopped at `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.

No row above is a physical mechanism conclusion. The present evidence only
records the observed response under each bounded intervention and the route's
known counterfactual or coverage limitation.
