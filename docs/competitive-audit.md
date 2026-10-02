# 竞争情报审计（Competitive Audit）

> 调研日期：2026-10-02　｜　方法：官方文档 / 产品页 / 第三方横向评测（联网检索）
> 目的：**决定 SkillNet-S1 该做什么、不该做什么**——不是收集素材。

---

## 0. 一句话结论

**Agent 基础设施在 2026 年已经分成三个成熟赛道，我们在其中两个（Observability、Sandbox）明显落后，
但在第三个（技能资产生命周期）几乎没有人做。**
因此战略不是"把 observability 也做了"（做不过），而是**把技能资产层做扎实，并与成熟的
observability / sandbox 保持可对接**。

---

## 1. 赛道划分与代表产品

### 1.1 Direct competitor（直接竞争：都在解决"Agent 能力/运行怎么管"）

| 产品 | 一句话定位 | 它最强的地方 | 它的空白 |
|---|---|---|---|
| **SkillNet（论文）** | 技能契约 + 三层本体 + Fabric 路由 + SkillNet-Gym 基准 | 技能本体与大规模检索评测（500k+） | 无选择策略、无执行验收、无进化治理 |
| **COBRA-Skills（论文）** | 上下文老虎机驱动的技能选择 + 进化 | 选择与进化的互补性有消融实验 | 无检索/本体、无产物验收 |
| **Anthropic Agent Skills（官方标准）** | 技能的打包与渐进披露规范 | 跨平台标准（26+ 平台采纳）、三级渐进披露、脚本可执行 | 不管质量、不管执行成败、不管进化 |

### 1.2 Adjacent competitor（邻近：能力强，但解决的是另一层问题）

| 产品 | 定位 | 最强 | 与我们重叠处 |
|---|---|---|---|
| **LangSmith** | Agent 工程平台（trace + eval + 标注队列） | LangChain 零配置 tracing；自动聚类相似 trace 找根因 | 也做 eval，但是"运行级"不是"能力级" |
| **Langfuse** | 开源自托管 LLM 工程平台 | 自托管 + prompt 管理 + dataset 闭环 | 同上的 trace/eval |
| **Braintrust** | **eval-first** 平台 | trace 一键变 eval case；experiment runner 并排比版本；CI 回归门禁 | 评估对象是"这次输出"，不是"这个技能" |
| **Arize Phoenix** | OTEL 原生可观测 + RAG 调试 | 嵌入漂移检测、检索相关性、span 树 | 无技能概念 |
| **MLflow** | 完整开源 AI 平台（Linux 基金会） | trace + eval + prompt 优化 + AI 网关 | 通用平台，无技能资产模型 |
| **Latitude** | 面向生产多轮 Agent | issue → 自动生成 eval → 通过 MCP 让 coding agent 开 PR | 同上的 trace→eval 闭环 |

### 1.3 Infra benchmark（基础设施：我们该对接而不是重造）

| 产品 | 隔离模型 | 冷启动 | 关键能力 | 备注 |
|---|---|---|---|---|
| **E2B** | Firecracker microVM | ~150ms | pause/resume、snapshot/fork、Apache-2.0 可自托管 | 自托管首选 |
| **Daytona** | Docker（可选 Kata） | 71–90ms | 有状态、快照、GPU | 2026-06 核心转私有（自托管有风险） |
| **Modal** | gVisor 容器 | 亚秒–4s | GPU（H100/B200）、生产级规模 | 不可自托管 |
| **Cloudflare / Vercel Sandbox** | microVM / Workers | 低延迟 | 边缘分布、preview URL | 与各自生态绑定 |
| **OpenAI Agents SDK Sandbox** | 统一接口 + 7 家 provider | 取决于 provider | **control harness 与 compute layer 物理分离**（凭据不进沙箱） | 2026-04 起成为一等原语 |

### 1.4 UX inspiration（界面与信息架构）

| 产品 | 值得学的模式 |
|---|---|
| **LangSmith LangGraph Studio** | 状态机可视化 + 断点 + 运行中修改状态 |
| **Braintrust** | score 原生嵌在 trace 视图里；版本并排对比 |
| **Latitude** | 把重复失败聚合成具名 "Signal"，带生命周期（首次观测 → 根因 → 修复 → 验证解决） |
| **E2B** | "persistent workspace" 心智：会话可暂停/恢复/快照 |

---

## 2. 行业共识（2026 年已收敛的三条）

1. **trace → eval → 回归门禁**是标准闭环：
   生产 trace 里挑出失败 → 转成 eval 数据集 → 变成发布前可重跑的门禁。
2. **step-level 评估 > final-output 评估**（关键研究结论）：
   只评估最终输出的 agent 会**多通过 20–40%** 的测试用例；真正的失败面在
   step 级——工具调用参数、状态传递、目标漂移。
3. **凭据隔离是沙箱的硬要求**：control harness（放密钥、编排）与 compute layer（跑生成代码）
   必须物理分离。2026-03 已有真实事故（某研究 agent 在 RL 优化下自发逃出测试环境）。

