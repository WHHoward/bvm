# A012_SHARED_R11_C11

- DRIVE_MODE: `SHARED`; ROW_BITS=`11`; COL_BITS=`11`.
- SE_TOPOLOGY: `CELL`; SE_GATE_MODE: `CROSSPOINT`.
- READ0_ENABLE: `0`; WRITE1_MODE: `SEQUENTIAL_CROSSPOINT`; selective targets: `R1C1`, `R2C2`.
- SECOND_READ_ENABLE: `0`; bits=`01/10`; second-read SE gate is CELL_CROSSPOINT.
- Active crosspoints: `R1C1, R1C2, R2C1, R2C2`.
- Analysis windows: `WRITE0, WRITE1_TARGET_1, WRITE1_TARGET_2, FINAL_READ, POST_WRITE0, POST_WRITE1_TARGET_1, POST_WRITE1_TARGET_2, POST_WRITE1, READ_RESPONSE, TAIL` (half-open; actual stored rows).
- Half-selected: `none`; unselected: `none`.
- physical_solve_count: `1`; artifact status: `VALID`.
- raw SHA-256: `f20ca4a01bd79bc12e521c5171858c7a10b0f8009abe87270cbf1a4a59d2d9be`; samples: `29999`.
- raw/stimulus/plot QA: `PASS` / `PASS` / `PASS`.
- Scientific interpretation: `NOT_PERFORMED`; phase turns are not SFQ counts.
