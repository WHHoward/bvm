# Result

## 1. What we changed

- Baseline: `../bvm-load-qb-matrix-v1-20260901/inputs/physical/13ps/12x320/logical1_read.cir`
- Candidate: `inputs/physical/13ps/12x320/p1_physical_lin_removed.cir`
- Changed variables: {'QB Lin': '0.8 pH → removed'}

## 2. What was held fixed

- canonical BVM and BVM L_SL=0.4 pH
- logical1 initialization, 13 ps READ timing, and all source timing
- 12 JSL junctions with IC=320 uA each and unchanged JSL topology
- BJs/BJL1/BJL2 areas and models
- L0/L1/L2, RJ1/RJ2, RB, QB bias IBIAS=35 uA, and R_LOAD=10 ohm
- jjmit model, timestep=0.0125 ps, stop time=170 ps, and solver
- no logical0/no-read controls, other Lin values, BJs/bias/L variants, JTL, T1, or magnetic coupling

## 3. Why we tested it

若移除 QB Lin 能改善输入电流传递且不破坏 QB 自身工作，则 P1 physical 与 I1 ideal-replay 的 matched trajectory gap 应相对 P0/I0 缩小；source-side distortion 也可能同步减小。Lin 越小越好不作预设。

## 4. What happened

- p1-physical-lin-removed：最大同段相位 -0.121120970144 turn，同段电压面积 -0.121125596163 Φ0，兼容性分类 `INCONCLUSIVE`。
- i1-ideal-replay-lin-removed：最大同段相位 1.016028922894 turn，同段电压面积 1.016036834433 Φ0，兼容性分类 `INCONCLUSIVE`。

## 5. What it means

这是 QUICK 层的有界方向性观察，只用于筛选假说；它不是 formal evidence 或物理 Gate。

## 6. What it does NOT prove

- 不证明完整物理机制、鲁棒裕度、下游接收或 system Gate。
- 不把 local phase/area candidate 自动升级为成功 SFQ。
- 不能替代 Promotion 计划、匹配控制、收敛和必要的独立复核。

## 7. Current status

`QUICK_AMBIGUOUS`
`AWAITING_USER_REVIEW`

## 8. Possible next options

- 用户先复核本摘要和 compact classic waveform。
- 若理解结果，可明确授权关闭该问题或继续一个最小 Quick。
- 若结果值得依赖，可明确授权生成 Promotion plan；工具不会自动执行。

## Result artifacts

- Classic overview: `not generated`
- Detailed machine-readable metrics: `analysis.json`
- Human gate: `human-gate.yaml`
