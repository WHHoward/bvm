---
name: feedback-interpretation-overreach
description: 我在 BVM 物理解读上反复过度断言；算术可靠、interpretation 层不可靠，需强制自查
metadata: 
  node_type: memory
  type: feedback
  originSessionId: abeab4c9-4a8d-4023-9606-8193892acd7a
  modified: 2026-09-17T07:09:11.297Z
---

2026-09-17 会话中，用户在 BVM→QB 映射讨论里连续纠正了我 9 处实质错误。算术层（raw 重算、比值、字节比对）全部经受住复核；**全部错误都发生在解读层**。

错误清单（供识别模式）：
1. 断言"QB 不是量化器、是阈值+runaway"——未先算 ∫V dt/Φ₀（实际精确整数 1/2/4/4）。
2. 断言"病根在源侧、不在接收器"——把闭环可观测量 I(Lin) 当成 source-only 量。
3. 断言"输出 3 不存在"——与我自己上一条引用的 LS3 0.3 ps replay（N3→3）自相矛盾。
4. 拓扑误读：把 `R_S 6 10` 与 `L_S3 6 10` 当成串联输出阻抗，实际是同节点对并联 bridge；真实输出路径是 node10→L_PSL→R_SL→L_SL→SL。据此给出的"把 R_S 抬 3–5×"建议会破坏 R-loop damping。
5. 参数误读：BJs 用 area=0.5，实际 canonical 用 area=4，电容算成 0.035 pF（实为 0.28 pF）。
6. 编造物理律：声称"大电感 → ∫I dt = 固定 Q_quantum → 按构造线性"。JJ slip 只有 ∫V dt = Φ₀，没有该规律。项目自带的 josim-evidence-audit skill 明确写了这一条，我加载了却仍违反。
7. 从相关性断言因果："LS3 delay 只是削弱幅度"——未用已有的 branch 对照（R_S-branch delay 无效、L_S3-branch delay 才 4→3）。
8. 断言"BVM 结构性多级锁定"——被仓库里 6 天前就存在的 passive-capture 实验证伪（隔离源 per-cell JS1 恒定 2.996 turns，闭环才变 3.05/7.05）。我没搜"同一 fixture 换下游边界"这一类实验。
9. 搭出"两个可分离缺陷"框架——实际是拿两个**不同 QB**（RJ2=12 vs canonical）当同一系统分解，比较无效。

**Why:** 每个错误版本都是"更有意思"的那个故事；正确的版本每次都更平淡（偏置而非非线性、单 fixture、未被判别）。我有偏好叙事完整性的偏差。而且我在会话开始时加载了 `reviewer-adversarial` skill（其核心正是 overclaim / stale-artifact / coupling 探针），却从未把它用在自己的结论上——纠错全部来自外部（用户/GPT），没有一次是自查出来的。

**How to apply:**
1. 提出任何 mechanism claim 前，先说出**能判别它的那个测量**；没做就把结论标成 hypothesis，不写"病根/结构性/固有"这类词。
2. 建议任何参数改动前，先读**真实网表行与 model card**（不靠记忆）。
3. 声称"X 是子系统 S 的固有行为"前，必须先搜**换过 S 边界的实验**。
4. 每个定量断言在同句里带 raw 路径 + 窗口 + 列名。
5. 发出结论前，用 reviewer-adversarial 的探针自查一遍自己的草稿（尤其 overclaim 与 coupling）。
6. 数据不判别时写"未被判别"，不要挑更有趣的那支。

相关：[[feedback-trust-and-advice]]、[[bvm-chain-status-20260817]]、[[strictly-follow-repo-specs]]
