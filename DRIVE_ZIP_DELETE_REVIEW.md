# BVM_Backages Drive ZIP review — 2026-10-15

**Read-only audit. No Drive file was deleted, moved, renamed, or edited.** The 58 duplicate groups have been byte-verified, but none is deletion-cleared because global reverse-reference closure is not fully observable through the current connector.

## Recursive inventory and space

Folder `BVM_Backages` (`1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh`) was listed directly and all three child folders were recursively listed. The scan returned 377 root files and three folders; those folders contain five additional files. Total: **382 files** (380 ZIP, 2 Markdown), **11,671,479,003 bytes** (about 11.67 GB / 10.87 GiB). Of that, ZIPs are 11,671,456,802 B and summary Markdown is 22,201 B. Root files total 11,636,642,487 B; nested files total 34,836,516 B.

| Inventory disposition | ZIP files | Bytes | Meaning |
|---|---:|---:|---|
| `KEEP_ACTIVE` | 164 | 3,413,909,621 | 137 current 4×4 archives (2,669,439,626 B) and 27 `sfq_clock_two_read_v1` archives (744,469,995 B); no ZIP matched `bvm-qb-test-1013` |
| `UNKNOWN_REFERENCE_CLOSURE` | 58 | 1,320,886,648 | One extra file ID from each byte-identical pair; content identity is proven, but deletion reference closure is not |
| `HISTORICAL_REVIEW` | 157 | 6,936,617,234 | Historical archive copies; no per-run restore closure completed here |
| `SUPERSEDED_METADATA` | 1 | 43,299 | In the explicitly named superseded-metadata folder; retain pending review |

The categories sum to the 380 ZIP files. All 380 remain in Drive. `DRIVE_ZIP_INVENTORY.csv` includes every file ID, parent folder, size, timestamps, Drive URL, Git/D: mapping, platform relationship, available hash, and reference status.

## Duplicate verification

There are **58 same-name/same-size ZIP pairs** (54 in the root folder, one pair spanning the 4×4 upload-retry subfolder, and three pairs spanning the 2×2 retry subfolder). I streamed both Drive file IDs in each pair through SHA-256 computation, without saving ZIPs to the repository or D: drive:

- All **116/116** cloud streams completed with byte counts matching Drive metadata.
- All **58/58** pairs had identical SHA-256; no size/hash mismatch was found.
- Extra-copy upper bound: **1,320,886,648 B** (about 1.23 GiB).
- The recursive local D: mirror contains 382 files totaling exactly 11,671,479,003 B. All candidate pairs have corresponding D: paths. The 54 root duplicate pairs' D: hashes match each other and the Drive stream; the four cross-folder pairs' D: copies were also individually hashed and match.
- 50 duplicate groups have an exact tracked Git archive path and their current Git-worktree SHA-256 matches the Drive stream. Eight groups have no exact tracked archive basename/size match; do not infer that an archive under another name is absent.

The Drive connector metadata did not expose `md5Checksum` or `sha256Checksum`; the hashes above come from the file bytes streamed by file ID. This verifies byte identity for the 58 known duplicate groups, **not** content-identical archives with different names. Singleton ZIPs were not downloaded or hashed, so different-name/content duplicates remain `UNKNOWN`.

## Manifest and recovery-chain limits

- Exact file-name/Drive-ID search over local manifest, package-QA, archive, Markdown, and recovery text found no references to the 58 duplicate file IDs/names.
- The two Markdown files inside `BVM_Backages` were fetched and inspected. The 4×4 summary names six A001–A006 evidence ZIPs; the 2×2 summary names one 2×2 snapshot. None names the duplicate groups. These summary-linked files are retained as active/historical evidence and are recorded in the inventory.
- A Drive `fullText contains` query did not return even a known existing ZIP title, so it is not a usable global reverse-reference check in this connection. ZIP-internal manifests and documents outside this folder were not exhaustively inspected.
- Consequently the 58 pairs are **content-verified duplicate identities**, but their extra file IDs remain in category `UNKNOWN` because reference closure is incomplete. SHA identity is recorded separately; `VERIFIED_DUPLICATE` is not used as a deletion-ready classification. Preserve both IDs until the remaining reference question is resolved and the user approves exact IDs.

## Possible space recovery — not authorization

- **1,320,886,648 B** is the content-verified duplicate-copy ceiling, contingent on confirming external link/reference safety and explicit approval.
- **6,936,617,234 B** of historical ZIPs plus **43,299 B** of superseded metadata are review-only upper bounds. Their raw/deck/stimulus/source/solver/package restoration chains were not independently verified in this Drive audit, so this is not safe-to-delete space.
- Combined theoretical maximum from all non-active categories is 8,257,547,181 B, but it is not a current reclaim estimate or recommendation.
- Actual bytes deleted or moved: **0**. All exact IDs and candidate dispositions are in `DRIVE_ZIP_DELETE_CANDIDATES.csv`; no automatic cleanup or trash operation was performed.
