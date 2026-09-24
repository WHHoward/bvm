---
name: josim-submit
description: Submit and package an already-completed JoSIM/BVM experiment using the repository's established commit, delta/full package, mirror, checkpoint, and push conventions. Do not run new physics or interpret scientific results.
---

# Submit completed JoSIM/BVM evidence

Use only when the user asks to commit, package, mirror, or push an already
completed experiment, or when the active experiment contract explicitly
requires that delivery. This skill does not run simulations, sweep parameters,
design experiments, visualize/reinterpret results, or choose follow-up work.

Before acting, read `memory/LUNA_EXECUTOR_MEMORY.md` and the active series'
README and local submit/package scripts. Inspect `git status`, HEAD/upstream, the
series scope, current QA, tag collisions, and the exact package/mirror targets.
Preserve unrelated changes; do not stage outside the requested series.

Prefer an existing series-local `scripts/submit.py` or `submit.sh` and follow
its established behavior. Do not bypass it with hand-written `git add`, ZIP,
checkpoint, or mirror logic. Use root `scripts/submit.py` only when the active
series has no local workflow; its generic special cases are not a universal
experiment convention.

Run the workflow's dry-run first and inspect its proposed files, package base,
head, package name, and push target. Submit/package must never call JoSIM or
trigger a follow-up solve. If the established workflow's QA fails, a base/hash
is ambiguous, a destination name collides, or unrelated source-authority
changes block submission, stop and report the exact blocker.

Keep experiment/source identity separate from package metadata identity. Bind a
package to the committed experiment HEAD specified by the local workflow; a
later checkpoint/QA metadata commit does not change that identity. Preserve old
packages, and refuse to overwrite same-name packages or mirrors. Verify mirror
bytes with SHA-256 where the workflow supports it, and describe exactly what
the workflow's QA did and did not verify. In particular, do not claim archive
CRC/member-hash QA merely because a detached package QA says `PASS`.

When complete, provide a concise executor summary (commits, package name/SHA,
mirror and push, QA, blockers) with scientific interpretation marked not
performed, then STOP.
