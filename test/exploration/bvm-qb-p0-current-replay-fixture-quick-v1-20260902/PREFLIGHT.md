# PREFLIGHT — BVM_QB_P0_CURRENT_REPLAY_FIXTURE_QUICK_V1

预检记录时间：`2026-09-02T11:55:26+08:00`。
本文件在唯一 RP science run 之前冻结，之后不得按结果修改实验规则。

## 授权与基线

- 授权任务：`BVM_QB_P0_CURRENT_REPLAY_FIXTURE_QUICK_V1`。
- 授权范围：恰好一次新的 JoSIM science run；不重跑 P0/I0。
- 授权前 gate transition commit：`0ab139aca7f452faf93cf6d81e3f30be714a7e51`。
- PREFLIGHT checkpoint：本文件与 `experiment.yaml`、生成器、runner、独立复核脚本和
  literal replay deck 一起提交；提交 hash 作为运行前 HEAD 记录。
- 当前工作分支基线：`master`，授权前 HEAD 为 `0ab139aca7f452faf93cf6d81e3f30be714a7e51`。

## P0 输入与方向核验

- P0 raw：`../bvm-load-qb-matrix-v1-20260901/raw/physical/13ps/12x320/logical1_read/run-01.csv`。
- P0 raw SHA-256：
  `9aecc3f626148737bbd14e8cdb42a546002d7b2f268cc39badc430647c877d66`。
- 选择列：完整 `I(LIN|XBQ)`，occurrence `0`，样本数 `13599`，时间范围
  `0–169.9875 ps`。
- 父 P0 deck 的末级 JSL：`B_LD12 njsl11 IN jjmit area=3.2`。
- 冻结 QB 的输入电感：`Lin IN 1 0.8p`。
- 因此 RP 源固定为：`I_REPLAY 0 IN`，正方向为流入 QB `IN`；保留 P0 每一个
  原始 timestamp/current pair。
- 生成变换为空：不 fit、不 smoothing、不 scaling、不 hold、不 truncate、不删负瓣、
  不 retime、不 resample、不 interpolate。

## 生成 deck 与冻结模型

- literal RP deck：`inputs/rp_p0_current_replay.cir`。
- RP deck SHA-256：`07e92f7c04e8ae75a90b3eb7efcdf84a32b7e7bdd1fefd3581dea54b83dc86eb`。
- QB snapshot：`inputs/bq_cell.cir`，SHA-256
  `5ee4e8f054a9a49aea7e48493b20ef3d794db01b2902f15a439b0ea31f2276a2`。
- JJ model snapshot：`inputs/jjmit.cir`，SHA-256
  `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`。
- solver：`build/josim-cli v2.7.2837d13`，SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`。
- `.tran 0.0125p 170p`；QB bias `35 µA`；`R_LOAD=10 Ω`；所有 P0/I0 QB 输出列均保留，
  并新增 `I(I_REPLAY)`。

## 预注册判据

1. 先做输入 fidelity：P0 `I(LIN|XBQ)` 对 RP `I(I_REPLAY)`，必须 exact time grid，且
   `max_abs_error ≤ 1.0e-6 µA`。同时记录 sample count、grid identity、max/RMS error、
   correlation、signed/positive/negative area difference。
2. 只有第 1 项通过，才解释 W2 `[80,90) ps` PRE；P0/RP 的五个 current 和三个
   continuous-unwrapped、W2-median-centered phase 必须分别满足 `0.01 µA` 与 `0.001 turns`
   的 max-abs limit。
3. W3 `[95,110) ps`、W4 `[110,130) ps` 只在 exact grid 上比较预注册的七个 primary
   signals。对每个非退化 signal 计算
   `C_x = RMS(RP-P0) / RMS(I0-P0)`；分母不超过 `1e-9`（对应单位）时报告
   `NOT_DEFINED_SMALL_REFERENCE_GAP`，不制造 ratio。
4. BJL2 `P(BJL2|XBQ)` 与同一 branch 的 `V(BJL2|XBQ)` 使用冻结
   `StrictLocalEventSpec`/`strict_event_summary`，activity `[95,115) ps`、post
   `[115,130) ps`、tail `[125,130) ps`；报告最大 segment 的 start/end、phase turns、
   same-segment area/`Φ0`、residual、complete count、post/tail boundedness 和第二个
   complete segment。phase turns 永不写成 SFQ count。
5. KCL 必须调用共享 `scripts/bvmtools/kcl.py`，四条声明方程和 `0.001 µA` tolerance
   固定不变。

## 结果标签与停止条件

- 全部非退化 `C_x≤0.10`、strict class 与 P0 相同且 local 值 close：
  `CURRENT_REPLAY_FIXTURE_QUALIFIED / QUICK_PROMISING`。
- 仅一个 ratio 窄幅落在 `(0.10,0.20]` 且其余条件通过：
  `PARTIAL_CURRENT_REPLAY_CLOSURE / QUICK_AMBIGUOUS`，不静默放宽。
- 输入/PRE 有效但上述两者都不满足：
  `CURRENT_ONLY_REPLAY_INSUFFICIENT / QUICK_OPPOSITE`。
- 输入 grid/fidelity、PRE 或 artifact 失败：`REPLAY_INVALID / QUICK_INVALID`，停止解释
  W3/W4。
- 运行结束只生成一张 `plots/RESULT_OVERVIEW.html`（`CLASSIC_LOCKED`，
  `sep_comb/dark/-j 2pi`），然后状态固定为 `AWAITING_USER_REVIEW`、`next_action: STOP`；
  不自动执行任何后续选项。

## 运行前文件清单

`experiment.yaml`、`README.md`、`analysis/build_replay_deck.py`、`analysis/run_once.py`、
`analysis/review_replay.py`、`inputs/rp_p0_current_replay.cir` 及本文件均属于运行前
checkpoint；运行后只新增 raw、logs、analysis 和唯一 plot 产物，不覆盖父目录历史 raw。
