# TEST_COMMANDS

本轮是 `ANALYSIS_ONLY_NO_NEW_SIMULATION`。所有列出的最终检查均在仓库 `/home/howard/JoSIM` 执行。

| command | exit code | result |
|---|---:|---|
| `python3 -m py_compile analysis/analyze_history.py analysis/independent_check.py analysis/render_plots.py` | 0 | syntax check passed |
| `python3 analysis/analyze_history.py` | 0 | 157 common probes; exact grid; `raw_unchanged=True`; `simulation_invoked=false` |
| `python3 analysis/independent_check.py` | 0 | independent parity/area/crossing assertions passed |
| `python3 analysis/render_plots.py` | 0 | 11 plot pages and `plots/RESULT_OVERVIEW.html` rendered |
| `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test/tools` | 0 | 48 passed |
| inline plot QA: verify 11 outputs, `sep_comb`, `dark`, `-j 2pi`, no `Unknown` axis, and raw hashes | 0 | `plot_qa=PASS` |

未执行：`build/josim-cli`；没有重跑、改写或生成任何物理 raw/deck。

最终输入 raw SHA256：

- OLD `raw.csv`: `9563ac09d75770cd9d9c2f2a93de0f418778012e64adb40fbf118ae0561d813f`
- NEW `raw.csv`: `b3d421822dd893d17331016b7f954784d24c90c97f58bc362676467c7650998b`
