# JM2-connected single-BVM A/B Quick — result brief

- **comparison coverage**：保留原有 8 张 comparison，并新增 6 张 JTL-load
  comparison；最终矩阵为 direct=6、JTL=8、合计 14。新增页面包含 S0/S1
  的 BVM internal、sensing 和 QB，且沿用旧 single-BVM 图的布局与顺序。
- **范围**：只改变 historical BVM 的 `L_M2` 第二节点 `4→3`；四个 single-BVM 新 run；不使用 canonical BVM。
- **artifact**：preflight=`ARTIFACT_VALID`，all runs=`True`。
- **可视化**：严格复用 corrected single-BVM 的 `scripts/josim-plot2.py`、现有命名、signal order、`sep_comb + dark + 2pi`；旧图与新图可直接并排比较。
- **JM2 READ 观察**：S0 direct/JTL 的 Δphase 为 `-0.002486` / `-0.002457` turns；S1 direct/JTL 为 `0.151472` / `0.134874` turns。这里的 turns 是 rad/(2π) 的局部净相位位移，不是 SFQ count。
- **QB 负载观察**：S1 direct 与 JTL 的 BJ2 RESPONSE Δphase/V-area 分别约 `1.999431`/`1.999418` 和 `0.999168`/`0.999151` turns；这是固定 fixture 的 load-sensitive observation。
- **观察边界**：JM2 的相位/面积、电压/电流、BVM sensing、QB 和 JTL 数据均已分层保存；没有把局部 phase displacement 升级为 SFQ event 或系统 Gate。
- **历史限制**：A-side immutable raw 没有 `L_M1/L_M2/L_M3/L_PM`，因此未伪造这些 A/B 对照。
- **状态**：`AWAITING_USER_REVIEW`；未授权任何自动后续实验。
