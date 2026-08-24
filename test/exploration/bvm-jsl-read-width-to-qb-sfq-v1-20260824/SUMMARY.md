# BVM_JSL_READ_WIDTH_TO_QB_SFQ_V1

## 主结论

本 Exploration 先在 canonical BVM 的 external `R_LD=12 Ω` fixture 中比较
READ plateau，再把同一注册宽度接入已接受的 external-series 12×JSL source
fixture，最后将真实 JSL branch current 原样 replay 到 frozen scaled QB。

- Phase A：`DURATION_SUPPORTED`，注册宽度选择 `W*=12 ps`。
- Phase B：`PAPER_JSL_WSTAR_SOURCE_VALID`，12×JSL 保持 bounded、read1-selective，且没有本地 JSL complete event。
- Phase C：`WIDTH_IMPROVES_QB_MARGIN_BUT_SUBTHRESHOLD`，W*=12 ps 将 frozen QB 的 BJL2 最大同向连续段从约 `0.892527` 提高到 `0.975402 turn`，但仍未达到完整事件判据。

因此，本轮没有建立 exactly-one QB event，也没有建立 physical
`canonical BVM → 12-JSL → QB` closure。

## 分阶段结果

### Phase A：READ width requirement

比较 `9/12/15/20 ps`，使用相同 canonical BVM、初始化、`R_LD=12 Ω` 和
matched controls。9 ps 使用已接受 raw；12/15/20 ps 为本轮新运行。

`W*=12 ps` 是满足注册规则的最短点：read1 的 positive baseline-subtracted
`I(L_SL)` area 从约 `357.742` 增加到 `466.278 µA·ps`，而 logical0 约为
`56.606 → 57.514 µA·ps`，READ=0 controls 仍接近零。存储和 source guard
保持 bounded。这个结论只适用于该 canonical BVM + 12 Ω fixture，不是普适
READ dwell requirement。

### Phase B：12-JSL source stage

冻结 accepted external-series 12×`AREA=3.2` JSL topology，仅将 READ active
transition 改为 W*=12 ps。12 个 JSL 全部保持 non-switching；read1 的
`I(L_SL)` activity range 为约 `−21.025…79.067 µA`，logical0 为
`−3.514…3.636 µA`，controls 更小。read1/read0 与 source/storage guard
仍有清楚分离，因此满足进入 Phase C ideal replay 的 gate。

### Phase C：frozen scaled QB replay

使用真实 W*=12 ps JSL current 的原始时间轴、极性和幅值作为理想 current
replay；不做 rescale、rectify、hold、smooth、resample 或重定时。

| replay | BJL2 最大单调段 | 同段电压面积 | complete event |
|---|---:|---:|---:|
| accepted 9 ps comparator, logical1 | `0.892527 turn` | `0.892537 Φ0` | 0 |
| W*=12 ps, logical1 | `0.975402 turn` | `0.975411 Φ0` | 0 |
| W*=12 ps, logical0 | `−0.00528549 turn` | `−0.00528686 Φ0` | 0 |
| W*=12 ps, READ=0 controls |约 `±2.5×10⁻⁵ turn` | 同量级 | 0 |

W*=12 ps 确实改善了 frozen QB 的 read1 near-threshold margin，但没有关闭
quantization window。BJL2 的 phase range、current 或 voltage peak 均未被单独
当作 event evidence。

## 证据边界

### Observed

- 新 raw 只包含注册的 Phase-A `12/15/20 ps`、Phase-B `12-JSL + 12 ps` 和
  Phase-C 四个 W*=12 ps replay cases；9 ps baseline/control raw 按 preregistration
  复用 accepted provenance。
- 所有 event 相关结果使用 continuous unwrapped phase、同一 JJ/同一 monotonic
  segment 的直接 `∫Vdt/Φ0`，并检查 post bounded/retrap。
- Phase C 的 four matched cases 中，read1 仍远强于 read0/control，但 BJL2
  没有 complete event。

### Derived

- Phase A 的 shortest useful point 是 12 ps。
- W*=12 ps source waveform 对 frozen QB 的 read1 BJL2 response 产生了约
  `0.8925 → 0.9754 turn` 的 near-threshold 增益。

### Inference

- 在本 frozen ideal-replay fixture 中，READ width 是影响 QB margin 的一个
  有效 source-side variable，但不是完成 QB quantization 的充分条件。

### Unknown

- physical BVM、external 12-JSL load 与 QB 同时连接时的真实 load-line、
  back-action 和 current transfer 尚未测试。
- 本轮没有接 JTL/T1，也没有证明 downstream SFQ delivery。

## 正式报告与图

- [Phase A report](analysis/PHASE_A_REPORT.md)
- [Phase B report](analysis/PHASE_B_REPORT.md)
- [Phase C report](analysis/PHASE_C_REPORT.md)
- [9 ps vs W*=12 ps QB replay comparison](plots/9ps-vs-Wstar-qb-replay-comparison.html)
- [9 ps vs W*=12 ps QB current comparison](plots/9ps-vs-Wstar-qb-current-comparison.html)
- [SL readout current comparison](plots/sl-readout-current-comparison.html)
- [plot provenance metadata](plots/9ps-vs-Wstar-qb-replay-comparison.metadata.json)

图是 descriptive visualization，不改变 raw、analysis 或正式 verdict。

## 停止边界

本轮到 Phase C 结束即停止；没有追加 READ width、amplitude、timestep、QB
parameter、JTL 或 T1 实验。
