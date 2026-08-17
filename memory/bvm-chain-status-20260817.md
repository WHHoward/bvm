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

**MAINT-004/005（2026-08-17 20:28 更新）**：MAINT-004 因**冻结输入冲突** BLOCKED（scope.hash_paths 与 read_paths 全同，冻结了全部 writable deliverables，执行后 verify-task 必失败；§3.1 停止升级，BLOCKED receipt + mailbox claude-20260817-201202 上报）。Codex 签发 MAINT-005（corrected scope；hash_paths 收敛为 AGENTS/HANDOVER/METRIC_SPEC），A01 的链条与 40 项回归均可机械验证。**但 C01 = REWORK_REQUIRED，未接受**：snapshot 校验以删除 `issuer_snapshot_commit` 后的结构相等替代要求的 byte-identical request binding；handoff.py 仍未逐项重算 bundle entry 的安全路径、SHA-256 与 bytes。正式裁决：`research/tasks/JH-20260817-WORKFLOW-MAINT-005/audits/C01/verdict.yaml`。等待用户裁决可满足 byte-identical 约束的非自引用 v1 表示；不启动科学任务。

**硬约束**：所有交付物在**工作区未提交**（合同 commit:false）；不触碰 S0/S1/S2 frozen evidence；build/josim-cli 唯一（SHA 48655cb3…）；mailbox 检查必须**全量**（用户 2026-08-17 两次强调）。
