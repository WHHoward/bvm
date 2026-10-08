# A017_SHARED_R10_C11

- DRIVE_MODE: `SHARED`; ROW_BITS=`10`; COL_BITS=`11`.
- SE_TOPOLOGY: `CELL`; SE_GATE_MODE: `CROSSPOINT`.
- READ0_ENABLE: `1`; WRITE1_MODE: `SIMULTANEOUS`; selective targets: `NONE`, `NONE`.
- SECOND_READ_ENABLE: `0`; bits=`01/10`; second-read SE gate is CELL_CROSSPOINT.
- Active crosspoints: `R1C1, R1C2`.
- Analysis windows: `WRITE0, READ0, WRITE1, FINAL_READ, POST_WRITE0, POST_READ0, POST_WRITE1, READ_RESPONSE, TAIL` (half-open; actual stored rows).
- Half-selected: `R2C1, R2C2`; unselected: `none`.
- physical_solve_count: `1`; artifact status: `VALID`.
- raw SHA-256: `35bac0500aef70973c043db2d419ae580ccfc5b20548e235fad503b2f0e83a07`; samples: `24999`.
- raw/stimulus/plot QA: `PASS` / `PASS` / `PASS`.
- Scientific interpretation: `NOT_PERFORMED`; phase turns are not SFQ counts.
