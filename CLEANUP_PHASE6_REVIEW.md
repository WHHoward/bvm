# BVM Cleanup Phase 6 — Human Review

**No cleanup was performed in Phase 6.** The current `master` snapshot is `891d7502f46dc73788093a0703d1cf377926a094`; the worktree was clean at audit start. This report and the companion CSVs classify evidence for discussion only. Every `potential` byte figure is an upper bound, not an authorized reclaim amount.

## Current storage, separated by layer

| Storage layer | Logical / allocated size | Notes |
|---|---:|---|
| Workspace, includes `.git` | 102,852,623,802 B logical / 102,955,991,040 B allocated | Latest `du` snapshot after the five Phase 6 deliverables were generated; decimal 102.85 / 102.96 GB |
| `test/exploration` | 82,672,780,894 B logical / 82,760,728,576 B allocated | Included in workspace total; decimal 82.67 / 82.76 GB |
| `.git` | 18,733,641,896 B logical / 18,737,561,600 B allocated | Included in workspace total; 7 packs, 11.43 GiB packed, 2.31 GiB loose, one 21.34 MiB garbage object |
| `.git/lfs` | 3,918,524,121 B logical / 3,919,388,672 B allocated | Included in `.git`; 260 LFS paths |
| D: `/mnt/d/BVM_Backages` | 11,671,495,387 B logical / 11,672,293,376 B allocated | Separate local archive mirror; not part of workspace total |
| Drive `BVM_Backages` | 11,671,479,003 B metadata size | 382 files across the root and three subfolders, plus 3 folders. Metadata IDs are present; cloud content SHA is not available from this listing. |
| Filesystem `/dev/sdd` | 747,096,711,168 B available at the recorded `df` snapshot | System free space; not additive with any directory size |

The inventory CSV’s earlier `.git` aggregate is 18,721,169,015 B logical / 18,725,056,512 B allocated; the directory-summary snapshot is 18,727,394,343 / 18,731,290,624 B; the latest `du` above is larger again. HEAD is unchanged and no GC/prune/history rewrite was run. The `.git` size drift across snapshots is unresolved and is not attributed to a particular cache or process. The `df` free-space number is a prior audit snapshot, not the post-report free-space reading.

The inventory covers 40,879 non-`.git` entries: 40,872 regular files, 7 symlinks, and no special files. All regular files were SHA-256 hashed with no read errors. The `.git` internals are represented as an aggregate, with objects/packs/LFS separately summarized; individual Git objects are intentionally not expanded. The inventory is a pre-output snapshot and does not self-list its own CSV or the later Phase 6 report files.

## Space by file type and Git state

| Type | Count | Logical bytes | Allocated path bytes |
|---|---:|---:|---:|
| HTML | 7,998 | 46,460,723,114 | 46,478,397,440 |
| Raw CSV | 1,292 | 20,538,181,235 | 20,541,288,448 |
| ZIP | 284 | 8,534,843,140 | 8,535,461,888 |
| Other CSV | 2,772 | 5,213,380,556 | 5,220,917,248 |
| JSON | 8,285 | 1,491,866,062 | 1,510,793,216 |
| Data/text | 3,353 | 1,093,418,976 | 1,099,841,536 |
| Logs | 1,624 | 219,001,799 | 223,940,608 |
| SPICE netlists | 5,618 | 88,663,103 | 104,398,848 |
| SPICE includes | 1,003 | 2,209,742 | 4,403,200 |

Tracked files: 32,511 paths / 52,635,762,413 logical bytes / 52,715,393,024 allocated path bytes. Ignored files: 8,368 paths / 31,395,428,790 logical bytes / 31,415,226,368 allocated path bytes. There were no ordinary untracked, non-ignored files at audit start. File-level allocated sizes are per path; directory totals below come from `du`. No hard-linked file groups were found.

Of the inventory rows, 748 have an indexed local archive path, 3,364 have an exact member-SHA match recorded, and 5,743 have only run/package-level status. 31,771 archive states remain UNKNOWN (no direct per-file archive mapping in the reviewed indexes); this does not prove that no backup exists. One current canonical BVM source has indexed historical archive variants whose member SHA does not match the current Git version. Manifest path matching found 21,349 paths (including manifest self-rows); 3,682 manifest-like JSON files were parsed without error.

## 30 largest experiment directories

Sizes are allocated bytes (decimal GB in parentheses); raw bytes are retained in the CSV. Each row is a sibling experiment root, so the rows do not overlap one another.

