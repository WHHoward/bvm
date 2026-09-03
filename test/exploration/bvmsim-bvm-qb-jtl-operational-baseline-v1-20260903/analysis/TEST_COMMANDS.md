# Commands and exit codes

以下命令均从 `/home/howard/JoSIM` 执行：

| command | exit code | meaning |
|---|---:|---|
| `./build/josim-cli --version` | 0 | recorded solver version |
| `python3 inputs/generate_baseline_decks.py --check-only` | 0 | source/template preflight |
| 20 nominal `./build/josim-cli -o <raw> <deck>` runs | 0 each | usable nominal raw; `F4_1011` corrected result is under `attempt-02` |
| first `F4_1011` command with wrong experiment path | 255 | preserved executor path error, not physics evidence |
| `python3 analysis/analyze_baseline.py --check-only` | 0 | all 20 selected raw paths available |
| `python3 analysis/analyze_baseline.py` | 0 | analysis completed; physical result is `BASELINE_FUNCTIONAL_FAIL` |
| `python3 analysis/analyze_baseline.py` (review-fix regeneration) | 0 | regenerated metrics with post-hoc status, crossing markers, single artifact status, and execution bindings |
| `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest test/tools/test_bvmtools.py -q` | 0 | 24 passed, including explicit `POST_HOC_EXPLORATORY` strict-spec readiness |
| `python3 analysis/render_baseline_plots.py --check-only` | 0 | 20 individual + 2 comparison inputs checked |
| `python3 analysis/render_baseline_plots.py` | 0 | 20 individual + 2 comparison HTML plots generated and QA-checked |
| `python3 analysis/write_baseline_report.py` | 0 | report and raw hash index generated |

The independent Sol XHigh review disposition was `REWORK_REQUIRED`; the review
fixes were documentation/provenance/analysis-boundary corrections only and did
not execute another JoSIM run.  The selected execution manifest now binds every
nominal raw to an exit code and solver-log SHA-256; the exceptional missing
command record for `F4_1111` is explicitly supplied by
`analysis/execution_outcomes.json`.

The operational solver was `build/josim-cli`, version `v2.7.2837d13`, SHA-256
`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.  The
analysis/test exit code describes artifact production only; it does not turn a
physical count mismatch into a pass.
