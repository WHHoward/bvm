# M10-004 reseal boundary

This task supersedes M10-003 solely because M10-003 placed four documents that
it authorized to change in its immutable scope-hash manifest. Its A01 output
and its C01 `REWORK_REQUIRED` verdict are preserved as read-only inputs.

M10-004 performs no reconstruction and no physical interpretation. It only
checks the preserved output hashes and the existing deterministic regression
evidence, then creates a fresh ACK/receipt chain whose mutable paths are only
its own attempt directory. The four historical overview documents are frozen
at their already-bannered bytes; no document, JSON, script, test, raw CSV, or
legacy JSON may be edited.
