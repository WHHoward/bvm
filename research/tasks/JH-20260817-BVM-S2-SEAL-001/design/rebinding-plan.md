# BVM-S2 evidence rebinding plan

This is a protocol recovery task, not a new scientific experiment. It binds the
already-created `bvm-s2-load-20260817-01` package to a new, correctly captured
baseline after `JH-20260817-BVM-S2-001/A01` could not pass mechanical
verification: its immutable request records `baseline.git_head=96599fc`, while
the truthful ACK records `b3a467d`.

The successor must not edit, move, rename, delete, rerun, regenerate, or
reinterpret any original S2 file. It must recursively enumerate every regular
file under the original run root and bind each path and SHA-256 in a new
evidence inventory. It also binds the original request, request hash, ACK and
receipt as **historical execution/provenance records**; the original receipt is
not final authority because its baseline assertion cannot pass `verify-task`.

The only permitted new files are this successor's attempt-owned inventory,
read-only verifier, logs and receipt. No JoSIM command is authorized. The
successor may establish only evidence-integrity/provenance status. It does not
accept the original raw artifact, numerical status, readiness outcome,
terminal-affine observation or any physical interpretation; those await one
Copilot skeptical review and one Codex scientific audit of the sealed package.
