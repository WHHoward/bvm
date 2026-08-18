# BVM_LOGICAL_SEMANTICS_V1 — BVM logical semantics freeze

status: FROZEN
frozen_by: project lead (user), 2026-08-19
checkpoint_anchor: `a6ab47419af5238574f058684df53fed39298967`
based_on: exploration checkpoint `a6ab474`（完整 2×2 state/READ matrix，
`test/exploration/bvm-internal-readout-20260819/`）
source_authority: JH-20260817-BVM-S2-STABLE-LOAD-001（ACCEPTED）—
initialization 与 read PWL 的 source；JH-20260814-BVM-S0-D0（ACCEPTED）—
operational stored-state distinctness
scope: BVM logical semantics only; 不定义 SFQ 阈值、JTL 验收、
receiver/transducer 设计或 paper 级主张。

## 1. Frozen definitions

### Logical 1
State A：
- initialization：WL + BL = **+100 µA**
- 对应当前 operational **positive** stored state
- 正式定义为 **logical 1**

### Logical 0
State B：
- initialization：WL + BL = **−100 µA**
- 对应当前 operational **negative** stored state
- 正式定义为 **logical 0**

### Canonical READ（正式固定为 positive READ polarity）
- WL = **+100 µA**
- SE = **+100 µA**
- 当前 frozen characterization timing：**96–105 ps plateau**
- 注：timing/amplitude 是当前 canonical simulation condition；逻辑语义的
  核心是 **positive READ polarity**。

### Downstream event semantics（正式冻结）
- **logical 1 → exactly 1 SFQ event**
- **logical 0 → 0 SFQ event**
- 即 **1 → 1 event**，**0 → 0 event**
- 这是目标语义（receiver/transducer 的验收方向），不是当前 raw 行为。

## 2. Current BVM raw-readout state（必须明确）

- **logical 1 + canonical READ** 当前产生 **strong multi-turn R-loop/JJ
  dynamics**（JS1/JS2 连续相位旋转）；
- **logical 0 + canonical READ** 当前产生 **weak edge-dominated /
  no-running dynamics**；
- 当前 BVM raw readout **不是标准 SFQ output**；
- **~3 phase turns 不得称为 3 SFQ**；
- receiver/transducer 的任务：把 logical-1 的 strong response 转换成
  **exactly one JTL-receivable SFQ**，同时 logical-0 不触发。

## 3. Evidence anchor

### Checkpoint
`a6ab47419af5238574f058684df53fed39298967`
（`explore: 2x2 state/READ matrix closure + v2 machine-readable fixes`）

### 2×2 observation（JS1 unwrapped turns in READ window）
| cell | JS1 turns | status |
|---|---|---|
| A/+READ | ≈ **−2.994** | running |
| A/−READ | ≈ **+0.002596** | no running |
| B/+READ | ≈ **−0.002596** | no running |
| B/−READ | ≈ **+2.994** | running |

### Formal logical operation
只采用：
- **A/+READ = read1**（logical 1 + canonical READ）
- **B/+READ = read0**（logical 0 + canonical READ）

A/−READ 与 B/−READ 仅保留为 **polarity/mechanism diagnostic**，不属于
canonical logical READ。

## 4. Usage constraints

- logical 1/0 命名仅在本文件冻结范围内有效；任何 receiver/JTL/Gate 结论
  仍需独立预注册实验与审计。
- phase turns 是 raw phase 的 (rad/2π) 显示；不得升级为 SFQ count。
- 本冻结不修改任何 accepted evidence、canonical BVM 或历史 audit。
