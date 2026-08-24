# BVM_READ_SEMANTICS_AUDIT_AND_JSL_WIDTH_BRACKET_V1

## Verdict

`IDEAL_REPLAY_SELECTIVE_ONE_SFQ_CANDIDATE`；首个 1/0/0 width = **13 ps**。

## Pulse quantization class and execution disposition

`complete_event_units` 仍是同段、同 JJ 的低层整数单位；`pulse_quantization_class` 单独判断 clean one-SFQ candidate、subthreshold、overdrive、multi-event 和 free-running。
`EARLY_STOP_EXECUTION_DEVIATION`：13 ps 是已注册的首个选择性 candidate；更宽的 width 只是 candidate 之后已执行的 bounded observation，不具有 operating-point 选择权。

本 Exploration 先修正 READ 语义，再对 canonical BVM → external 12-JSL → frozen scaled QB 做 12/13/14/15 ps local bracket。理想 replay 只消费物理 JSL 的实际 `I(B_LD1)(t)`，没有整形、保持、归一化或重采样；本轮没有 physical BVM→JSL→QB 联合连接。

## Observed

- 12 ps corrected canonical logical0 使用负 WL+BL initialization 与正 WL+SE READ；QB BJL2 最大同向段仍约 `-0.02549 turn`，zero complete event。
- 12 ps canonical logical1 的 BJL2 最大同向段约 `0.975402 turn`，同段 voltage area 约 `0.975411 Phi0`，仍未完整。
- 13 ps 首次出现 read1 BJL2 完整同向段；read0 与两个 no-READ controls 没有完整 event。
- 14/15 ps 也在本次已注册 bracket 中完成记录；13 ps 已满足 early-stop candidate 条件，14/15 仅作已执行的 bounded post-candidate observations，不用于继续选择。

## QB replay result

| width | role | BJL2 activity p2p (turn) | largest monotonic segment (turn) | same-segment area (Phi0) | complete units | legacy classification | pulse quantization class |
|---:|---|---:|---:|---:|---:|---|---|
| 12 | `logical1_read` | 1.09398 | 0.975402 | 0.975411 | 0 | `NO_COMPLETE_EVENT` | `SUBTHRESHOLD` |
| 12 | `logical0_read` | 0.0449086 | -0.0254939 | -0.0254963 | 0 | `NO_COMPLETE_EVENT` | `SUBTHRESHOLD` |
| 12 | `logical1_no_read_control` | 2.5051e-05 | -2.5051e-05 | -2.5055e-05 | 0 | `NO_COMPLETE_EVENT` | `SUBTHRESHOLD` |
| 12 | `logical0_no_read_control` | 2.50351e-05 | 2.50351e-05 | 2.50412e-05 | 0 | `NO_COMPLETE_EVENT` | `SUBTHRESHOLD` |
| 13 | `logical1_read` | 1.13461 | 1.01603 | 1.01604 | 1 | `EXACTLY_ONE` | `CLEAN_ONE_SFQ_CANDIDATE` |
| 13 | `logical0_read` | 0.0455457 | -0.0257304 | -0.0257325 | 0 | `NO_COMPLETE_EVENT` | `SUBTHRESHOLD` |
| 13 | `logical1_no_read_control` | 2.5051e-05 | -2.5051e-05 | -2.5055e-05 | 0 | `NO_COMPLETE_EVENT` | `SUBTHRESHOLD` |
| 13 | `logical0_no_read_control` | 2.50351e-05 | 2.50351e-05 | 2.50412e-05 | 0 | `NO_COMPLETE_EVENT` | `SUBTHRESHOLD` |
| 14 | `logical1_read` | 1.17928 | 1.06071 | 1.06071 | 1 | `EXACTLY_ONE` | `CLEAN_ONE_SFQ_CANDIDATE` |
| 14 | `logical0_read` | 0.0443489 | -0.0254939 | -0.0254963 | 0 | `NO_COMPLETE_EVENT` | `SUBTHRESHOLD` |
| 14 | `logical1_no_read_control` | 2.5051e-05 | -2.5051e-05 | -2.5055e-05 | 0 | `NO_COMPLETE_EVENT` | `SUBTHRESHOLD` |
| 14 | `logical0_no_read_control` | 2.50351e-05 | 2.50351e-05 | 2.50412e-05 | 0 | `NO_COMPLETE_EVENT` | `SUBTHRESHOLD` |
| 15 | `logical1_read` | 2.02031 | 1.90044 | 1.90045 | 1 | `EXACTLY_ONE` | `OVERDRIVEN_ONE_PLUS_LARGE_RESIDUAL` |
| 15 | `logical0_read` | 0.0439537 | -0.0254939 | -0.0254963 | 0 | `NO_COMPLETE_EVENT` | `SUBTHRESHOLD` |
| 15 | `logical1_no_read_control` | 2.5051e-05 | -2.5051e-05 | -2.5055e-05 | 0 | `NO_COMPLETE_EVENT` | `SUBTHRESHOLD` |
| 15 | `logical0_no_read_control` | 2.50351e-05 | 2.50351e-05 | 2.50412e-05 | 0 | `NO_COMPLETE_EVENT` | `SUBTHRESHOLD` |

## JSL source current

| width | role | min (µA) | max (µA) | positive area (µA·ps) | negative area (µA·ps) | signed area (µA·ps) |
|---:|---|---:|---:|---:|---:|---:|
| 12 | `logical1_read` | -21.0247 | 79.0668 | 755.714 | -64.8623 | 690.852 |
| 12 | `logical0_read` | -21.8384 | 19.1096 | 68.5456 | -68.2247 | 0.320849 |
| 13 | `logical1_read` | -14.4918 | 79.0668 | 899.297 | -36.0987 | 863.198 |
| 13 | `logical0_read` | -21.4884 | 19.1096 | 59.828 | -60.064 | -0.235978 |
| 14 | `logical1_read` | -30.5261 | 79.0668 | 934.044 | -75.2535 | 858.791 |
| 14 | `logical0_read` | -20.9267 | 19.1096 | 67.275 | -66.8535 | 0.421518 |
| 15 | `logical1_read` | -21.7888 | 79.0668 | 921.569 | -60.5464 | 861.023 |
| 15 | `logical0_read` | -19.9754 | 19.1096 | 61.9986 | -62.4024 | -0.403858 |

## Derived

- 所有 reported event units 都来自同一 BJL2、同一 continuous monotonic segment、同段 direct voltage area 与 post bounded/retrap 检查；total phase range、I>Ic、voltage peak 没有单独计数权力。
- 13 ps 的 read1 segment/area 均超过 1，且 post window 没有第二个 complete event；read0/control 保持 zero。
- JSL source raw 中的 12 个 B_LD junction 仍需由 source metrics 一起检查；本分析不把 source current peak 直接等价成 QB event。

## Inference

- READ protocol correction 后，旧 PAPER-SL logical0 gate provenance 被隔离；在 corrected canonical logical0 下，13 ps 选择性闭合先于 14/15 ps。
- 这支持“width margin 是本 frozen replay fixture 的限制因素之一”，但不等于 physical BVM→JSL→QB 已闭合。

## Unknown

- 尚未测试 physical BVM→12JSL→QB 的联合 load-line/back-action；不能把 ideal replay candidate 当作系统级 SFQ delivery。
- 尚未连接 JTL/T1。

## Physical-cascade boundary

13 ps ideal replay 已达到 1/0/0 candidate，因此下一轮可以另开 preregistered physical BVM→JSL12→QB；本轮不执行。
