# QB-Q2C artifact and raw-data QA

## Execution status

- Twelve final matched JoSIM runs completed with exit code `0`: four cases at each of S085, S070 and S055.
- The first two S085 control attempts exited `255` before producing raw data because the scale-local `bq_cell.cir` include path was wrong. The corrected decks were rebuilt, rerun and retained under distinct `*-final` logs.
- Controls were completed and checked before READ cases at each scale. No scale hit the stop condition.
- The analysis command completed with exit code `0` and returned `UNIFORM_SCALE_NO_OUTPUT_EVENT`.

## Raw matrix integrity

Each of the 12 final CSVs contains the direct P/V/I columns for BJs/BJL1/BJL2, Lin/L0/L1/L2/RB/RJ1/RJ2, input, output and replay source. Each has 13,599 data rows, finite numeric values, strictly increasing time, and time from 0 to 169.9875 ps.

The output-time pattern is the same as the parent Q2A/Q2B runs: nominal 0.0125 ps intervals with one common 0.025 ps interval around 1.84 ps. Analysis uses the actual raw time column and does not resample.

The post window remained bounded: the largest read1 post-window phase p2p across all three JJ stages and all tested scales was below `4.2e-4 turn`; READ=0 controls were near numerical zero.

The four replay snapshots were byte-compared against the Q2B snapshots and matched exactly. Every final deck has `.tran 0.0125p 170p`, the declared scale-local QB cell, the shared `jjmit.cir`, fixed external R/L/load values and the declared scaled bias.

## Physical-evidence QA

- Event decisions use continuous unwrapped phase and direct same-JJ/same-segment voltage area.
- No `scripts/sfq_metrics.py` fast-event field was used.
- BJs local read1 activity is not interpreted as downstream SFQ delivery.
- This is standalone voltage replay; physical BVM SL/N6/JM/JS guards are not applicable.
- No timestep-convergence claim is made; the result is bounded to the preregistered `0.0125 ps` run.
