# JoSIM/BVM 工具指南

这份指南面向研究者本人。工具的“计算权威”不等于物理结论权威；raw、网表、
实验报告和已接受审计仍是科学证据来源。

## 如何运行 JoSIM

新实验使用仓库内绑定的 solver，并保存版本/hash：

```bash
build/josim-cli --version
build/josim-cli -a 1 -o path/to/unique/run.csv path/to/run.cir
```

输出目录必须唯一、不可覆盖；保存 netlist、include/model 快照、stdout/stderr、
raw CSV 和 provenance。历史 `scripts/run_exp.sh` 只用于明确标注的历史复现，
不能作为当前物理 Gate runner。

## 如何开始 Compact Quick

新实验先查看 TOOL_REGISTRY.yaml、scripts/bvmtools/、presets 和 supported
scripts，然后从 scripts/templates/compact-quick/ 创建 experiment.yaml 和薄
run.sh：

```bash
./run.sh
./run.sh analyze A001
./run.sh analyze A001 --scientific-review-authorized
./run.sh plot A001
./run.sh package A001
./run.sh inspect A001
```

run 调用 scripts/bvm-exp.py 并创建不可覆盖的 runs/Axxx attempt；每个 attempt
保存 deck.cir、raw.csv、run.log、metadata.json 和 result.yaml。默认 run 只做
mechanical QA，使用 scripts/josim-plot2.py 生成标准描述性可视化，生成
`handoff/<experiment_id>_raw_handoff.zip` 与 detached `PACKAGE_QA.json`，并在
仓库内默认提交 Git，完成后状态为
`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`。analyze 默认只消费已有
raw 做 QA；只有显式 `--scientific-review-authorized` 才生成独立 scientific
review artifact。package 只打包现有证据，不运行 solver。

旧的 python3 scripts/bvm-exp.py quick path/to/experiment.yaml 入口保留给已经
创建的 V1 fixture，不作为新实验默认接口。

## 如何检查 JoSIM raw

```bash
PYTHONPATH=scripts python3 - <<'PY'
from bvmtools.raw import read_csv

trace = read_csv("path/to/run.csv")
print(trace.qa())
print(trace.column("P(BJL2|XBQ)"))
# 重复列必须显式选择：
print(trace.column("I(B_LD1)", occurrence=0))
print(trace.column("I(B_LD1)", all_matches=True))
PY
```

reader 保留 quoted header 的 exact label、duplicate occurrence、sample count、
实际 nonuniform time grid，并拒绝 non-increasing time、NaN 和 Inf。

## 如何计算 strict BJL2 local event

`scripts/bvmtools/sfq.py` 是未来共享实现。严格分类不能依赖隐含全局阈值，必须从
case 的 hash-bound `strict_event.spec` 构造完整 `StrictLocalEventSpec`；缺少 spec
时仍可得到 raw arithmetic，但 classification 必须是 `INCONCLUSIVE`：

```python
from bvmtools.sfq import StrictLocalEventSpec, strict_event_summary

spec = StrictLocalEventSpec.from_mapping(case["strict_event"]["spec"])

summary = strict_event_summary(
    trace.time,
    trace.column("P(BJL2|XBQ)"),
    trace.column("V(BJL2|XBQ)"),
    activity_window_s=(94e-12, 130e-12),
    post_window_s=(140e-12, 170e-12),
    post_tail_window_s=(165e-12, 170e-12),
    spec=spec,
    actual_raw_sha256=raw_sha256,
    actual_metric_spec_sha256=metric_spec_sha256,
)
```

它只给同一 JJ 的 local phase/area evidence。`WINDOW_PHASE_DISPLACEMENT` 不等于
`EVENT_COUNT`；`complete_segment_count` 和 compatibility label 也不等于 event/SFQ
count。局部一圈不等于 downstream SFQ、闭环 fluxoid 或 system Gate。

## phase turn 是什么

JoSIM `P(...)` 是 raw phase radians。先保留：

```text
phase_delta_rad = phase_last - phase_first
phase_delta_turns = phase_delta_rad / (2*pi)
```

连续轨迹需要 deterministic unwrap；不能把绝对 `P=2π`、peak、p2p 或导数样本
直接叫 SFQ count。相位和电压面积的交叉校验必须是同一 JJ、同一端点/方向、同一
时间窗、同一次运行。

## 哪个工具是 authoritative

