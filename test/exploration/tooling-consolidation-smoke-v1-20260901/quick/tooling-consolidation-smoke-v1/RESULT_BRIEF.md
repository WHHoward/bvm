# Result

## 1. What we changed

Tooling action performed in this smoke:

- no circuit change
- no parameter change
- no JoSIM rerun
- only reprocessed existing historical raw through the new shared tooling path

Historical scientific comparison represented by those reused raw files:

- READ width: 9 ps → 13 ps
- all other registered scientific conditions remain existing historical fixture conditions

## 2. What was held fixed

- existing 9 ps and 13 ps raw CSV bytes
- BVM/JSL/QB topology and all scientific parameters
- strict-event windows and residual semantics
- classic sep_comb/dark/rad/(2*pi) rendering profile

## 3. Why we tested it

Existing raw evidence should reproduce the frozen 9 ps and 13 ps BJL2 anchor values without running JoSIM or changing scientific evidence.

## 4. What happened

- 9ps-12x320-replay：最大同段相位 0.892527233534 turn，同段电压面积 0.892537008757 Φ0，兼容性分类 `SUBTHRESHOLD`。
- 13ps-12x320-replay：最大同段相位 1.016028922894 turn，同段电压面积 1.016036834433 Φ0，兼容性分类 `CLEAN_ONE_SFQ_CANDIDATE`。

## 5. What it means

共享 raw reader、strict-event 实现、结果摘要和经典 compact 后端已用既有 raw 做工具链重放；这些输出不产生新的 physics conclusion。

## 6. What it does NOT prove

- 不证明任何新的电路行为、SFQ delivery、下游接收或 system Gate。
- 不替代历史 raw、既有报告或 METRIC_SPEC_V2 的科学权威边界。
- 未运行 JoSIM，也未改变历史输入或 raw。

## 7. Current status

`TOOLING_SMOKE_TEST_ONLY`
`AWAITING_USER_REVIEW`

## 8. Possible next options

- 用户先复核本摘要和 compact classic waveform。
- 若理解结果，可明确授权关闭该问题或继续一个最小 Quick。
- 若结果值得依赖，可明确授权生成 Promotion plan；工具不会自动执行。

## Result artifacts

- Classic overview: `/home/howard/JoSIM/test/exploration/tooling-consolidation-smoke-v1-20260901/quick/tooling-consolidation-smoke-v1/plots/RESULT_OVERVIEW.html`
- Detailed machine-readable metrics: `analysis.json`
- Human gate: `human-gate.yaml`
