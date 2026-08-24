# Strict replay execution record

- Accepted scientific parent: `8bb86f61c3243655467d61f00680977349b41cf3`
- Working checkpoint before this successor run: `abf14b1`
- JoSIM binary: `build/josim-cli` v`2.7.2837d13`
- Binary SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- Runs: 9 independent fixtures × timestep points
- Commands: `analysis/run_cases.sh`, then `python3 analysis/analyze_strict_freeze.py`
- Exit codes: all 9 JoSIM runs returned `0`
- Physical changes: none; only the registered `.tran` timestep was changed
- Analysis-only views: 3×3 independent pre/post window combinations per raw

The input snapshot and source hashes were recorded in
`inputs/PRE_RUN_SHA256SUMS.txt` before the first JoSIM process. Raw `P(...)`
was consumed directly as radians; the successor analysis did not apply an
additional phase unwrap.
