# RESEARCH_WORKFLOW_TOOLING_CONSOLIDATION_V1

状态：`TOOLING_CONSOLIDATION_V1_ACCEPTED`
Human gate：`AWAITING_USER_REVIEW`（smoke 结果仍为 `TOOLING_SMOKE_TEST_ONLY`）
范围：只整合研究工具和工作流；没有新建 JoSIM physics run，没有修改历史 raw、网表、报告或 audit。

## WHAT CHANGED

- 建立 [`TOOL_REGISTRY.yaml`](TOOL_REGISTRY.yaml)、[`TOOL_CONSOLIDATION_PLAN.md`](TOOL_CONSOLIDATION_PLAN.md)、[`EXPERIMENT_INDEX.md`](EXPERIMENT_INDEX.md) 和 [`TOOLS.md`](TOOLS.md)。
- 建立 [`scripts/bvmtools/`](../../scripts/bvmtools/) 共享核心：严格 raw reader、provenance、phase/segment、带显式 spec 的 local phase/area、waveform 和 exact-grid compare。
- 增加 [`scripts/bvm-exp.py`](../../scripts/bvm-exp.py) 的显式 Quick 入口、`RESULT_BRIEF.md`、classic compact plot 和 Human Understanding Gate。
- 增加 [`FUTURE_EXPERIMENT_WORKFLOW.md`](FUTURE_EXPERIMENT_WORKFLOW.md)，并更新相关 skills；`research/WORKFLOW.md` 的 `josim-handoff/v1` 内容保持原样。
- 用既有 raw 建立 tooling-only smoke fixture；没有调用 JoSIM 生成新科学数据。

## WHAT IS NOW THE DEFAULT

未来新实验先走 Reuse First：查 registry、`bvmtools`、presets 和 supported scripts，
然后使用显式 `experiment.yaml` 与 1–4 个 case 的 `QUICK`。默认只生成 2–5 条关键
波形的 `CLASSIC_LOCKED` compact visualization，结果交付后停在
`AWAITING_USER_REVIEW`；不会自动 Promotion、扫参或启动下一项物理实验。

## HOW I START A QUICK EXPERIMENT

```bash
python3 scripts/bvm-exp.py quick path/to/experiment.yaml
```

配置必须明确 baseline、candidate、changed variables、held-fixed variables、run
的 timestep/stop、probe preset、metrics、visualization、promotion rule、stop rule
和显式 cases。普通 Quick 只执行登记的 case；路径已存在时拒绝覆盖。主网表必须有
唯一 `.tran timestep stop`，并与配置一致。

## HOW I SEE THE RESULT

先读：

```text
quick/<probe-id>/RESULT_BRIEF.md
quick/<probe-id>/plots/RESULT_OVERVIEW.html
quick/<probe-id>/human-gate.yaml
```

`RESULT_BRIEF.md` 固定回答 changed、held fixed、why、happened、meaning、does not
prove、图的位置和当前状态；机器细节在 `analysis.json`、`manifest.json` 与
`provenance.json`。初始 gate 的 `user_reviewed` 和 `next_step_authorized` 都为
`false`，工具不代填。

## HOW CLASSIC VISUALIZATION WORKS

默认后端是：

```bash
python3 scripts/josim-plot2.py raw.csv \
  -s 'P(BJL2|XBQ)' 'V(BJL2|XBQ)' 'V(OUT)' \
  -t sep_comb -c dark -j 2pi -x plots/RESULT_OVERVIEW.html
```

`-j 2pi` 对 raw phase radians 做真实的 `rad/(2*pi)` 数值归一化；不把 turns 当
SFQ count。V1 compact profile 固定 `sep_comb`/`dark`/`2pi`，只画与当前问题直接
相关的 2–5 条信号。`josim-plot2.py` 的 `grid`、`stacked`、`combined`、`square`、
`sep_comb` 五种布局都有数据级相位归一化回归。重复 exact label 不能由历史 CLI
安全选择 occurrence，Quick 会拒绝对此类 case 生成错误图。

## HOW FULL VISUALIZATION IS REQUESTED

必须在配置中明确 opt-in：

```yaml
visualization:
  mode: full
  style: CLASSIC_LOCKED
```

`full` 只增加已登记的关键信号，仍使用 classic backend。替代视觉风格需要用户
明确授权；V1 不实现第二套 backend。

## WHAT TOOLS ARE NOW AUTHORITATIVE

这里的 authoritative 指“该计算/渲染操作的唯一共享实现”，不等于物理 Gate：

