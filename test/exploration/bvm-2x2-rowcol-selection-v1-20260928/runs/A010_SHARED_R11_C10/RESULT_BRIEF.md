# A010_SHARED_R11_C10

- DRIVE_MODE: `SHARED`; ROW_BITS=`11`; COL_BITS=`10`.
- SE_TOPOLOGY: `CELL`; SE_GATE_MODE: `CROSSPOINT`.
- READ0_ENABLE: `1`; WRITE1_MODE: `SIMULTANEOUS`; selective targets: `NONE`, `NONE`.
- SECOND_READ_ENABLE: `1`; bits=`10/10`; second-read SE gate is CELL_CROSSPOINT.
- Active crosspoints: `R1C1, R2C1`.
- Analysis windows: `WRITE0, READ0, WRITE1, FINAL_READ, SECOND_READ, POST_WRITE0, POST_READ0, POST_WRITE1, POST_FINAL_READ, RECOVERY_BEFORE_SECOND_READ, FIRST_READ_RESPONSE, SECOND_READ_RESPONSE, POST_SECOND_READ` (half-open; actual stored rows).
- Half-selected: `R1C2, R2C2`; unselected: `none`.
- physical_solve_count: `1`; artifact status: `VALID`.
- raw SHA-256: `a9687368e8cf89ff18dc99c353cc4e001a241cc2d5780335f57fcc7786bdfadf`; samples: `24999`.
- raw/stimulus/plot QA: `PASS` / `PASS` / `PASS`.
- Scientific interpretation: `NOT_PERFORMED`; phase turns are not SFQ counts.
