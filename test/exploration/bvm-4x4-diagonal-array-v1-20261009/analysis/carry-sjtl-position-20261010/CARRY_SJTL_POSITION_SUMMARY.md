# Carry sJTL placement — mechanical evidence handoff

- Status: `MECHANICAL_QA_PASS`; physical solves: 6; scientific interpretation: `NOT_PERFORMED`.
- Raw files are immutable and all post-analysis SHA-256 values match their run manifests.
- DOUT/JOIN voltages are mixed boundary signals and are not counted as array-only events.
- JJ phase remains radians; same-JJ voltage integrals use the same stored rows/window. Positive/negative phase variation is descriptive arithmetic only.
- No event classifier, bit decoder, parameter tuning, or follow-up solve was run.

| Run | Position/mask | Clock | Raw bytes | Raw SHA-256 | QA |
|---|---|---:|---:|---|---|
| A034_D2_ONLY_POST_CB_SJTL_ALL_200 | POST_CB / 010000 | 200p | 84559918 | `9181e1eaed213cfd950f6f1e85c07906db09732da346bf3a5b5d5c96bd379a57` | PASS |
| A035_D2_ONLY_POST_CB_SJTL_PAPER_200 | POST_CB / 010000 | 200p | 84593695 | `ded810953244189ae906482b72364992ff1653a34bc5e79f8af6157d6b9dad10` | PASS |
| A036_PRE_CB_SJTL_ALL_200 | PRE_CB / 111111 | 200p | 94506907 | `586ba6eafa62d25bf6cd7a7ea8b533903826616b4b5575a9023f7393b74faf75` | PASS |
| A037_PRE_CB_SJTL_ALL_210 | PRE_CB / 111111 | 210p | 94534795 | `fcb9c40bf27fcc9e10a0b385e7ee110f429f33d2d2ac7480260a636447a9ff01` | PASS |
| A038_PRE_CB_SJTL_PAPER_210 | PRE_CB / 111111 | 210p | 94594453 | `e178b40dcda2fbef11005ec9ed3605687b88db89dc24746f213eef6797ccf5b7` | PASS |
| A039_PRE_CB_SJTL_3X3_210 | PRE_CB / 111111 | 210p | 94649166 | `af7a4e7b71549ff0c65bce49f0888eecd8015df41cb95a2d2da718f7441ca06d` | PASS |

The stage and comparison CSVs report registered arithmetic only. No physical mechanism or success classification is assigned.
