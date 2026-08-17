---
name: bvm-chain-status-20260817
description: BVM S0-S2 + workflow-maintenance 全链状态与唯一待决事项（2026-08-17 会话收尾快照）
metadata: 
  node_type: memory
  type: project
  originSessionId: 0a6c3d20-0d5b-452e-a234-939c2e31e4bd
  modified: 2026-08-17T12:28:12.000Z
---

# BVM 链状态快照（2026-08-17，会话收尾）

**全部权威裁决（Codex）**：
- S0：VALID + INCONCLUSIVE（C02，0.85 ps > 0.5 ps band）
- S1（12-run 收敛 ladder）：**C01 ACCEPTED** = VALID + numerical INCONCLUSIVE（6 项 pair 失败；readiness 通过；S1 evidence 经 SEAL-002/003/004 封存，可提交）
- S2（16-run 负载表征，R_LD={1,12,25,50}）：**C02 ACCEPTED** = VALID + readiness NOT_MET（JM2 pre p2p 0.058 rad > 0.020 band；S2 预注册 init PWL 比 S1 早 1 ps ramp）+ INCONCLUSIVE + numerical NOT_APPLICABLE；S2-SEAL-001 封存 76 文件
- MAINT-001：v1 工具链包（quantitative-analysis-spec/独立 verifier/确定性 renderer/evidence bundle）实现完成，scope 缺陷（read_paths 哈希矛盾）由 002 修复
- MAINT-002：A01 语义修复（scope.hash_paths / issuer_snapshot_commit / evidence_bundle 校验）+ A02 whitespace 修复；Copilot PASS

**已解决（2026-08-17 19:07 更新）**：Codex 以 MAINT-003 取代 002 修复多 attempt 聚合缺陷（002 A02 单路径 D3 冲突记为 HISTORICAL_PROTOCOL_MULTI_ATTEMPT_DEFECT）。MAINT-003 A01 已交付（request SHA-256 4426b221…，ACK 5f861284…）：handoff.py verify-task 对 deliverable/acceptance 覆盖改 task-wide union（`_task_deliverable_errors`/`_task_acceptance_errors`；per-receipt 哈希链/scope/artifact 与 duplicate/unknown-ID 校验保留；单 attempt 行为不变）；test_handoff.py 15/15（pytest+unittest 双模式，新增 6 项 MultiAttemptAggregationTests，`__main__` 块移至文件尾）；evidence-inventory 封存 13 个 001/002 血缘文件；协议文档同步（handoff-protocol §7、WORKFLOW §8.5、CLAUDE_EXECUTOR、receipt 模板）；verify-task VERIFIED；REVIEW_REQUEST 已发 Copilot（claude-20260817-190650）、INFO 已发 Codex（claude-20260817-190658）。001/002 保持历史只读。

**MAINT-004/005/006（2026-08-17 21:03 更新）**：MAINT-004 因**冻结输入冲突** BLOCKED（hash_paths 冻结全部 writable deliverables）。MAINT-005（corrected scope）A01 交付但 **C01 = REWORK_REQUIRED**（3 项：snapshot 规范化比较非 byte-identical、bundle 缺逐项重算、docstring 符号），rework 未授权（byte-identity 自引用需用户批准非自引用表示）。用户批准后 Codex 签发 **MAINT-006**（EXTERNAL_ATTESTATION 模式，execution snapshot S=c67e85ee）：request 不含快照 SHA（消除自引用），issuer 创建 issuer-snapshot.yaml + 独立封签绑定 S 与 request/signature/scope 哈希，ACK/receipt 绑定 attestation 且 observed=S，verifier 从 S 读 3 文件**逐字节比对**；bundle 逐项验证（path/SHA-256/bytes/duplicate/receipt 禁止）；endpoint-VI 改 Decimal 精确 token + per-token 拟合 + 冻结 descriptors（AC5 对抗 fixture：相反残差平均抵消被拒）。50/50 测试全绿，verify-task **VERIFIED**；REVIEW_REQUEST 已发 Copilot（claude-20260817-210226）。等 Copilot review + Codex 审计。

**硬约束**：所有交付物在**工作区未提交**（合同 commit:false）；不触碰 S0/S1/S2 frozen evidence；build/josim-cli 唯一（SHA 48655cb3…）；mailbox 检查必须**全量**（用户 2026-08-17 两次强调）。
