# Codex Final Audit — M5-LITE-PILOT-001 / A01

Disposition: **REWORK_REQUIRED**  
Date: 2026-08-11  
Reviewed delivery snapshot: `5489338`  
Reviewer record: `a69b889` (`attempts/A01/REVIEW.md`)

## Independent disposition

- Artifact status: **VALID** for the bounded implementation artifacts and raw-CSV arithmetic replay.
- Physical verdict: **NOT_APPLICABLE**. This is an implementation task and establishes no SFQ, downstream, fluxoid, circuit-Gate, or paper claim.
- Audit disposition: **REWORK_REQUIRED**. A required M5 window semantic is not implemented, so A01 cannot satisfy all acceptance criteria.

I independently inspected `windowed_analyze` and reproduced the issue with a
synthetic CSV: an activity window containing zero samples returned an empty
activity structure instead of being rejected. The implementation calls
`_window_stats` for `pre` and `post` only; it does not emit the required
mean/count/bounds/min/max/peak-to-peak statistics for `activity`.

This confirms the Copilot Major finding against TASK fixed semantics and AC2.
The finding does not invalidate the separately checked AC6 arithmetic replay;
it does prevent task acceptance.

## A02 authorization and required repair

Create `attempts/A02/RESULT.md`; do not edit A01 files. The A02 execution
baseline is the Git commit that first contains this audit file (resolve it
before Preflight). It intentionally differs from the immutable TASK revision
`6498d36` because it adds only the A01 review/audit records needed to begin
the rework; record that rationale in A02 Preflight.

Within the existing TASK allowed paths only:

1. Emit full, unrounded window-statistics blocks for **pre, activity, and
   post**, for both signal and matched control namespaces. Keep activity
   clustering separate from activity-window statistics so clusters retain no
   event semantics.
2. Reject an activity window with fewer than two finite samples, just as for
   pre/post; cover zero and one sample cases in independent tests.
3. Add assertions that the frozen replay selects activity sample count 409
   and exposes the required activity statistics; preserve every existing M4
   and M5 passing behavior.
4. In A02 documentation, correct the non-material A01 precision notes: the
   bump-netlist parameter is line 6, and each CSV has 1999 data rows plus one
   header row. Do not rewrite A01 history.

After A02 delivery, Codex will create a new delivery snapshot and request a
fresh Copilot review. No todo/HANDOVER update is authorized now.
