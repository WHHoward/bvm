# R3-A numerical and adversarial review

## Review scope

Claim under test: "the single preregistered extractor instance produced zero complete B_OUT events; verdict `NO_OUTPUT_EVENT`." This review checks the negative result as rigorously as a positive one — a missed event would be the dangerous failure mode here.

## Numerical checks

1. Event oracle per preregistration: continuous adjacent-sample unwrapped P(B_OUT|XTRIG) over [20,170] ps, monotonic segments, complete = ≥1.0 turn, qualifying requires onset in [97,130) ps and same-segment V-area residual ≤0.05 turn.
2. Zero forward-complete and zero reverse-complete segments exist in any of the four runs. The largest read1 sub-turn activity is far below 1 turn (peak junction drive 8.064 µA vs Ic=10 µA makes a full slip dynamically implausible given R2-E/F evidence).
3. Missed-event hunt: a hidden 2π slip between samples would require sustained |V| > Φ0/Δt ≈ 80 mV-scale; observed |V(B_OUT)| max is 172 µV — five orders below. No aliasing risk at dt≈0.0125–0.025 ps for these dynamics.
4. Controls are exactly clean (|I_BOUT| stays at 7.000 µA bias; zero READ-edge response beyond common-mode blips).
5. All four CSVs artifact-valid: 13,599 rows, finite, strictly increasing time, no missing probe columns.

## Adversarial checks

1. **Was the fixture actually stimulated?** Yes: I(C_ON) shows clear proportional response to B_TRIG voltage excursions (±0.9 µA class), and read1 vs controls differ exactly as the source state dictates. A dead fixture would show zero I(C_ON); it does not.
2. **Polarity check:** C_ON orientation passes both polarities of the alternating onset; the junction drive excursions appear on both sides but never approach criticality.
3. **Could a larger event exist outside [20,170]?** Simulation covers 0–170 ps entirely; pre-20 ps is write-settling with no READ stimulus.
4. **Stop-rule / scope discipline:** four cases only, one run each; no sweeps of C_ON/L_Q/R_Q/bias/AREA; rearm not run because the gate (primary PASS) was not met; JTL/T1 not attached.
5. **Guard integrity:** all seven preregistered back-action guards checked and preserved; notably read1 B_TRIG multi-turn behavior is unchanged from R0b within reading precision, so the extractor did not even perturb the source it taps.
6. **Interpretation discipline:** the differentiator-regime explanation is labeled Inference; the report does not extrapolate to other C_ON values (no-sweep rule) and keeps the failure boundary limited to this instance.

## Disposition

Artifacts valid; preregistered analysis executed as registered; **bounded verdict `NO_OUTPUT_EVENT`** with a quantitative mechanism (differentiator coupling delivers ~1 µA-class spikes vs the ~4.5 µA + ~20 ps hold calibrated requirement). Rearm correctly withheld. This falsifies only the current instance and is fully consistent with the architecture comparison's prediction that capture-and-hold, not edge coupling, is required.
