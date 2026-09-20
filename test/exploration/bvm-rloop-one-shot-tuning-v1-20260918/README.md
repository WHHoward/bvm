# BVM R-loop one-shot readout tuning v1

## Daily user workflow

1. Edit [`USER_CASE.env`](USER_CASE.env).
2. Preview: `./try.sh --dry-run`.
3. Run: `./try.sh`.
4. Open [`LATEST_REVIEW.html`](LATEST_REVIEW.html).

`MASKS=quick` means N1/N2/N3; `MASKS=full` means N0/N1/N2/N3/N4. An explicit
mask such as `MASKS=0111` or list such as `MASKS=0001,0111` is also supported.

For the optional one-dimensional sweep, set `SWEEP_ENABLED=yes`, choose one
`SWEEP_KEY`, and provide comma-separated `SWEEP_VALUES`. `./try.sh --dry-run`
must be inspected before `./try.sh`; existing points are reused only after
deck/config/stimulus/source/raw-QA/hash verification. Sweep output is stored
under `batches/` and does not change the meaning of `LATEST_REVIEW.html`.

Evidence packaging defaults to DELTA mode:

```bash
python3 scripts/package.py --mode delta --tag B004
```

Use FULL only for an explicit checkpoint:

```bash
python3 scripts/package.py --mode full --tag checkpoint_name
```

Delta base selection is checkpoint-manifest based and hard-stops when the base
package identity cannot be verified. Use `--dry-run` before creating an archive.

The old `run.sh`/`analyze.sh`/`plot.sh` path remains as the preserved Stage-A
backend interface. It is not required for the normal manual workflow. This
platform refactor itself performs no physical solve and creates no U case.

This is an independent, exploratory, manually operated platform. It does not
modify canonical BVM/QB sources or historical raw artifacts.

The registered Stage A physical matrix is:

| Case | JS1 shunt | JS2 shunt | Mode | Masks |
|---|---:|---:|---|---|
| `A000_CANONICAL` | OPEN | OPEN | PASSIVE | `0000,0001,0011,0111,1111` |
| `A001` | 20 ohm | 20 ohm | PASSIVE | `0000,0001,0011,0111,1111` |
| `A002` | 12 ohm | 12 ohm | PASSIVE | `0000,0001,0011,0111,1111` |
| `A003` | 8 ohm | 8 ohm | PASSIVE | `0000,0001,0011,0111,1111` |

Total: exactly 20 PASSIVE solves. The runner also supports future manually
authorized `closed` or subset-mask cases, but does not provide a sweep command.

Edit `config/current_candidate.env`, then run for example:

```bash
./run.sh --dry-run
./run.sh --case A001 --mode passive
./run.sh --case A004 --mode closed --masks 0001,0011,0111
```

An existing `runs/<CASE_ID>/` is a hard stop. The runner never overwrites a
case, deck, raw CSV, log, or summary.

`analyze.sh` and `plot.sh` operate only on completed case directories. The
visual output is a compact `review.html` plus a few grouped JoSIM plots; no
exhaustive all-signal atlas is generated.

Scientific interpretation is not performed by this platform. Gate-S is left
`REVIEW_REQUIRED` unless a later authorized scientific review changes that
status. Gate-R labels are descriptive navigation labels only, not SFQ counts or
a formal classifier.
