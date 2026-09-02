---
name: josim-handoff
description: Issue, execute, verify, or audit an explicit file-backed Codex–Claude handoff for JoSIM/BVM. Do not load for an ordinary user→Codex Quick.
---

# JoSIM Codex↔Claude 任务交接

## 触发边界

普通用户→Codex 的 Compact Quick 不使用本 skill、不要求 mailbox ritual，也不
创建 ACK/receipt。仅当请求明确涉及 Codex↔Claude 合同、ACK/receipt、正式委派
审计、stand-in 或等价多代理交接时加载。

## v1 冻结

josim-handoff/v1 的协议、schema、签名/哈希、路径权限和历史任务语义保持
冻结。完整机械流程见 references/handoff-protocol.md；本入口只做路由提醒，
不复制协议正文，也不把 handoff 变成普通实验的前置门槛。

## 最小流程

1. 读取 AGENTS.md、research/CLAUDE_EXECUTOR.md、活动 request 和
   contracts.read_first。
2. 合同执行者先验证有效 ISSUED request，编辑前 ACK；只写
   scope.write_paths，保留 raw/失败历史，不覆盖 attempt。
3. 执行后写绑定 receipt；执行者不签发最终物理 Gate。
4. Codex 独立验证 request、ACK、receipt、diff、日志、哈希、测试和科学证据，
   分开裁决 artifact、physical verdict 和 audit disposition。
5. 只有接受的 audit 才能上推 todo、HANDOVER 或论文层文档。

Mailbox 只是显式 handoff 的通知/索引渠道，不是科学或合同权威；普通 Quick
无需查信箱。需要相位、SFQ、JTL 或 Gate 判断时另加 josim-evidence-audit，
修改/运行 .cir 时另加 josim-experiment。
