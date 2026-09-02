# 执行命令与退出码

记录时间：`2026-09-02T19:59:14+08:00`

本文件只记录本 Quick 的执行审计；raw、失败日志和历史文件均未被覆盖。

## 物理运行

| run | command | exit code | raw |
|---|---|---:|---|
| T100 attempt-01 | `./build/josim-cli -o test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/runs/T100/raw.csv test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/runs/T100/deck.cir` | 255 | 未生成；include 路径打包错误，见 `runs/T100/FAILED_ATTEMPT_01.md` |
| T100 attempt-02 | `./build/josim-cli -o test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/runs/T100/attempt-02/raw.csv test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/migrated/T100.cir` | 0 | `runs/T100/attempt-02/raw.csv` |
| T050 attempt-01 | `./build/josim-cli -o test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/runs/T050/attempt-01/raw.csv test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/migrated/T050.cir` | 0 | `runs/T050/attempt-01/raw.csv` |
| T025 attempt-01 | `./build/josim-cli -o test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/runs/T025/attempt-01/raw.csv test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/migrated/T025.cir` | 0 | `runs/T025/attempt-01/raw.csv` |
| T0125 attempt-01 | `./build/josim-cli -o test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/runs/T0125/attempt-01/raw.csv test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/migrated/T0125.cir` | 0 | `runs/T0125/attempt-01/raw.csv` |
| T100_FULL attempt-01 | `./build/josim-cli -o test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/runs/T100_FULL/attempt-01/raw.csv test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/migrated/T100_FULL.cir` | 0 | `runs/T100_FULL/attempt-01/raw.csv` |

## 分析与测试

| command | exit code | purpose |
|---|---:|---|
| `python3 test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/analysis/analyze_convergence.py` | 0 | 生成 strict metrics、provenance 和结果摘要 |
| `python3 test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/analysis/independent_recheck.py`（第一次） | 1 | 复核器边界错误：把 T100 不存在的第五事件误视为异常；无 raw 改动 |
| `python3 test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/analysis/independent_recheck.py`（修正后） | 0 | 独立 unwrap、同段端点和梯形积分复核 |
| `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test/tools/test_bvmtools.py test/tools/test_strict_event_list.py` | 0 | bvmtools 套件、冻结 strict anchor、新增多事件 helper 及 provenance 边界；29 passed |
| `python3 test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/analysis/render_plots.py` | 0 | 生成 3 个 plot2 classic HTML；每个 plot2 子命令 exit code=0 |

分析器在审阅前做过一次不改变 raw 的报告修正：将每个 association window 的最大 segment 和 continuous 标志改为只统计该窗口内起始的 segment，避免完整 0–200 ps 扫描状态泄漏到 READ0 等窗口。修正后再次运行 `analyze_convergence.py` 和 `independent_recheck.py`，退出码分别为 `0`、`0`。

## 约束核对

- 只运行 4-BVM → BVMSim QB → 六级 JTL 原 fixture 的 timestep / print-start Quick。
- 没有 canonical BVM、single-BVM、参数 sweep、QB bias sweep、JSL/T1、拓扑改造或后续实验。
- `BVMSim/data_tran.csv` 只读；重复 `V(O2)` 由 occurrence 0/1 显式选择。
