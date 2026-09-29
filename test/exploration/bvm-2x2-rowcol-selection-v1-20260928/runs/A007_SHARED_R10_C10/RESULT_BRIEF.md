# A007_SHARED_R10_C10

- DRIVE_MODE: `SHARED`; ROW_BITS=`10`; COL_BITS=`10`.
- SE_TOPOLOGY: `CELL`; SE_GATE_MODE: `CROSSPOINT`.
- SECOND_READ_ENABLE: `1`; bits=`01/10`; second-read SE gate is CELL_CROSSPOINT.
- Active crosspoints: `R1C1`.
- Analysis windows: `WRITE0, READ0, WRITE1, FINAL_READ, POST_WRITE0, POST_READ0, POST_WRITE1, RECOVERY_BEFORE_SECOND_READ, SECOND_READ, POST_SECOND_READ` (half-open; actual stored rows).
- Half-selected: `R1C2, R2C1`; unselected: `R2C2`.
- physical_solve_count: `1`; artifact status: `VALID`.
- raw SHA-256: `1d45b918241aeb1f56d7a12d9f8010822b864426e820de8e81e1e4d7577f5816`; samples: `24999`.
- raw/stimulus/plot QA: `PASS` / `PASS` / `PASS`.
- Scientific interpretation: `NOT_PERFORMED`; phase turns are not SFQ counts.
