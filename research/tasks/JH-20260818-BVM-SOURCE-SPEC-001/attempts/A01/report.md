# BVM_SOURCE_SPEC_V1 — accepted BVM terminal waveform family

- run: bvm-s2-stable-load-20260817-01
- family size: 16 (4 loads x 2 polarities x read/control)
- preconditions: all 8 strata READY (JM1/JM2 PRE [80,90) p2p <=0.020 rad); BOUNDED_SOURCE_CHARACTERIZATION_REPORTED; per-polarity NOT_SUPPORTED at registered tokens (recorded fact, no affine source model asserted)
- windows (ps): {'pre': [80, 90], 'source_activity': [94, 130], 'post': [140, 160]}
- timestamp: Decimal_from_literal_CSV_token; interpolation/resampling/fitting prohibited

## Sources

| case | load (ohm) | polarity | type | samples | csv sha256 |
|---|---|---|---|---|---|
| L01-positive-read | 1 | positive | read | 13599 | 3e58669da0ba... |
| L01-positive-control | 1 | positive | control | 13599 | c7af45f6ba68... |
| L01-negative-read | 1 | negative | read | 13599 | 5a636f5a29c6... |
| L01-negative-control | 1 | negative | control | 13599 | 727ae9197011... |
| L12-positive-read | 12 | positive | read | 13599 | 0d726f7559d3... |
| L12-positive-control | 12 | positive | control | 13599 | a70338eb7a9b... |
| L12-negative-read | 12 | negative | read | 13599 | 81a5d3d8ee00... |
| L12-negative-control | 12 | negative | control | 13599 | 35bcdcfe9244... |
| L25-positive-read | 25 | positive | read | 13599 | 0be094e502df... |
| L25-positive-control | 25 | positive | control | 13599 | b37e396443d7... |
| L25-negative-read | 25 | negative | read | 13599 | a14befe25c43... |
| L25-negative-control | 25 | negative | control | 13599 | 4dc16756ccbe... |
| L50-positive-read | 50 | positive | read | 13599 | 0308bdebf239... |
| L50-positive-control | 50 | positive | control | 13599 | 0bd12b9ca076... |
| L50-negative-read | 50 | negative | read | 13599 | 94fd42111071... |
| L50-negative-control | 50 | negative | control | 13599 | 818078f002b5... |

## Claim ceiling

- Hash-bound source-observation specification only; accepted STABLE-LOAD-001 remains the sole scientific authority.
- No Thevenin/Norton/affine source model, BQ/receiver/cascade/interface/SFQ/fluxoid/mechanism/hardware claim.
