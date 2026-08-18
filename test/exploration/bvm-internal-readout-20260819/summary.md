# BVM Internal Readout Event Survey — Exploration summary

date: 2026-08-19 | tier: Exploration | solver: build/josim-cli v2.7.2837d13
（hash 48655cb3…）| dt=0.0125ps | R_LD=12Ω | fixture 与 accepted
L12-positive-read 逐 token 一致（14 共享列 / 190386 tokens / 0 mismatch）。

## Research question
canonical BVM 在 READ 中，内部是否存在稳定、局部、可重复的 switching/event
source，可用于构造 one BVM → one SFQ？

## Observed（直接观测，raw CSV 窗口统计）

1. **JS1/JS2 phase 行为**（窗口 [94,130)ps，半开）：**无任何 >π/2 的离散
   相位跳变**（0 events / 0 slips in all 4 runs），但窗口内净相位累积
   持续平滑变化：
   - pos: JS1 Δφ=−18.8126 rad（≈−3.0 圈）；JS2 −18.8420 rad
   - neg: JS1 −25.1738 rad（≈−4.0 圈）；JS2 −25.1269 rad
   - 单步最大 |Δφ| = 0.080 rad（远小于 π/2）→ 平滑连续旋转，非离散 slip
2. **phase 旋转时域分布**（pos JS1）：[94,96) +0.05；[96,105) READ 期间
   −15.33；[105,110) −3.98；[110,130) +0.44；[130,150) ≈0 → 旋转几乎全部
   发生在 READ 脉冲期间及后沿 5ps，然后相位稳定
3. **V(B_JS1) 形态**：READ 窗口内持续正负振荡（幅值 ~1e-4–2e-3 V 级），
   非单调单脉冲 → 与连续 running 一致
4. **repeated READ**（pos/neg 各 2 次）：READ1 vs READ2 的 JS Δφ 逐字一致
   （pos: −18.8125595 / −18.99635；neg: −25.17380896 / −25.15557）→ 高度可重复
5. **storage 保存**（JM1/JM2，PRE [80,90) vs POST1 [140,150) vs POST2
   [210,220)）：
   - pos: JM1 POST1 偏移 +0.66 rad → POST2 恢复 −0.0003 rad；JM2 +0.44 → −0.055
   - neg: JM1 +0.74 → +0.0009；JM2 +0.18 → −0.030
   → READ 后 storage 相位在 POST2 窗口回到 PRE 值（|Δ|<0.06 rad），未翻转
6. **N6 vs SL 瞬态**（V，READ1）：
   - pos: N6 peak 1.81mV @100.99ps，半峰宽 10.26ps；SL peak 0.90mV
     @101.01ps，同宽 10.26ps
   - neg: N6 2.38mV @103.25ps，半峰宽 5.44ps；SL 1.19mV，同宽 5.44ps
   → N6 幅度约为 SL 的 2 倍，峰位几乎同时，宽度相同

## Derived（自洽重算）

7. **phase/voltage-area 自洽**（同结、同 run、同窗口）：JS1/JS2 的
   Δφ(rad) 与 ∫V dt·2π/Φ0 一致到 <1e-5 rad（4 runs 全 True）→ 旋转量
   与结电压面积完全对应，无缺失 slip
8. **圈数**：pos 极性 READ ≈ 3.0 整圈连续旋转；neg ≈ 4.0 整圈 → 极性
   通过 running 圈数区分（3 vs 4），不是 0/1 数字事件
9. 事件源定位：旋转源是 JS1/JS2（R-Loop 分支结），不是 JM1/JM2
   （S-Loop 存储结在 READ 后相位复原）

## Inference（解释性推断，非 Gate）

10. READ 期间 JS1/JS2 处于**持续相位 running**（多圈连续旋转），而非
    isolated single-2π switching；该行为可重复、可被 READ 触发与停止。
11. N6 是比 SL 更局部、幅度更大的内部信号点（SL 经 RSL/LSL 分压
    衰减 ~0.5×）；两者时域宽度相同，均反映 running 过程而非单个 SFQ
    事件。
12. 当前证据下，canonical BVM 内部**不存在现成的 isolated single-2π
    event source**；若要做 one BVM → one SFQ，需要把 running 过程
    截断/量子化为单事件（外部 one-shot receiver 候选动机）。

## Unknown

- READ 脉冲幅度/宽度变化时 running 圈数是否稳定（未扫）
- 该 running 是否可通过电路参数设计收敛为单圈（未做参数改动——
  本轮不动 canonical）
- 12Ω 负载以外的 R_LD 行为（未跑；accepted 1/25/50Ω 可复用）
- JS running 与 SL 输出的因果链细节（电流分配）未单独隔离

## Next（下一步候选，待授权方向内自行推进）

- A. 简化 stimulus screening：构建与 running 特征一致的受控单脉冲源，
      测试 shared-quantizing 与 local self-quenching one-shot 两种
      candidate 的 trigger→quench→output 行为
- B. 最小 control run（read 幅度 0，同拓扑）以分离 running 触发条件
- C. 负载灵敏度（复用 accepted 1/25/50Ω inputs 结构）

## Promising internal event candidate?
**否**（本轮未发现 isolated single-2π 内部事件源；发现的是可重复、
可触发的 multi-turn phase-running 于 JS1/JS2 —— 是 receiver 设计输入，
不是现成 SFQ 源）。值得继续 exploration，不升级为 Candidate。
