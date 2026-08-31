# PAPER-SL-Q1 analysis report

## Verdict: `PAPER-SL_QB_SUBTHRESHOLD`

This is an ideal-current waveform-replay requirement result; it is not physical BVM-to-QB interface evidence.

## Event summary

| case | BJs complete units | BJL1 complete units | BJL2 complete units | BJL2 largest activity segment (turns) | BJL2 largest same-segment area (Phi0) | post complete units | classification |
|---|---:|---:|---:|---:|---:|---:|---|
| q0-68p4u-positive-control | 94 | 6 | 6 | 1.09601 | 1.09652 | 0 | `Q0_POSITIVE_CONTROL_VALID` |
| paper-j1-logical1-read | 14 | 0 | 0 | 0.892527 | 0.892537 | 0 | `NO_COMPLETE_EVENT` |
| paper-j0-logical0-read | 0 | 0 | 0 | 0.0065587 | 0.00656041 | 0 | `NO_COMPLETE_EVENT` |
| paper-j1-logical1-read0-control | 0 | 0 | 0 | -2.5051e-05 | -2.5055e-05 | 0 | `NO_COMPLETE_EVENT` |
| paper-j0-logical0-read0-control | 0 | 0 | 0 | 2.50351e-05 | 2.50412e-05 | 0 | `NO_COMPLETE_EVENT` |

## Per-JJ activity details

### q0-68p4u-positive-control

| JJ | activity phase p2p (turns) | largest monotonic delta (turns) | same-segment area (Phi0) | current min..max (µA) |
|---|---:|---:|---:|---:|
| BJs | 16.3905 | 16.4233 | 16.426 | 0 .. 68.4 |
| BJL1 | 1.22553 | 1.22553 | 1.22678 | -36.3423 .. 42.8598 |
| BJL2 | 1.09601 | 1.09601 | 1.09652 | -63.0725 .. 61.6719 |

### paper-j1-logical1-read

| JJ | activity phase p2p (turns) | largest monotonic delta (turns) | same-segment area (Phi0) | current min..max (µA) |
|---|---:|---:|---:|---:|
| BJs | 14.3749 | 14.0921 | 14.0921 | -20.0366 .. 79.0668 |
| BJL1 | 1.07308 | 0.829846 | 0.82988 | -51.3624 .. 51.9265 |
| BJL2 | 1.02498 | 0.892527 | 0.892537 | -58.6905 .. 61.1632 |

### paper-j0-logical0-read

| JJ | activity phase p2p (turns) | largest monotonic delta (turns) | same-segment area (Phi0) | current min..max (µA) |
|---|---:|---:|---:|---:|
| BJs | 0.0344871 | 0.0236757 | 0.0236817 | -4.19892 .. 3.63586 |
| BJL1 | 0.0230758 | 0.019226 | 0.0192314 | 12.2858 .. 17.8623 |
| BJL2 | 0.00868477 | 0.0065587 | 0.00656041 | 18.2778 .. 21.3792 |

### paper-j1-logical1-read0-control

| JJ | activity phase p2p (turns) | largest monotonic delta (turns) | same-segment area (Phi0) | current min..max (µA) |
|---|---:|---:|---:|---:|
| BJs | 0.000180388 | 0.000180388 | 0.000180427 | -0.00972477 .. 0.00864419 |
| BJL1 | 7.16993e-05 | -7.16993e-05 | -7.17232e-05 | 15.1138 .. 15.1303 |
| BJL2 | 2.5051e-05 | -2.5051e-05 | -2.5055e-05 | 19.8739 .. 19.8824 |

### paper-j0-logical0-read0-control

| JJ | activity phase p2p (turns) | largest monotonic delta (turns) | same-segment area (Phi0) | current min..max (µA) |
|---|---:|---:|---:|---:|
| BJs | 0.000180388 | -0.000180388 | -0.000180427 | -0.00864419 .. 0.00972477 |
| BJL1 | 7.16993e-05 | 7.16993e-05 | 7.17227e-05 | 15.113 .. 15.1295 |
| BJL2 | 2.50351e-05 | 2.50351e-05 | 2.50412e-05 | 19.8743 .. 19.8828 |

## Observed

- The source builder used `I(B_LD1)` and verified the twelve series JSL branch-current columns were equal within the recorded numerical tolerance.
- All replay source points retain the original PAPER-SL-L0 time grid, polarity, and amplitude; no shape transformation was applied.
- Event counts above use only continuous phase, same-JJ monotonic segments, and same-segment voltage area.

## Derived

- A complete-unit count is the floor of the absolute phase change for an area-consistent monotonic segment; phase activity below one turn is not counted as an event.
- The Q0 row is an independent fixture check and is not a paper-JSL source result.

## Inference

- The selected verdict is limited to waveform compatibility of the frozen scaled QB under these ideal current replays.
- It does not establish that the physical twelve-JSL BVM load can supply the replay current into QB, nor that source loading/back-action is acceptable.

## Unknown

- The physical combined BVM/JSL/QB load-line and any reflected source disturbance were not tested.
- A local BJL2 event, if present, is not downstream SFQ delivery because no JTL is connected.
