# BVM Cleanup Phase 5 Report

Audit basis: `WHHoward/bvm`, `master` HEAD `9822b49f6b120f9c260dd3cdea86789163464021` (confirmed before and after the cleanup). This phase did not run JoSIM or alter circuit/configuration files.

## Actual workspace space reclaimed — primary result

The exact, pre-verified whitelist contained **355 ignored, untracked 4×4 HTML files**. All 355 were unlinked by exact file path after a final path/type/size/SHA/raw-SHA check; no directory-level deletion was used.

| Measure | Result |
|---|---:|
| Removed HTML logical bytes | 8,059,925,226 B (8.060 GB / 7.51 GiB) |
| Removed HTML allocated blocks (`st_blocks`) | 8,060,649,472 B (8.061 GB / 7.51 GiB) |
| `df` free-space increase observed immediately after the unlink batch | 8,041,865,216 B |
| 4×4 experiment-root allocated snapshot before → after | 42,709,225,472 B → 34,648,576,000 B |

The immediate `df` delta is 18,784,256 B below the sum of file blocks; filesystem metadata/journal activity and the measurement interval can account for the difference. A later workspace snapshot is not used to overstate attribution. The exact per-file sizes, allocated blocks, SHA-256, associated raw path/SHA, renderer/manifest references and unlink status are in `CLEANUP_PHASE5_ACTIONS.csv`.

One first unlink completed before a cleanup-ledger script hit a field-name mismatch. That exact file was independently confirmed absent, its raw SHA and replacement pages were rechecked, and its original values were reconciled into the ledger. The remaining 354 whitelist entries then completed with zero skips and zero failures. Final reconciliation is 355/355. No raw, deck, stimulus, model, log, manifest, source, or configuration file was removed.

## Current storage snapshot and separation by storage layer

These are separate storage layers and must not be summed as if they were one reclaimable pool.

| Layer | Snapshot / contents | Cleanup effect in this phase |
|---|---|---|
| Local workspace | Final report snapshot: `du -sb .` ≈ 102,798,637,064 B; `test/exploration` = 82,672,780,894 B. The 4×4 root is the largest experiment directory. | Only the 355 listed HTML files were removed |
| Git working tree history | `.git` logical size about 18.714 GB (allocated `du` about 18.725 GB); `.git/lfs` logical about 3.919 GB (allocated about 3.919 GB), 260 LFS paths. `git count-objects`: packed about 11.43 GiB, loose about 2.30 GiB | None; no GC, prune, history rewrite, or sparse-checkout |
| Local D archive mirror | `/mnt/d/BVM_Backages`: about 11.672 GB allocated | None; read-only |
| Google Drive BVM_Backages | Read-only metadata listing: 377 files / 375 ZIPs, 11,636,642,487 B | None; no cloud content SHA or deletion was performed |

The initial HTML scan recorded 8,325 files / 54,199,625,459 logical bytes / 54,217,961,472 allocated bytes. A fresh post-cleanup scan found 7,998 files / 46,460,723,114 logical bytes / 46,478,397,440 allocated bytes. The count delta is 327, not 355, and the apparent-size delta is 321,022,881 B smaller than the deletion ledger. The enumeration snapshots therefore do not reconcile (28 files / about 321 MB); the cause is not established, so **the scan-to-scan delta is not used as a reclaim claim**. The authoritative Phase 5 reclaim is the exact per-file unlink ledger and allocated-block sum above. The requested top-300 set totaled 17,167,276,150 logical / 17,168,584,704 allocated bytes before deletion. None of the Phase 5 target files were in that top-300 set.

The Drive/D duplicate review remains metadata-limited for cloud: 54 same-name/same-size groups are candidates, but cloud content SHA is unverified. The earlier estimate of about 1.286 GB of possible duplicate bytes is **not** proven reclaim and was not acted on. Local D ZIP hashes do not establish cloud byte identity.

## Large HTML: keep versus verified removal

The largest pages are not automatically safe cleanup targets. The top-300 set has 48 tracked and 252 ignored pages; none was removed. It includes approximately 251 4×4 run pages and 33 tracked QB-CB pages. The biggest 4×4 groups include:

| Page family | Approximate allocated bytes | Decision / reason |
|---|---:|---|
| `02_carry.html` | 6.58 GB | KEEP: carries six input-current signals not covered elsewhere |
| `04_t1.html` | 3.64 GB | KEEP: unique T1 internal evidence |
| `05_stage_D3_focus.html` | 2.635 GB | KEEP: unique D3 internal probes |
| tracked `05_acc_gap.html` pages | included above/top-300 | KEEP: tracked evidence; no Git-history operation authorized |

The deleted 355 pages were only D1/D2/D4/D5/D6 stage-focus pages whose selected signal sets were covered by retained, QA-passed pages from the same raw. All 13 distinct plot-recipe groups had a representative temporary rebuild through `scripts/josim-plot2.py`; Plotly trace data, layout and config matched (`PASS_CONTENT_EXACT`). HTML byte hashes differ because the renderer creates a random Plotly div ID and embeds a different temporary path; this is content/plot-structure equivalence, not byte-identical HTML. Every candidate's raw SHA remained unchanged.

There are 376 4×4 manifest references to absent HTML after this phase: 355 from this exact cleanup, 16 previously removed in Phase 4, and 5 pre-existing/unmapped absences. The Actions CSV distinguishes these. Manifests/QA were not rewritten. Retained large pages were not bulk-deleted merely because a raw exists; each still needs exact recipe, raw/probe, asset, and replacement/review-value validation before any future removal.