| # | Experiment directory | Allocated bytes (GB) | Files |
|---:|---|---:|---:|
| 1 | `bvm-4x4-diagonal-array-v1-20261009` | 34,650,099,712 (34.65) | 4,571 |
| 2 | `bvm-qb-cb-array-topology-v1-20260924` | 9,570,643,968 (9.57) | 1,381 |
| 3 | `bvm-rloop-one-shot-tuning-v1-20260918` | 6,961,168,384 (6.96) | 12,747 |
| 4 | `bvm-2x2-rowcol-selection-v1-20260928` | 2,032,631,808 (2.03) | 843 |
| 5 | `bvm-qb-50ghz-merge-v1-20260922` | 1,964,834,816 (1.96) | 1,461 |
| 6 | `sfq_clock_two_read_v1` | 1,795,166,208 (1.80) | 556 |
| 7 | `bvm-load-qb-matrix-v1-20260901` | 1,539,563,520 (1.54) | 451 |
| 8 | `qb-rj1-l1-local-sensitivity-v1-20260909` | 1,495,863,296 (1.50) | 537 |
| 9 | `bvm-bq-cb-gap-2x1-v2-20260923` | 1,129,943,040 (1.13) | 317 |
| 10 | `bvm-qb-rj1-timestep-robustness-v1-20260903` | 1,015,226,368 (1.02) | 398 |
| 11 | `bvm-qb-t1-interface-topology-v1-20260914-v2` | 687,341,568 (0.69) | 158 |
| 12 | `bvm-qb-t1-interface-topology-v1-20260914` | 686,616,576 (0.69) | 157 |
| 13 | `bvm-full-closed-loop-qb-parameter-screening-v1-20260911` | 672,849,920 (0.67) | 580 |
| 14 | `bvmsim-4bvm-paperlike-common-sl-accumulation-isolation-v1-20260904` | 518,332,416 (0.52) | 158 |
| 15 | `bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910` | 499,073,024 (0.50) | 130 |
| 16 | `qb-l1-ibias-full-grid-bjs400-v1-20260910` | 445,370,368 (0.45) | 171 |
| 17 | `physical-bvm-jsl12-qb-sfq-closure-v1-20260824` | 438,480,896 (0.44) | 108 |
| 18 | `qb-l1-ibias-rj1-independent-characterization-v1-20260909` | 422,813,696 (0.42) | 497 |
| 19 | `bvmsim-jm2-delta4-replay-sensitivity-v1-20260908` | 419,655,680 (0.42) | 147 |
| 20 | `bvmsim-jm2-single-vs-4bvm-shared-sl-v1-20260907` | 401,625,088 (0.40) | 152 |
| 21 | `bvm-qb-two-parameter-combination-v1-20260911` | 372,445,184 (0.37) | 211 |
| 22 | `bvmsim-4bvm-state-position-closure-v1-20260903` | 347,422,720 (0.35) | 140 |
| 23 | `bvm-qb-current-baseline-n0-n4-closed-passive-replay-v1-20260917` | 315,527,168 (0.32) | 443 |
| 24 | `qb-rj1-highrange-boundary-search-bjs400-v1-20260910` | 305,565,696 (0.31) | 129 |
| 25 | `bvm-sfq-receiver-r1c-bias-margin-20260821` | 298,971,136 (0.30) | 146 |
| 26 | `qb-rj2p12-timestep-robustness-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910` | 280,690,688 (0.28) | 91 |
| 27 | `bvm-sfq-receiver-r2a-coupling-20260821` | 275,423,232 (0.28) | 154 |
| 28 | `bvm-population-scaling-rj2p11-midpoint-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911` | 271,843,328 (0.27) | 117 |
| 29 | `bvm-jsl8-500-physical-qb-recheck-v1-20260824` | 271,110,144 (0.27) | 68 |
| 30 | `bvm-sfq-receiver-r1-oneshot-20260819` | 269,529,088 (0.27) | 107 |

The full 159 experiment-root list, and per-root type/status byte totals, are in `CLEANUP_PHASE6_DIRECTORY_SUMMARY.csv`. `CLEANUP_PHASE6_REVIEW_CANDIDATES.csv` additionally lists the eight exact `2×2` A019–A026 `run.log` paths marked local-only.

## Largest individual files and major root composition

The complete top-100 file list, each file SHA, Git state, archive status and risk are in `CLEANUP_PHASE6_REVIEW_CANDIDATES.csv`. The largest examples include:

