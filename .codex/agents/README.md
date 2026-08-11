# JoSIM Codex custom agents

这些是项目级 Custom Agents。调用时选择**角色名**，而不是在临时 spawn 参数中直接指定 Luna：

| 角色 | 模型/推理 | 用途 |
|---|---|---|
| `josim_scout` | Luna / Low | 定位文件、符号、测试与所有权 |
| `josim_explorer` | Luna / Medium | 跟踪执行路径、数据流、依赖 |
| `josim_docs_researcher` | Luna / Medium | 核对版本、API、论文与仓库文档 |
| `josim_tester` | Luna / Medium | 运行授权的最小测试并记录证据 |
| `josim_verifier` | Luna / High | 只读验收与证据一致性检查 |
| `josim_reviewer` | Terra / High | 材料性工程 review / debugging |
| `josim_architect` | Sol / XHigh | 高风险架构、计量和实验设计决策 |

`luna_smoke` 用于可用性测试。新增或修改 `.toml` 后，**新开 Codex thread 或重启 IDE**再调用；已启动会话的 agent-type 注册表不会热加载新角色。

项目根目录 [AGENTS.md](../../AGENTS.md)、[research/WORKFLOW.md](../../research/WORKFLOW.md) 和已签发任务合同优先于任何 agent 提示。Luna/Terra 子代理不得绕过实验、计量或合同边界。
