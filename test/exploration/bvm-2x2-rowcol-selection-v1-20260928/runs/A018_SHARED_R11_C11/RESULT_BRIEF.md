# A018_SHARED_R11_C11

- DRIVE_MODE: `SHARED`; ROW_BITS=`11`; COL_BITS=`11`.
- SE_TOPOLOGY: `CELL`; SE_GATE_MODE: `CROSSPOINT`.
- READ0_ENABLE: `1`; WRITE1_MODE: `SIMULTANEOUS`; selective targets: `NONE`, `NONE`.
- SECOND_READ_ENABLE: `0`; bits=`01/10`; second-read SE gate is CELL_CROSSPOINT.
- Active crosspoints: `R1C1, R1C2, R2C1, R2C2`.
- Analysis windows: `WRITE0, READ0, WRITE1, FINAL_READ, POST_WRITE0, POST_READ0, POST_WRITE1, READ_RESPONSE, TAIL` (half-open; actual stored rows).
- Half-selected: `none`; unselected: `none`.
- physical_solve_count: `1`; artifact status: `VALID`.
- raw SHA-256: `5ce1430420117479ba3581b8f2f0234b00e545770ad9348b0bba81c07846dfe7`; samples: `24999`.
- raw/stimulus/plot QA: `PASS` / `PASS` / `PASS`.
- Scientific interpretation: `NOT_PERFORMED`; phase turns are not SFQ counts.