| File | Logical bytes | Type / state |
|---|---:|---|
| `bvm-qb-cb-array-topology-v1-20260924_delta_U005-U012_20260924.zip` | 2,026,365,221 | ZIP / ignored; package lineage and member closure need review |
| `bvm-qb-50ghz-merge-v1-20260922_raw_handoff_classic-v4.zip` | 331,196,857 | ZIP / tracked |
| `bvm-qb-cb-array-topology-v1-20260924_full_U004_2x1_topology_baseline.zip` | 308,671,324 | ZIP / ignored |
| `bvm-qb-50ghz-merge-v1-20260922_raw_handoff_combined-v3.zip` | 212,256,973 | ZIP / tracked |
| `bvm-qb-50ghz-merge-v1-20260922_raw_handoff_stimulus-v2.zip` | 212,173,016 | ZIP / tracked |
| 4×4 `A022_CHAIN_PAPER_GLOBAL_CLOCK/raw.csv` | 95,786,305 | Raw CSV / tracked, unique run identity preserved |

Largest roots by file-type allocation:

| Experiment | Allocated total | Raw CSV | HTML | ZIP | Other notable content |
|---|---:|---:|---:|---:|---|
| 4×4 diagonal array | 34.65 GB | 9.49 GB (27.4%) | 21.86 GB (63.1%) | 2.67 GB (7.7%) | 4,571 files; HTML is mostly run diagnostics and review pages |
| BVM-QB-CB topology | 9.57 GB | 2.14 GB (22.3%) | 4.72 GB (49.4%) | 2.62 GB (27.4%) | 38 raw, 10 ZIPs, tracked and ignored outputs |
| BVM R-loop one-shot | 6.96 GB | 3.22 GB (46.3%) | 1.99 GB (28.6%) | 0.83 GB (12.0%) | 514 raw, 3,529 HTML, 39 ZIPs |
| 2×2 row/column selection | 2.03 GB | 1.59 GB (78.0%) | 46.8 MB (2.3%) | 311.6 MB (15.3%) | 26 raw, 33 ZIPs, 8 local-only run logs |
| BVM-QB 50 GHz merge | 1.96 GB | 116.1 MB (5.9%) | 985.8 MB (50.2%) | 849.4 MB (43.3%) | 43 raw, 4 ZIPs |
| `sfq_clock_two_read_v1` | 1.80 GB | 202.0 MB (11.3%) | 976.4 MB (54.4%) | 25.8 MB (1.4%) | 532.3 MB other CSV, 55.7 MB logs |
| BVM load-QB matrix | 1.54 GB | 0 local `raw.csv` | 1.06 GB (69.2%) | 0 | 408.7 MB CSV; 66 tracked HTML |
| QB-RJ1/L1 sensitivity | 1.50 GB | 35.5 MB (2.4%) | 1.31 GB (87.6%) | 6.3 MB | 5 raw; tracked HTML/CSV |
| BVM-BQ-CB gap 2×1 v2 | 1.13 GB | 239.7 MB (21.2%) | 496.5 MB (43.9%) | 361.8 MB (32.0%) | 4 raw, 9 ZIPs |

## Exact-SHA duplicate candidates

The full file-and-SHA relationships are included in the review candidate CSV. Across the workspace snapshot (excluding `.git` internals), there are **1,726 exact-SHA groups / 11,842 file paths**, with 2,920,680,936 B of theoretical extra logical copies and about 2,945,740,800 B of block-allocation excess if one copy in each group were no longer needed. These are not safe-delete estimates: identical raw bytes can be intentional references from distinct experiments, and identical assets/archives can have path or recovery significance.

| Content class | Groups | File paths | Extra logical bytes |
|---|---:|---:|---:|
| Raw CSV | 88 | 226 | 1,437,605,880 |
| Other CSV | 222 | 1,062 | 1,009,762,148 |
| HTML | 16 | 32 | 206,183,612 |
| Shared Plotly JS | 1 | 18 | 80,987,881 |
| ZIP | 2 | 4 | 14,005,159 |

The remaining groups are JSON, logs, netlists, images, configs, and other support files. A matching SHA proves byte identity, not scientific interchangeability. No duplicate path was removed.

Separately, the earlier Phase 4 index reports 54 exact-SHA duplicate ZIP groups on the D: mirror (about 1,286,093,431 B extra-copy estimate). Phase 6 did not re-hash all those external files. Drive metadata shows 54 same-name/same-size groups, but cloud contents have no verified SHA; these are not local-workspace savings and are not confirmed Drive duplicates.

## Historical experiment review categories

