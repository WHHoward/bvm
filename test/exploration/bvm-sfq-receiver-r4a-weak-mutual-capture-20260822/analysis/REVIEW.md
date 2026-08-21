# R4-A amended-run numerical and adversarial review

## Scope

Claim under review: "with R_GAUGE=1 GΩ the simulation runs cleanly; read1 produces zero complete B_SET segments and no persistent fluxoid state (loop peak 4.874 µA vs ~10.34 µA half-quantum boundary); verdict `R4A_NO_PERSISTENT_READ1_STATE`." Reviewed for both correctness of the negative result and legitimacy of the amendment.

(The earlier formulation-failure review is preserved as `REVIEW_INCONCLUSIVE_RUN.md`.)

## Numerical checks

1. Amendment scope: only `R_GAUGE N_CAP1 0 1G` added plus its probe; all scientific parameters (L_TX, |K|, polarity sign, L_H, AREA, bias) unchanged; single formulation point, no sweep.
2. Gauge-necessity verification by direct probe: max |I(R_GAUGE)| = 2.82e-22 A across all four runs — sixteen orders of magnitude below loop currents. The element is numerically necessary and physically nil; capture physics is not perturbed.
3. Event oracle per preregistration applied to P(B_SET|XTRIG): zero complete (≥1 turn) segments in any case; largest sub-turn excursions only.
4. Fluxoid-balance cross-check: Φ0/L_H = 20.68 µA state spacing; delivered loop-current peak 4.874 µA = 0.236 of the ~10.34 µA half-quantum boundary; whole-run net phase change −0.0555 turn ≈ 0 (loop stayed in n=0). Independent lines of evidence agree.
5. False-switch hunt: J_SET total current touched −5.269 µA (< −Ic) at t=116.575 ps. Adversarially examined: V(B_SET) passes through zero at that instant with large dV/dt — the total current includes a capacitive spike; unwrapped phase shows no slip (φ ≈ +0.0709 turn stable across the excursion). Supercurrent channel never crossed criticality. Correctly not counted as an event.
6. Guards: JM signs preserved in all runs; read1 B_TRIG response retained; controls clean.
7. All four CSVs artifact-valid: 13,599 rows, finite, strictly increasing time.

## Adversarial checks

1. **Could the gauge resistor have created a hidden leakage path that prevented capture?** Leakage is 2.8e-22 A measured; the loop current reached 4.87 µA during the transient and returned to ~0 because no fluxoid was trapped — the return-to-zero is a state-topology fact (n=0 is the only accessible state at these flux levels), not gauge-resistor drainage. Drainage through 1 GΩ at µV nodes cannot produce µA-scale current reversal.
2. **Was the precheck's margin estimate wrong?** The precheck itself flagged its estimate as optimistic ("does not assume that the loop current follows Phi_ext/L_H instantaneously once J_SET dynamics begin"). The simulated shortfall (factor ≈2.1 vs the state boundary) is consistent with that caveat; the estimate guided point selection and did not mislead the oracle.
3. **Polarity audit:** K sign = −0.80 implements the preregistered additive orientation (read1 negative I(L_TX) lobe adds to +3 µA bias). The data confirm the negative lobe dominates the loop response (I_LH peaks align with negative I_L_TX lobes).
4. **Probe-scope fix legitimacy:** initial amended runs probed `|XCAP` (a node-name mistake); JoSIM device labels take the subckt instance suffix (`|XTRIG`) per `Netlist::expand_io`. Renaming probes changed reporting only, not circuit semantics. Failed-run logs preserved as evidence.
5. **Stop-rule/scope discipline:** four cases, one run each in the amended formulation; no sweep of gauge value or any physics parameter; rearm correctly withheld on primary failure.

## Disposition

Amended execution valid end-to-end; **bounded verdict `R4A_NO_PERSISTENT_READ1_STATE`** confirmed with a quantitative structural mechanism (delivered flux ≈0.24 of the trapping boundary). This falsifies the weak-mutual direct-capture instance and, by the margin arithmetic, the whole "passive weak-mutual capture at these flux levels" sub-family — while leaving biased-quantizer architectures (QB-style) untouched.