- raw 解析：`bvmtools.raw`；
- phase/segment：`bvmtools.phase`；
- local strict event：`bvmtools.sfq`；
- waveform diagnostics：`bvmtools.waveform`；
- exact-grid compare：`bvmtools.compare`；
- classic waveform backend：`scripts/josim-plot2.py`；
- evidence-first package/ZIP QA：`scripts/build_experiment_package.py`；
- Authority/FROZEN handoff：`.agents/skills/josim-handoff/scripts/handoff.py`。

“authoritative for calculation”不表示这些工具自己给出物理 Gate；Gate 仍由
`josim-evidence-audit`、原始证据和对应合同裁决。

## 默认 classic compact 图

直接使用：

```bash
python3 scripts/josim-plot2.py path/to/run.csv \
  -s 'P(BJL2|XBQ)' 'V(BJL2|XBQ)' 'V(OUT)' \
  -t sep_comb -c dark -j 2pi -x plots/RESULT_OVERVIEW.html
```

只选最少的关键波形；`-j 2pi` 的数值是 `rad/(2*pi)` turns，不是 SFQ 数。未来
Quick 默认就是这一 classic profile，compact 只减少信号数量。
未来 BVM→QB→JTL 标准 evidence 还必须保存 visualization manifest、visualization
QA 和 per-run navigation；HTML/PNG 可按体积不放入 ZIP。V2.1 语义结构为
`01_SIGNAL_TIMING`、`02_BVM_STATE`、`03_JSL_CHAIN`、`04_QB_STATE`、
`05_JTL_CHAIN`，每层均为 `INPUT -> INTERNAL -> OUTPUT` 加 whole-run overview
和 focused windows。任何 phase display 仍是 `rad/(2*pi)`，不是 SFQ count。

## 如何请求 full visualization

在配置中明确：

```yaml
visualization:
  mode: full
  style: CLASSIC_LOCKED
```

full 可以加入 BVM core、JSL、QB internal、branch current、control 等更多已
注册信号，但仍使用 `josim-plot2.py` classic style。没有明确 opt-in 时保持
compact。

## 如何请求 alternative visual style

只有用户明确授权“自由发挥/其他方案/论文风格图/不要经典方案”等等价语句后，
才可以另立可视化设计任务。V1 CLI 不实现 alternative backend；没有这项授权时
拒绝非 `CLASSIC_LOCKED` 配置。

## legacy 工具

- `scripts/sfq_metrics.py`：SUPERSEDED，不能使用旧事件字段作当前 Gate；
- `scripts/run_exp.sh`：LEGACY，会调用旧指标且可能覆盖固定输出；
- `scripts/sfq_metrics_v2.py`：M4–M9 历史/校准实现，保留可复现，不是未来 strict
  primitive 的唯一入口；
- `scripts/josim-plot.py`：历史绘图复现；默认 classic backend 收敛到 `plot2`。

完整路径、重叠和替代关系见 [`TOOL_REGISTRY.yaml`](TOOL_REGISTRY.yaml)。

## 如何添加 diagnostic：Rule of Two

第一次新 diagnostic 可以在单个实验中标记 `EXPERIMENTAL_LOCAL`。当第二个实验
需要同样功能时停止复制：先比较 registry/现有工具，提升到 `scripts/bvmtools/`，
补 focused tests，登记 authoritative boundary，然后再使用。

## Quick 与 Formal

Evidence-first Quick 默认只提供 raw/mechanical QA、标准描述性可视化和科学审阅
所需的 immutable package；`RESULT_BRIEF.md` 不给出 mechanism、root cause、
winner 或下一实验建议。只有用户明确给出
`SCIENTIFIC_REVIEW_AUTHORIZED`，才另行生成 scientific-review artifact；新的
physical solve 仍须独立注册和授权。

## Human Understanding Gate

每个标准结果优先交付：experiment identity、exact run matrix、mechanical QA、
raw/plot/package links、UNKNOWN 和当前状态。Evidence-first V2 将这些内容放入
`RESULT_BRIEF.md`、`EVIDENCE_MANIFEST.md`、`result.yaml` 和
`human-gate.yaml`；默认 scientific interpretation 为 `NOT PERFORMED`，状态为
`AWAITING_SCIENTIFIC_REVIEW`。只有明确授权后才可进入 review；agent 不得自填
REVIEWED 或自动执行下一项。
