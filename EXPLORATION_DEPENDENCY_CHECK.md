# Exploration dependency check — 2026-10-15

## Protected roots

These three direct directories were treated as immutable for this task:

- `test/exploration/bvm-4x4-diagonal-array-v1-20261009`
- `test/exploration/bvm-qb-test-1013`
- `test/exploration/sfq_clock_two_read_v1`

The directory census found 159 direct directories plus one direct file under `test/exploration`; 156 directories are retirement targets and the three named directories are protected. The direct file `receiver-architecture-comparison.md` is not a directory and is out of this retirement scope.

## Hard runtime dependency — blocks retirement

The protected 4×4 platform hardcodes a Plotly asset path in:

`test/exploration/bvm-4x4-diagonal-array-v1-20261009/scripts/diagonal_platform.py`

```text
PLOTLY_ASSET = REPO / "test/exploration/bvm-qb-cb-array-topology-v1-20260924/plots/assets/plotly.min.js"
```

The same module requires this file during `validate_registered_matrix()` and `validate_t1_chain_matrix()` and during plot rendering. The protected `try.sh` routes into this platform code. Thus deleting the containing direct experiment directory would break current validation/rendering even though the simulation sources themselves are elsewhere.

Dependency identity, read from the current tracked file:

- Path: `test/exploration/bvm-qb-cb-array-topology-v1-20260924/plots/assets/plotly.min.js`
- Size: 4,763,993 logical bytes; 9,312 allocated blocks
- SHA-256: `122e3be346d66616944d0b83eaaf7242581508c3c1cfa0995a17af0d83eff770`
- Git blob: `c2ef34bc3bdf43c25ab32c4e31a7a197273db406`
- Git mode: `100644`

No `plotly.min.js` was found at the repository root, under `scripts`, `circuits`, `test/final`, or in any of the three protected experiment directories. `scripts/josim-plot2.py` is a renderer, not a replacement for the JS asset that the 4×4 code explicitly checks and references. There is therefore no existing formal root dependency to retarget to without changing protected platform code or adding/moving an asset. The task prohibits editing anything inside the protected experiment directories, so that migration cannot be done in this turn. **Stop condition satisfied; no tracked retirement files were removed.**

## Other references among protected directories

- `bvm-qb-test-1013/CLOSED_N4_1111/metadata.json` and `stdout.txt` refer to the historical run path `bvm-qb-current-baseline-n0-n4-closed-passive-replay-v1-20260917/runs/A001/cases/CLOSED_N4_1111/...`.
- The protected QB test's local `actual_deck.cir` and `raw.csv` have SHA-256 values recorded in the preceding audit as matching that historical A001 deck/raw. The local `run.sh` uses its local deck and `data_tran.csv`; it does not execute from the old run directory. This is a provenance/recovery reference, not an active runtime path dependency. The tag covers tracked bytes; ignored bytes in either location are not covered by the tag.
- No text/code/manifest reference from `sfq_clock_two_read_v1` into a retirement target was found by the static scan.

## Scope and limitations

The reference scan covered readable text/code/config/manifest files in the three protected roots and exact path strings for direct exploration roots. It did not run any experiment, import or execute a protected platform, or establish dynamic behavior. Static results are sufficient to establish the explicit Plotly blocker. No circuit, stimulus, model, raw, or protected-directory file was changed.

All 6,349 ignored files found under `test/exploration` are enumerated with exact path, size, type, and disposition in `EXPLORATION_PRUNE_PATHS.csv`. The frozen Git tag preserves tracked Git content only; it is not a backup of ignored/untracked artifacts. No ignored/untracked file was deleted because the task requires explicit abandonment approval for such data.
