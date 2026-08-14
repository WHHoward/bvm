# REJECTED_HISTORICAL_REFERENCE — JH-20260809-M4-001 / A01

This directory preserves a bounded copy of the original A01 execution evidence
from the retired `claude/JH-20260809-M4-001` worktree.  It is retained solely
for lineage and auditability.

## Status and use

- **Status:** `REJECTED_HISTORICAL_REFERENCE`
- **Not acceptance evidence:** Do not use these files to satisfy M4, to update
  project status, or to support a physical claim.
- **Reason:** the original M4-001 attempt was rejected.  Its later replacement,
  M4-003, is the accepted M4 evidence.  The authoritative rejection record is
  [`standin/S01/review.yaml`](../../standin/S01/review.yaml) in the parent task.
- **Deliberately omitted:** old workflow, HANDOVER, todo/history, and stand-in
  implementation files from the retired worktree.  Those files were superseded
  and must not be reintroduced through this archive.

## Preserved scope

The copy contains only the candidate implementation and test named by the old
receipt, its ACK/receipt, and the three claimed logs.  Every preserved file is
byte-bound by the SHA-256 manifest below.  The paths are historical archive
paths; they are not live implementation paths.

| Archive path | SHA-256 |
| --- | --- |
| `candidate/sfq_metrics_v2.py` | `acb2f44850d3d24745c3b915dcfed21c0fb1428ca9948e6bbd261302031ad862` |
| `candidate/test_sfq_metrics_v2.py` | `044d30c4914b1d8b7414a971446702efc8965a4ea3d2030f523e12d28042a13c` |
| `protocol/ack.yaml` | `daef483de7f2abaa798a8f1ea5ee7d6f93c8bb2d412a3630c187b2a68fab537b` |
| `protocol/receipt.yaml` | `fb8775b97cf7ccad115ae50a6bd0aa3f1c1ec5e9753c41c136bfa4879b5f179c` |
| `logs/help.txt` | `7da826bd3cb6b052e46cc60f3bc848a610c6c4eded07e437a583e1311c8af00f` |
| `logs/smoke.json` | `6d1c13096b4c9c8308863c107c84de486f93ba906ba0dfd2d22b2fcf32c5e6b6` |
| `logs/unit-tests.log` | `a5844541e773982576e69f5ea0a00c8d5a390984cd0aef16d6212f40ead9634f` |

The source worktree was `/home/howard/JoSIM-m4`, branch
`claude/JH-20260809-M4-001`, at commit
`384d75337e23d08516a66f71bb93d87c3f633013` before removal.  The branch pointer
is intentionally left untouched by this archival cleanup.