| Family / path | Category | Purpose and current reference | Archive / unique-evidence status | Daily access |
|---|---|---|---|---|
| 4×4 diagonal array | CURRENT | Current platform family and historical BVM→QB→CB/sJTL→T1/DFF work; user’s newer row-shared-SE design is not reflected by this checkout’s `USER_CASE.env` | 108 raw / 138 ZIP; full independent per-run restore closure incomplete; keep all run evidence | Yes for platform files; user decides for each historical run |
| `sfq_clock_two_read_v1` / V9_analysis | CURRENT / protected | V0–V9 multi-round multiplier evidence; V9 files protected | SHA snapshot matches prior report; Drive IDs are metadata-only for payload content | Yes for V9 review and current continuation |
| 2×2 row/column selection | ARCHIVE_REVIEW | Independent/shared drive modes, SE gating, second-read and T1 tests | 26 core run archives/member hashes and prior restore PASS; eight `run.log` remain local-only | Likely not daily; user decides |
| BVM R-loop one-shot | HISTORICAL_IMPORTANT | BVM state/read/shunt and receiver-boundary controls | 514 raw/39 ZIP; incomplete QA/restore closure; unique controls remain | Not presumed |
| BVM-QB-CB array topology | HISTORICAL_IMPORTANT | Array and output-chain topology, including controls/negative evidence | 38 raw/10 ZIP; full closure incomplete | Not presumed |
| BVM-QB merge / load matrix / QB-T1 interfaces | HISTORICAL_IMPORTANT or UNKNOWN | Receiver, loading, merge, and T1 connection history | Per-run closure incomplete; some tracked HTML has no local raw mapping | Not presumed |
| Ignored generated HTML | DERIVED_REVIEW | Rendered views of raw evidence | Some groups are reproducible; this does not imply each page is redundant or non-unique | User review |

The directory summary assigns one of `CURRENT`, `HISTORICAL_IMPORTANT`, `ARCHIVE_REVIEW`, `DERIVED_REVIEW`, or `UNKNOWN` to every experiment root and records raw/HTML/ZIP/other sizes, tracked/ignored counts, archive notes, purpose hints, current-reference status, unique-evidence caveats, and daily-access prompts. These labels are for discussion only.

## Largest potential future workspace reductions — none performed

Ranked by current measured allocated bytes, not by file count:

| Candidate path | Current allocated upper bound | Closure/risk | Phase 6 action |
|---|---:|---|---|
| 4×4 `runs/` | 9,971,326,976 B (9.97 GB) | Largest potential; 108 raw and 138 ZIPs, but full per-run restore closure not verified | Keep; complete archive/member/restore map first |
| BVM-QB-CB `runs/` | 6,943,604,736 B (6.94 GB) | 38 raw/10 ZIP; one package lacks standard manifest | Keep; close all run/source/member hashes |
| R-loop `runs/` | 4,095,565,824 B (4.10 GB) | 514 raw/39 ZIP; review/QA and full restore closure incomplete | Keep; repair QA/index mapping without JoSIM before discussing |
| 2×2 `runs/` | 1,661,902,848 B (1.66 GB) | Strongest archive closure, but eight logs remain local-only | `ARCHIVE_REVIEW` only; preserve logs; no sparse-checkout |

Each number is a parent directory's upper bound and overlaps all files beneath it. Do not add these to HTML/raw/ZIP candidate totals. Git sparse-checkout would affect only the worktree, not `.git`/LFS, and was not performed. Every candidate needs a separate exact target list, recovery map, and explicit user authorization.

## User data and action boundary

The inventory records all current ignored files, including V9_analysis artifacts. Git was clean at the start, so no pre-existing uncommitted tracked changes were detected; ignored files are nevertheless preserved and hashed. The checkout’s current `USER_CASE.env` still specifies `SE_TOPOLOGY=CELL` and `SE_GATE_MODE=CROSSPOINT`, not row-shared SE. I did not change it or infer that the described 11×13 design was absent from other copies; this finding only describes the audited checkout.

One archive-version distinction is worth human review: current tracked `circuits/bvm/bvm_cell_0923.cir` is SHA-256 `bbb741ba572924f018749d1fa0cf888876e4e0e352635614b9aeec14fb8cdb16`; indexed historical package members for that same source path use other frozen hashes. Git HEAD is the verified restore path for the current bytes, but no independent archive copy matching this current SHA was verified in the indexed archive records. The V9_analysis frozen copy remains a separate source version with its own recorded SHA.

The five Phase 6 deliverables are audit outputs; the full file inventory is an inventory-start snapshot, so it does not recursively list its own CSV or later Phase 6 outputs. The directory summary uses an explicit workspace aggregate and marks parent totals non-additive.

**No file has been deleted, moved, archived, or sparse-checked-out in Phase 6.** The review candidate CSV is not authorization to act. Git history/LFS, D:, and Drive remain unmodified.
