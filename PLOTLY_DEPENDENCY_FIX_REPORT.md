# Plotly dependency migration and Drive ZIP audit — 2026-10-15

## Part A — shared Plotly asset

**Status: `BLOCKED` for retiring the historical directory.** The future-render dependency is migrated, but existing review HTML still points to the old path and the platform dry-run is blocked by a BVM source-hash mismatch. No historical directory or HTML was changed or removed.

### Change

- Added `assets/vendor/plotly.min.js` by byte-copying `test/exploration/bvm-qb-cb-array-topology-v1-20260924/plots/assets/plotly.min.js`.
- Old and new SHA-256 are both `122e3be346d66616944d0b83eaaf7242581508c3c1cfa0995a17af0d83eff770`; each is 4,763,993 bytes.
- Updated only `test/exploration/bvm-4x4-diagonal-array-v1-20261009/scripts/diagonal_platform.py`: `PLOTLY_ASSET = REPO / "assets/vendor/plotly.min.js"`.
- No netlist, stimulus, model, raw, or historical HTML was modified.

### Call path and rendering

- The protected 4×4 `try.sh` dispatches to `scripts/diagonal_platform.py`; that runner validates `PLOTLY_ASSET` and computes a page-relative URL from the asset path when rendering.
- The protected 4×4 `submit.sh` dispatches to the platform-local `scripts/submit.py`. That script does not hardcode the old Plotly path; it delegates package/archive operations to the repository helper. Generated HTML is not part of the ZIP evidence flow by default.
- The shared root asset is outside the 4×4 experiment scope and is not added to its handoff ZIP by the local submit helper. Because the helper also excludes HTML, the ZIP remains an evidence supplement rather than a standalone plot-rebuild bundle. A normal Git checkout at the commit containing `assets/vendor/plotly.min.js` has the required runtime; no package logic was changed.
- Repository `scripts/josim-plot2.py` calls Plotly `fig.write_html()` without an external `include_plotlyjs` path, so its default output embeds its JS runtime. It is not the asset referenced by existing 4×4 pages.
- The other protected roots, `bvm-qb-test-1013` and `sfq_clock_two_read_v1`, have no `plotly.min.js`/`PLOTLY_ASSET` references in their scripts or HTML; their `josim-plot2` pages are independent of this shared path.

### Existing HTML compatibility

All **600/600** existing HTML files under the protected 4×4 `plots/` tree contain an external script reference resolving to the old asset in `bvm-qb-cb-array-topology-v1-20260924`. The exact per-page old and proposed new relative paths are in `PLOTLY_HTML_REFERENCE_MAP.csv`.

Those 600 pages still work while the old asset exists, but **all 600 would lose Plotly JS if the old experiment directory were removed**. They were not batch-rewritten. In addition, 121 4×4 JSON metadata/QA files retain the historical asset path. Those fields are provenance snapshots and were not rewritten. New render output and generated QA will use the new root asset.

Thus the new root asset is suitable for future pages, but current historical HTML is not yet compatible with retiring the old directory. A later cleanup must either preserve a compatible legacy path or explicitly replace/rebuild those pages and navigation under a separately approved scope.

### Validation

| Check | Result |
|---|---|
| Old/new asset SHA-256 | PASS — identical `122e3be3…eff770` |
| Python AST parse of `diagonal_platform.py` | PASS |
| Relative asset URL smoke for comparison, run, and deep T1 page locations | PASS — resolves to `assets/vendor/plotly.min.js` |
| `bash -n` for protected 4×4 `try.sh` and `submit.sh` | PASS |
| Existing HTML reference map | PASS — 600 mapped, 0 unmatched; no HTML rewritten |
| `./try.sh --dry-run` | **FAIL / BLOCKED before solve** — platform expects BVM SHA `ddf90076d40c0856f73dfcdcd22adeae6eddb7dd650798957a0d6c73953456b7`; current `circuits/bvm/bvm_cell_0923.cir` is `bbb741ba572924f018749d1fa0cf888876e4e0e352635614b9aeec14fb8cdb16`. This task did not alter the BVM source or expected physical-source hashes. |
| JoSIM physical solve | 0 — not run |

### Adversarial review / residuals

- **Stale artifact probe:** confirmed the entire current 4×4 HTML set depends on the legacy relative asset; changing the Python constant alone would not preserve those pages after retirement.
- **Wrong-branch / weak-oracle probe:** the authorized dry-run fails at frozen BVM source verification before it can complete platform QA; the successful path smoke is only a path-resolution check, not a platform regression pass.
- **Coupling probe:** the other two retained experiment roots have no shared-asset references; no files in them were changed.
- **Residual:** no dynamic browser launch was performed. The dependency fix does not authorize resuming directory cleanup. Keep the old directory until both the HTML compatibility and pre-existing BVM source-hash issue are resolved by explicit follow-up.

## Part B — Drive ZIP audit

The Drive folder was recursively listed read-only. The complete file-level inventory, duplicate-group audit, and exact-ID review candidate ledger are:

- `DRIVE_ZIP_INVENTORY.csv`
- `DRIVE_DUPLICATE_AUDIT.csv`
- `DRIVE_ZIP_DELETE_CANDIDATES.csv`
- `DRIVE_ZIP_DELETE_REVIEW.md`

Cloud metadata exposes IDs, names, sizes, timestamps, parent folders, and links, but the connected metadata response does **not** expose Drive MD5/SHA fields. Therefore the 58 same-name/same-size groups were individually stream-read by Drive file ID; the stream lengths matched Drive sizes and each pair's SHA-256 matched. The 2.64 GB of candidate bytes were streamed to hash computation and were not saved to the repository or D: mirror.

All 58 groups are byte-identical. This confirms 58 redundant-copy identities totaling **1,320,886,648 bytes** (about 1.23 GiB) if one copy from every pair were eventually removed. That is not deletion authorization. The in-scope local manifest/recovery-text scan and two Drive `BATCH_SUMMARY.md` files found no reference to these duplicate IDs/names, but Drive-wide reverse-reference search did not return usable results even for a known title; ZIP-internal manifests and Drive documents outside this folder were not exhaustively indexed. The duplicate rows therefore remain **review-only**, not deletion-cleared.

No Drive file was deleted, moved, renamed, or edited. The full scan and residual content-different-name uncertainty are detailed in `DRIVE_ZIP_DELETE_REVIEW.md`.
