# Historical Cold-Archive Plan — Phase 5

Baseline HEAD: `9822b49f6b120f9c260dd3cdea86789163464021`. This is a plan only: no raw or run directory was moved, deleted, sparsified, or rewritten. Candidate byte counts are local allocated footprints and overlap their parent experiment totals; **do not sum parent and child rows**.

## Ranked by potential local working-tree space

| Rank | Exact candidate | Current allocated footprint | Closure status | Safe next step (requires separate authorization) |
|---:|---|---:|---|---|
| 1 | `test/exploration/bvm-4x4-diagonal-array-v1-20261009/runs/` | 9,970,487,296 B | B / incomplete: 108 raw and 138 ZIP/QA records; no complete independent per-run restore closure | Build a run-ID-to-package-member closure, independently restore representative and then all candidate members; preserve any unmatched run/log. |
| 2 | `test/exploration/bvm-qb-cb-array-topology-v1-20260924/runs/` | 6,942,785,536 B | B / incomplete: 38 raw, 10 ZIPs; at least one ZIP lacks standard manifest; no complete restore | Identify the unmanifested ZIP and prove all 38 raw/deck/stimulus/source/solver identities against archives. |
| 3 | `test/exploration/bvm-rloop-one-shot-tuning-v1-20260918/runs/` | 4,086,136,832 B | B / incomplete: 514 raw, 39 ZIPs; 205 run-level plot-QA files missing/failed and review-linked pages | Repair audit metadata from existing raw/manifests, map every run to archive member and review page, then independently restore. |
| 4 | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/` | 1,661,399,040 B | C for core run evidence: 26 runs, package/member SHA checks and prior independent restore PASS; eight run logs are local-only | Candidate only for a narrowly scoped future sparse-checkout of archive-verified files. Keep logs for A019–A026 local unless their separate recovery is verified. |
| 5 | `test/exploration/bvm-qb-50ghz-merge-v1-20260922/` | 1,963,335,680 B root | B / incomplete: 43 raw, 4 ZIPs; no full run closure | Inventory each raw and required deck/stimulus/source/solver closure; do not remove root. |
| 6 | `test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/` | 1,494,986,752 B root | E / incomplete: 5 raw, 1 ZIP, tracked HTML; no full restore map | Establish raw-to-package and renderer provenance; retain all files until then. |
| 7 | `test/exploration/bvm-load-qb-matrix-v1-20260901/` | 1,539,031,040 B root | E / incomplete: 66 tracked HTML, no local `raw.csv` | Locate and verify raw source/archive; absent that, preserve pages as possibly unique review evidence. |
| 8 | `test/exploration/bvm-qb-t1-interface-topology-v1-20260914/` and `...-v2/` | about 0.687 GB each | E / incomplete: 15 raw each, no verified full archive closure | Verify each run independently; keep both versions until source/fixture differences and archive closure are known. |

The top-30 root inventory, run-level SHA/status fields, and exact archive locators are in `CLEANUP_PHASE5_ACTIONS.csv`. The 4×4 project root is about 34.65 GB allocated after Phase 5; its `runs/` subtree is the largest potential cold-archive target, but the root includes current platform source and historical evidence and must not be moved wholesale.

## Required recovery closure before any future move

For each run, independently bind:

`run ID → raw SHA → deck/stimulus SHA → complete frozen source SHA map → JoSIM version + binary SHA → run manifest / package QA → archive member SHA → archive SHA + local path or Drive file ID → extracted-file SHA verification`

Drive metadata and a matching filename/size are not content verification. A local D archive SHA does not prove the corresponding remote Drive object has identical bytes. ZIP CRC alone is not the required member-level restore check. Retain failed and anomalous runs.

## Recommended order

1. **4×4 runs**: highest potential space return; close all 108 raw identities to the 138 packages/QA records and restore-verify in an isolated temporary directory. Do not affect `V9_analysis` or the user's newer row-shared-SE work.
2. **QB-CB topology runs**: resolve the ZIP without the standard manifest and close all 38 runs.
3. **R-loop runs**: fix the 3,194 plot QA gaps (without JoSIM), account for all 216 HTML pages outside the plot manifest, and preserve review navigation; then archive-restore-check all 514 runs.
4. **2×2 runs**: already the best-evidenced subset, but keep the eight local-only logs unless separately recovered. A later sparse-checkout can reduce only working-tree expansion, not Git object/LFS storage.
5. **Other interface/QB runs**: investigate exact raw/source/ZIP mappings before proposing any working-tree exclusion.

For any approved sparse-checkout, record the before/after exact file list and bytes, retain a restorable Git commit and archive map, and provide the inverse sparse-checkout command. No Git history rewrite, `git clean`, LFS prune, or Drive delete is part of this plan.
