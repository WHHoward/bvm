# BVM_SOURCE_SPEC_V1 A02 (C01 rework)

- corrected V/I strata: 8 (4 loads x 2 polarities)
- descriptors: 8 sets (peak/rms/time-normalized-L1 per V*/I*)
- windows (ps): {'pre': [80, 90], 'source_activity': [94, 130]}
- timestamp: Decimal_from_literal_CSV_token; no interpolation/resampling/fitting

## Claim ceiling

- Hash-bound source-observation specification only; no affine source model; accepted STABLE-LOAD-001 remains sole authority.
