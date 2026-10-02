# SkillNet-S1 · Final Delivery Report（2026-10-02）

> 当前事实基线：HEAD `5a25830` · live 库 **98 技能 / 41 领域 / 200 关系边 / 23 演化**（`/api/health` 实时）
> 测试：pytest **34/34 ×3 连续全绿** · verify **31/31** · selfcheck **18/18** · 套件 2.9s（零真实 API 依赖）

---

## 1. 一句话最终定位

**SkillNet-S1 是 Agent 的技能运维层**：把 Agent 的能力作为资产，完成「发现 → 选择 → 关系编排 → 真实执行 → 修复 → 程序化验收 → 产物 → 反馈 → 进化」的完整生命周期，全过程可追溯。

## 2. 相比 Original 强在哪里（Before → Final）

| 维度 | Original | Final |
|---|---|---|
| 首页 | 静态汇报页 | Hero 产品舞台 + 真实数据技能星图（可交互力导向） |
| 运行体验 | 跳转后台看文本日志 | 本页 Live Run：星图点亮 → 收束成 DAG → 节点状态环 → 产物流动 → Run Summary |
| 执行语义 | plan 线性链，编排图仅展示 | **编排 workflow = 权威执行图**，真并行调度 + 失败阻断 + 关键路径 |
| 失败处理 | 失败被掩盖或误报成功 | 修复后成功（try=3 真实 E2E）、PARTIAL/COMPLETED 语义严格、预算超限不被覆盖 |
| 评估 | 51 技能时代的旧实验 | 当前库 manifest 基准（含 library_hash/git_commit/dataset_hash）+ 补回/噪声量化 |
| 工程质量 | 测试少且污染真实 LLM | 34 项确定性测试（不联网），每个生产 bug 带 regression test |

## 3. 五个 Moment 现状

| Moment | 状态 | 证据 |
|---|---|---|
| 1 Skill Network Activation | ✅ | 检索事件 → HeroNet.highlight（真实 selected） |
| 2 Network → DAG | ✅ | dag.ready → dagify 平滑收束（同一批节点，非 fade 切换） |
| 3 Real Execution + Repair | ✅ | E2E `b5bf6a46-130540`：step3 try=3 修复后成功；状态环/产物流 |
| 4 Evidence | ⚠️ 部分 | L1/L2 检查 + 产物 hash 有；L3 语义评审 UI 与 deep-link 未做 |
| 5 Feedback / Evolution | ⚠️ 部分 | 星图进化环 + /api/evolve 闭环有；Candidate→审批 UI 未串进 Live Run |

## 4. Runtime 最终架构

```text
Orchestrator workflow（技能依赖边，权威）
  → build_steps 映射为 RunStep DAG（无入边保守串行兜底 + 环防御）
  → _run_steps_graph 图调度器（线程池并行 / context 隔离账本 / max_concurrency 记录）
  → run_step（代码生成 → 语法预检 → 沙箱真实执行 → L1/L2 检查 → 产物登记 + 跨步传播）
  → 失败阻断下游 / 预算超限停派发 / finalize_status 唯一终态权威
```

## 5. Performance

- E2E（3 步真实任务）：52–153s，其中 LLM 等待 ≈81%（execution 子阶段拆分可见）
- TTFE <100ms（run.started 即达）；关键路径自动计算（失败步计入）
- 测试套件 28s → 2.9s（8×）

## 6. Evaluation（Current，manifest 锁定）

**Experiment A — Retrieval**（Recall@5，98 技能/200 边库）：
dev bm25 0.725 → hybrid 0.742 → **fabric 0.825**；heldout bm25 0.653 → **hybrid 0.708** → fabric 0.667。
负面结果如实：fabric 纯图扩展补回中噪声占 84–95%（dev 37/44、heldout 18/19）——佐证 LLM 重排与置信度分流的必要性；heldout 上 fabric 不敌 hybrid，不包装。

