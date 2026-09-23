# bvm-qb-50ghz-merge-v1-20260922

## Status

`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`

- scientific interpretation = NOT PERFORMED
- automatic follow-up = none
- Phase A/B/C artifact QA = PASS
- Phase C direct MERGE mechanical gate = FAIL
- Phase D integration = NOT RUN by registered stop rule

## OBSERVED

- Phase A contains 14 repeated-read raw runs; Phase B contains 3 rewrite/read raw runs; Phase C contains 26 MERGE raw runs.
- All retained A/B/C raw artifacts passed raw and plot QA.
- The registered terminal response-candidate locator reports A-only=1 and B-only=1.
- The same locator reports the registered aligned 1+1 case as 1 candidate and aligned 2+2 as 1 candidate.
- `MERGE.cir` contains a non-ASCII character in its `.param BiasCoef` line; the source was preserved and not edited.

## DERIVED

- All raw hashes were rechecked after analysis using actual stored time grids.
- Same-JJ QB phase/voltage-area arithmetic records are stored in each run's `analysis/metrics.json`; raw P values remain radians and turn columns are navigation arithmetic only.
- The direct-MERGE gate is mechanically FAIL because registered collision multiplicities are not met.

## INFERENCE

- No scientific mechanism, SFQ count, hardware claim, parameter ranking, or root-cause interpretation was performed.
- The conditional 4-BVM integration was not executed because the pre-registered direct-MERGE gate failed.

## UNKNOWN

- Whether the observed response-candidate collapse reflects MERGE dynamics, source fixture behavior, or another physical mechanism is not established here.
- Physical SFQ count, downstream logical correctness, storage-basin preservation, and 50 GHz system viability remain UNKNOWN.

## Evidence

- `analysis/summary.csv`
- `analysis/FINAL_QA.json`
- `analysis/provenance.json`
- `phase_c_merge_collision/analysis/merge_gate.json`
- `RAW_ANALYSIS_HANDOFF_MANIFEST.json`,
- per-run `raw.csv`, decks, logs, source manifests, QA and review HTML under `phase_a_repeated_read/`, `phase_b_rewrite_read/`, and `phase_c_merge_collision/`.

## Stimulus visualization update

- `plots/STIMULUS_INDEX.html` links every run's registered excitation plots.
- `plots/COMBINED_INDEX.html` now links classic `josim-plot2.py -t sep_comb` figures where excitation and output traces are selected into the same plot invocation.
- Each BVM/QB run has one figure for each WL, BL, and SE source-current group. Each figure also includes `V(QBOUT)` and `V(R_TERM)` from the same `raw.csv`.
- Each MERGE run has one figure containing raw input-pin `V(SFQ_A/B)` and output `V(SFQ_Q)`, `V(SFQ_OUT)`, and `V(R_TERM)`.
- Combined visualization QA: `analysis/CLASSIC_COMBINED_VIZ_QA.json` = PASS for 43 valid runs and 77 classic figures. All selected traces are direct columns from the same run's raw CSV; raw hashes were not changed. The preserved failed solver attempt has no output raw and is listed separately.
