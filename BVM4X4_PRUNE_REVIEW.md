# BVM 4×4 internal prune review — planning only

**No 4×4 internal files were removed, moved, or modified.** This is a file-level review queue for later user/ChatGPT selection, not deletion authorization. The machine-readable exact-path ledger is [BVM4X4_PRUNE_CANDIDATES.csv](BVM4X4_PRUNE_CANDIDATES.csv).

## Current footprint

Snapshot from the Phase 6 inventory, cross-checked against the current tracked tree and local directory summaries:

| Item | Files/records | Logical bytes | Allocated bytes | Review status |
|---|---:|---:|---:|---|
| 4×4 platform root | 4,571 files | 34,638,818,698 | 34,650,099,712 | CURRENT; not a single deletion target |
| `runs/` tree | 108 runs | 9,962,296,845 | 9,970,487,296 | Review by run; parent total is not additive to child rows |
| `raw.csv` | 108 | 9,494,469,207 | 9,494,966,272 | Preserve all raw |
| `plots/**/*.html` | 600 | 21,857,252,090 | 21,859,008,512 | Review individually; no deletion authorized |
| `handoff/*.zip` | 138 | 2,669,482,925 | 2,669,780,992 | Preserve pending per-run restore closure |
| `manual_batches/` | 59 files | 33,665 | 126,976 | Protect recent manual evidence |

The above category totals overlap where a run directory contains raw, QA, decks and other artifacts; do not sum parent and child rows. “Allocated” means filesystem blocks reported by the local scan, not reclaim guaranteed by unlinking. All units above are bytes.

The current tracked `USER_CASE.env` is the old snapshot `SE_TOPOLOGY=CELL`, `SE_GATE_MODE=CROSSPOINT`, row/column `1111`; this is **not** evidence of the user's newer row-shared-SE architecture. It was not modified. `V9_analysis` and other user-selected raw/configuration files were not touched. The user's new architecture must not be inferred from this old example.

## Run ranges

The review ledger contains rows for all 108 A-runs. Potential review-only ranges are A001–A041, A048–A075, and A079–A106 (97 runs; 8,871,761,575 logical bytes for those run directories in the generated ledger). Preserve A042–A047, A076–A078, A107–A108 and both recent `manual_batches` (`C4R28_210`, `C5R28_210`). This range distinction only prioritizes review; it does not establish redundancy or authorize removal.

All 108 current run raw files have exact member-SHA matches recorded in Phase 6, but the complete independent recovery closure is not established for every run: raw/deck/stimulus/source closure, solver version and binary, package manifest, archive SHA/location, and an independent extraction test must be tied together per run before any cold move. ZIP existence or a member hash alone is insufficient. The 138 ZIPs in the candidate ledger are Git-tracked; archive status remains `UNKNOWN` for deletion/recovery decisions.

## HTML review

The candidate CSV lists all 600 current HTML files with exact path, size, recorded inventory SHA, associated run/page-QA mapping when available, renderer/asset metadata, and a no-delete disposition. Current recipe evidence breaks down as:

| Review class | HTML pages | Allocated bytes | Meaning |
|---|---:|---:|---|
| Human-review value; preserve pending explicit choice | 231 | 13,174,661,120 | Treat as valuable review evidence |
| Recipe present, replacement/equivalence not tested | 293 | 6,670,168,064 | Possible future rebuild candidate, not yet proven interchangeable |
| Unique/unmapped review page | 38 | 1,182,048,256 | No exact run-level recipe/QA mapping found; preserve |
| Protected manual pages | 38 | 832,131,072 | Preserve |

Run-page QA has 562 `PASS` mappings and 38 pages with no run `plot_qa.json` entry. The PASS state authenticates prior plot QA, but does not by itself prove a replacement HTML would be equivalent or that the current HTML SHA still equals the inventory snapshot. The file-level ledger marks `html_current_sha_rechecked=NO`; therefore its HTML SHA values are recorded audit values, not fresh per-file hashes from this review. No HTML was deleted. A future HTML cleanup should first re-hash candidates, prove raw SHA and probe set, renderer plus Plotly asset SHA and rendering options, perform representative rebuilds per recipe, map every removed page to an accepted replacement, and protect unique/manual views.

Largest page families identified in prior local reports include `02_carry.html` (~6.58 GB allocated), `04_t1.html` (~3.64 GB), and `05_stage_D3_focus.html` (~2.64 GB). Their size makes them worth reviewing early, but these are also high-value scientific review pages and should not be selected by size alone.

## Candidate order and estimated benefit

1. **HTML recipe candidates (293 files, 6,670,168,064 allocated bytes upper bound).** Highest plausible reclaim without losing raw, but not currently safe: exact per-file SHA not freshly rechecked, page-level re-render equivalence not tested, and some HTML is valuable to human review. Each row is `NO_DELETE; user review only`.
2. **A-run directories A001–A041, A048–A075, A079–A106.** 8,871,761,575 logical bytes in the run-directory grouping; not a safe worktree reclaim estimate until full restore closure is proven. Do not delete raw or move runs yet.
3. **Handoff ZIPs (138 files, 2,669,482,925 bytes).** Keep until each run's closure and package role are established. The ZIP data are tracked by Git, so removing them from the working tree would not remove their Git-history storage.
4. **Recent manual ranges and `manual_batches`.** Keep.

The total 21,859,008,512 allocated bytes of HTML is a theoretical ceiling only. The currently evidenced subset of recipe-present pages is 6,670,168,064 allocated bytes; even that is not presently a safe deletion estimate. No worktree space is released by this review. Any `git rm` of tracked material would make the files absent from a new tree but would not erase prior Git objects or LFS history.
