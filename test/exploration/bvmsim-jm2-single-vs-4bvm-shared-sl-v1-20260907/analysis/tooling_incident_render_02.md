# Tooling incident RENDER-02

- Renderer attempt: `2026-09-07T13:xx:xx+08:00`.
- Failure: the three quiet-BVM derived CSVs used the same human-facing labels, so their combined page had duplicate columns.
- Effect: standalone pages through `TARGET_BVM_OUTPUT.html` were generated; `QUIET_BVMS.html` and later pages were not generated. Raw and all existing derived values were untouched.
- Correction: add the source instance number to labels while combining BVM2/BVM3/BVM4.
- Preservation: generated pages are retained under `analysis/attempts/RENDER-02/`.
