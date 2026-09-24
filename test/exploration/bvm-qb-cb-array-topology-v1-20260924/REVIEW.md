# Static implementation review

Scope: platform source and render-only fixtures. Review started from
`3874aca666361696b319f682ed09ed195d9d9f30`. No JoSIM/raw/package/mirror action
was performed.

| Hidden-error hypothesis | Probe | Result |
|---|---|---|
| Render-only follows a solver/process branch | Unit test patches `run_case.subprocess.run` to fail and invokes render-only | PASS; returns `josim_invoked: false`. |
| A zero-stage carry is left dangling or represented by an inserted device | T2/T3/zero-terminal renders; inspect actual instance connections and manifest aliases | PASS; direct wires share the mapped merge node; no merge or measurement element is added. |
| Probe labels are invented rather than resolved from included component sources | Parse all four source snapshots and validate each instance, pin count, and internal element during probe generation | PASS for T1–T4 fixtures. |
| MASK affects pre-final stimulus or bit order is reversed | Evaluate generated PWL at WRITE0, READ0, WRITE1, and FINAL READ for 00/01/10/11 | PASS; only FINAL READ changes, leftmost bit maps to BVM1. |
| A dry-run silently creates evidence ZIPs or reaches a solver | Package creation is patched to fail in package preview; submit subprocess/package creation patched to fail in submit preview | PASS; no archive, mirror, commit, or physical process. |
| A dirty-tree package preview truncates the first path character or rewrites checked-in render fixtures | Regression-test the porcelain status parser; render deterministic fixtures only in temporary directories | PASS; dirty paths are preserved and tracked fixtures remain unchanged. |
| Direct documented CLI is broken despite unit imports passing | Ran `python3 scripts/run_case.py --render-only --mask 01` and `inspect_runs.py` from the series directory | PASS after renaming `inspect.py`, which had shadowed Python's stdlib module. |

All three fixture trees are deterministic and marked `RENDER_FIXTURE_ONLY`;
their source snapshots match the canonical component files by SHA-256. There are
zero `raw.csv`, real plot HTML, ZIP, or Axxx run directories.

Residuals: JoSIM parsing/include resolution and the solver's handling of the
repeated `.model jjmit` definitions in the supplied QB/CB/sJTL sources remain
UNKNOWN because this task explicitly forbids a physical solve. Real-raw Plotly
rendering is implemented but not exercised without raw; only its five-page plan
is statically checked.