R-loop currently has 3,294 manifest-indexed pages plus 216 HTML files not in that manifest index (3,510 files on disk). Of the indexed pages, 100 have plot-QA PASS and 3,194 have a missing/failing QA file; 2,835 are linked from review pages, and the remaining 459 are marked for separate review. **No R-loop page was deleted.** Before any future cleanup, restore plot QA from existing raw/manifest evidence where possible, identify the 216 unmanifested pages, preserve review navigation, and verify replacement content. No JoSIM run is needed for those checks. An earlier scratch count of 235 extras was stale; the reproducible current filesystem-to-manifest comparison is 216.

Other high-space areas that remain protected include the BVM-QB-CB root (tracked HTML around 4.72 GB; 38 raw files), QB-RJ1/L1 sensitivity (about 1.31 GB HTML, tracked), and `bvm-load-qb-matrix` (about 1.06 GB HTML, 66 tracked pages, no local `raw.csv`). For the last two, the missing/unclosed raw-to-plot mapping means a non-destructive HTML rebuild cannot yet be proven; retain them.

## Historical evidence classification

The raw/run inventory covers 1,000 records: **15 A / active baseline references**, **759 B / unique scientific evidence**, **26 C / verified cold-archive run evidence**, and **200 E / unknown or incomplete closure**. The A references are the 15 cases in the existing current-baseline index; they remain protected. This is a recovery-status classification, not permission to delete. No raw was removed or relocated.

| Experiment area | Local allocated footprint (approx.) | Evidence and current disposition |
|---|---:|---|
| 4×4 diagonal array | 34.65 GB root; `runs/` 9.97 GB, 108 raw (~9.49 GB), 138 ZIPs | Keep. No full independent per-run recovery closure completed in Phase 5. |
| BVM-QB-CB topology | 9.57 GB root; `runs/` 6.94 GB, 38 raw, 10 ZIPs | Keep. At least one ZIP lacks the standard manifest; no full restore closure. |
| BVM R-loop one-shot | 6.95 GB root; `runs/` 4.09 GB, 514 raw (~3.22 GB), 39 ZIPs | Keep. QA gaps and human review links remain; archive closure is incomplete. |
| 2×2 row/column selection | 2.03 GB root; `runs/` 1.66 GB, 26 runs | Run evidence core has local-D ZIP/member SHA and prior independent restore PASS; eight `run.log` files remain local-only. Future scoped worktree exclusion is a candidate, not executed. |
| BVM-QB 50 GHz merge | 1.96 GB root; 43 raw, 4 ZIPs | Keep; no full per-run recovery closure. |
| V0–V9 `sfq_clock_two_read_v1` | 1.80 GB root; V0–V9 evidence protected | Keep. V9_analysis bytes were verified before and after this phase. |
| BVM load-QB matrix | 1.54 GB root; 66 tracked HTML, no local raw | Keep/unknown; cannot establish offline re-render closure. |
| QB-RJ1/L1 local sensitivity | 1.49 GB root; 5 raw, 1 ZIP, 233 tracked HTML | Keep; no complete archive/restore chain. |
| BVM-BQ-CB gap 2×1 v2 | 1.13 GB root; 4 raw, 9 ZIPs | Keep; no complete closure established here. |
| QB-T1 interface v1/v2 | about 0.69 GB each; 15 raw each | Keep; no verified full archive closure. |

Full top-30 directory sizes and per-run evidence fields are in `CLEANUP_PHASE5_ACTIONS.csv`. No old experiment is declared superseded and disposable solely by age or outcome.

## V9_analysis preservation and checkout note

V9_analysis files matched the pre-cleanup SHA snapshot after the HTML work:

| File | SHA-256 |
|---|---|
| `final_runs/V9_analysis/deck.cir` | `474a254f4511fb46bea6afd36500aa28111323f23f1be66b720170ee297ccb70` |
| `final_runs/V9_analysis/stimulus.inc` | `824eb8c5fe7adf2369721c87b76ec66c39165d4eacb8c72fefb45b90df877211` |
| `final_runs/V9_analysis/run.sh` | `4cb0760ffe697e28c05a060db5e2e1615ab2da1c78103d52189a26ceffbcfc97` |
| `final_runs/V9_analysis/sources_frozen/01_bvm_cell_0923.cir` | `76b7b90b4e58cc45d55adc24d1bc6e626957461a2abe21ca4a33319d58ac6489` |
| `final_runs/V9_analysis/raw.csv` | `03c2af990bd87c1c8cbe355245127f9edb619d8740c1cbe0679cef4b61420339` |

The audit checkout's tracked 4×4 `USER_CASE.env` still reads `DRIVE_MODE=SHARED`, `SE_TOPOLOGY=CELL`, `SE_GATE_MODE=CROSSPOINT`. This report did not edit it. Confirm/sync the user's newer row-shared-SE 11×13 topology separately before using this checkout for that experiment; no inference about the newer uncommitted design is made here.

## Recommended next action

Prioritize a **separate, approved worktree-visibility reduction**, not raw deletion: first complete exact backup closure for 4×4 (largest potential run subtree, 9.97 GB allocated), then QB-CB (6.94 GB), then R-loop (4.09 GB). The 2×2 `runs/` subtree (1.66 GB) has the strongest existing archive verification, but preserve its eight local-only run logs or explicitly define their Git-based recovery before any scoped sparse-checkout. Sparse-checkout affects the working tree only; it does not shrink `.git` or LFS.

Before cold-moving any run: verify `run ID → raw/deck/stimulus/source SHA → solver version/binary SHA → package manifest/member SHA → archive SHA and location/Drive ID → independent restore`. Drive IDs and metadata are locators, not content verification. Keep Phase 5 report and action ledger with the audit record. No additional cleanup is performed in this phase.
