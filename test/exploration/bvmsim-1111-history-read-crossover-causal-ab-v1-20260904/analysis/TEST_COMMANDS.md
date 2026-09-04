# Test and execution record

本文件记录本轮 `1111 HISTORY-READ CROSSOVER CAUSAL A/B` 的命令和退出码。
所有物理运行均在 preregistration 与静态 preflight 提交、且工作树干净后执行。

## Setup and static checks

| command | exit | note |
|---|---:|---|
| `python3 generate_decks.py` | 0 | 生成 O− / N+ 两个冻结 deck |
| `python3 -m py_compile generate_decks.py analysis/static_preflight.py analysis/write_metadata.py analysis/analyze.py analysis/independent_check.py analysis/render_plots.py` | 0 | Python syntax check |
| `python3 analysis/static_preflight.py --check-only --require-clean` | 0 | 在 preregistration commit `1eed8965` 上通过 |
| `python3 analysis/static_preflight.py --check-only --require-clean --write-report` | 0 | 静态报告；随后提交为 `37398670` |

## Authorized physical runs

| command | exit | note |
|---|---:|---|
| `./run.sh` | 0 | 严格执行且只调用两次 recorded `build/josim-cli`；O− 与 N+ 均 exit 0 |

Solver: `build/josim-cli`, version `v2.7.2837d13`, SHA-256
`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`。

## Analysis and independent arithmetic check

| command | exit | result |
|---|---:|---|
| `python3 analysis/analyze.py` | 0 | artifact QA PASS；四条件 crossover analysis complete |
| `python3 analysis/independent_check.py` | 0 | 不读取 metrics/report 的 raw-only arithmetic cross-check PASS |
| `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test/tools/test_bvmtools.py test/tools/test_bvmtools_infrastructure.py test/tools/test_bvmtools_sl_probes.py` | 0 | `35 passed in 0.75s` |

## Visualization

| command | exit | note |
|---|---:|---|
| `python3 analysis/render_plots.py --phase standalone` | 0 | 28 个 standalone HTML；standalone-first |
| `python3 analysis/render_plots.py --phase comparison` | 1 | 首次发现 comparison overview 相对路径工具错误；未触发 JoSIM |
| `python3 analysis/render_plots.py --phase comparison` | 0 | 修复 renderer 路径后 12 个 crossover HTML |

comparison renderer 的一次失败只涉及 HTML 链接路径，随后已修复并重新生成；没有重跑物理仿真、没有改写 raw CSV。

在最终脚本稳定前曾有一次试探性把历史 O+ 缺失的 `R_S/L_S3` 纳入四条件聚合，导致 `KeyError`（exit 1）；已撤回该不完整聚合并重新运行通过。该过程没有修改 raw、deck 或再次调用 JoSIM。

最终 plot 选项固定为 `scripts/josim-plot2.py -t sep_comb -c dark -j 2pi`。
