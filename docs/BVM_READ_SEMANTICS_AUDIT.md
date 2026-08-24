# BVM READ semantics audit

审计 parent HEAD：`576ca9d32b15c99f8c35c4271336ffa079664b64`。本文件只重标语义和 provenance，不修改任何旧 raw。

## Canonical READ_PROTOCOL_V1

- logical1：positive WL+BL initialization；logical0：negative WL+BL initialization。
- 两种 stored state 的 READ 完全相同：WL=+100 µA、SE=+100 µA、相同 onset/plateau/rise/fall。
- WL-only negative-state read 是 `WL_ONLY_NEGATIVE_STATE_DIAGNOSTIC`，不是 canonical logical0 gate。
- WL=0、SE=0 的 case 是 `NO_READ_CONTROL`。
- phase 图统一为原始 JoSIM `P(t)/(2π)` 连续轨迹；不等于 SFQ count。

## 审计结论

| 范围 | 结论 | 处置 |
|---|---|---|
| canonical BVM `neg-init-pos-read.cir` | canonical logical0_read | 保持当前有效 |
| PAPER-SL-L0 `logical0-read.cir` | negative initialization + WL-only READ | 重标为 WL-only diagnostic |
| PAPER-SL-Q1→Q6 logical0 replay | 继承 PAPER-SL-L0 noncanonical source | 不得作为 canonical logical0 gate evidence |
| Phase-A width 12/15/20 ps | WL+SE canonical pair | 可用于 canonical width source comparison |
| Phase-B/C 既有 12 ps logical0 | 继承 WL-only source | 旧结论保留 provenance，但 logical0 gate 降级 |

## 影响边界

PAPER-SL 的 read1 source、同一 read1 source 下的 QB 参数相对比较，以及真正无 READ 的 controls 不因该审计自动撤销。受影响的是把旧 PAPER-SL logical0 直接表述为 canonical logical0→zero 的结论。

## 机器审计结果

- case 数：46；matched pair 数：4。
- validator：`PASS`。

## Case inventory

