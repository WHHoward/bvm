# PHASE B preflight and scope

本实验只执行六个预注册状态：`0000`、`1000`、`0100`、`0010`、`0001`、`1111`。
它消费 PHASE A 的 `INFRA_REGRESSION_PASS`，但不改变 PHASE A 或历史
BVMSim 证据。

固定内容：历史 `BVMSim/test_bvm_mixed_0.cir`、历史 BVM/QB/JTL、RJ1=12 Ω、
RJ2=4 Ω、QB bias=250 µA、六级 JTL、10 Ω 终端、`.tran 0.1p 200p 45p`。
本阶段只增加观测探针，并把每个状态的 deck 直接写到
`runs/<state>/deck.cir`，JoSIM 直接输出到同目录的 `raw.csv`。

PHASE B 不做 16-state 扫描、参数优化、canonical BVM 替换、timestep sweep
或自动 follow-up。所有 raw、run.log 和 metadata 在创建后视为不可覆盖。

状态判别是 task-local 的观测规则：用 WRITE1 期间各 BVM 的 `JM1` phase
displacement 的符号和预读窗口稳定性报告“observed state basis”。它不会把
该规则升级为普适存储机制证明。
