# Chronology observation — JH-20260814-BVM-S0-002 A01

## 1. Predecessor receipt created_at vs mtime mismatch (source UNKNOWN)

Observed on the immutable predecessor
`research/tasks/JH-20260814-BVM-S0-001/attempts/A01/receipt.yaml`:

| attribute | value |
|---|---|
| `created_at` (declared) | `2026-08-14T20:05:00+08:00` |
| filesystem mtime | `2026-08-14 19:54:03.798561357 +0800` |

The declared `created_at` is approximately 11 minutes later than the file's
last-modification time. This task does not have authority to determine which
is the authoritative record. The discrepancy is recorded here as **source
UNKNOWN**: the predecessor's internal timestamp was likely estimated at write
time rather than taken from a clock, and the mismatch is not resolvable
without modifying frozen predecessor metadata, which is prohibited.

No predecessor metadata was altered by this task.

## 2. Host clock used for this task's protocol timestamps

The protocol timestamps in this attempt (`ack.yaml`, `evidence-seal.yaml`,
`receipt.yaml`, this file) use the host system clock output:

```text
$ date -Iseconds
2026-08-14T20:31:46+08:00
```

Recorded on 2026-08-14 20:31:46 +08:00 (host wall clock, CST).

## 3. Corrective practice

For all timestamps written in this and future attempts, the actual host time
is used (`date -Iseconds`), not an estimated/rounded value, so that
`created_at` never precedes or postdates the file's mtime by a material
margin.
