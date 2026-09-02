# BVMSim Stage-A timestep / event-count convergence Quick

状态：预注册设置，尚未运行新的 JoSIM science matrix。

## 任务边界

本目录是一个独立的 Exploratory Quick。它只复现实验 A 的冻结
4-BVM → accumulated sensing line → BVMSim QB → 六级 BVMSim JTL → 10 Ω
负载 fixture，并改变 `.tran` 控制行。它不替换 canonical BVM，不改变 QB、
JTL、bias、source、load 或 topology，也不启动 Stage B。

关键问题是：历史约 4 turns 与 Stage-A S1 约 5 turns 是否为 timestep-induced
branch change，以及这些净相位位移是否真正由分离、re-trapped、同一 junction
上的完整事件组成。

## 预注册矩阵

| run | transient | 输出起点 | 目的 |
|---|---|---:|---|
| T100 | `.tran 0.1p 200p 45p` | 45 ps | 历史 print-start 复现 |
| T050 | `.tran 0.05p 200p` | 0 ps | timestep probe |
| T025 | `.tran 0.025p 200p` | 0 ps | Stage-A S1 复现 |
| T0125 | `.tran 0.0125p 200p` | 0 ps | 更细诊断 |
| T100_FULL | `.tran 0.1p 200p` | 0 ps | print-start control |

所有 deck 从已 hash-bind 的 Stage-A M0 fixture 模板生成；生成器会拒绝任何
除单一 `.tran` 行之外的差异。历史 `BVMSim/data_tran.csv`、Stage-A M0 raw
和 Stage-A S1 raw 均为只读输入，新的 raw 使用独立目录。

## 已记录的输入指纹

记录时间：`2026-09-02T19:36:03+08:00`。任务开始时工作树干净，HEAD 为
`c54ed80`（完整指纹见 `experiment.yaml` 和最终 provenance）。

```text
e0eeb3435336ca86253241f6bdabb86b8c39baf642cb16c7b0a6409035a0518e  Stage-A M0 fixture template
942a5a42a948561d9d9963e2c2ae222c7fbe96dd09b4213c38c3acd288360bd4  BVMSim/data_tran.csv
74e75a9d77abd302d552a27c10b1e8d57116df66a65e8a6a86dc939eef092399  Stage-A M0 raw
a2101459d0c17114676e44bd77fdc40eec2d0daf568a803bfb0fe8c5cf33ba57  Stage-A S1 raw
48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2  build/josim-cli
19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336  circuits/models/jjmit.cir
9cb0f218db8a8a85a811b6be4984e1af7121edeff2961a6f5608cdb808866ac7  circuits/qb/bq_cell_bvmsim_v1.cir
009e0683c7d4ffe14e2582c6d0a807669cc9b290639af7298d290ff7bbb43125  BVMSim/bvm_cell.cir
ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a  BVMSim/library_josim/jtl2.cir
09b30458cf2bec3fbe85221e9f34661ecee4c6e28aed18c54aaa30a94ad1f948  BVMSim/test_bvm_mixed_0.cir
```

`BVMSim/bvm_cell.cir` 是历史/探索性 BVM，不是 canonical authority；已知
差异为其 `R_JM1=8 Ω`，而 `circuits/bvm/bvm_cell.cir` 为 `R_JM1=6 Ω`。
本 Quick 不使用 canonical BVM，不能声称 canonical BVM 驱动该 QB。

预注册脚本和共享分析工具指纹：

```text
3afc4cab7fa62cf6095a998e17e49116e80159e0185dfc1eb36cd62d76dcf9d2  inputs/generate_decks.py
760252ffaac695964f3ec58f5c25555078c78d0c6411b0e4bfed35913209a0ea  analysis/audit_existing.py
2b7303fd5f99a61846f24d50c18594d073e858a74e6fa632bc90d7d1dbb1f8e2  scripts/bvmtools/raw.py
ac79f640bc9fae8784f75ef00a6cb978e8fa3606a9938cf0eb131fc728caba3c  scripts/bvmtools/phase.py
bce9f07baaadca3bdd0c84aae6f4ca287039d7c92cec0430e7f0976f00991e99  scripts/bvmtools/sfq.py
75ca2f24ff3df4c7706af5cf4bb23880e74100e7f694ab612cb02ad07d0f2af1  scripts/bvmtools/waveform.py
105f21a3fd8fc0199988dc7b5a0c586f98554f940255d66a3c4c31a5a2d8317f  scripts/bvmtools/compare.py
0cbdf83063d64d18d8c9a56a66fe6d996df26ec1b1815659968eee1e10ce153d  scripts/bvmtools/kcl.py
f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470  docs/research/METRIC_SPEC_V2.md
0aaf0b4bfd148e073d318c9a0762ec13995045abd88cad28336fb8128c33a1d6  scripts/josim-plot2.py
```

## 既有 raw 审计与判定边界

运行新 JoSIM 之前先执行 `analysis/audit_existing.py`。它只使用
`bvmtools.raw` 读取 CSV，并对 exact stored timestamp overlap 做比较；不插值，
历史 duplicate `V(O2)` 必须显式按 occurrence 选择。110–170 ps 的“有意义分歧”
预先定义为：相位轨迹差至少 0.05 turn，且电压差至少
`max(5 µV, 0.10 × 两者窗口峰值)`，并持续三个共同采样点。

此规则用于定位分歧，不把它当成 SFQ event count 判据。event count 仍须依据
同一 JJ 的连续单调 segment、相位 delta、同 segment `∫Vdt/Phi0`、方向和
retrap/bounded interval。

## 运行前检查

```text
git status --short --branch
git log -1 --format=%H
build/josim-cli --version
sha256sum build/josim-cli
python3 inputs/generate_decks.py --help
python3 analysis/audit_existing.py
```

预注册设置必须先提交；提交后才允许生成 deck、运行 T100/T050/T025/T0125
及可选的 T100_FULL。每次运行保存独立 deck、command、log、raw、hash 和
artifact result，不覆盖历史文件。

注意：冻结模板使用相对 `.include` 路径，所以执行 deck 必须放在本实验的
`migrated/` 目录（与 Stage-A 模板相同的目录深度）。生成器现在会拒绝其他
输出位置。首次误放在 `runs/T100/` 的 T100 attempt 保留在 `runs/T100/`，其
退出码为 255、没有 raw，不作为 science result。

## 停止条件

新的实验与分析结束后停止在：

```yaml
state: AWAITING_USER_REVIEW
user_reviewed: false
next_step_authorized: false
automatic_next_experiment: false
stage_b_authorized: false
```

Sol XHigh reviewer 只读审阅必须完成，重点挑战 4→5 的 timestep 因果归因；
用户审阅前不进行任何后续实验。
