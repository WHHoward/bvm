# BVM Source Characterization — preflight

> 状态：**PRE-FLIGHT ONLY（2026-08-13）**。这不是已签发 task、不是
> `INTERFACE_GATE_V1`、不授权改网表或运行 JoSIM，也不改变任何 BQ、DCSFQ_BVM
> 或 `published_qb` 的 reproduction/provenance 状态。

## 目的与边界

下一项科学工作应先建立 BVM 在已声明状态和负载下的**source-side facts**：读激励
如何影响存储状态、source port 的电流/电压波形，以及这些观察在匹配控制和局部数值
收敛下是否可复现。它不判断 receiver 是否接收，不比较 BQ 与 DCSFQ_BVM，不定义
“恰好一个事件”，也不建立系统 Gate。

研究问题（待正式合同预注册）：

> 在固定 BVM 模型、初态、读激励和显式负载集合下，read0/read1 与匹配零输入控制的
> source-port 观察量及存储状态保持量分别是什么；哪些量仍因 BVM direct P/V mapping、
> 全局容差或初态证据不足而只能记为 `UNKNOWN` / `INCONCLUSIVE`？

该任务应标为 `CALIBRATION + CRITICAL + FROZEN`：它生成后续 receiver/interface
工作所需的受控 source facts，但不产生 candidate 或 physical Gate verdict。

## 已接受的输入与明确未知项

- 计量语义：[`METRIC_SPEC_V2.md`](METRIC_SPEC_V2.md) v2.0.0，尤其 raw rad→turns、
  半开窗口、matched control、activity-only、same-JJ P/V、实际时间积分和三步收敛。
- 历史 source 线索只作设计输入：P2 的读扰动/擦除观察、BVM 负载扫描和 M10 endpoint
  reconstruction。它们不是本任务的 source characterization 结论。
- M11B 的 `bvm_source_output` 目前是 `LEGACY_ONLY` / `NOT_ATTEMPTED`；完整 source
  characterization 是其明确的 next discriminator。
- BVM/BQ junction mapping 仍是 `UNKNOWN`。任何涉及 JM1/JM2 的 phase-area cross-check
  必须在新 run 中输出直接 `P(B...)` 与同一结的直接 `V(B...)`，并声明端点与方向；
  不得以 SL/WL/BL/SE 对地电压替代结电压。
- 全局 integer、phase-area residual、platform stability、BVM drift、amplitude、jitter
  接受容差仍 `UNFROZEN`。缺少 task-local、预注册且适用的容差时，分类为
  `INCONCLUSIVE`，不能凭看图写 PASS/FAIL。

## 正式 task 签发前必须固定的项目

1. **对象与网表闭包**：选择唯一 BVM testbench 和唯一 BVM cell/model/include 闭包；
   记录 Git HEAD、dirty snapshot、`build/josim-cli` 版本与 SHA-256。若需要插入直接
   JJ 探针，先在合同中限定 netlist/testbench 修改路径。
2. **状态初始化**：以可复放且可观察的 procedure 形成 read0/read1 初态；把初态建立
   本身与读出分开记录。若初态不能证明，停止为 `BLOCKED`，不把旧 CSV 标签当状态事实。
3. **输入与对照**：每个 read stimulus 有同网表/模型/偏置/负载/步长/窗口的零输入
   control；若要比较状态，则 read0 与 read1 除初态外保持一致。周期源只能作为
   `periodic_regression`，source causality 优先单次 PWL。
4. **负载矩阵**：在合同中预先列出有限、物理上有意义的 source-port loads（含已有
   baseline load）；负载是独立自变量，不得在看到输出后扩扫。记录每个 load 的端口
   定义、极性和测量节点。
5. **观测量与窗口**：预先列出 source-port `I/V`、pulse timing/width 的描述性量、
   storage pre/post observables、以及适用时的 direct same-JJ `Δφ/(2π)` / `∫Vdt/Φ0`。
   每项注册 pre/activity/post 半开窗口、正方向和 `NOT_APPLICABLE` 理由。
6. **数值 procedure**：预先声明 nominal、代表性 low/high load、最接近边界或无响应点
   的 0.1/0.05/0.025 ps ladder、比较量、task-local bands、最大深度及 stop rule。此
   procedure 不能把 M8 canonical-JTL fixture bands 迁移为 BVM 全局容差。
7. **产物与审计**：每次运行使用新 run ID，保存网表/include/model/input snapshot、raw
   CSV、stdout/stderr、manifest、hash、analysis 与 metric-spec hash。失败和 `INVALID`
   raw 同样保留，不覆盖历史 P2/BASELINE 数据。

## 预注册判定语言

- `VALID`：运行产物、闭包、原始数据与指定测量合同完整；它不等于 source 已通过接口。
- `INCONCLUSIVE`：源端观察量存在，但控制、状态、same-JJ mapping、稳定平台或数值分类
  不能支撑预注册问题。
- `INVALID`：缺列、NaN/Inf、非单调时间、solver/运行错误、缺结束稳定窗、闭包或 hash
  断裂。
- 本 task 不注册 candidate `PASS/FAIL`。任何 interface acceptance、read1/read0
  system logic、下游 JTL reception 或 route selection 都留给后续独立合同。

## 签发阻断条件

在下列任一项未明确前，不签发或运行：唯一 testbench/闭包、初态 procedure、有限负载
矩阵、direct-JJ probe strategy、匹配 controls、窗口/方向表、收敛 ladder、run ID 与
不可覆盖输出路径。若这些信息只能靠尝试调参或同时改变多个变量得到，先签发
exploratory characterization-design task，而非执行 calibration run。
