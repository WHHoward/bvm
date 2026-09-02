# Stage A 结果摘要

## 1. What changed

仅将 BVMSim 活动 QB 封装迁移到 `circuits/qb/bq_cell_bvmsim_v1.cir`，子电路接口为 `BQ_BVMSIM_V1 IN OUT BIAS`；原 QB 内部 250-uA bias 以完全相同的 `I_QB_BIAS 0 QB_BIAS pwl(0 0 1p 250u)` 外置。

## 2. What held fixed

Stage A 保持 BVMSim 的 4-BVM、累积 sensing-line、BVMout、原始刺激、QB 元件值、六级原始 `BVMSim/library_josim/jtl2.cir`、10-ohm 终端负载和 200-ps 停止时间。BVMSim BVM 不是 canonical BVM authority：BVMSim 的 `R_JM1=8 Ω`，canonical `circuits/bvm/bvm_cell.cir` 为 `6 Ω`；本阶段没有替换它。

## 3. Why tested

区分真实分离、重捕获的多 SFQ 事件与一条连续多圈 running phase trajectory；全窗口约 4 turns 不会被自动报告为 4 个 SFQ。

## 4. What happened

- M0 迁移等价性为 PASS；共享网格=True，未插值。
- S1 BJ2 READ0：complete segments=0，clean separated=0；READ1：complete segments=1，clean separated=0。
- BJ2 READ1 端点相位位移=4.999188001682507 turns；这是相位轨迹量，不单独等于 SFQ 数。
- READ1 transport cell-minimum clean counts：BJ2=0, JTL1=0, JTL2=0, JTL3=1, JTL4=1, JTL5=1, JTL6=2。
- 主分类=CONTINUOUS_MULTI_TURN_RUNNING_STATE，Quick=QUICK_OPPOSITE；额外/自发活动按窗口列在 metrics.json。
- KCL 已计算并保存于 metrics.json。

## 5. Physical meaning

在本 BVMSim exploratory fixture 和本阶段 strict task-local 口径下，当前主分类是 `CONTINUOUS_MULTI_TURN_RUNNING_STATE`（Quick `QUICK_OPPOSITE`）。它只描述本次仿真的局部相位/同结电压面积与 JTL 逐级关系；它不把局部相位圈直接升级为闭环 fluxoid 或硬件 SFQ 计数。

## 6. What it does NOT prove

不证明 canonical BVM compatibility、single-BVM compatibility、一个 BVM contribution 对应一个 SFQ、timestep convergence、process margin、T1 compatibility、paper mechanism identity 或唯一 QB operating mechanism；也不是 Formal PASS。

## 7. Current status

`AWAITING_USER_REVIEW`。本阶段没有自动开始 Stage B，前序 replay Quick 的 human gate 也未被本授权改写。

## 8. Possible next options (not executed)

- 用户先审阅本阶段 raw、metrics、结果摘要和关键图。
- 如确有必要，另行授权并预注册 `CANONICAL_BVM_TO_BVMSIM_QB_QUICK_V1`。
- 另行审查 BVMSim QB 的局部工作点和机制；本阶段未做参数扫掠。
