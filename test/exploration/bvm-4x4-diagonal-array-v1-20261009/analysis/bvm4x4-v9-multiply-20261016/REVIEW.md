# Adversarial implementation review — V9 static migration

Review type: bounded NORMAL implementation/artifact review; no scientific interpretation.

## Strongest bounded implementation claim

The explicit V9 mode generates the selected four-case stimulus against a run-local copy of the hash-pinned V9 source closure, preserving the current V9 reference circuit statements apart from the registered `.print` set and `.tran` setting.

## Hidden-error probes

| Hypothesis | Probe | Result |
|---|---|---|
| The new mode is a no-op or still emits 16 cell-local SE sources. | Generated-source count, exact source names, and 11×13 active PWL comparison against the current V9 stimulus. | PASS: 4 WL + 4 BL + 4 shared-row SE + 8 CLK; generated 11×13 active source lines match the current V9 reference exactly. |
| Operand bits are reversed or one input is ignored. | Generate and validate all 256 A/B encodings; independently assert the 11×13 row/column selection and all four registered products. | PASS: 256/256 mappings are generated; 11×13 selects SE_R1/R2/R4 and BL_C1/C2/C4; registered products are 0, 1, 143, 225. |
| V9 topology is only device-count-equivalent, not connected as the reference. | Compare rendered and reference deck bodies after removing only active `.print` and `.tran` lines; check per-cell ports, carry-chain endpoints, clocks, Sum JTLs and DFF wiring. | PASS: non-probe/non-time circuit body is identical; explicit instance/port checks pass. |
| A stale V9 manifest or package causes the wrong source bytes to be used. | Independently SHA-256 current deck, stimulus, raw and all 11 source inputs; pin BVM to the required canonical source SHA; refuse mismatch. | PASS: current byte hashes are recorded directly; old manifest/package identities are not treated as authority; current historical raw is not an oracle. |
| Probe growth silently bypasses the raw storage guard. | Project against current 80-column V9 raw with 5% headroom and enforce 100,000,000 bytes. | PASS: 168 probes, estimate 94,712,327 bytes; no truncation/downsampling. |
| The implementation labels phase/current activity as event counts or arithmetic success. | Inspect registered metrics, CSV fields, and run result defaults. | PASS: event counts/observed bits remain UNKNOWN and arithmetic/timing remain INCONCLUSIVE absent an authorized classifier. |

## Regression and execution evidence

- `tests/test_v9_migration.py`: 7 tests PASS, including local external-Plotly HTML generation and DFF-bit UNKNOWN behavior; temporary fixture raw is not retained.
- Full platform suite after A109 postprocess recovery: 53 tests PASS.
- Legacy `./try.sh --dry-run`: PASS, `solver_invoked=false`.
- V9 `./try.sh --v9-multiply-batch --dry-run`: PASS, `solver_invoked=false`, 0 physical solves, no run directories or manifest changes.
- `./try.sh --v9-case --dry-run`: PASS for the editable USER_CASE A=11/B=13 preview; no run ID reserved.
- The first classic figure page keeps the 12 shared-bus source currents and 8 product outputs together; HTML is local and uses the shared Plotly asset.
- Exactly four authorized JoSIM invocations completed: A109–A112. Solver exit code was 0 for each, raw QA and three classic pages passed for each, and all four raw files remain below the 100,000,000-byte guard.
- A109's initial postprocessor failed with `KeyError: P(B7|XDFF)` after solver success. That failed result and run manifest were preserved under `runs/A109.../postprocess_attempts/001/`; the missing internal DFF probe is now explicitly UNKNOWN, the same raw SHA was reprocessed, and A109 was not solved again. A110–A112 remained within the original registered matrix.
- Independent post-run CSV/trapezoid recomputation matched the stored A111 D3 sum-JJ phase/voltage arithmetic and terminal signed-area row; the raw SHA remained unchanged.
- Google Drive/D: not accessed.

## Residual uncertainty

- This review does not assign product bits, event counts, timing margins, or physical meaning; DFF bit7 internal P/V was not probed; the four raw packages remain awaiting user + ChatGPT review.
- An internal CLK peak is only a stored-sample waveform descriptor; no event-edge or setup/hold criterion is frozen.
- Output area/Φ0 and local same-JJ phase/area arithmetic are not an event classifier, multiplication Gate, convergence test, or physical mechanism claim.
