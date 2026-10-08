# A013_SHARED_R00_C00

- DRIVE_MODE: `SHARED`; ROW_BITS=`00`; COL_BITS=`00`.
- SE_TOPOLOGY: `CELL`; SE_GATE_MODE: `CROSSPOINT`.
- READ0_ENABLE: `1`; WRITE1_MODE: `SIMULTANEOUS`; selective targets: `NONE`, `NONE`.
- SECOND_READ_ENABLE: `0`; bits=`01/10`; second-read SE gate is CELL_CROSSPOINT.
- Active crosspoints: `none`.
- Analysis windows: `WRITE0, READ0, WRITE1, FINAL_READ, POST_WRITE0, POST_READ0, POST_WRITE1, READ_RESPONSE, TAIL` (half-open; actual stored rows).
- Half-selected: `none`; unselected: `R1C1, R1C2, R2C1, R2C2`.
- physical_solve_count: `1`; artifact status: `VALID`.
- raw SHA-256: `2e9f8f9fcc322f2d95a49f91f4d5d2136dcff8f7dc3880b9b237e6ed9a84654e`; samples: `24999`.
- raw/stimulus/plot QA: `PASS` / `PASS` / `PASS`.
- Scientific interpretation: `NOT_PERFORMED`; phase turns are not SFQ counts.
