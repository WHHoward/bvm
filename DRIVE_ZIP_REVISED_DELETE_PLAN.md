# Google Drive ZIP revised deletion plan

## Snapshot

This is a file-ID-level proposal only. No Drive file was deleted, moved, renamed, or edited. The read-only inventory covered `BVM_Backages` and its subfolders: **382 files total** (380 ZIPs and 2 Markdown summaries), **11,671,479,003 bytes** total. ZIP bytes are 11,671,456,802; Markdown summaries are 22,201 bytes.

The revised rule is to keep only the existing `sfq_clock_two_read_v1` set and a small BVM 4×4 reference set. Older experiments may be deliberately abandoned; for them, the plan does not claim that raw can still be independently recovered. The exact Drive file ID, URL, size, cloud hash status, local/Git path, paired file, and loss warning are in `DRIVE_ZIP_REVISED_DELETE_CANDIDATES.csv`.

## Proposed retained set

Keep **43 ZIPs totaling 950,377,055 bytes**:

- 27 existing `sfq_clock_two_read_v1` ZIPs: 744,469,995 bytes. This retains the present V9 and 11×13 evidence set without trying to prune that platform in this task.
- 16 BVM 4×4 ZIPs: 205,907,060 bytes: A018/A019 quiet/clocked T1; A027 full CB chain; A030–A033 post-CB-sJTL comparisons; A107/A108 recent 11×13/3×3; and the source/metadata ZIPs associated with those selected batches.
- The two Markdown summary files remain; no ZIP is mapped to `bvm-qb-test-1013` in the inventory.

The exact retained 4×4 file IDs are:

| Reference | Retained Drive file IDs |
|---|---|
| A018/A019 and T1 source | `1y549d-OXtGcDQw3C1NER8FjrZsd30Oi7`, `1gkUX_J-I0izXhFROo6lpJd013mc_EGfj`, `1RbnRl-U-oax8wXj91c7XwuRKe9_Yvz1i` |
| A027 and its batch source/metadata | `1XrXEW047qilCuugCWwaMyFDmhCQOLioV`, `197NcouE5TigL6yGmsc_d5DpshzfeIh0O`, `149X82KjVIrRW1KDjfkWbuBkZuyBN687F` |
| A030–A033 and their batch source/metadata | `1O4R41NU3MtzIncIjN2KWHr8hmmY9V6HQ`, `19KjjvLmUDTpR1XV70l-1y4HRN_trz0mF`, `1ow3WHPPbJFzZQYEZP879G6uVAckerzDQ`, `1QxnK_8NA77KaPinnUsvG4OxfSABJfljA`, `1XBYUUEQNXSSBUtNiylFtYmClhGM7jYI0`, `1TsqEXaEGunXHmyKzpQNqKxPeOjVAAT0N` |
| A107/A108 and run metadata | `1w07QXZBQOZQXWZEUM2EC_Y9Ds_tD7a4G`, `1tj2CzqIy8w2OUBFP_XqjJaKN86LQzif7`, `1h7pi17NHGB_7sI3gRPLK44FiIAdCcPtZ`, `1qFIkqme_ZGSej0occabdbsmKcLbM9eLv` |

The retained 27 `sfq_clock_two_read_v1` IDs are unchanged from `DRIVE_ZIP_INVENTORY.csv`; the revised deletion CSV lists only proposed deletion IDs.

## Proposed exact deletion set

The CSV contains **337 unique ZIP file IDs** totaling **10,721,079,747 bytes (9.99 GiB)**:

| Disposition | Count | Bytes | Notes |
|---|---:|---:|---|
| `DELETE_OBSOLETE_HISTORICAL` | 157 | 6,936,617,234 | Historical experiment archives under the revised abandon/rerun policy. They may be their only archive copy; data may become non-recoverable if the user approves. |
| `DELETE_DUPLICATE_EXTRA` | 58 | 1,320,886,648 | Extra member of a byte-identical pair; pair SHA-256s were streamed and matched. The CSV records both IDs and whether the paired file is itself retained or also proposed for retirement. |
| `DELETE_OBSOLETE_4X4_ARCHIVE` | 121 | 2,463,532,566 | Earlier 4×4 package/archive files not in the selected 16-file reference set. Old A001–A108 evidence not selected for retention may be abandoned. |
| `DELETE_SUPERSEDED_METADATA` | 1 | 43,299 | Prior metadata version. |
| **Total** | **337** | **10,721,079,747** | No Drive operation performed. |

The 58 duplicate groups are byte-verified at the ZIP level: both cloud streams had the same size and SHA-256 for every pair, and the corresponding D-drive copies matched. This verifies identity only, not whether a pair is referenced inside another ZIP or external manifest. For groups whose experiment is being retired, both paired IDs may appear in the deletion plan; the former “keep copy” is not represented as retained evidence. For the selected A107/A108 or active clock archives, the paired retained ID remains explicit.

## Projected Drive usage

If every proposed deletion were later approved: **950,377,055 ZIP bytes** would remain, plus 22,201 bytes of Markdown summaries, for **950,399,256 bytes total** (about 0.885 GiB). This is a scenario estimate, not an action or promise of a verified full restore chain.

The existing inventory has no cloud SHA-256 for most singleton ZIPs. Those are deletion proposals because the experiment is considered obsolete, not because a complete alternate backup was proven. The loss warning in each CSV row makes that explicit. There is no global proof that no external manifest references a ZIP; this task did not expand into exhaustive archive-member or global Drive-reference indexing.

## Approval boundary

Only exact file IDs in `DRIVE_ZIP_REVISED_DELETE_CANDIDATES.csv` are candidates. Review/edit that list before any later Drive deletion request. No folder-level deletion, trash-emptying, or implicit cleanup is authorized by this plan.
