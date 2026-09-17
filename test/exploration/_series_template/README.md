# JoSIM experiment-series template

This is a lightweight reference scaffold for Codex when creating a new
experiment series. It is not a universal manager and it contains no canonical
scientific circuit values.

Before a physical run, replace the clearly marked placeholders with the real
series fixture. The template runner refuses unresolved placeholders, so a
copy cannot accidentally be mistaken for a scientific result.

Typical user workflow:

```bash
./run.sh --dry-run
./run.sh
./analyze.sh A001
./plot.sh A001 --list-signals
./plot.sh A001
```

After changing `run.sh`, a local circuit, or `stimuli/manual.inc`, run the
same command again. The runner creates `A002`, `A003`, ... and never overwrites
an earlier attempt.

Generated stimulus parameters live in the `STIMULUS` section of `run.sh`.
Manual stimulus edits are made directly in `stimuli/manual.inc`; select one
mode explicitly and do not mix modes silently.

Use `plot.sh --group GROUP` for a standard group or `plot.sh --signals ...`
for a non-destructive ad hoc plot. Missing signals fail loudly and point to
`--list-signals`.

The series-specific `PREFLIGHT.md` must be rewritten by Codex with the actual
question, parent, topology, parameters, source closure, windows, and scope.
