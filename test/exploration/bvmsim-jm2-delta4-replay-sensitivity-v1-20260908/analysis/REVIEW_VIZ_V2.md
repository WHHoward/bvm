# REVIEW — delta4_v2 visualization rework

## Numerical review

- PASS: all QB critical CSVs are actual half-open [118,140) windows with
  220 stored samples, first sample 118.0 ps and last stored sample 139.9 ps.
- PASS: all JTL downstream CSVs are actual half-open [118,180) windows with
  620 stored samples, first sample 118.0 ps and last stored sample 179.9 ps.
- PASS: critical pages contain the complete 25-label QB internal view.
- PASS: standalone and downstream pages contain JTL1-JTL6 B01/B02 P/V/I
  and stage-output labels.
- PASS: pairwise CSV raw tracks are copied from exact N4/intervention raw
  timestamps; non-phase derived deltas are recomputed from signed values.
- PASS: phase deltas are recomputed from independently unwrapped complete
  raw traces before window selection and subtraction; wrapped subtraction is
  false.
- PASS: no raw hash changed while creating v2 data or HTML, and all v1
  hashes remained unchanged.
- UNKNOWN: no physical convergence or sensitivity claim is made by this
  visualization-only rework.

## Adversarial review

- Structure probe PASS: all four run directories contain the eight required
  plot classes plus a per-run index.
- Pairwise probe PASS: every run has N4_VS_RUN_QB_RAW_DELTA and
  N4_VS_RUN_JTL_RAW_DELTA with N4 raw, intervention raw and derived delta
  tracks.
- Source-kind probe PASS: every BVM source page contains the exact marker
  IMMUTABLE_PASSIVE_SOURCE_REFERENCE / NOT REPLAY-RUN RAW and the N3/N4
  passive raw hashes.
- Stale-artifact probe PASS: v2 inputs point to the intended run raw or
  windowed/derived CSV, while v1 is preserved.
- Tool-boundary probe PASS: the v2 renderer invokes josim-plot2.py only and
  contains no JoSIM solver command.
- Overclaim probe PASS: plot titles and metadata do not use SFQ count or
  event count semantics.

The v2 package changes visualization organization and QA only. It does not
change raw data, decks, metrics, scientific Findings, BOUNDED_RESULT,
UNKNOWN, or MIXED_OR_UNRESOLVED.
