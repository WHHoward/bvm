# A014_SHARED_R10_C10

- DRIVE_MODE: `SHARED`; ROW_BITS=`10`; COL_BITS=`10`.
- SE_TOPOLOGY: `CELL`; SE_GATE_MODE: `CROSSPOINT`.
- READ0_ENABLE: `1`; WRITE1_MODE: `SIMULTANEOUS`; selective targets: `NONE`, `NONE`.
- SECOND_READ_ENABLE: `0`; bits=`01/10`; second-read SE gate is CELL_CROSSPOINT.
- Active crosspoints: `R1C1`.
- Analysis windows: `WRITE0, READ0, WRITE1, FINAL_READ, POST_WRITE0, POST_READ0, POST_WRITE1, READ_RESPONSE, TAIL` (half-open; actual stored rows).
- Half-selected: `R1C2, R2C1`; unselected: `R2C2`.
- physical_solve_count: `1`; artifact status: `VALID`.
- raw SHA-256: `079a6f731c4ececb625665f2aed8a20aa202f8764a9c85d8fb2ea56a681b99dd`; samples: `24999`.
- raw/stimulus/plot QA: `PASS` / `PASS` / `PASS`.
- Scientific interpretation: `NOT_PERFORMED`; phase turns are not SFQ counts.