| case | stored state | role | classification | validity | source lineage |
|---|---|---|---|---|---|
| `canonical.logical1_read.pos-read-single` | logical1 | `logical1_read` | `CANONICAL_LOGICAL1_READ_V1` | `CURRENT_VALID` | canonical_bvm |
| `canonical.logical0_read.neg-init-pos-read` | logical0 | `logical0_read` | `CANONICAL_LOGICAL0_READ_V1` | `CURRENT_VALID` | canonical_bvm |
| `canonical.logical1_no_read_control.pos-control` | logical1 | `logical1_no_read_control` | `NO_READ_CONTROL` | `VALID_WITH_RELABELED_CONTROL` | canonical_bvm |
| `canonical.logical0_no_read_control.neg-control` | logical0 | `logical0_no_read_control` | `NO_READ_CONTROL` | `VALID_WITH_RELABELED_CONTROL` | canonical_bvm |
| `canonical.negative_polarity_read_diagnostic.pos-init-neg-read` | logical1 | `NEGATIVE_POLARITY_READ_DIAGNOSTIC` | `NEGATIVE_POLARITY_READ` | `VALID_WITH_RELABELED_CONTROL` | canonical_bvm |
| `canonical.logical0_read.neg-read-single` | unknown | `SUPERSEDED_INVALID_INIT_FIXTURE` | `INITIALIZATION_PROTOCOL_MISMATCH` | `SUPERSEDED_INVALID_INIT_FIXTURE` | canonical_bvm |
| `paper_sl_l0.logical1-read` | logical1 | `logical1_read` | `CANONICAL_LOGICAL1_READ_V1` | `CURRENT_VALID` | paper_sl_l0 |
| `paper_sl_l0.logical0-read` | logical0 | `WL_ONLY_NEGATIVE_STATE_DIAGNOSTIC` | `NONCANONICAL_WL_ONLY_LOGICAL0_SOURCE` | `LOGICAL0_GATE_NOT_TESTED` | paper_sl_l0 |
| `paper_sl_l0.logical1-read0-control` | logical1 | `logical1_no_read_control` | `NO_READ_CONTROL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_l0 |
| `paper_sl_l0.logical0-read0-control` | logical0 | `logical0_no_read_control` | `NO_READ_CONTROL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_l0 |
| `width.phase_a.12ps.logical1_read` | logical1 | `logical1_read` | `CANONICAL_LOGICAL1_READ_V1` | `CURRENT_VALID` | canonical_bvm |
| `width.phase_a.12ps.logical0_read` | logical0 | `logical0_read` | `CANONICAL_LOGICAL0_READ_V1` | `CURRENT_VALID` | canonical_bvm |
| `width.phase_a.15ps.logical1_read` | logical1 | `logical1_read` | `CANONICAL_LOGICAL1_READ_V1` | `CURRENT_VALID` | canonical_bvm |
| `width.phase_a.15ps.logical0_read` | logical0 | `logical0_read` | `CANONICAL_LOGICAL0_READ_V1` | `CURRENT_VALID` | canonical_bvm |
| `width.phase_a.20ps.logical1_read` | logical1 | `logical1_read` | `CANONICAL_LOGICAL1_READ_V1` | `CURRENT_VALID` | canonical_bvm |
| `width.phase_a.20ps.logical0_read` | logical0 | `logical0_read` | `CANONICAL_LOGICAL0_READ_V1` | `CURRENT_VALID` | canonical_bvm |
| `width.phase_b.12ps.logical1_read` | logical1 | `logical1_read` | `CANONICAL_LOGICAL1_READ_V1` | `CURRENT_VALID` | paper_sl_l0.logical1-read |
| `width.phase_b.12ps.logical0_read` | logical0 | `WL_ONLY_NEGATIVE_STATE_DIAGNOSTIC` | `NONCANONICAL_WL_ONLY_LOGICAL0_SOURCE` | `LOGICAL0_GATE_NOT_TESTED` | paper_sl_l0.logical0-read |
| `paper_sl_q1.paper-j1-logical1-read` | logical1 | `logical1_read` | `INHERITED_PROTOCOL` | `CURRENT_VALID` | paper_sl_l0.logical1-read |
| `paper_sl_q1.paper-j0-logical0-read` | logical0 | `logical0_read` | `INHERITED_PROTOCOL` | `LOGICAL0_GATE_NOT_TESTED` | paper_sl_l0.logical0-read |
| `paper_sl_q1.paper-j1-logical1-read0-control` | logical1 | `logical1_no_read_control` | `INHERITED_PROTOCOL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_l0.logical1-read0-control |
| `paper_sl_q1.paper-j0-logical0-read0-control` | logical0 | `logical0_no_read_control` | `INHERITED_PROTOCOL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_l0.logical0-read0-control |
| `paper_sl_q2.37p5u.paper-j1-logical1-read` | logical1 | `logical1_read` | `INHERITED_PROTOCOL` | `CURRENT_VALID` | paper_sl_q1.paper-j1-logical1-read |
| `paper_sl_q2.37p5u.paper-j0-logical0-read` | logical0 | `logical0_read` | `INHERITED_PROTOCOL` | `LOGICAL0_GATE_NOT_TESTED` | paper_sl_q1.paper-j0-logical0-read |
| `paper_sl_q2.37p5u.paper-j1-logical1-read0-control` | logical1 | `logical1_no_read_control` | `INHERITED_PROTOCOL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_q1.paper-j1-logical1-read0-control |
| `paper_sl_q2.37p5u.paper-j0-logical0-read0-control` | logical0 | `logical0_no_read_control` | `INHERITED_PROTOCOL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_q1.paper-j0-logical0-read0-control |
| `paper_sl_q2.40u.paper-j1-logical1-read` | logical1 | `logical1_read` | `INHERITED_PROTOCOL` | `CURRENT_VALID` | paper_sl_q1.paper-j1-logical1-read |
| `paper_sl_q2.40u.paper-j0-logical0-read` | logical0 | `logical0_read` | `INHERITED_PROTOCOL` | `LOGICAL0_GATE_NOT_TESTED` | paper_sl_q1.paper-j0-logical0-read |
| `paper_sl_q2.40u.paper-j1-logical1-read0-control` | logical1 | `logical1_no_read_control` | `INHERITED_PROTOCOL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_q1.paper-j1-logical1-read0-control |
| `paper_sl_q2.40u.paper-j0-logical0-read0-control` | logical0 | `logical0_no_read_control` | `INHERITED_PROTOCOL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_q1.paper-j0-logical0-read0-control |
| `paper_sl_q3.paper-j1-logical1-read` | logical1 | `logical1_read` | `INHERITED_PROTOCOL` | `CURRENT_VALID` | paper_sl_q2.40u.paper-j1-logical1-read |
| `paper_sl_q3.paper-j0-logical0-read` | logical0 | `logical0_read` | `INHERITED_PROTOCOL` | `LOGICAL0_GATE_NOT_TESTED` | paper_sl_q2.40u.paper-j0-logical0-read |
| `paper_sl_q3.paper-j1-logical1-read0-control` | logical1 | `logical1_no_read_control` | `INHERITED_PROTOCOL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_q2.40u.paper-j1-logical1-read0-control |
| `paper_sl_q3.paper-j0-logical0-read0-control` | logical0 | `logical0_no_read_control` | `INHERITED_PROTOCOL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_q2.40u.paper-j0-logical0-read0-control |
| `paper_sl_q4.paper-j1-logical1-read` | logical1 | `logical1_read` | `INHERITED_PROTOCOL` | `CURRENT_VALID` | paper_sl_q2.40u.paper-j1-logical1-read |
| `paper_sl_q4.paper-j0-logical0-read` | logical0 | `logical0_read` | `INHERITED_PROTOCOL` | `LOGICAL0_GATE_NOT_TESTED` | paper_sl_q2.40u.paper-j0-logical0-read |
| `paper_sl_q4.paper-j1-logical1-read0-control` | logical1 | `logical1_no_read_control` | `INHERITED_PROTOCOL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_q2.40u.paper-j1-logical1-read0-control |
| `paper_sl_q4.paper-j0-logical0-read0-control` | logical0 | `logical0_no_read_control` | `INHERITED_PROTOCOL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_q2.40u.paper-j0-logical0-read0-control |
| `paper_sl_q5.paper-j1-logical1-read` | logical1 | `logical1_read` | `INHERITED_PROTOCOL` | `CURRENT_VALID` | paper_sl_q2.40u.paper-j1-logical1-read |
| `paper_sl_q5.paper-j0-logical0-read` | logical0 | `logical0_read` | `INHERITED_PROTOCOL` | `LOGICAL0_GATE_NOT_TESTED` | paper_sl_q2.40u.paper-j0-logical0-read |
| `paper_sl_q5.paper-j1-logical1-read0-control` | logical1 | `logical1_no_read_control` | `INHERITED_PROTOCOL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_q2.40u.paper-j1-logical1-read0-control |
| `paper_sl_q5.paper-j0-logical0-read0-control` | logical0 | `logical0_no_read_control` | `INHERITED_PROTOCOL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_q2.40u.paper-j0-logical0-read0-control |
| `paper_sl_q6.paper-j1-logical1-read` | logical1 | `logical1_read` | `INHERITED_PROTOCOL` | `CURRENT_VALID` | paper_sl_q2.40u.paper-j1-logical1-read |
| `paper_sl_q6.paper-j0-logical0-read` | logical0 | `logical0_read` | `INHERITED_PROTOCOL` | `LOGICAL0_GATE_NOT_TESTED` | paper_sl_q2.40u.paper-j0-logical0-read |
| `paper_sl_q6.paper-j1-logical1-read0-control` | logical1 | `logical1_no_read_control` | `INHERITED_PROTOCOL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_q2.40u.paper-j1-logical1-read0-control |
| `paper_sl_q6.paper-j0-logical0-read0-control` | logical0 | `logical0_no_read_control` | `INHERITED_PROTOCOL` | `VALID_WITH_RELABELED_CONTROL` | paper_sl_q2.40u.paper-j0-logical0-read0-control |

## Required action

1. 继续使用正式四角色命名。
2. 对 canonical logical0 gate 只使用 `neg-init-pos-read.cir` 或其协议完全一致的后继。
3. 先完成新 Exploration 的 12 ps canonical logical0 correction，再决定 13/14/15 ps。
4. 未完成 ideal replay 的 1/0/0 closure 前，不进入 physical BVM→JSL12→QB。
