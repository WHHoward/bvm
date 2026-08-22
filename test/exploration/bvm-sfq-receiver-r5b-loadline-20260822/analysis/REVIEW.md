# R5-B numerical and adversarial review

## Scope

Claim under review: "the minimal load-line branch, in its functionally active wiring (across B_SET), acted as plain extra junction damping — suppressing the R5-A oscillation by 3–8× without producing any slip; verdict `R5B_STILL_BOUNDED_OSCILLATION`." Also reviewed: the v1→v2 wiring iteration legitimacy.

## Numerical checks

1. Oracle identical to R5-A (direction-neutral complete segments, onset window, area residual ≤0.05 turn): zero complete segments in all eight runs (four v1 + four v2).
2. v1 functional-absence proof: I(RJ1) ≤1.8e-22 A and P(BJL1) ≤3e-17 rad across the read1 window — the branch sat on N_A which the solver pinned at ground; V(B_SET) swings ±800 µV appear entirely on N_B.
3. v2 activity proof: |I(BJL1)| up to 3.4 µA, |I(RJ1)| up to 1.43 µA — the relocated branch genuinely participates.
4. Damping quantification: R5-B φ range [−0.0695, 0] vs R5-A [−0.2496, +0.1844]; V peak 143.3 vs 1087.5 µV. Monotonic suppression consistent with RCSJ parallel-resistor damping arithmetic.
5. Guards preserved in all eight runs; controls clean; artifacts valid (13,599 rows each).

## Adversarial checks

1. **Was the v1→v2 rewire a silent protocol violation?** No: v1 was diagnosed as functionally absent within the same session, both wirings' raw data and logs are preserved separately (`raw/` vs `raw-v2/`), and the report presents both. The preregistration's intent ("minimal BJL1/RJ1-class load-line branch") was implemented in v2 per the paper's actual functional placement; v1 was a wiring error caught by its own zero-current signature.
2. **Could the shunt have been given a chance in a better position?** The position tested (across B_SET) is the only one that constitutes "shunt across the SET junction." The finding is about that specific hypothesis — that a shunt across the SET junction converts oscillation to escape. It does not and cannot test the paper's actual topology (RJ1 from loop node to ground with BJs in the input arm and RB bias routing), which requires the full core.
3. **Is "extra damping" the right physics?** Yes, and it is verifiable from the numbers: parallel 100 Ω with RN=320 Ω gives R_eff ≈ 79 Ω, raising damping by ~4×; the observed excursion collapse (~7× in phase, ~7.6× in voltage) is consistent with stronger damping plus current diversion to the branch.
4. **Guard integrity:** JM signs preserved; SL/N6 ordering intact; B_TRIG multi-turn retained — the added branch did not corrupt source or storage.
5. **Scope discipline:** single new branch, no sweep of its values, no output regeneration, no JTL/T1, rearm not applicable (no PASS).

## Disposition

Both iterations validly executed and honestly reported; **bounded verdict `R5B_STILL_BOUNDED_OSCILLATION`** confirmed with the structural lesson that the QB load-line function is not detachable from the QB bias topology. Per the preregistered plan, next work returns to full-QB-core / flux-bias architecture assessment rather than further ad-hoc minimization.
