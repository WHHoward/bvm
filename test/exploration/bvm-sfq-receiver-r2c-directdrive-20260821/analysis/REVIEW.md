# R2-C numerical and adversarial review

## Review scope

Strongest bounded claim: "with the measured narrow pulse shape (FWHM 0.27 ps), no amplitude in {2,3,4,5} µA injected directly into N_SEC produces a complete B_OUT transition; the junction-drive transfer ratio is constant at 22.4 % and the junction never reaches Ic." This review tests that claim against the five runs. It does not upgrade anything to Candidate, does not bound amplitudes beyond 5 µA, and does not claim duration independence.

## Numerical checks

1. Event oracle identical to R2-A/R2-B: continuous adjacent-sample unwrapped P(B_OUT|XTRIG), monotonic segment ≥1.0 turn, start ≤130 ps, same-segment direct V(B_OUT|XTRIG) trapezoid area within 0.05 turn on actual CSV timestamps. No I_peak>Ic or voltage-peak oracle used anywhere.
2. Largest segment anywhere is 0.013792 turn (amp50u0); area residual +3.1e-06 turn; no complete segment exists in any run; POST window has exactly zero voltage activity.
3. Independent fresh-implementation spot check (separate unwrapping and segmentation code path) reproduces amp50u0 largest = 0.013792 turn exactly.
4. All five CSVs artifact-valid: 13,599 rows, finite, strictly increasing time, no missing columns; single timestep setting, no convergence claim.
5. Linearity: phase ratios match amplitude ratios to 0.2 % (2.505 vs 2.5), confirming deep subcritical linear operation with no threshold proximity signature.

## Adversarial checks

1. **Could the fixture have failed to inject?** No: drive diagnostics show clean amplitude-proportional ΔI(B_OUT) (+0.447→+1.118 µA) and ΔV(N_SEC) (+23.8→+59.5 µV) responses; the pulse is present and active in every run. The control run is exactly zero, proving the response comes from I_DIRECT.
2. **Polarity check:** positive injection produced increasing-direction phase segments and positive ΔI(B_OUT), matching the real read1 forward-lobe direction verified from R2-B raw data with KCL closure. Sign conventions were measured, not assumed.
3. **Is "22.4 % transfer" an artifact of reading peaks at different times?** The ratio is taken between same-run maxima of ΔI(B_OUT) and the known source amplitude; it is constant across four amplitudes, which is the expected linear-network behavior and unlikely to arise coincidentally from timing artifacts.
4. **Could a longer simulation reveal late switching?** The pulse ends at 105.05 ps; POST window (130–170 ps) shows zero activity in all runs; there is no slow relaxation mechanism left to trigger.
5. **Was the matrix stopped honestly?** Yes: per the preregistered plan, no amplitude above 5 µA was run after the sub-turn pattern was clear, and no duration/shape/AREA/bias/damping axis was opened without authorization.
6. **Known limitation recorded:** the unipolar triangle simplifies away the real chain's biphasic structure; the comparison "real chain delivers more than 5 µA direct" is qualitative and bounded by this shape choice. Also the 0.27 ps FWHM spans only ~11–22 samples at dt=0.0125–0.025 ps; convergence at this width is explicitly listed as Unknown.
7. **Interpretation discipline:** Observed/Derived separated; node-shunt explanation labeled Inference; quasi-static expectation labeled as expectation, not result; Unknown lists five explicit gaps including the dimensionally-correct charge/voltage estimates (an earlier C·Φ0 charge benchmark was discarded as dimensionally wrong and does not appear in the report).

## Disposition

Artifacts valid; preregistered analysis executed as registered; **bounded verdict `NO_THRESHOLD_IN_BOUNDED_MATRIX`** for the amplitude axis at the measured narrow shape, with a quantitative failure mode (22.4 % transfer, peak i_BOUT 8.12 µA < Ic, strictly linear response). This redirects receiver design toward the (amplitude × duration) activation boundary rather than either parameter alone.
