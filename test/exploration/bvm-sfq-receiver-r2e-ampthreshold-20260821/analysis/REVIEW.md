# R2-E numerical and adversarial review (recovered package)

## Recovery scope

The runs commit `8c95eb6` shipped raw evidence without the declared analysis artifacts. This package regenerates them strictly from the committed raw CSVs. Verification performed before regeneration:

1. Raw integrity: SHA-256 of all three committed CSVs matches the committed `sha256sums.txt` line-for-line (`227581dc…`, `62ba0dd1…`, `91018c26…`); row counts 13,599 each. No corruption → no JoSIM re-run needed, per the recovery constraint.
2. No raw, netlist, or manifest science content was modified; the manifest's research question, matrix, and criteria are unchanged.

## Numerical checks

1. Event oracle identical to R2-B/C/D: continuous adjacent-sample unwrapped P(B_OUT|XTRIG), monotonic segment ≥1.0 turn, start ≤130 ps, same-segment direct V(B_OUT|XTRIG) trapezoid area within 0.05 turn on actual timestamps.
2. Zero complete-2π segments exist in any run; largest segments are 0.101389 / 0.123538 / 0.154960 turn — all relaxation legs of reversible excursions with area residuals ≤4.9e-08 turn.
3. Whole-run net drift is +0.12341 turn in every run, exactly the initial φ=0 → arcsin(0.7)/2π equilibrium establishment; this proves full reversibility and rules out hidden net phase accumulation.
4. POST windows are stable (phase range ≤0.0033 turn, V decaying to −0.00 µV) — no free-running, no ringing, no multi-turn.
5. KCL closure verified at peak instants: i_BOUT = I_BIAS + I_DIR − I_LSEC − I_RDAMP within rounding across all three runs.

## Adversarial checks

1. **Stop-rule audit:** sequential ascending execution with per-run qualifying checks; no point qualified, so running all three was required, not a violation. Recorded explicitly in the summary JSON (`stop_rule_compliance`).
2. **Could a complete transition hide between samples?** The unwrapped phase uses adjacent-sample deltas with ±π wrap handling at dt≈0.0125–0.025 ps; a full 2π slip between samples would require V > ~80 mV, five orders above observed values (≤56.5 µV). Physically impossible here.
3. **Is "8 nA gap" meaningful given numerical noise?** The gap is computed from the same CSV used for all R-series analyses; current resolution at these amplitudes is far below nA. The asymptotic-saturation trend (140→18→8 nA for +1 µA total) is monotonic and consistent across independent runs.
4. **Creep-race interpretation:** labeled Inference; supported by measured plateau phase velocity (~1.3 turn/ns from V≈2.7 µV via the Josephson relation) versus the ~10 ps drive-decay window. The alternative (a static solution exists but was missed numerically) is disfavored because V ≠ 0 and dφ/dt > 0 persistently during the plateau.
5. **Guard integrity:** storage signs preserved in every run; background identical to R2-C/D family; controls inherited from the same fixture design.
6. **Recovery hygiene:** analysis code path (`analyze_lib.py` + inline aggregation) is the same one used in-session; results reproduce the numbers previously reported interactively (largest segments identical to 6 decimals).

## Disposition

Artifact package restored as declared by the manifest: `r2e-summary.json`, `R2E_AMPTHRESHOLD_REPORT.md`, `REVIEW.md`, regenerated `sha256sums.txt`. Bounded verdict unchanged and now fully documented: **`NO_THRESHOLD_IN_BOUNDED_MATRIX`**, with stop-rule compliance confirmed and the creep-vs-decay mechanism quantified. No new experiment started; no parameters touched.
