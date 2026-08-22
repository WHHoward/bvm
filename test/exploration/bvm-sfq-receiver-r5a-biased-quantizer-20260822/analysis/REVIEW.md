# R5-A numerical and adversarial review

## Scope

Claim under review: "at bias 4.2 µA the quantizer state executed a large plasma oscillation (±0.18–0.25 turn, loop current ±4.4–4.9 µA, V peak 1.09 mV) but completed zero phase slips; verdict `R5A_NO_SET_EVENT`." The dangerous failure mode here is a missed event (a real slip misclassified as oscillation), so this review focuses there.

## Numerical checks

1. Oracle per amended preregistration: direction-neutral complete segments (≥1 turn) of unwrapped P(B_SET|XTRIG), onset in [97,130) ps, same-JJ V-area residual ≤0.05 turn. Zero complete segments in all four runs; read1 net window V-area −0.0265 turn ≈ 0.
2. Missed-slip hunt: a hidden slip between samples requires |V| sustained near Φ0/Δt ≈ 165 mV; observed |V| max is 1.09 mV — two orders below even the transient peak needed for an inter-sample slip. Additionally the whole-run net phase change is bounded (<0.26 turn), so no net topological charge exists to hide.
3. Boundary-crossing reconciliation: displacement crossed the static reverse-critical distance (0.2496 vs 0.1672 turn) without a slip. Verified this is dynamically consistent: at the extremum (t=113.29 ps) V passes through zero with I_BSET steady at +2.43 µA — a turning point of bounded oscillation, not a running state. The 1.09 mV burst is at a different time/phase location and is mutual-coupling feedthrough of the B_TRIG multi-turn burst.
4. Controls exactly clean; storage signs preserved; gauge leakage ≤5.6e-22 A (amendment assumption re-verified in-loop).
5. All CSVs artifact-valid: 13,599 rows, finite, strictly increasing time; single timestep, no convergence claim.

## Adversarial checks

1. **Is "plasma oscillation" an over-interpretation?** The trajectory shows smooth sinusoid-like turning points with V→0 crossings and steady supercurrent — the signature of bounded phase motion on the junction's tilt-washboard. Labeled Inference where interpretive; the raw facts (no complete segment, zero net area, V zero-crossings at extrema) stand alone.
2. **Oracle amendment legitimacy:** the direction-neutral amendment was made *before* execution, justified by measured operating-point asymmetry (reverse critical nearer). It widened, not narrowed, the event definition — no risk of hiding a positive result.
3. **Asymmetry explanation vs data:** the inference that symmetric biphasic drive cannot escape predicts zero net area — confirmed (−0.0265 turn). It also predicts the excursion should be nearly symmetric around OP: measured [−0.2496, +0.1844] — mildly asymmetric toward negative, consistent with the negative-lobe dominance; recorded honestly.
4. **Guard integrity:** all back-action checks pass; the quantizer load did not degrade B_TRIG behavior (range 5.343 turns retained) nor BVM storage.
5. **Scope discipline:** single point, four cases, one run each; no bias sweep after failure; rearm withheld; JTL/T1 untouched; failure boundary limited to this instance.

## Disposition

Artifacts valid; preregistered analysis executed as registered; **bounded verdict `R5A_NO_SET_EVENT`** with a decisive mechanistic finding: symmetric biphasic drive around a stable operating point produces bounded plasma oscillation that can cross the static critical boundary in displacement without escaping — the missing ingredient is irreversibility at the crossing (the QB shunt/load-line function). This upgrades the paper-QB core from "possibly incidental structure" to "evidently necessary function" and defines the next falsifiable step precisely.