**Experiment B — Skill Usage**（5 dev 任务 × 3 模式 × 真实 deepseek 执行，skill_usage_20261002_135229.json）：

| 模式 | 成功率 | 平均尝试 | 修复率 | 验收通过 | 成本/run | 时延 |
|---|---|---|---|---|---|---|
| none | 100% | 1.4 | 40% | 17.8 | ¥0.143 | 14.7s |
| prompt | 100% | **1.0** | **0%** | **20.2** | ¥0.157 | **14.3s** |
| contract | 100% | 1.2 | 20% | 17.6 | ¥0.200 | 17.6s |

**负面结果如实（天花板效应）**：在简单单步 dev 任务上三种模式全部成功，
contract 模式成本最高（+40% vs none）、速度最慢，本样本**不支持「契约模式更好」**——
其价值主张（陷阱规避、逐条验收）需要更难任务/heldout 验证。
历史实验（51 技能时代，contract 信息量 2217 vs 1285/1510 字）标 **Historical**，不冒充当前结论。

*Historical*：51 技能/62 边与 90/162 时代的实验数字仅作历史参照。

## 7. Tests

pytest 34/34 ×3 · verify 31/31 · selfcheck 18/18；含 DAG 集成测试（A→(B,C)→D 并行/产物流/失败全阻断）、账本隔离、终态保护、产物传播 cwd、Windows 文件锁重试。

## 8. Visual

截图包 `out/final_shots/`（1920/1440/1280/1024/390 + graph + dashboard）。
高级浅色科技产品 + 深色沉浸星图 + 中文产品语言，已成立。

## 9. Known Limitations（真实存在）

1. Experiment B/C/D（Skill Usage、Evolution、LinUCB 显著性）**未在当前 98 库重跑**——评估短板的最大项。
2. L3 语义评审仍是同模型自评（已明示为"语义评审"非客观验证）；异模型 judge 未接。
3. Evidence deep-link（点击证据跳转 Artifact 对应行）未实现。
4. Evolution Candidate → 审批流 UI 未串进 Live Run 叙事。
5. 结构化日志（run_id/step_id/attempt 字段化）未做，仍靠文本日志。
6. 多 Run 并发 smoke test 未自动化（ledger 隔离有单测，但两 Run 同时提交的端到端未验证）。
7. briefing 七阶段演示的阶段播放节奏是前端 tick 排程（数据真实来自 /api/demo，仅展示节奏非事件驱动）——Live Run 主路径已全事件驱动。
8. dashboard 组件仍有默认表格感，未完全对齐 Hero 的组件质感。

## 10. Final Gate Scores（Evidence-driven）

| Gate | 分数 | 依据 / 差距 |
|---|---|---|
| Visual | **88** | 截图包成立；组件一致性与获奖级差距（dashboard/run 未完全对齐 Hero 质感） |
| Runtime | **90** | DAG=Runtime 已证；缺结构化日志、并发 smoke、cancel×DAG 复验 |
| Evaluation | **82** | A/B 两实验已在当前库落地（含负面结果）；C/D 未跑、judge 独立性未解决、B 样本仅 n=5 单步任务 |
| Engineering | **86** | 34×3 全绿零联网；缺结构化日志与并发 smoke |
| Demo | **82** | Moment 1–3 极强；Moment 4/5 的 UI 深度不足 |
| **综合** | **NOT DONE — 86/100** | 距 DONE 最大缺口：Evaluation 82（需 ≥90，C/D 实验未跑）与 Demo 82（需 ≥95） |

## 11. 通往 DONE 的剩余工作（按优先级）

1. Experiment B 扩样本：heldout 任务 + 多步真实任务（简单任务天花板效应掩盖契约模式价值）
2. Evidence deep-link + L3 展示 + Evolution Candidate 卡片进 Live Run（补齐 Moment 4/5）
3. 结构化日志 + 并发 smoke test（抬 Runtime/Engineering 过 92）
4. dashboard/run 组件对齐 Hero 设计 tokens（Visual → 95）
