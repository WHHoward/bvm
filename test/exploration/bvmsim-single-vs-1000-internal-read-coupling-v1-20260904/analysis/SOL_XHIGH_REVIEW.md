# Sol XHigh independent review

审阅角色：`josim_architect`（Sol XHigh）；范围为只读物理、数值和证据边界审阅。
审阅没有修改文件、没有运行 JoSIM 仿真、没有启动后续实验。

## 初始审阅结论

初始结论为 `NEED_REVISION`：无 BLOCKER，但发现四项 MAJOR：

1. centered difference-in-differences 错把每个窗口自己的 median 当作
   PRE_READ1 中心；
2. READ1 起点的首个阈值样本不能直接命名为 response onset；
3. 报告遗漏了 commanded-0 victim 的 JS1/JS2 大幅 local phase-area 活动；
4. READ0 位于 WRITE1 之前，且没有 WRITE1 后 state-matched READ=0/no-read
   control，`1000-0000` 不能作为纯 READ 因果对照。

另有两项 MINOR：串联支路电流可由已有观测推导，不应与 `R_S || L_S3` 并联
分流缺口混列；输入父实验的运行元数据没有全部复制到本任务 provenance。

## 修正状态

- 已把所有 centered READ/early-response 指标固定为同一 `PRE_READ1` median。
- 已将 onset 改为“窗口内首个持续阈值样本”，并增加
  `PRE_EXISTING_ACTIVITY_LEFT_CENSORED` 状态；它不再被解释为传播延迟。
- 已在报告中加入 BVM2–4 的 JS1/JS2 READ1 phase delta 与 `Vdt/Phi0` 对照，
  并明确这些不是 SFQ count。
- 已在 metrics、experiment 语义和报告中写明 READ0/WRITE1 的因果边界。
- 已把真正的 `OBSERVABILITY_GAP` 限定为 `I(R_S)` 与 `I(L_S3)` 的并联分流；
  `I(L_S1)`、`I(L_S2)`、`I(R_SL)` 列为已确认串联关系下的可推导量。

## 保留的独立意见

在当前 historical JM2-connected、0.1 ps、固定 shared-sensing fixture 中，
改变 BVM1 state command 与 BVM2–4 的 READ-window LSL/SL 以及强烈的局部
R-loop phase-area 响应相关，并与 shared-network back-action/cross-loading
相容；但直接电流路径、唯一传播机制、canonical BVM 普适性和 SFQ 数量均未被
证明。最终 gate 仍为 `AWAITING_USER_REVIEW`。

## Post-fix confirmation

同一审阅线程在修正后的当前工作区再次检查并返回 `OK`：四项 MAJOR 均已落地，
无残留必须修正项；centered LSL 指标、左删失阈值语义、victim JS1/JS2 披露、
READ0/WRITE1 因果边界、raw unchanged、18 个 plot 的 `returncode=0` 以及
`AWAITING_USER_REVIEW/STOP` 均再次确认。该确认仍是只读的，没有修改文件或运行
JoSIM。
