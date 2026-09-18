# Evidence manifest — BVM R-loop one-shot tuning v1

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Identity and authority

- Experiment: `bvm-rloop-one-shot-tuning-v1-20260918`
- Parent HEAD: `a80302e44a75a42991a00f0175fb93ac580dd42`
- Remote `bvm/master`: `a80302e44a75a42991a00f0175fb93ac580dd42`
- Study phase: `EXPLORATORY`
- Solver: `build/josim-cli`, version/hash recorded in every run metadata.

## Run order

```text
A000_CANONICAL: PASSIVE_N0_0000, PASSIVE_N1_0001, PASSIVE_N2_0011, PASSIVE_N3_0111, PASSIVE_N4_1111
A001:           PASSIVE_N0_0000, PASSIVE_N1_0001, PASSIVE_N2_0011, PASSIVE_N3_0111, PASSIVE_N4_1111
A002:           PASSIVE_N0_0000, PASSIVE_N1_0001, PASSIVE_N2_0011, PASSIVE_N3_0111, PASSIVE_N4_1111
A003:           PASSIVE_N0_0000, PASSIVE_N1_0001, PASSIVE_N2_0011, PASSIVE_N3_0111, PASSIVE_N4_1111
```

## Mechanical QA

- `qa/raw_qa.json`: `PASS`, 20 raw files, JoSIM grid `0…199.9 ps`, 1999 rows each.
- `qa/plot_qa.json`: `PASS`, 100 grouped plots, 4 compact review pages, no atlas, no cross-run comparison.
- Each run has a signal manifest. Unsupported/not-emitted quantities, if any,
  are explicit; no signal is silently substituted.

## Raw and derived artifacts

- `runs/`: immutable raw/deck/stimulus/log/metadata evidence.
- `analysis/case_metrics.json`: registered-window arithmetic and R-loop activity descriptions.
- `analysis/gate_s_comparison.json`: candidate minus A000 mechanical comparison; no Gate verdict.
- `analysis/per_signal_window_metrics.csv`: S-loop/R-loop signal-window metrics.
- `analysis/population_metrics.csv`: passive `I(B_JSL8)` metrics.
- `runs/<CASE_ID>/REVIEW_SUMMARY.md`: human-readable per-candidate summary.
- `plots/index.md`: compact review navigation.

## Interpretation boundary

No winner, mechanism, one-shot claim, SFQ count, storage Gate, QB conclusion,
or architecture recommendation is assigned. The evidence is waiting for a
separate scientific review.

