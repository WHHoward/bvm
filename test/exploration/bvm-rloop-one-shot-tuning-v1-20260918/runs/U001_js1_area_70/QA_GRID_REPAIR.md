# U001 raw-grid QA repair

This is an analysis-tool repair only. No JoSIM solve was rerun.

- Case: `U001_js1_area_70`
- Run: `PASSIVE_N4_1111`
- Solver exit code: `0`
- Raw SHA-256: `dd33a17aec3635651eb691d02408e490bf28870405c2eb17f5e3abc8f4f38604`
- Physical solve count: unchanged at `1`

## Original failure

The first dynamic QA implementation treated `STOP/DT=200p/0.1p` as a hard
requirement for 2000 samples. JoSIM stored 1999 samples on this run, from
`0.0` to `199.9 ps`, so `user_analyze.py` returned `FAIL` even though the
solver completed successfully.

The actual stored grid also contains one irregular step:

```text
14.7 ps -> 14.9 ps = 0.2 ps
```

## Repair

The QA now records nominal grid expectations separately from actual stored-grid
facts. It no longer rejects a valid raw file solely because the sample count is
different from the nominal uniform count. It checks monotonicity, actual range,
finite values, raw hash, sample count, and reports `irregular_step_count` and
`grid_status=IRREGULAR_STORED_GRID`.

Post-repair status: `PASS`; scientific interpretation: `NOT_PERFORMED`.

