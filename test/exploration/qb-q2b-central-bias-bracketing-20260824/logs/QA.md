# QB-Q2B artifact and raw-data QA

## Execution status

- Eight final matched JoSIM runs completed with exit code `0`.
- The first two attempts for the 30 µA logical1 READ=0 control exited `255` before producing raw data: first due to an unresolved include path, then due to a missing output directory. They are retained in the log directory and are fixture failures, not scientific cases.
- The corrected run was executed before the other 30 µA cases; the 40 µA controls were also completed before the 40 µA READ cases.
- The analysis command completed with exit code `0` and returned `BIAS_BRACKET_NO_BJL1_EVENT`.

## Raw matrix integrity

All eight final CSVs contain the same required JoSIM columns for BJs, BJL1, BJL2, Lin/L0/L1/L2, RB, RJ1/RJ2, input, output and replay-source branches. Each has `13,599` data rows, finite numeric values, and time from `0` to `169.9875 ps`.

The solver output contains `13,597` nominal `0.0125 ps` intervals and one common `0.025 ps` interval from `1.8375 ps` to `1.8625 ps` in every case. This is the same output-time pattern present in the parent Q2A/Q1 `.tran 0.0125p 170p` runs; no resampling or interpolation was introduced in analysis. The analyzer integrates voltage using the actual raw time column.

The two canonical logical replay snapshots were byte-compared with the Q2A copies and matched exactly. All eight decks contain the frozen QB include paths, the declared bias, the same `10 Ω` load and `.tran 0.0125p 170p`.

## Physical-evidence QA

- Event counts were obtained from unwrapped phase monotonic segments and the direct same-JJ/same-segment voltage area.
- No `scripts/sfq_metrics.py` fast-event output was used.
- The read1 BJs activity is retained as upstream source activity; it is not counted as BJL1/BJL2 output delivery.
- Because the experiment is standalone voltage replay, BVM SL/N6/JM/JS source guards are not applicable here.
