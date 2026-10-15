# BVM 4×4 revised prune plan

## Decision and boundary

This is a proposed narrower retention plan, not a cleanup execution. No 4×4 run, raw, HTML, ZIP, or Drive file was deleted or moved. The scope is
`test/exploration/bvm-4x4-diagonal-array-v1-20261009/`; the other two protected experiment roots were not changed. No JoSIM solve was run.

The new 4×4 working tree occupies **34,650,099,712 allocated bytes (32.27 GiB)**. The figures below come from the Phase 6 inventory plus a current filesystem presence/size check of all 600 plot files. All 600 exist; 591 are proposed removal candidates and nine are selected references. The nine retained pages have been changed only to point at the root shared Plotly asset; their allocation size did not change.

| Component | Count | Logical bytes | Allocated bytes |
|---|---:|---:|---:|
| `runs/` case directories | 108 | 9,962,296,845 | 9,970,487,296 |
| `runs/*/raw.csv` (subset of `runs/`, do not add twice) | 108 | 9,494,469,207 | 9,494,966,272 |
| `plots/` HTML | 600 | 21,857,252,090* | 21,859,008,512 |
| `handoff/` ZIP | 138 | 2,669,482,925 | 2,669,780,992 |
| `manual_batches/` | 2 dirs / 59 files | 33,665 | 126,976 |
| Remaining platform/config/artifact files | — | — | approximately 150,687,744 |

\* The original inventory logical-size total predates the nine 30-byte Plotly path substitutions; allocated bytes, and therefore the reclaim estimate, are unchanged.

## Proposed run retention

Keep nine run directories as a compact reference set:

| Category | Run IDs | Reason |
|---|---|---|
| `KEEP_REFERENCE` | A018, A019 | Quiet/clocked T1 reference pair. |
| `KEEP_REFERENCE` | A027 | One full CB-chain baseline retained for carry-chain comparison/anomaly localization. |
| `KEEP_REFERENCE` | A030, A031 | Matched 15×15 pair differing in registered global clock start (200/210 ps). |
| `KEEP_REFERENCE` | A032, A033 | Same post-CB-sJTL topology on 11×13 and 3×3 inputs. |
| `KEEP_REFERENCE` | A107, A108 | Most recent archived 11×13 and 3×3 manual carry cases before selecting the V9 BVM source. |

Propose `DELETE_OBSOLETE` for the other 99 exact run directories:

- A001–A017
- A020–A026
- A028–A029
- A034–A106

This covers the early array/T1 baselines, superseded CBU variants and carry-position/count exploration, the C4R28/C5R28 batches, and the intermediate manual cases. In particular, A042–A047, A048–A075, A076–A078, and A079–A106 are no longer automatically protected. They can be rerun against the new design if later needed. A017 also has no accepted page QA in the inventory. No run is retained merely because a manifest once referenced it.

The nine retained run directories occupy **815,484,928 allocated bytes**. The 99 proposed obsolete directories occupy **9,155,002,368 allocated bytes (8.53 GiB)**. Their raw subset is 8,717,672,224 logical bytes; deleting those runs would abandon those raw results from the current tree.

## Proposed plot, ZIP, and manual-batch scope

Keep only these nine local HTML review pages; the candidate CSV contains the exact paths and refreshed hashes for them:

- A018 and A019: `01_t1_overview.html`
- A027: `02_carry_propagation.html`
- A030 and A031: `02_carry.html`
- A032 and A033: `04_t1.html`
- A107 and A108: `00_full_chain_overview.html`

Their Plotly URLs now resolve to `assets/vendor/plotly.min.js` from each page. They remain ignored/untracked local files and are not part of the Git commit.

Propose `DELETE_GENERATED` for the other **591 HTML files (21,545,263,104 allocated bytes, 20.06 GiB)**. No requirement to prove equivalent re-rendering is imposed for files that the user elects to abandon. This plan does not render replacements.

Propose removing all **138 local handoff ZIPs (2,669,780,992 allocated bytes)** as package copies, and the two exact old manual-batch directories (126,976 allocated bytes). The candidate CSV lists every ZIP and every manual-batch directory/file. ZIP member closure was not re-audited in this phase: removal is an intentional archive-retirement proposal, not a claim that each ZIP is redundant or recoverable. Selected raw/run directories remain separately listed as kept.

## Estimated current-worktree effect

| Proposed removal | Allocated bytes |
|---|---:|
| 99 run directories | 9,155,002,368 |
| 591 HTML files | 21,545,263,104 |
| 138 handoff ZIPs | 2,669,780,992 |
| Two manual-batch directories | 126,976 |
| **Total estimated worktree reclaim** | **33,370,173,440 (31.08 GiB)** |
| **Estimated 4×4 directory remaining** | **1,279,926,272 (1.19 GiB)** |

These are current-tree filesystem allocations, not a Git repository shrink estimate. The run/raw files and handoff ZIPs are Git-tracked; an ordinary commit removing them would remove working-tree copies but **would not remove their Git history/object storage**. The 591 HTML files are ignored/untracked, so their removal would reclaim working-tree blocks directly. Current `.git` allocation is 18,744,664,064 bytes; no GC, LFS prune, or history rewrite is proposed. Do not add `.git` bytes to the worktree-reclaim total.

## Current platform items to keep

Keep the runner, source/configuration, `experiment_manifest.json`, root Plotly asset, and all three protected experiment directories. `USER_CASE.env` remains unchanged and still specifies `SE_TOPOLOGY=CELL` and `SE_GATE_MODE=CROSSPOINT`; it is not evidence that the newly selected shared-row-SE / BL+SE-read architecture has been migrated. The V9 source identity change is separate from that topology work.

## Review map and next decision

`BVM4X4_REVISED_PRUNE_CANDIDATES.csv` has 1,016 exact-path inventory rows. It assigns the five requested categories and includes `estimated_reclaim_bytes` plus a de-duplication flag so run-directory totals are not added again from raw-file child rows. Its proposed actions are not authorization to execute.

Before a later execution, approve or edit the exact rows in that CSV. If approved as written, the selected historical results will no longer have current-tree copies; the Git history still holds tracked objects unless a separate history-retirement action is explicitly authorized. No such history action is included here.
