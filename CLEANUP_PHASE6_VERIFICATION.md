# BVM Cleanup Phase 6 — Verification

Audit snapshot: `WHHoward/bvm`, branch `master`, HEAD `891d7502f46dc73788093a0703d1cf377926a094` (2026-10-15). The worktree was clean before the Phase 6 outputs were generated. No delete, move, sparse-checkout, Git maintenance, circuit edit, Drive/D write, or JoSIM run was performed.

## Phase 3–5 deletion audit

The listed deletion paths were extracted from the Phase 3 result table, Phase 4 `execution_status=DELETED` rows, and Phase 5 `PHASE5_DELETED_HTML` rows. Every path was checked directly against the current local filesystem, independent of GitHub.

| Phase | Recorded paths | Unique paths | Current path absent | Current ignore rule still matches | SHA/size record cross-check | Associated raw SHA |
|---|---:|---:|---:|---:|---:|---|
| 3 | 161 | 161 | 161 | 161 | 161/161 vs Phase 2 whitelist | 32 unique recorded raw SHAs found unchanged |
| 4 | 10,651 | 10,651 | 10,651 | 10,651 | 10,651 SHA records well-formed | Every associated raw path/SHA matched |
| 5 | 355 | 355 | 355 | 355 | 355 SHA/size rows consistent with the ledger | Every associated raw path/SHA matched |
| **Total** | **11,167** | **11,167** | **11,167** | **11,167** | **No cross-phase path overlap** | **No mismatch found** |

No deleted HTML currently exists at its recorded path, and none of the 11,167 deleted HTML SHA-256 values occurs at another current workspace path. Thus there is no evidence of exact-byte relocation or same-byte regeneration in this workspace. This check does not rule out a different-content replacement; the Phase 5 action ledger names 355 × 5 retained replacement-page references, and all 355 unique replacement pages currently exist. Phase 4 replacement/rebuild rationale remains as recorded in its QA report. Phase 3 pages remain recoverable from preserved raw/renderer/asset records, not from a same-byte copy.

The Phase 3 result rows match the corresponding Phase 2 whitelist SHA and size 161/161. The Phase 4/5 recorded paths are all still classified as ignored by current Git ignore rules; this status is only a current ignore-rule check, while the old action ledgers record their pre-unlink untracked status. Because these HTML files were ignored/untracked, GitHub commits alone would not prove local removal; the direct filesystem absence check above does.

### Phase 5 28-file discrepancy — partial reconciliation, cause UNKNOWN

The Phase 5 report recorded 8,325 HTML files / 54,199,625,459 B before cleanup and 7,998 / 46,460,723,114 B afterward. The 355 executed deletions total 8,059,925,226 B, so the two Phase 5 scan totals differ by only 327 files and by 321,022,881 B less than the deletion ledger.

Independent count arithmetic from the earlier full inventory gives:

- Phase 2 all-workspace baseline: 19,165 HTML files / 58,111,665,106 B.
- Expected before Phase 5 after the unique Phase 3+4 deletions: 8,353 files / 54,520,615,960 B.
- Phase 5's reported pre-cleanup scan is lower by **28 files / 320,990,501 B**. The Phase 5 pre-cleanup path-level census was not retained, so those 28 paths and the cause cannot be identified. Status: **UNKNOWN**; no specific cause is inferred.
- Phase 2 baseline minus all 11,167 unique Phase 3–5 deletion records predicts 7,998 remaining HTML files; the current full filesystem inventory independently finds exactly 7,998. Logical bytes predict 46,460,690,734 B versus current 46,460,723,114 B, a 32,380 B residual that also lacks a path-level baseline. The aggregate count therefore reconciles, but it does not explain the missing pre-scan paths or the small byte residual.

This is evidence against a current 28-file deletion failure: all exact deletion paths are absent and the current total matches the earlier baseline less the executed unique targets. It is **not** evidence that identifies why Phase 5's pre-scan differed. The Phase 5 aggregate discrepancy remains unresolved at path level.

## Preserved evidence and archive checks

