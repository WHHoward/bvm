# Luna Experiment Executor Memory

This is a compact executor convention, grounded in the mature series
`test/exploration/bvm-rloop-one-shot-tuning-v1-20260918/` and its historical
runner, submit/package scripts, checkpoints, and commits. It is not a source of
scientific conclusions and does not replace the experiment contract.

## 1. Role

For ordinary JoSIM/BVM execution, Codex/Luna owns:

- implementation and config rendering;
- only the user-requested JoSIM run(s);
- immutable artifact collection and mechanical QA;
- requested visualization;
- submission/package when requested or required by the active experiment contract;
- a concise handoff, then STOP.

The user and ChatGPT own experiment design, physical interpretation, scientific
judgment, and choosing the next experiment. Do not infer permission for those
steps from a successful, failed, unusual, or interesting run. Do not rank
topologies, claim mechanisms, extend a sweep, or start a follow-up run unless
requested.

## 2. Default working style

- Reuse the active experiment platform first. Prefer its `USER_CASE.env`, env,
  or config interface; make the minimum diff and add the fewest files needed.
- Do not redesign a runner or add dashboards, reports, or QA layers without a
  demonstrated need.
- Preserve failed attempts, decks, logs, raw, and provenance. Never overwrite
  raw or silently delete history.
- A valid existing raw plus a parser/plot/report failure calls for a repair
  against that same raw, not another physical solve. In the golden platform,
  `scripts/user_analyze.py --case-root runs/<case>` and
  `scripts/user_plot.py --case-root runs/<case>` are separate post-processing
  entry points. Re-running `./try.sh` is not a repair: it allocates a new U case
  and can launch another solve.
- Separate experiment/evidence commits from workflow/tool fixes. In the golden
  history, experiment commits, package metadata commits, and runner/package
  maintenance commits have distinct messages and scopes.
- One requested task means one bounded delivery. Stop for user review; do not
  automatically choose the next experiment.

## 3. Golden execution reference

The canonical style reference is:

`test/exploration/bvm-rloop-one-shot-tuning-v1-20260918/`

Use its mature manual path before considering a replacement:

```bash
./try.sh --dry-run
./try.sh
```

The env file drives a new case. The runner snapshots effective config and
rendered sources, gives each case/run its own directory, uses `mkdir` with
`exist_ok=False`, and preserves deck, stimulus, raw, stdout/stderr, log,
metadata, provenance, and QA. Existing case IDs are hard stops. Its normal
post-solve analysis and plotters can also be called separately on the same case.
`U190` records artifact validity, raw hashes, source/config snapshots, solver
identity, `scientific_interpretation_performed: false`, and
`automatic_follow_up: false`; this is an execution example, not a physics
reference.

## 4. Submit and package behavior verified in the golden series

Prefer the series-local workflow whenever the active series has
`scripts/submit.py` (usually through `./submit.sh`). Do not replace it with the
generic root submit workflow or copy its special-case behavior into another
series.

Typical commands:

```bash
./submit.sh <tag> --dry-run
./submit.sh <tag>
```

Options actually supported by the series-local submit script:

```bash
./submit.sh <tag> --no-push       # still commits/packages and mirrors; skips git push only
./submit.sh <tag> --package-only  # skips the experiment commit; binds packaging to current HEAD
./submit.sh <tag> --allow-large-delta
```

The submit script always asks `package.py` for a DELTA. Direct package commands
are:

```bash
python3 scripts/package.py --mode delta --tag <tag> --dry-run
python3 scripts/package.py --mode delta --tag <tag>
python3 scripts/package.py --mode full --tag <tag> --dry-run
python3 scripts/package.py --mode full --tag <tag>
```

DELTA is the daily default. FULL is for an explicitly requested checkpoint;
the series submit script does not automatically register a FULL checkpoint.
`--base-commit <sha>` is accepted only for a commit already registered in
`analysis/PACKAGE_CHECKPOINTS.json`. Otherwise the package script uses the last
registered checkpoint whose package exists and matches its recorded SHA, then
requires its commit to exist and be an ancestor of HEAD. Do not guess a base
from timestamps.

