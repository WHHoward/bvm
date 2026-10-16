# FULL256 SE375 preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: `V9_SE375_FULL256_20261016`; risk `NORMAL`.
- Baseline repository HEAD at task start: `595b3d568471d1e835bd08e876730dad907e0b55`.
- Prepared scheduler commit: `c78c4416eaf2f9800e43161a533c3881eef27dd9`.
- Existing platform: `test/exploration/sfq_clock_two_read_v1/`; no change to `platform.py`, `try.sh`, V9 template, frozen sources, or physical parameters.
- Template SHA-256: `2ea1cee249ad8939003b1108fda41a65dda81e12afd43d53fefaecb4c529392b`.
- Source-manifest SHA-256: `3e1d6ba694aad927c4797e9282163c8a4d65e5f0527f3c01d99a77eb2b0346d4`.
- Frozen configuration is recorded in `experiment.yaml`; per-run `PREFLIGHT.md` records the exact execution HEAD, solver, binary SHA, inputs, rendered deck/stimulus, and probes.
- Run matrix is exactly the 16×16 Cartesian product. The validated existing input set contains 25 unique pairs; the remaining 231 are authorized once each, in A-major/B-minor order. `runs/FULL256_SE375_INDEX.csv` enumerates all 256 pairs and starts with the 25 existing rows plus 231 `NOT_RUN` rows.
- `EXPECTED_PRODUCT=A*B` and input popcounts in the index are theoretical/input metadata only; they are never compared with simulation output by Codex.
- The only per-case configuration changes are `CASE_NAME`, `A`, and `B`. No input may be inferred complete from RUN_ID alone: the scheduler checks manifest inputs and raw/evidence hashes.
- Each missing case must pass `./try.sh --dry-run` before one `./try.sh --run-local` call. A mechanical failure stops execution; no automatic retry or parameter adjustment.
- Mechanical checks: fixed config and source closure; exact topology/probes; solver exit; raw presence, schema, finite values, increasing time, 8 probes and SHA; manifest and visualization QA. Output traces are not read for scientific classification.
- Archive target is the user-confirmed `D:\BVM_Backages` local directory. Cloud File IDs are recorded only after Drive API readback; local file presence alone is not cloud confirmation. If D is inaccessible, the scheduler keeps a local per-run ZIP pending upload.
- Drive API readback for the 24 prior G1-G3 packages confirmed exact names, sizes, parent folder and File IDs. The metadata connector did not expose cloud content SHA-256; no ZIP was downloaded for a hash comparison. The earlier V9R001 GitHub package was not found in this Drive folder.
- Scientific interpretation, SFQ counting, and multiplication correctness are not performed. No follow-up is authorized.