- `bvmtools.raw`：exact header、duplicate occurrence、实际时间轴和 raw QA；
- `bvmtools.provenance`：SHA-256、Git、solver version/hash 和输入快照；
- `bvmtools.phase`：raw radians、unwrap、turns、确定性 monotonic segmentation；
- `bvmtools.sfq`：显式 `StrictLocalEventSpec` 下的 same-JJ phase/area arithmetic 和受保护的 Anchor compatibility label；
- `bvmtools.waveform`：实际时间轴上的 waveform diagnostics；
- `bvmtools.compare`：默认 exact time-grid 的比较；
- `scripts/josim-plot2.py`：classic waveform rendering 和 phase scaling。

strict local classification 必须声明同一 JJ 的 phase/voltage 列、端点、两个 sign、
run/window、raw SHA、METRIC_SPEC version/hash 和 task-local frozen tolerance。缺少
或不匹配时是 `INCONCLUSIVE`。`complete_segment_count`、phase/area compatibility
label 和 waveform activity 都不是 event/SFQ count，也不证明 downstream reception
或 system Gate。

## WHAT REMAINS LEGACY

`scripts/run_exp.sh`、`scripts/sfq_metrics.py`、旧的 `sfq_metrics_v2.py`、
`scripts/josim-plot.py` 以及 experiment-local builder/analyzer/plotter/verifier
均保留原路径，用于历史复现或其登记边界；没有批量迁移、删除或重写历史 raw。
`run_exp.sh` 和旧 v1 指标不能作为当前 physical Gate runner。

## REGRESSION STATUS

- focused suite：`19 passed`，覆盖 raw duplicate/occurrence、时间轴、NaN/Inf、unwrap、turns、segment、实际时间面积、waveform、compare、Anchor A/B 和五种 plot2 layout。
- Anchor A（既有 9 ps / 12×320 replay raw）：`0.8925272335342432` turn、同段面积 `0.8925370087565057 Φ0`，compatibility label 为 `SUBTHRESHOLD`。
- Anchor B（既有 13 ps / 12×320 replay raw）：`1.0160289228944646` turn、同段面积 `1.0160368344325383 Φ0`，compatibility label 为 `CLEAN_ONE_SFQ_CANDIDATE`。
- 两个 Anchor 都通过独立 raw arithmetic、实际 raw SHA 和 METRIC_SPEC SHA 校验；这些是 tooling compatibility regression，不是新的 physics conclusion。
- tooling smoke：输出 [`RESULT_BRIEF.md`](../../test/exploration/tooling-consolidation-smoke-v1-20260901/quick/tooling-consolidation-smoke-v1/RESULT_BRIEF.md)、[`RESULT_OVERVIEW.html`](../../test/exploration/tooling-consolidation-smoke-v1-20260901/quick/tooling-consolidation-smoke-v1/plots/RESULT_OVERVIEW.html)，`visualization: PASS`、`joSIM_run: false`，状态为 `TOOLING_SMOKE_TEST_ONLY` / `AWAITING_USER_REVIEW`。
- 最终 smoke provenance 记录运行前仓库为 clean，HEAD 为 `f6fbfe4`，solver 为 `build/josim-cli` `v2.7.2837d13`，binary SHA-256 为 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`。

## KNOWN LIMITATIONS

- V1 CLI 只实现 `QUICK`；`PROMOTION_PLAN` 和 `FORMAL` 仍由既有严格流程承载，不自动执行。
- JoSIM CLI 没有独立的 timestep/stop 参数；runner 校验主 deck 的 `.tran`，但不替换它，也不自动发现或快照 include/model closure。runner 执行原始 deck，并记录运行前后 deck hash；include closure 仍需实验按严格流程保存。
- `StrictLocalEventSpec` 中的容差是 task-local compatibility profile，不是全局物理容差；BQ/BVM P/V mapping 的 `UNVERIFIED` 状态不会升级成 Gate。
- classic backend 仍不能安全选择重复 exact label 的 occurrence；应使用唯一信号标签或另行完成明确的 preprocessing 设计。
- smoke 只消费已经存在的 9 ps/13 ps raw，验证共享工具链，不产生新 raw、不改变旧结论，也不授权继续 BVM/QB/JSL/L_SL/Lin/JTL/T1 工作。

## IMPLEMENTATION NOTES

本批次使用三层交付：

1. inventory/policy：`c65a183`；
2. shared analysis core：`69c3aee`；
3. Quick/classic gate and workflow sidecar：`5cc40f1`；
4. strict provenance guard follow-up：`f6fbfe4`。

当前报告与 smoke artifact 是本报告对应的最后交付层。完成后保持
`AWAITING_USER_REVIEW`，不自动进入任何下一项物理实验。
