# PREFLIGHT — BVM_QB_RJ1_TIMESTEP_ROBUSTNESS_V1

本记录对应本次新建的 exploratory robustness experiment。记录时间：
2026-09-03T11:08:50+08:00。

## 工作树与版本

- HEAD before task: `751a276adb73214c34b5f39fcfab4fbff95d1060`
- branch: `master`
- `git status --porcelain=v1`: 空（开始时 clean）
- solver: `build/josim-cli`
- JoSIM: `v2.7.2837d13`, compiled 2026-05-30 20:37:57
- solver SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`

## 固定来源 SHA-256

| source | SHA-256 |
|---|---|
| `BVMSim/BQ.cir`（仅作历史参照，不作为新 formal source） | `f3dcbf5f9bb3898faf5194b5f7c4771df3fa1ed16150496de4b52cb6f7256dfd` |
| `BVMSim/bvm_cell.cir` | `009e0683c7d4ffe14e2582c6d0a807669cc9b290639af7298d290ff7bbb43125` |
| `BVMSim/library_josim/jtl2.cir` | `ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a` |
| `BVMSim/data_tran.csv`（历史 raw，不重写、不作为本矩阵 raw） | `942a5a42a948561d9d9963e2c2ae222c7fbe96dd09b4213c38c3acd288360bd4` |
| `circuits/models/jjmit.cir` | `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336` |
| `circuits/qb/bq_cell_bvmsim_v1.cir` | `9cb0f218db8a8a85a811b6be4984e1af7121edeff2961a6f5608cdb808866ac7` |
| `scripts/josim-plot2.py` | `0aaf0b4bfd148e073d318c9a0762ec13995045abd88cad28336fb8128c33a1d6` |
| `docs/research/METRIC_SPEC_V2.md` | `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470` |

模板来源也已锁定并由 `inputs/generate_decks.py` 记录：

- four-BVM template `.../bvmsim-stagea-timestep-event-count-v1-20260902/migrated/T100.cir`：
  `e0eeb3435336ca86253241f6bdabb86b8c39baf642cb16c7b0a6409035a0518e`
- single-BVM S0-J template：
  `88b45b0a364e01e6b87e8f7ffdf47ecaa314f3cb1804d7e1bba8745daea4d50c`
- single-BVM S1-J template：
  `92946f450d2fab90dd03ed416f77543b070815bccd40b20f668191e8cf7186bc`

## 来源边界

`BVMSim/bvm_cell.cir` 是本轮 four-BVM 和 single-BVM 使用的历史/探索性 BVM
source，不是 canonical BVM authority。尤其 `BVMSim` 版本的 `R_JM1 = 8 ohm`，而
canonical `circuits/bvm/bvm_cell.cir` 的 `R_JM1 = 6 ohm`；本轮不替换 BVM，也
不声称 canonical BVM 驱动了这些 QB。

`BVMSim/BQ.cir`、`BVMSim/BQv1.cir`、`BVMSim/BQv2.cir` 均不作为本轮 formal
source。三份 experiment-local QB variant 从已提交的
`circuits/qb/bq_cell_bvmsim_v1.cir` 生成，唯一物理差异是 `RJ1`。

## 工具边界

分析使用共享 `bvmtools.raw/phase/sfq/waveform/compare/kcl/provenance`；事件
枚举使用已有的 `bvmtools.sfq.strict_event_list`，不建立实验本地第二套 SFQ
计数算法。绘图使用 `scripts/josim-plot2.py`；图只描述 raw，不认证事件或
Gate。开始运行前已完成目录与 deck 的 machine-check，并单独提交 setup。
