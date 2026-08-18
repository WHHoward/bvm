# BVM Continuous Rewrite/Read Closure — Exploration summary

date: 2026-08-19 | tier: Exploration | solver v2.7.2837d13 | dt=0.0125ps |
load 12Ω | 2 new long-run fixtures（680ps，4 cycles × 170ps），不重跑其他
raw，不改 canonical BVM

## 实验设计
- `rewrite-read-1010.cir`：write 1/0/1/0，每 cycle canonical +READ
- `rewrite-read-0101.cir`：write 0/1/0/1，每 cycle canonical +READ
- cycle=170ps：write 10–21（±100µA WL+BL）→ readiness 21→96（75ps，
  S0 D0 bound）→ READ 96–105（+100µA WL+SE）→ post 140–150 → 下一 cycle
- logical semantics 严格按 `BVM_LOGICAL_SEMANTICS_V1`（write1=+100U、
  write0=−100U、canonical READ=+100U）

## 结果（rewrite-read-analysis.json，全 Decimal）

### 1. 写/读正确性：**全部正确**
storage 签名严格按序列翻转（JM1 PRE）：
- 1010: +5.9111 → −5.9114 → +5.9114 → −5.9114
- 0101: −5.9111 → +5.9114 → −5.9114 → +5.9114
L_M1 同步翻转（∓43.6µA）。

### 2. read1 持续 strong delayed nonlinear response：**是**
4 个 read1 cycle：JS1 turns = −2.99411 / −2.99420 / −2.99420 / −2.99420
（≈−3 圈持续）；N6 主峰 +1.8144/1.8142mV @ 100.99/270.99/440.99/610.99ps
（delayed onset，非 READ 边沿）。

### 3. read0 持续 weak edge/no-running：**是**
4 个 read0 cycle：JS1 turns = −0.00260 / −0.00252 / −0.00252 / −0.00251
（≈0 圈）；N6 仅 +0.5617mV @ READ 边沿（96/266/436/606ps）。

### 4–5. cycle-to-cycle reproducibility：**高度可重复**
- read1: JS1 turns 极差 8.6e-5 turns（0.003%）；N6 peak 差 2e-7 V（0.01%）
- read0: JS1 turns 极差 8.1e-5；N6 peak 差 1e-7 V
- 同类型 cycle 间 timing 完全一致（±0.025ps 内）

### 6. drift / history dependence：**仅首次写入微小偏移，之后无累积**
- JM1 PRE 首次 cycle = 5.911090，后续 cycles = 5.911370/5.911419
  （差异 +2.8e-4 rad ≈ 首次 READ 后相位恢复的固定偏移）
- 第二次起完全稳定（cycle 1↔3、cycle 2↔4 逐位一致）：**无累积 drift、
  无 phase/current accumulation**

### 7. previous READ 对 opposite WRITE 的影响：**无可测影响**
write0 前为 read1、write1 前为 read0 的混合序列均正确翻转；storage
签名与 isolated canonical（±5.9111）差异 <5e-4 rad。

## 参考比较（informational，不要求逐字一致）
- read1 cycles 与 isolated `pos-read-single`（JS1 −2.9941、N6 1.8145mV）
  一致到 0.01% 级
- read0 cycles 与 isolated `neg-init-pos-read`（JS1 −0.0026、N6 0.5617mV）
  一致到 0.1% 级

## Observed / Derived / Inference / Unknown / Next
- Observed: 16/16 cycle 写读正确；read1/read0 行为持续；可重复性极佳
- Derived: continuous rewrite/read 无历史依赖（首次偏移固定后稳定）
- Inference: BVM 支持连续 rewrite→read 操作，为 receiver 提供稳定的
  per-cycle 判别输入
- Unknown: 更短 cycle（<170ps）时的 readiness 边界（未扫）；读写
  交叉时序对 receiver 的耦合（未设计 receiver）
- Next: receiver exploration（magnitude-threshold one-shot），本轮不启动

## Promising / Candidate
**不升级 Candidate**；BVM functional closure 已完成（支持结束 BVM
functional Exploration 进入 receiver 设计）。
