# Stage A preflight

任务：`IMPORT_BVMSIM_QB_AND_STRICTLY_QUALIFY_V1`  
阶段：A（Exploratory qualification）  
授权时间：`2026-09-02T06:24:35Z`

## Git and solver

- HEAD before task: `22376a3f1a8c3cfd40a6f9afaf85da7b43e3c3f6`
- working tree before task: clean (`git status --short --untracked-files=all` empty)
- QB import commit: `b3d86c1b5619d09d891c4e4c2957f611e80b201a`
- setup was prepared from the clean QB-import commit; the exact clean
  execution HEAD is recorded immediately before the science runs in
  `logs/pre-run-head.txt`
- executable: `build/josim-cli`
- version: `v2.7.2837d13` (compiled 2026-05-30 20:37:57)
- solver SHA-256:
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`

## Preserved source SHA-256

The following files were read-only inputs.  No file under `BVMSim/` was
edited, renamed, deleted, or overwritten.

```text
f3dcbf5f9bb3898faf5194b5f7c4771df3fa1ed16150496de4b52cb6f7256dfd  BVMSim/BQ.cir
009e0683c7d4ffe14e2582c6d0a807669cc9b290639af7298d290ff7bbb43125  BVMSim/bvm_cell.cir
09b30458cf2bec3fbe85221e9f34661ecee4c6e28aed18c54aaa30a94ad1f948  BVMSim/test_bvm_mixed_0.cir
942a5a42a948561d9d9963e2c2ae222c7fbe96dd09b4213c38c3acd288360bd4  BVMSim/data_tran.csv
ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a  BVMSim/library_josim/jtl2.cir
0a63f11cd5cc997f69e2ba94551222c7e274ae38147ede1d872f5a892fd4f487  BVMSim/run.sh
775fad35e12438e0f2e2f1fee7b3d2e66a69710e077be5a17ec74b5f6566010e  BVMSim/josim-plot.py
```

Shared/model and migrated circuit hashes at setup:

```text
19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336  circuits/models/jjmit.cir
ea7346546bef091dc2efa39ab6f0abcfa54f833aeeabb909dcf3815cdaea42a4  circuits/bvm/bvm_cell.cir
9cb0f218db8a8a85a811b6be4984e1af7121edeff2961a6f5608cdb808866ac7  circuits/qb/bq_cell_bvmsim_v1.cir
e0eeb3435336ca86253241f6bdabb86b8c39baf642cb16c7b0a6409035a0518e  migrated/m0_bvmsim_qb.cir
4ee38ad2b515c170a2c4f6847176ea0d20e923f767101a15a288a745514780db  migrated/s1_bvmsim_qb.cir
```

`BVMSim/bvm_cell.cir` is explicitly not canonical BVM authority: its
`R_JM1=8 Ω`, while `circuits/bvm/bvm_cell.cir` has `R_JM1=6 Ω`.  Stage A does
not reconcile this and does not claim that canonical BVM drives this QB.

## Analysis/tool hashes at setup

```text
0bc0e4775517072b5ba042688cbafdb91648cf510e41fa064dc66f2d26794843  analysis/analyze.py (preregistered setup)
544729761950f3485c73ae642d1edbad042887f0e8620d3b6b74e2822fc77190  inputs/prepare_decks.py
0aaf0b4bfd148e073d318c9a0762ec13995045abd88cad28336fb8128c33a1d6  scripts/josim-plot2.py
bce9f07baaadca3bdd0c84aae6f4ca287039d7c92cec0430e7f0976f00991e99  scripts/bvmtools/sfq.py
2b7303fd5f99a61846f24d50c18594d073e858a74e6fa632bc90d7d1dbb1f8e2  scripts/bvmtools/raw.py
f403bd75eb9aef9391272cb44e10266f95767b10f01122931f5042bd5d538369  scripts/bvmtools/provenance.py
ac79f640bc9fae8784f75ef00a6cb978e8fa3606a9938cf0eb131fc728caba3c  scripts/bvmtools/phase.py
75ca2f24ff3df4c7706af5cf4bb23880e74100e7f694ab612cb02ad07d0f2af1  scripts/bvmtools/waveform.py
105f21a3fd8fc0199988dc7b5a0c586f98554f940255d66a3c4c31a5a2d8317f  scripts/bvmtools/compare.py
0cbdf83063d64d18d8c9a56a66fe6d996df26ec1b1815659968eee1e10ce153d  scripts/bvmtools/kcl.py
f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470  docs/research/METRIC_SPEC_V2.md
```

分析器在 S1 raw 生成后发现 KCL 节点 2 还必须包含与 `BJ1` 并联的
`RJ1` 支路；这是分析口径修正，不是物理网表或 raw 重跑。最终使用的
`analysis/analyze.py` SHA-256 为
`2c1758678aa3e42f00d135f833a449eadc3c602ab2da34a8e7c6095b408439d8`，并在
`provenance.json` 中同时保留了最终工具闭包。

## Run authorization and stop conditions

- M0: exactly one migrated legacy-resolution run, `.tran 0.1p 200p 45p`.
- S1: exactly one run, only if M0 passes; `.tran 0.025p 200p`, saving from
  `t=0`.
- No raw file is reused as a mutable output; M0 and S1 have separate paths.
- No Stage B, canonical BVM replacement, single-BVM test, sweep, redesign,
  T1, or automatic follow-up is authorized.
- S1 strict event lists use the existing `bvmtools.sfq` segment list and
  same-JJ direct phase/voltage-area arithmetic.  The analyzer does not count
  voltage peaks, over-threshold samples, or whole-window phase displacement as
  SFQ events.
