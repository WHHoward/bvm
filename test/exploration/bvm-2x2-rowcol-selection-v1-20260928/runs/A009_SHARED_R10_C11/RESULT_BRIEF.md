# A009_SHARED_R10_C11

- DRIVE_MODE: `SHARED`; ROW_BITS=`10`; COL_BITS=`11`.
- SE_TOPOLOGY: `CELL`; SE_GATE_MODE: `CROSSPOINT`.
- SECOND_READ_ENABLE: `1`; bits=`10/10`; second-read SE gate is CELL_CROSSPOINT.
- Active crosspoints: `R1C1, R1C2`.
- Analysis windows: `WRITE0, READ0, WRITE1, FINAL_READ, POST_WRITE0, POST_READ0, POST_WRITE1, RECOVERY_BEFORE_SECOND_READ, SECOND_READ, POST_SECOND_READ` (half-open; actual stored rows).
- Half-selected: `R2C1, R2C2`; unselected: `none`.
- physical_solve_count: `1`; artifact status: `VALID`.
- raw SHA-256: `26129172e539c340f9bde2f2f5b55414d90f7a4c25cee6a46ee30c2234e45cb9`; samples: `24999`.
- raw/stimulus/plot QA: `PASS` / `PASS` / `PASS`.
- Scientific interpretation: `NOT_PERFORMED`; phase turns are not SFQ counts.
