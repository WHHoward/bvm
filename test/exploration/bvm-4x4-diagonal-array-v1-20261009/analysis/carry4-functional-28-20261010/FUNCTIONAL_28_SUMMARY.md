# CARRY4 functional 28 — mechanical raw summary

Status: `MECHANICAL_ANALYSIS_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.

No JoSIM solver was invoked by this analysis (physical solve count for this work unit: 0). All reported phase/voltage values were recomputed from each immutable raw.csv using actual stored timestamps.

## Classification boundary

All 28 rows are `INDETERMINATE` for product-bit matching. The bound run metrics explicitly state `actual_product_bit_decoding = NOT_PERFORMED; no decode threshold preregistered`. This analysis does not invent a threshold or round signed voltage-area/Φ0 values to bits. Thus this is not a report of 0 matches or 28 physical failures; candidate match and mismatch counts are both zero, and 28 are undecoded.

The raw-derived output areas and same-JJ phase/area arithmetic are presented as measurements/arithmetic, not as SFQ counts, bit values, or a scientific functional verdict. For T1 stages D0/D1/D4/D5/D6, the stored focus probe set lacks B_J2/B_J9/B_J10; those internal values remain `UNKNOWN`. B_J1 and B_J11 P/V and S/C output waveforms are present. D2/D3 have the broader internal T1 P/V set.

## Coverage and QA

- Unique input pairs/runs: 28/28.
- Artifact+mechanical QA: 28/28 PASS.
- Raw/static/chain/plot/provenance QA: 28/28/28/28/28 PASS, each of 28.
- Effective circuit deck SHA equals A045: 28/28.
- Exact PWL input mapping checks: 28/28 PASS.
- Raw-recomputed metrics match stored same-version mechanical metrics: 28/28.
- Independent raw arithmetic spot checks: 2 run(s); maximum absolute same-JJ area difference versus platform arithmetic: 0 Φ₀ arithmetic.
- Candidate statuses: 0 `CANDIDATE_MATCH`, 0 `CANDIDATE_MISMATCH`, 28 `INDETERMINATE`.
- Existing experiment manifest remains at observed solve count 75 with registered maximum 41; this analysis added no authorization record.
- Duplicate raw-content hashes: 1 group(s); distinct case/run evidence was preserved.
- Manual wrapper run logs empty: 28 of 28; each run still has its own solver stdout/stderr/run.log artifacts.
- All generated HTML remains local and is excluded from the DELTA archive.

## Input, encoding and candidate results

ROW encoding: R1 is bit 0 / least-significant bit. COL encoding: C1 is the highest-valued / leftmost bit. Expected output bits below are theoretical LSB-first 8-bit products only.

| Run | A×B | ROW_BITS | COL_BITS | Theoretical product | Theoretical bits LSB→MSB | Candidate status |
|---|---:|---|---|---:|---|---|
| A048_C4R28_210_15x14 | 15×14 | 1111 | 1110 | 210 | 01001011 | INDETERMINATE |
| A049_C4R28_210_14x15 | 14×15 | 0111 | 1111 | 210 | 01001011 | INDETERMINATE |
| A050_C4R28_210_14x14 | 14×14 | 0111 | 1110 | 196 | 00100011 | INDETERMINATE |
| A051_C4R28_210_15x13 | 15×13 | 1111 | 1101 | 195 | 11000011 | INDETERMINATE |
| A052_C4R28_210_13x15 | 13×15 | 1011 | 1111 | 195 | 11000011 | INDETERMINATE |
| A053_C4R28_210_15x11 | 15×11 | 1111 | 1011 | 165 | 10100101 | INDETERMINATE |
| A054_C4R28_210_11x15 | 11×15 | 1101 | 1111 | 165 | 10100101 | INDETERMINATE |
| A055_C4R28_210_15x7 | 15×7 | 1111 | 0111 | 105 | 10010110 | INDETERMINATE |
| A056_C4R28_210_7x15 | 7×15 | 1110 | 1111 | 105 | 10010110 | INDETERMINATE |
| A057_C4R28_210_7x7 | 7×7 | 1110 | 0111 | 49 | 10001100 | INDETERMINATE |
| A058_C4R28_210_7x14 | 7×14 | 1110 | 1110 | 98 | 01000110 | INDETERMINATE |
| A059_C4R28_210_14x7 | 14×7 | 0111 | 0111 | 98 | 01000110 | INDETERMINATE |
| A060_C4R28_210_9x13 | 9×13 | 1001 | 1101 | 117 | 10101110 | INDETERMINATE |
| A061_C4R28_210_13x9 | 13×9 | 1011 | 1001 | 117 | 10101110 | INDETERMINATE |
| A062_C4R28_210_5x10 | 5×10 | 1010 | 1010 | 50 | 01001100 | INDETERMINATE |
| A063_C4R28_210_10x5 | 10×5 | 0101 | 0101 | 50 | 01001100 | INDETERMINATE |
| A064_C4R28_210_1x1 | 1×1 | 1000 | 0001 | 1 | 10000000 | INDETERMINATE |
| A065_C4R28_210_1x15 | 1×15 | 1000 | 1111 | 15 | 11110000 | INDETERMINATE |
| A066_C4R28_210_15x1 | 15×1 | 1111 | 0001 | 15 | 11110000 | INDETERMINATE |
| A067_C4R28_210_2x15 | 2×15 | 0100 | 1111 | 30 | 01111000 | INDETERMINATE |
| A068_C4R28_210_15x2 | 15×2 | 1111 | 0010 | 30 | 01111000 | INDETERMINATE |
| A069_C4R28_210_4x15 | 4×15 | 0010 | 1111 | 60 | 00111100 | INDETERMINATE |
| A070_C4R28_210_15x4 | 15×4 | 1111 | 0100 | 60 | 00111100 | INDETERMINATE |
| A071_C4R28_210_8x15 | 8×15 | 0001 | 1111 | 120 | 00011110 | INDETERMINATE |
| A072_C4R28_210_15x8 | 15×8 | 1111 | 1000 | 120 | 00011110 | INDETERMINATE |
| A073_C4R28_210_0x0 | 0×0 | 0000 | 0000 | 0 | 00000000 | INDETERMINATE |
| A074_C4R28_210_0x15 | 0×15 | 0000 | 1111 | 0 | 00000000 | INDETERMINATE |
| A075_C4R28_210_15x0 | 15×0 | 1111 | 0000 | 0 | 00000000 | INDETERMINATE |

## Task-listed input group counts

| Group | Cases | Candidate status |
|---|---:|---|
| G01 (`15×14, 14×15, 14×14`) | 3 | INDETERMINATE for each case |
| G02 (`15×13, 13×15, 15×11, 11×15`) | 4 | INDETERMINATE for each case |
| G03 (`15×7, 7×15, 7×7`) | 3 | INDETERMINATE for each case |
| G04 (`7×14, 14×7, 9×13, 13×9`) | 4 | INDETERMINATE for each case |
| G05 (`5×10, 10×5`) | 2 | INDETERMINATE for each case |
| G06 (`1×1, 1×15, 15×1`) | 3 | INDETERMINATE for each case |
| G07 (`2×15, 15×2`) | 2 | INDETERMINATE for each case |
| G08 (`4×15, 15×4`) | 2 | INDETERMINATE for each case |
| G09 (`8×15, 15×8`) | 2 | INDETERMINATE for each case |
| G10 (`0×0, 0×15, 15×0`) | 3 | INDETERMINATE for each case |

## Raw-derived output-area and stage tables

`FUNCTIONAL_28_CASES.csv` contains S0–S6 and DFF.O signed V·s/Φ0 arithmetic in ARRAY_FINAL_READ, PRE_CLOCK, CLOCK_EDGE, POST_CLOCK, and TOTAL windows. `FUNCTIONAL_28_STAGE_DETAILS.csv` contains 196 case×D0…D6 records including array last-CB, configured pre-CB sJTL, Carry-CB, T1 input/carry-path JJ P/V arithmetic, branch currents, S/C areas, and descriptive lobe timing. These tables preserve rad, turns-navigation, and same-JJ area values separately; they do not count events.

## First-anomaly classification

No case can be assigned a first abnormal physical stage from the current frozen metrics: the product-bit decoder has no preregistered decision threshold, and no post-hoc threshold was added. `FUNCTIONAL_28_ANOMALIES.csv` therefore lists each undecoded case with first supported anomaly stage `UNKNOWN`, rather than infer a stage from area rounding or a local phase excursion.

## Figures

- `plots/carry4-functional-28-20261010/01_output_area_post_clock.png` — 28×8 signed post-clock output voltage-area matrix.
- `plots/carry4-functional-28-20261010/02_t1_input_bj1_pre_clock.png` — T1 input B_J1 PRE_CLOCK net phase-navigation matrix.
- `plots/carry4-functional-28-20261010/03_carry_cb_bj1_pre_clock.png` — Carry-CB BJ1 PRE_CLOCK net phase-navigation matrix.
- `plots/carry4-functional-28-20261010/04_descriptive_lobe_clock_margin.png` — Descriptive lobe-candidate time margin to configured clock.
- `plots/carry4-functional-28-20261010/05_input_group_candidate_status.png` — Case counts by listed input group; candidate status is all indeterminate.
- `plots/carry4-functional-28-20261010/06_candidate_decode_status.png` — Classification availability; no product-bit threshold invented.

The per-run classic full-chain overview and subsystem pages generated at run time remain available under `plots/runs/<run_id>/`; this summary does not duplicate the 28×11 HTML pages.

## Evidence and interpretation boundary

A073 (0×0) and A074 (0×15) have identical raw SHA-256 content; both distinct run directories, configuration snapshots, and run identities are preserved. Identical file hashes are not treated as a missing run. The original experiment maximum 41 / observed manifest count 75 discrepancy is not modified by this analysis. A045–A047 are read-only anchors and their raw is not recopied.

Scientific interpretation: `NOT_PERFORMED`. No physical mechanism, successful multiplication, or functional gate is claimed.
