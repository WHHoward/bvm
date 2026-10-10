# C4R28 manual functional-regression read-only analysis

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Scope lock

- Parent HEAD: `e246b41421e4341bf43f5a6c92797dd990cc6889`.
- Input evidence: the 28 already-existing `C4R28_210_*` run directories listed in
  `ANALYSIS_SCOPE.json`; anchors A045-A047 are read-only references only.
- Work type: read-only raw reanalysis, mechanical QA, summary visualization and
  evidence packaging. No JoSIM execution, no circuit/config/raw edits, no
  parameter or timing changes, no follow-up experiments.
- Required physical solve count for this work unit: **0**.
- Input encoding: R1 is ROW bit 0 / least-significant bit; C1 is the highest
  valued COL bit / leftmost bit. Verify from the batch script, env snapshots,
  result records, and active-crosspoint lists.
- Analysis uses raw.csv actual stored timestamps and half-open windows:
  ARRAY_FINAL_READ `[110,121) ps`, PRE_CLOCK `[121,210) ps`, BEFORE_CLOCK
  `[0,210) ps`, CLOCK_EDGE `[210,215) ps`, POST_CLOCK `[215,300) ps`, and TOTAL
  `[0,300) ps`.
- `P(...)` remains radians; phase divided by 2π is navigation arithmetic only.
  Same-JJ phase/voltage integration comparisons must use the same run, JJ,
  direction, exact rows, and actual timestamp grid.
- Existing run metrics explicitly say `actual_product_bit_decoding` was not
  performed because no decode threshold was preregistered. This analysis will
  not invent or tune a threshold. Therefore all bit-level product candidates
  remain `INDETERMINATE` unless a previously frozen rule is found in bound
  evidence; no scientific pass/mismatch claim will be inferred from voltage
  areas or phase turns alone.
- Missing probes are `UNKNOWN`; no values are inferred from other stages.
- HTML is local-only and excluded from all ZIPs. Existing per-run classic
  `josim-plot2.py` pages are preserved; this work adds only compact derived
  comparison graphics.

## Acceptance

- Exactly 28 expected distinct input pairs map one-to-one to valid run IDs.
- Every run has valid raw SHA and artifact/mechanical/plot QA; common circuit
  deck SHA matches anchor A045; effective config differs only by CASE and
  encoded operands.
- Independently recomputed raw-derived metrics preserve raw SHA before/after.
- Candidate decode limitation, missing T1 internal probes, and any duplicate
  raw-content hashes are explicitly recorded.
- Analysis outputs and all ZIP members are SHA-bound; no old raw is recopied.
