# V9 main-platform static QA

Status: PLATFORM_STATIC_QA_PASS / DRIVEFS_ARCHIVE_ACCEPTANCE_BLOCKED / JO-SIM_PARSE_ONLY_UNAVAILABLE

Date: 2026-10-16

## Revision and scope

- Starting HEAD: 8baf65df95186125a069a26522dfff92b0a8d1c1
- Remote bvm/master at inspection: 8baf65df95186125a069a26522dfff92b0a8d1c1
- Starting worktree: clean
- No JoSIM solve was run; physical_solve_count=0.
- All changes are confined to test/exploration/sfq_clock_two_read_v1/.
- final_runs/ and the old bvm-4x4-diagonal-array-v1-20261009 platform were not modified.

## Circuit source and topology identity

The new template was derived from the V9 actual deck, not the historical V10
deck.template.cir:

- V9 actual deck SHA-256:
  474a254f4511fb46bea6afd36500aa28111323f23f1be66b720170ee297ccb70
- New template SHA-256:
  2ea1cee249ad8939003b1108fda41a65dda81e12afd43d53fefaecb4c529392b
- Allowed deck differences are only the old .print set replaced by eight
  OUTPUTS probes and the .tran values replaced by DT_PS/STOP_PS placeholders.
- Normalized circuit-body comparison against V9 actual deck: PASS.
- The 11 frozen source files in the new template are byte-identical to the
  corresponding V9 and V10 source snapshots. Their SHA-256 values are in
  template/source_manifest.json.
- The exact frozen jtl2 snapshot carries trailing padding whitespace from V9;
  it was retained byte-for-byte for SHA identity. diff --check is clean for
  platform code/docs/tests and excludes only the immutable source snapshot.
- BVM source includes active B_SE and R_BSE; SHA-256:
  76b7b90b4e58cc45d55adc24d1bc6e626957461a2abe21ca4a33319d58ac6489.
- Static topology checks: 16 BVM, 16 QB, four row WL, four column BL, four
  shared row-SE sources, seven T1, six carry CB, the registered carry sJTL
  counts including two at D4, eight DCSFQ2, eight clock-input JTL2, fourteen
  Sum-output JTL2, one D0 entrance JTL, and one DFF.
- The 16 BVM instances use SE_R1…SE_R4 by row and BL_C1…BL_C4 by column.
- The repository-wide *.json ignore rule was checked: the two platform JSON
  source/index files are explicitly included, and runs/.gitignore re-includes
  future per-run JSON manifests; raw.csv is not ignored.

The V10 template SHA-256 is
a4793b4caf077daef44eefdac628dd35f054b89f5ad4724934b1edc0763a11c1. Compared
with the V9 actual deck, its BVM inputs use per-cell SE_RxCy nodes and its D4
carry has one rather than two sJTL stages. Its 11 frozen source files match
V9, but its template is not electrically equivalent; it is not used as the
new platform's topology authority.

## Configuration, stimulus, and probes

The current USER_CASE.env dry-run rendered:

- Protocol V9_SHARED_ROW_SE_BL; A=15, B=15; ROUNDS=3.
- READ PWL starts: 110, 190, 270 ps.
- CLK PWL starts: 178, 258, 338 ps.
- DT=0.01 ps; STOP=400 ps.
- WL/BL write=400u; BL read=400u; SE read=375u. The 375u value is labelled
  a user candidate, not a validated optimum.
- Exactly 20 sources: 4 WL + 4 BL + 4 shared-row SE + 8 CLK.
- OUTPUTS has exactly eight .print probes, in the requested D0…D6, DFF order.
- Default rendered deck SHA-256: 3bca7a96fd92f9d50a6d5fbe4fa68047df64b9a3d7ccfa4a8a2345ec958a3b80.
- Default generated stimulus SHA-256: 29defff22ad7f8de68948deff6ecef4a8f3e7b2f077fe9265a7d4f40bc726f0e.
- 1×1 render test: ROW_BITS=1000, COL_BITS=0001.
- 11×13 render test: ROW_BITS=1101, COL_BITS=1101.
- SE amplitude override test: changing 375u to 360u changes generated PWL.
- CUSTOM test: exactly two explicit probes add to the default eight; unknown
  nodes/elements are rejected before a solve.
- CUSTOM probes are checked against the documented expression forms, resolved
  top-level nodes/elements, and frozen subcircuit element names before a solve.
  Actual JoSIM parser acceptance was not executed: the repository's josim.cpp
  always constructs Simulation after parsing, and the CLI -s sanity-check
  switch does not skip the transient simulation. No JoSIM executable was run.
- The shared scripts/bvm_stimulus.py V9 generator is used. Its arithmetic
  product comment is omitted from the new stimulus; no arithmetic verdict is
  calculated.

## Tests and rendering

- Shell syntax: bash -n try.sh — PASS.
- Python syntax: py_compile platform.py and test_platform.py — PASS.
- Unit tests: 17 passed.
- try.sh --dry-run — PASS; solver_invoked=false; no run directory was created.
- Rendered 1×1 and 11×13 config/PWL cases in unit tests — PASS.
- Synthetic CSV plot test through scripts/josim-plot2.py — PASS. The test
  decodes the plotted typed-array data and confirms a one-sample synthetic
  pulse remains present; the HTML is standalone with inline Plotly JS.
- Synthetic archive test in a temporary directory — CRC and every member SHA
  PASS; immutable-name collision is refused. Temporary test ZIP was removed
  with the temporary directory. No persistent ZIP was created locally.
- Fail-closed test with an unavailable Drive target — JoSIM subprocess not
  invoked and no run ID reserved.

## DriveFS acceptance blocker

The required target is:

/mnt/g/.shortcut-targets-by-id/1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh/BVM_Backages

The exact path check returned “No such file or directory”; the writable check
failed. rclone was not available. No alternate path was guessed, no ZIP was
written to Drive or D:, and no remote file ID or cloud sync receipt was claimed.

The runner is fail-closed: a real ./try.sh invocation first performs an
exclusive write/read/unlink test at that exact target. If unavailable, it
returns before reserving a run ID or invoking JoSIM. When available, it writes
one self-contained ZIP directly there, validates CRC/member hashes and the
final path SHA, and records the folder ID, path, file name, and ZIP SHA. The
shell cannot independently prove asynchronous cloud sync or obtain a Drive
file ID from this environment; the manifest deliberately marks that remote
verification as unconfirmed rather than claiming success.

Therefore this is a completed static platform implementation, but real
DriveFS write/sync acceptance remains BLOCKED until the specified path is
available and can be verified. No experiment is authorized or run by this QA.