- All current `RAW_CSV` files were SHA-256 hashed in the inventory (1,292 files; no hash read errors). For the cleanup-linked runs, all recorded raw hashes match current raw bytes: Phase 3 by the 32 recorded raw hashes; Phase 4 and Phase 5 by their recorded raw paths and hashes.
- All Phase 5 affected run directories (71) still contain `raw.csv`, a deck (`deck.cir`, `actual_deck.cir`, or `deck.template.cir`), `stimulus.inc`, `plot_manifest.json`, `plot_qa.json`, `probe_manifest.json`, `run.log`, and `source_manifest.json`. The exact Phase 5 `manifest_path` field exists for all 355 rows. This is a presence check for the listed evidence closure, not a claim that every run has every possible manifest filename.
- The delete ledgers contain only `.html` paths. No raw, deck, stimulus, circuit model, log, manifest, source, or configuration path was an executed delete target. Phase 3/4/5 QA and archive claims are retained as historical records; Phase 6 did not reinterpret them as a complete archive closure for every historical run.
- Current 4×4 V9_analysis matches the prior protected SHA snapshot: `raw.csv` `03c2af990bd87c1c8cbe355245127f9edb619d8740c1cbe0679cef4b61420339`, `deck.cir` `474a254f4511fb46bea6afd36500aa28111323f23f1be66b720170ee297ccb70`, `stimulus.inc` `824eb8c5fe7adf2369721c87b76ec66c39165d4eacb8c72fefb45b90df877211`, `run.sh` `4cb0760ffe697e28c05a060db5e2e1615ab2da1c78103d52189a26ceffbcfc97`, and frozen `01_bvm_cell_0923.cir` `76b7b90b4e58cc45d55adc24d1bc6e626957461a2abe21ca4a33319d58ac6489`. Ignored `CASE_CONFIG.json`, `RUN_MANIFEST.json`, and `SOURCE_MANIFEST.json` were also present and hashed; none was changed.
- Current tracked `circuits/bvm/bvm_cell_0923.cir` has SHA-256 `bbb741ba572924f018749d1fa0cf888876e4e0e352635614b9aeec14fb8cdb16`. The indexed historical package/member records for that path refer to other frozen SHA variants; no indexed archive member matching the current bytes was found. The current file is tracked clean at this HEAD and recoverable from Git, but a separate current-byte archive copy was not verified. This is a versioned-source distinction, not evidence that the local file changed during Phase 6.
- The Phase 4 local D archive `bvm-qb-current-baseline-n0-n4-closed-passive-replay-v1-20260917_v3_raw_handoff.zip` exists at `/mnt/d/BVM_Backages/`, size 49,968,422 B, and its current SHA-256 `9d049b311f52c5e0a288572f287fd517a0fb227168d7c6d7e2eb53ea9be67348` matches the Phase 4 record. Its earlier member-level QA remains the basis for atlas restore claims; this phase did not extract or rewrite it.
- Read-only Drive listing returned 380 objects at the BVM_Backages root (377 files + 3 subfolders), and 5 files in those subfolders: 382 files / 3 folders total, 11,671,479,003 B. All 134 distinct Drive IDs in the archive index are present in current metadata. This verifies metadata presence only; it does **not** verify cloud bytes or SHA.

## Snapshot integrity and limits

The current 4×4 tracked `USER_CASE.env` remains `DRIVE_MODE=SHARED`, `SE_TOPOLOGY=CELL`, `SE_GATE_MODE=CROSSPOINT`, `ROW_BITS=1111`, `COL_BITS=1111`, WL read 400u and SE read 100u. The user's described row-shared-SE 11×13 change is not represented by this file at the audited HEAD. No attempt was made to restore, merge, or modify it; synchronize/review that design separately before using this checkout for the new experiment.

Inventory snapshot: 40,879 non-`.git` filesystem entries (40,872 regular files, 7 symlinks, 0 special files), plus one `.git` aggregate row. All regular files were SHA-256 hashed (84,031,190,948 B read; zero hash errors); symlink SHA fields hash the link-target text, not a dereferenced file. 3,682 manifest-like JSON files were inspected; 21,349 current paths have a matching manifest path reference, with no manifest parse errors. The inventory represents the pre-output workspace snapshot and deliberately does not self-list its own CSV or the later Phase 6 report files; those audit deliverables are separate outputs.

`.git` apparent/allocated size differed across the inventory scan, directory-summary measurement, and later `du` snapshots: 18,721,169,015 / 18,725,056,512 B, then 18,727,394,343 / 18,731,290,624 B, then 18,733,641,896 / 18,737,561,600 B. HEAD did not change during the audit and no `gc`, prune, or history rewrite was run. The reason for the `.git` directory-size drift is **UNKNOWN**; pack/LFS counts are reported separately and were not intentionally modified.

Review checks (adversarial/numerical): direct filesystem oracle, path uniqueness/intersection, recorded SHA/size cross-check, raw SHA rehash, exact byte sums, and parent/child storage-layer separation were all run. Residual UNKNOWNs are explicit above. No cleanup decision is made by this report.
