# V0_15x15_T70 — execution handoff

- Artifact status: `VALID`; exactly one JoSIM solve, exit code 0.
- Mechanical QA: static topology/stimulus PASS; raw-grid/probe/hash QA PASS;
  classic output visualization QA PASS.
- Registered terminal-area screen: `FAIL` in all three read windows. The compact
  pass-mask strings below use `x` for a failed area screen, not an unknown or a
  decoded logic bit.
- SFQ event count and extra-event status: `INCONCLUSIVE`. This probe profile
  contains final terminal voltages and CLK outputs, not independent event
  identity evidence.
- Scientific interpretation: `NOT_PERFORMED`; no physical mechanism or
  throughput claim is assigned.

| Read window | Expected D0…D7 | Area-screen mask D0…D7 | Window area screen |
|---|---|---|---|
| `[180,250)` ps | `10000111` | `xxxxx1x1` | FAIL |
| `[250,320)` ps | `10000111` | `1000xx11` | FAIL |
| `[320,400)` ps | `10000111` | `x00x01x1` | FAIL |

The full per-bit signed/absolute terminal areas are in
`THREE_ROUND_BIT_TABLE.md` and `output_qa.json`. The first post-solve QA attempt
used an overly strict exact-400-ps endpoint check; the same immutable raw ends
at 399.99 ps, one registered timestep before STOP. The check was corrected to
allow 1.5 × DT and the raw was re-QA'd without another solver invocation.

- Raw: `raw.csv`, 9,077,198 bytes, SHA-256
  `b507bb6c82a5a6be33a71a4babd6e352122bdf43184cdaf50c8cff381de945cb`.
- Deck SHA-256: `71becb54893d02068a1c6068e078a259040d604ae22ce6bb7957ecc603d0b17a`.
- Stimulus SHA-256: `b1337be290d66f812700403611bb8f242dbc66101dded662eea23acb2eb5f6db`.
- Visualization: local `res.html`, eight final outputs only; excluded from ZIP.

`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW` — no follow-up run was
started.
