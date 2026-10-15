# BVM source comparison and future 4×4 identity

## Files compared

| Role | Path | SHA-256 |
|---|---|---|
| Current root source, B_SE disabled | `circuits/bvm/bvm_cell_0923.cir` | `bbb741ba572924f018749d1fa0cf888876e4e0e352635614b9aeec14fb8cdb16` |
| Selected V9 frozen source | `test/exploration/sfq_clock_two_read_v1/final_runs/V9_analysis/sources_frozen/01_bvm_cell_0923.cir` | `76b7b90b4e58cc45d55adc24d1bc6e626957461a2abe21ca4a33319d58ac6489` |
| New versioned root identity | `circuits/bvm/bvm_cell_0923_v9_bse.cir` | `76b7b90b4e58cc45d55adc24d1bc6e626957461a2abe21ca4a33319d58ac6489` |

The versioned root file is an exact byte-for-byte copy of the V9 frozen source (`cmp` and SHA-256 agree). The current root file remains untouched.

## Exact circuit differences

Only the SE-entry branch differs:

```diff
-* B_SE     SE      SE_IN       jjmit area=1.0
-* R_BSE    SE      SE_IN      15
-R_SE    SE      14      20.0
+B_SE     SE      SE_IN       jjmit area=1.0
+R_BSE    SE      SE_IN      15
+R_SE    SE_IN      14      20.0
```

Thus V9 enables `B_SE` and `R_BSE` and moves `R_SE` from node `SE` to `SE_IN`. The other source lines compare identical. This records a source choice; it is not a statement that the new shared-SE topology has been implemented or physically validated.

## Future platform source identity update

The 4×4 generator now uses:

```text
circuits/bvm/bvm_cell_0923_v9_bse.cir
76b7b90b4e58cc45d55adc24d1bc6e626957461a2abe21ca4a33319d58ac6489
```

The root 4×4 `experiment.yaml` source identity was updated to the same path/hash. `scripts/diagonal_platform.py` had previously expected `ddf90076d40c0856f73dfcdcd22adeae6eddb7dd650798957a0d6c73953456b7`, which does not match the current root source (`bbb741…`) or the selected V9 source. Existing run manifests and all historical preregistration/PREFLIGHT records were left unchanged; for example, old run manifests continue to record their run-time BVM identity `ddf900…`.

The source selection does **not** migrate the rest of the topology. Current `USER_CASE.env` remains `SE_TOPOLOGY=CELL`, `SE_GATE_MODE=CROSSPOINT`; the platform currently validates the cell-local SE topology. Shared row SE and the new BL+SE read rule still need their own implementation and static acceptance before the 256-input campaign. This task did not change WL/BL/SE wiring, stimulus, parameters, raw, deck, or any historical manifest.

## Verification

- New source compared byte-for-byte with V9 frozen source: PASS.
- SHA-256 for the copy and V9 frozen source: identical (`76b7…6489`).
- Python AST parse of `diagonal_platform.py`: PASS.
- `tests/test_platform.py`: **39 passed**. Two golden checks were updated only to treat the V9 include-path change as the expected source identity delta; historical deck files remain unchanged and are compared after substituting that path only.
- `./try.sh --dry-run`: PASS, reported `solver_invoked=false; physical_solve_count=0`, static QA PASS, and no run directory created.
- No JoSIM solve was run. `USER_CASE.env`, old raw/deck/stimulus, run source manifests, and experiment run registry were not changed.

This resolves the stale BVM-hash blocker recorded for the then-current generator in `PLOTLY_DEPENDENCY_FIX_REPORT.md`; that earlier report is left as a time-stamped historical result. The 591 HTML pages proposed for removal still have their old Plotly references until a future approved cleanup; this plan does not delete them or claim the historical directory can now be retired wholesale.