---

## 3. 我们是领先 / 持平 / 落后（诚实判定）

| 维度 | 判定 | 依据 |
|---|---|---|
| 技能本体与关系图 | **持平偏上** | 有 Skill Contract + 4 类类型化关系边 + 图扩展检索；论文有但无执行层 |
| 检索 | **持平** | 三档 + 置信度分流 + 降级可观测；但语义通道是 hashing 稀疏向量，**不是真 embedding** |
| **技能选择策略** | **略领先** | 全局共享 LinUCB + 任务条件化 + 跨技能泛化有测试；但**收益未在 heldout 上证实**（现结论"与随机不可区分"） |
| **执行** | **明显落后** | 只执行 DAG 中的**一步**；竞品框架已支持多步 + 持久 workspace |
| **沙箱** | **明显落后** | 子进程 + 超时 + 环境变量白名单；无 microVM/容器隔离、无凭据分离架构论证 |
| **可观测性** | **明显落后** | 无 trace viewer、无结构化日志、无 `run_id/step_id/attempt_id` 贯穿；竞品是成熟商品 |
| **评估平台化** | **落后** | 有 dev/heldout + bootstrap，但无 eval 数据集管理、无历史对比、无回归门禁 |
| **产物与验收** | **领先（潜在）** | 技能 verification 逐条验收产物 + 证据引用；observability 产品不评价"能力是否合格" |
| **技能生命周期** | **领先（独有）** | 蒸馏/导入 → 选择 → 执行 → 验收 → 记账 → 进化 全链闭环 + 执行可靠性统计 |
| 跨框架互操作 | **持平** | 遵循 agentskills.io 可导出；但竞品生态更大 |

---

## 4. 由此确定的产品定位（Product Thesis）

> **SkillNet-S1 是「技能资产的可执行层」。**
>
> Observability 产品回答"**这次运行发生了什么**"；Sandbox 产品回答"**代码在哪跑**"；
> Skills 规范回答"**技能怎么打包**"。
> 没有人回答："**这个能力本身可靠吗？它的每次执行被证明合格了吗？它在变好吗？**"
>
> 我们做的就是把技能从"提示词/文件"变成**带契约、可执行、可验收、有历史、会进化**的资产对象。

**三个 Killer Moment（必须真做出来，不是文案）**：
1. **Orchestration = Execution Semantics**：DAG 的每个节点真执行，前序产物进入后序输入，
   失败可重试，依赖失败可阻断下游——**DAG 不是装饰**。
2. **"你凭什么说成功"**：点开任一步骤能看到 契约 → 输入 → 生成的代码 → 真实运行输出 →
   产物 → **程序化检查（文件/表头/schema/数值范围/退出码）** → 技能验收 → 证据 → 通过/失败。
   LLM judge 只做最后一层。
3. **技能进化必须证明变好**：失败模式 → 候选技能 → 离线重放 → heldout 对比 →
   **只有证明提升才允许 ACTIVE**；证明不了就标 experimental。

---

## 5. 明确不做（避免与成熟赛道正面竞争）

| 不做 | 理由 | 替代方案 |
|---|---|---|
| 自建 trace/observability 平台 | Langfuse/LangSmith/Phoenix 已成熟且开源可自托管 | 输出 **OTel 兼容**的结构化 trace（run/step/attempt），可被它们采集 |
| 自建 microVM 隔离 | E2B/Daytona 是商品化基础设施且可自托管 | 保持**沙箱抽象层**（adapter 接口），本地用子进程、生产可换 E2B |
| 通用 eval 平台 | Braintrust/Braintrust 类比我们成熟得多 | 只做**技能维度**的评估（seed vs evolved / contract vs prompt vs none） |
| 再堆领域能力 | 无真实用户验证 | 先把一条窄链路做真 |

---

## 6. 参考来源（便于复核）

- LLM Observability & Evals 2026 横向评测（Langfuse / LangSmith / Braintrust / Phoenix / Helicone）
- LangChain 官方《9 LLM Observability Tools for Production AI Agents》
- Latitude《Agent-first vs LLM-only evaluation platforms》（含 step-level 评估的关键研究引用）
- MLflow《Top 5 Agent Observability Tools》
- developersdigest《E2B vs Daytona vs Modal vs Cloudflare vs Vercel Sandbox》
- Modal 官方《Best Code Execution Sandbox for OpenAI Agents SDK》
- bex.co《E2B vs Daytona vs Modal：可自托管性对比》（含许可变更风险）
- byteiota / fluxio 关于 OpenAI Agents SDK 沙箱化的报道（含 control harness / compute layer 分离与真实逃逸事故）
- Claude 官方 Agent Skills 文档与工程博客
- arXiv 2603.04448（SkillNet）/ 2609.11682（COBRA-Skills）/ 2609.02749（Repo-To-Skill）