Calling `package.py` directly on a dirty tree includes Git-visible worktree
changes while `head_commit` still names committed HEAD. Use the series submit
workflow, which commits experiment evidence first, or commit the exact source
state before direct packaging; do not describe dirty-tree content as fully
bound to the recorded commit.

The verified series-local order is:

1. Complete the requested run(s), mechanical QA, and requested visualization QA.
2. Run `./submit.sh <tag> --dry-run`; inspect scope, evidence, package plan, and
   push target.
3. Submit commits experiment/source changes first. It stages the series but
   resets `handoff/`, so ZIP packages are not committed to Git by this workflow.
4. `package.py` creates the selected archive. DELTA records the checkpoint base
   and the current HEAD. In normal submit, current HEAD is the experiment commit.
5. `package.py` copies the ZIP to `/mnt/d/BVM_Backages`, compares package and
   mirror SHA-256, and writes `analysis/PACKAGE_QA.json`.
6. Submit checks QA status/type/head and package-vs-mirror SHA, appends one
   `PACKAGE_CHECKPOINTS.json` entry, commits package metadata separately, then
   pushes unless `--no-push` was supplied.
7. Report and STOP.

Before a real submit, the script resolves the latest review pointer, requires
batch QA PASS (or a non-INVALID single result), verifies registered legacy raw
hashes, and rejects unrelated edits to source-authority paths. It commits new
series evidence when present; with no new evidence it hard-stops unless this is
an explicit dry-run or `--package-only` request.

`--package-only` does not amend the earlier experiment commit: it uses the HEAD
that exists when invoked. The package `head_commit` must remain the committed
experiment/source identity; the later metadata commit must not be described as
part of the packed experiment. Be deliberate with package-only if HEAD includes
other changes.

### Package closure and historical limits

- FULL walks the series tree. DELTA uses `git diff <base>..<head>` plus
  Git-visible worktree changes. Both exclude `__pycache__`, `*.pyc`,
  `analysis/PACKAGE_QA.json`, and ZIPs directly inside `handoff/`.
- Include the actual deck, stimulus/config snapshots, source manifests,
  raw CSV, stdout/stderr/logs, provenance, mechanical analysis, requested plots,
  per-run QA, and concise review/result files when they are in the selected
  closure. Check the dry-run manifest: ignored files are not automatically
  present in DELTA just because they exist locally.
- A DELTA packages changed/new files, not all old raw again. Reused cases are
  represented by `referenced_existing_cases` with source case/path/raw SHA when
  their batch manifest is included. The ZIP itself is not recursively included.
- DELTA manifest includes base package name/SHA, base/head commits, file list
  and SHA map, new/modified lists, reused references, solve count, and reused
  point count. `PACKAGE_CHECKPOINTS.json` is append-only; conflicting package
  identities hard-stop. `PACKAGE_QA.json` is a latest-result file, not an
  append-only history.
- The recorded FULL v7 checkpoint is bound to the B003 experiment commit and
  predates its package-only metadata commit. This is the concrete historical
  pattern: metadata commits follow packaging but do not become the package's
  experiment `head_commit`.
- Existing ZIP names are immutable. `package.py` refuses an existing local
  target and refuses any existing same-name mirror rather than overwriting it.
  If a target exists, inspect its hash and stop; do not silently replace it.
- Historical `PACKAGE_QA.status=PASS` means the ZIP SHA matched the copied
  mirror SHA. The script records source-file hashes in QA and DELTA manifest,
  but does not reopen the ZIP to run CRC or compare each archive member to those
  hashes. Do not claim CRC/member-hash validation from this status alone. If a
  task requires that stronger check, perform an explicit read-only archive
  integrity audit or report the script gap.
- Actual order differs slightly from an ideal “QA then mirror” sequence:
  `package.py` writes the ZIP, copies it to the mirror, compares the two SHA
  values, then writes PACKAGE_QA; submit verifies that QA before checkpoint
  registration. Report the observed order accurately.

## 5. Final response

Keep the normal executor summary short: requested work/run count; mechanical and
visual QA; experiment/source commit; package metadata commit; package type/name
and SHA; mirror and push status; blocker/anomaly; “scientific interpretation:
not performed”; STOP. Do not add a scientific discussion or next-step proposal.
