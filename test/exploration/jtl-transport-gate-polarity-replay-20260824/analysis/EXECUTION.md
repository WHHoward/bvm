# Execution record

- start time: `2026-08-24T09:34:39+08:00` (Asia/Shanghai)
- parent HEAD: `090b8268132b9d5d4ae2e81a0131cafc458c24c1`
- JoSIM: `v2.7.2837d13` (compiled 2026-05-30)
- JoSIM binary SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- `JTL.cir` SHA-256: `ac02fc931742bb857723f9fbb57ac97a179beb6a6466d5a1184e7cf937f599aa`
- `jjmit.cir` SHA-256: `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`
- timestep / stop: `0.0125 ps / 300 ps`
- new raw rows: `23999` per replay (CSV header not counted)
- new replay exit codes: original `0`, reverse `0`
- new replay stderr: empty for both jobs

Commands:

```text
python3 analysis/build_replay.py
analysis/run_case.sh original
analysis/run_case.sh reverse
python3 analysis/analyze_reconciliation.py
```

The two JoSIM jobs used independent input/raw/log directories. The existing
R11, M1 and M5-PC CSVs were read-only inputs to the reconciliation analysis;
they were not regenerated.
