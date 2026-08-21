# R1b AREA=.08 numerical and adversarial review

## Disposition

本点为 **artifact-valid / R1b AREA=.08 FAIL**。失败条件明确：read1
`B_OUT` 没有完整 2π monotonic phase segment；read0/control 约束通过。

## Numerical review

1. primary analysis 直接使用 `P(B_OUT|XTRIG)` 与 `V(B_OUT|XTRIG)`；read1
   最大段为 `-0.0201217685` turn，same-JJ area `-0.0201271525` turn，
   residual `-5.3840e-6 turn`。read0 为 `-0.0052866497` / `-0.0052890792`
   turn。phase 与 area 都只支持 subturn activity。
2. 计算保留 raw radians，turns 显式为 `delta/(2*pi)`；voltage area 使用
   raw CSV 的实际 time 列梯形积分，没有把固定 requested dt 当作实际采样间隔。
3. 四个 CSV 各 `13,599` rows，时间 `0--169.9875 ps`，strictly increasing、
   finite、无缺列；实际 `dt_min≈0.0125 ps`、`dt_max=.025 ps`；四个 solver
   stderr 均为 0 bytes。
4. `analysis/independent_crosscheck.py` 从 raw 独立重算四 case 的 SHA、
   BTRIG/BOUT phase、same-JJ area、complete flags、secondary 和 storage，
   `all_comparisons_pass=True`。
5. `compare_area010.py` 独立读取 accepted e3a18da AREA=.10 raw 与本点
   AREA=.08 raw；read1 BOUT phase/area magnitude 分别下降约 8.78%/8.79%，
   不是 activation improvement。

## Adversarial probes

### Weak oracle / current shortcut

AREA=.08 read1 `I(B_OUT)` peak 约 `8.1637 uA`，超过 nominal `Ic=8 uA`，但
phase 只有 `0.0201 turn`。因此 current-over-Ic 不是 event oracle；最终判据
仍是 continuous phase + same-JJ area。

### Stale artifact

本点 raw 使用新 point ID `diff-a008-b07-r100-series-return/run-01.csv`；
baseline comparison 明确指向 accepted e3a18da 的 AREA=.10 raw。没有复用或
覆盖 baseline raw。

### Wrong branch / common-mode regression

新 fixture 的 `B_OUT` 仍为 `N_SEC -> 0`，`L_SEC` 仍经串联
`R_SEC_LOAD -> 0` 返回；没有恢复旧的 `V(N_OUT)-V(N_SEC)` common-mode
measurement。raw 同时 probe secondary branch、B_OUT branch 和 same-JJ V/P。

### Hidden coupling

AREA 改变后 secondary read1 current 从 `2.0960` 降至 `1.8597 uA`，说明
receiver load 会反过来影响 transfer；因此 report 没有把“pickup topology
未改”过度表述为“secondary drive 完全恒定”。

### Overclaim

没有把 local B_OUT subturn phase 称为 switching 或 SFQ；没有把 read1
B_TRIG complete 称为 output delivery；没有因四 case 通过就宣布 R1b PASS。

## Q2 review

“Ic margin alone”被单点结果削弱，但因 AREA 同时改 RN/R0/C，不能宣称纯 Ic
因果已证伪。secondary transfer 仍存在且 state-dependent，排除了 signal
absence，但其 amplitude 被 loading 改变。`beta_c` diagnostic 和 output
response 同时下降使 C（dynamic damping/storage）比 A 更可疑；B/C 仍由单点
无法唯一分离。最强安全措辞是：**在当前 topology、bias、damping、模型和
AREA=.08 点下，未见 activation；失败更符合 B+C 的加载动态限制，而非
纯 Ic margin 充分解释。**

## Residual uncertainty

未做三步 timestep convergence、固定 RN/C 的纯 Ic 实验、额外 AREA 点、
长时重复、self-quench 或 JTL。因此该结论只适用于声明的 model、激励、
load、时间步和 matched matrix，不是普遍不可能性。
