# SkillNet-S1 技术说明书

> 版本：v0.6（2026-10-02）　｜　用途：供外部评审——**请重点看第 8 节「已知缺陷与边界」**
> 阅读建议：第 1 节建立全貌（5 分钟）→ 第 5 节看完整链路（15 分钟）→ 第 8 节挑问题

---

## 0. 文档目的

本文档描述 SkillNet-S1 原型**当前的全部实现细节**：它是什么、前端怎么呈现、后端怎么实现、
数据怎么流、产物是什么、哪些地方做了妥协。目标是让读者能够**独立判断实现的合理性与缺陷**，
而不是只看演示效果。

阅读时的三条约定：

1. **所有数字都可核实**：文中给出的规模数字来自 `/api/graph` 与 `/api/health` 实时接口；
2. **所有"已验证"都有出处**：验证手段为 `verify.py`（31 项）、`pytest`（11 项）、
   `tools/selfcheck.py`（18 项）、真实运行记录；
3. **所有妥协都标注**：凡未实现、简化、有风险的实现，都在第 8 节列出，不做粉饰。

---

## 1. 产品是什么

### 1.1 一句话定位

**给 Agent 产品补一层「技能运维层」**：把 Agent 的能力以「技能」为单位资产化，
提供检索路由、编排、真实执行、评估与进化，并保证每一步可追溯。

面向的下游产品是**立理 S1**（s1.liliai.cn，AI 科学家系统，已有 300+ 科研工作流）。

### 1.2 解决什么问题（问题有外部证据）

| 问题 | 外部证据 | 本项目的应对 |
|---|---|---|
| 技能找不准 | SkillNet 论文（arXiv 2603.04448）实测：前沿 Agent 在真实社区技能池上检索完整度仅个位数至 30% | 三档检索 + 关系图扩展（实测 BM25 召回 66.7% → Fabric 100%） |
| 技能编排会崩 | 同上：要求按依赖组织工作流时硬任务分数进一步下滑 | 类型化关系图 + 拓扑排序编排 |
| 技能只进不出 | EvoScientist（华为）指出 AI 科学家系统是静态流水线，反复走死路 | 轨迹蒸馏 + 质量准入，库自动增长（演化技能数量随运行增长，实时以 /api/health 为准） |
| 技能质量无数据 | 通用做法没有执行成败记录 | 执行结果记账（`exec_total/exec_ok/exec_fix/exec_fail`）+ 失败样本归档 |
| 效果无法证明 | 现有方案多停留在演示 | 有/无技能的**三方对照实验**（内置三种技能使用模式） |

### 1.3 产品形态（三种使用方式）

| 形态 | 入口 | 面向 | 说明 |
|---|---|---|---|
| **汇报演示页** | `http://127.0.0.1:8848/` | 决策者 / 评审 | 六幕结构 + 对话式闭环演示（跑真实任务） |
| **技能星图** | `http://127.0.0.1:8848/graph` | 技术评审 / 探索 | Canvas 力导向图，可拖拽缩放，点击看技能详情 |
| **完整面板** | `http://127.0.0.1:8848/dashboard` | 使用者 / 开发者 | 七个视图：概览 / 演示 / 技能库 / 检索 / 执行 / 实验结果 / 跨框架导出 |
| **HTTP API** | `/api/*`（21 个端点） | 集成方 | 可被任何 Agent 产品调用 |
| **跨框架技能目录** | `/api/adapters` 导出 | 生态集成 | 导出为 Claude Code / Cursor / Gemini / ADK 可加载的 SKILL.md 目录 |

**部署形态**：单进程 FastAPI（默认 `127.0.0.1:8848`），前端为**零依赖静态单页**
（不依赖任何 CDN，内网/离线可运行）。无数据库，状态存于内存 + JSON 文件。

### 1.4 与同类方案的关系（诚实定位）

| 方案 | 它做了什么 | 本项目与其关系 |
|---|---|---|
| Anthropic Agent Skills（官方标准） | 技能打包、渐进披露（metadata → instructions → resources/code）、跨平台加载 | **遵循其规范**（我们的技能目录可直接导出给它用）；补的是它未覆盖的**后半段生命周期**：技能怎么被选、执行结果怎么验收、库怎么自己变大 |
| SkillNet 论文 | 技能契约、三层本体、Fabric 路由、SkillNet-Gym 基准 | **复现其核心**（契约 + 关系 + 图扩展路由），并补齐其未做的选择策略、执行验收、进化治理 |
| COBRA-Skills | LinUCB 技能选择 + 进化算子 | 采用其选择思想（本项目实现为全局共享参数 LinUCB），并把进化接入完整闭环 |
| Repo-To-Skill (DisCo) | 仓库蒸馏成技能、验证门槛 | 采用其"未经验证不入库"的准入思想 |
| 通用向量 RAG | 向量检索文档 | 我们的 hybrid 档包含语义通道，但另有图扩展与契约验收 |

---

## 2. 系统架构

### 2.1 进程与部署结构

```
┌──────────────────────────────────────────────────────────────┐
│  单进程：python run.py  →  uvicorn  →  FastAPI (server.py)   │
│                                                              │
│  /                 → web/briefing.html   （汇报演示页）      │
│  /graph            → web/graph.html      （交互式星图）      │
│  /dashboard        → web/index.html      （完整面板）        │
│  /static/*         → web/ 静态目录                           │
│  /api/*            → 21 个 JSON 端点                         │
└──────────────────────────────────────────────────────────────┘
        │                        │                       │
        │ 调用 LLM               │ 真实执行代码          │ 落盘
        ▼                        ▼                       ▼
  DeepSeek API          子进程沙箱（沙箱内 python）   out/ data/
  (OpenAI 兼容)         sandbox.py: subprocess      JSON / PNG
```

**关键设计**：沙箱执行是**独立子进程**，与主服务进程隔离；LLM 调用通过 httpx 连接池复用。

### 2.2 模块划分（skillnet/ 包，共 16 个模块 / 约 3,900 行）

| 模块 | 行数 | 职责 |
|---|---|---|
| `schema.py` | 362 | 数据模型：Skill / SkillContract / 五维质量 |
| `catalog.py` | 286 | 技能库 + 关系图（规范化、查询、持久化） |
| `index.py` | 252 | 三路索引：BM25 / 稀疏向量 / 加权融合 |
| `retriever.py` | 457 | 三档检索（bm25/hybrid/fabric）+ 降级可观测 + 置信度分流 |
| `orchestrator.py` | 153 | 依赖图编排（拓扑排序 + 断环） |
| `bandit.py` | 531 | 全局共享 LinUCB 上下文老虎机（任务条件化） |
| `agent.py` | 227 | 技能驱动的研究执行器（生成方案） |
| `sandbox.py` | 172 | 受控代码执行沙箱 |
| `executor.py` | 393 | 技能驱动的真实执行：生成代码 → 运行 → 修复 → 技能验收 |
| `judge.py` | 131 | 方案评分（LLM 盲评 + 参照点覆盖） |
| `evolver.py` | 300 | 技能进化（蒸馏/变异/交叉/再生 + 准入） |
| `artifacts.py` | 402 | 产物渲染（报告/方案）+ 交付物生成 + 沙箱产物收集 |
| `adapters.py` | 312 | 跨框架导出（4 种格式） |
| `llm.py` | 301 | LLM 客户端 + 请求级成本账本 |
| `config.py` | 38 | 路径与运行配置 |

**服务层**：`server.py`（850 行，FastAPI 全部端点）、`run.py`（27 行，启动器）。

### 2.3 一次请求的数据流（高层视图）

```
用户提问
   │
   ├─→ Retriever.search()                    三档检索 → RetrievalResult
   │      └─ 置信度分流（BM25 原始分 → auto/confirm/direct）
   │
   ├─→ Retriever.route_with_wiki()            任务级 Wiki（候选 + 证据）
   │
   ├─→ SharedLinUCB.rank()                    按历史反馈排序（预测 + 探索）
   │
   ├─→ Orchestrator.build_from_relations()    DAG 编排（拓扑序）
   │
   ├─→ ResearchAgent.run()                    生成研究方案（LLM，一次调用）
   │      └─ Judge.score_plan()               盲评打分 + 参照点覆盖
   │
   ├─→ Executor.execute_step()                真实执行（沙箱）
   │      ├─ 生成代码（技能契约约束）
   │      ├─ Sandbox.run_python()             子进程真实运行
   │      ├─ 失败 → 带「错误 + 技能陷阱」修复（≤2 次）
   │      └─ 技能 verification 逐条验收
   │
   ├─→ SharedLinUCB.update()                  反馈写回（改变下次排序）
   │
   ├─→ SkillEvolver.distill()                 轨迹蒸馏 → 新技能（过准入门槛）
   │
   └─→ Artifacts.render_bundle()              产物渲染
          ├─ report.html / plan.md（方案渲染）
          ├─ generate_deliverables()          按清单生成交付物（doc/code/table）
          └─ collect_execution_artifacts()    收集沙箱产物（图/表）
```

---

## 3. 后端实现

### 3.1 数据模型

**Skill（技能）** —— 定义于 `skillnet/schema.py:47`：

```python
@dataclass
class Skill:
    name: str                    # 唯一标识（kebab-case）
    description: str             # 检索用描述
    domain: str                  # 领域（当前 36 个）
    tags: list[str]
    # ---- Skill Contract ----
    capability: str              # 能力一句话
    inputs: list[str]            # 输入
    outputs: list[str]           # 输出
    use_when: list[str]          # 适用时机
    # ---- 操作性知识 ----
    steps: list[str]             # 执行步骤（→ 代码生成约束）
    pitfalls: list[str]          # 已知陷阱（→ 修复线索 + 红线）
    verification: list[str]      # 验收清单（→ 产物验收标准）
    # ---- 质量与关系 ----
    quality: dict[str, str]      # 五维：safety/completeness/executability/maintainability/cost_awareness
    relations: list[tuple[str, str]]   # (关系类型, 目标技能)
    # ---- 溯源 ----
    source: str = "seed"         # seed / evolved
    origin_task: str | None      # 由哪条任务蒸馏而来
    parent: list[str]            # 变异/交叉的父技能
    generation: int = 0          # 0 = 种子
    # ---- agentskills.io 规范字段 ----
    license: str; compatibility: str; metadata: dict; allowed_tools: str
    # ---- 运行期统计 ----
    stats: dict[str, float]      # pulls / reward_sum / best
                                 # + exec_total / exec_ok / exec_fix / exec_fail / exec_last_error
```

**关系类型**（`RELATION_TYPES`）：`depend_on`（依赖）/ `compose_with`（组合）/
`similar_to`（相似）/ `belong_to`（归属）。

**关系图规范化**（`catalog.py:28`，防止图上出现矛盾边）：
1. 若 A `depend_on` B，则删除 B 中所有指向 A 的边（B 再指向 A 就是矛盾）；
2. 双向 `compose_with` 去重，保留字典序较小的一方作为源。

### 3.2 技能库与关系图（catalog.py）

- **数据源**：`seed/catalog_data.py` 的 `RAW` 列表（`S(...)` 构造调用，1,363 行）。
  **注意**：`seed/skills/*/SKILL.md` 只是导出产物，不是数据源——改 SKILL.md 不会生效。
- **当前规模（2026-10-03 快照）**：106 个技能 / 48 个领域 / 233 条类型化关系边（其中 31 个为演化技能）。
  **库随每次运行自主增长，实时值以 `/api/health` · `/api/graph` · `/api/capabilities` 为准**——文档快照仅作参考，不构成承诺。
  库随每次运行自主增长，**实时值以 `/api/health`、`/api/graph`、`/api/capabilities` 为准**。历史口径 90/36/162（15 演化）与 51 技能/62 边的实验数据均标 **Historical**。
- **技能构成**：51 个科研方法技能 + 24 个工具交付技能（导入自开发组另一成员的项目）
  + 27 个演化技能（跨项目融合后持续增长，实时以 /api/health 为准）。
- **持久化**：技能库可落盘为 `data/library.json`（原子写：先写临时文件再替换）。
- **并发安全**：`SkillLibrary` 内部一把可重入锁；遍历类方法返回副本
  （否则 `/api/evolve` 加技能时并发的 `/api/search` 会抛
  `RuntimeError: dictionary changed size during iteration`）。锁不覆盖 LLM 调用。

### 3.3 检索（index.py + retriever.py）

**三路索引**：

| 通道 | 实现 | 说明 |
|---|---|---|
| BM25 | 自实现倒排索引（`index.py:46`） | 中文按 2-gram + 英文词切分；返回 TF-IDF 累加原始分 |
| 语义向量 | 稀疏 hashing 向量（`index.py:104`） | **非真实 embedding**：用 CRC32 稳定哈希把 token 映射到固定维度（跨进程可复现），做余弦相似 |
| 结构信号 | 领域名与标签的字面命中（`retriever.py._structural_hits`） | 领域名按「与/、/，」切段，原样出现在 query 中才算命中 |

**融合**（`index.py:223` `weighted_fuse`）：先对每路做 **min-max 归一化**，再按权重相加，
多路命中给一致性加成。权重 **BM25 0.70 / 语义 0.20 / 结构 0.10**
（0.55/0.30/0.15 时混合档会低于纯 BM25 基线，已调整）。

**三档模式**：
- `bm25`：仅关键词（无网络、无模型也可用，兜底档）
- `hybrid`：三路融合
- `fabric`：hybrid + **关系图扩展**（沿 90 条边补入关联技能）+ **LLM 重排**

**降级可观测**（v0.3 新增）：缺 API Key 时 fabric 的 LLM 重排不执行，但**显式返回**
`degraded=true` / `components={bm25, vector, structural, graph_expansion, llm_rerank}` /
`degraded_reason`，绝不静默。

**已知重要局限**：融合分经 min-max 归一化后**跨查询不可比**（同一技能在不同查询下分数尺度不同），
因此**不能用于绝对阈值**。这也是置信度分流改用 BM25 原始分的原因（见 3.4）。

### 3.4 置信度分流（retriever.py:34 起）

吸收自开发组成员项目的「混合调度」设计：按 Top-1 相关度分三档决定下游动作。

| 分档 | 判据（BM25 原始分） | 下游动作 |
|---|---|---|
| `auto` | ≥ 15 | 直接执行 |
| `confirm` | 2 ≤ x < 15 | 展示候选，人工确认后执行 |
| `direct` | < 2 | 交给通用模型，不硬套技能 |

**阈值标定依据**（42 条查询实测）：真实科研任务 dev 9.9–88.9（中位 42.6）、
heldout 20.7–61.8、交付物任务 8.0–29.0、无关问题 0.0–4.6。

**保守取向的原因（实测纠正）**：初版阈值取 6.0，结果 dev 集两条真实任务
（原始分 3.80 / 4.27）会被误判"无匹配"——**误杀技能比多问一句严重得多**，
因此降到 2.0。当前验证结果：32 条真实任务零误杀，5 条无关查询 4 条判 direct。

输出字段：`confidence`（0–1 归一）、`raw_bm25_top`、`fusion_score`、`decision`、
`decision_reason`。**分流只给建议，不改变检索结果**（代码中有明确注释与测试锁定）。

### 3.5 编排（orchestrator.py）

- `build_from_relations(names)`：从候选技能集出发，用**类型化关系边**构图，
  拓扑排序得到执行顺序；有环时按策略断环（`_break_cycles`）。
- `build_with_llm(query, names)`：LLM 在候选池内补充边，**但只保留两端都在候选池内的边**
  （等价于白名单校验，防止幻觉出库外技能）。
- 输出：`{skills, workflow（边列表）, order（执行顺序）}`。

**已知局限**：编排产出的顺序目前只用于展示与执行提示，**没有真正驱动分步执行**
（真实执行只挑一步落地，见 3.7）。

### 3.6 选择策略：全局共享 LinUCB（bandit.py）

**为什么不能用 per-arm**：per-arm LinUCB 每个技能独立维护 A/b，数学上不可能让
"评估 A 的反馈影响未评估的 B"，而项目文档曾如此声称——v0.3 已修正为**全局共享参数**。

**上下文 φ(task, skill)**（137 维，`ContextEncoder.encode`）：
task 词袋(64，IDF 加权) + skill 词袋(64，IDF 加权) + 领域 one-hot(24)
+ 交互特征(3：余弦、覆盖度、长度比) + 元特征(5)。

**打分**：`priority = θᵀφ + α·√(φᵀA⁻¹φ)`
- 前者为预测收益（θ = A⁻¹b，全局共享）
- 后者为探索奖励（不确定性越大越高）
- α 默认 0.25–0.3（`/api/demo` 用 0.3）

**更新**：`A += φφᵀ`，`b += r·φ`，`r` = 本次盲评均分 / 10。
**关键性质**：θ 全局共享 → 一次更新改变**所有**技能的预测，同领域变化最大。

**哈希稳定性**：`stable_hash` 用 `zlib.crc32`，**不用内置 `hash()`**（后者每进程随机）。
有 pytest 锁定跨进程可复现（不同 `PYTHONHASHSEED` 子进程输出一致）。

**实测的泛化行为**：一次任务反馈后，同领域技能预测变化约为异领域的 1.24 倍
（早期 24 维词袋时区分度不足，加领域 one-hot 后才拉开：同领域 cos≈0.90 vs 异领域 0.73）。

**状态持久性**：策略参数 A/b **不落盘**（服务重启后从零开始，靠探索机制重新积累）；
但技能库刷新（evolve 后）会**继承** A/b，不会把学习清零（曾因未继承而丢失，已修）。

### 3.7 真实执行（sandbox.py + executor.py）—— v0.6 核心

**设计依据**：Agent Skills 官方定义中，技能应附带可执行脚本、由环境运行、
**只有输出进入上下文**；官方推荐 **Run → Validate → Fix → Repeat**。

#### 沙箱（sandbox.py）

| 机制 | 实现 |
|---|---|
| 隔离 | `subprocess.run([python, "-I", "-B", script])`，`-I` 隔离模式 |
| 工作目录 | 独立临时目录（`out/demo_artifacts/{slug}/run/tryN`），HOME/TMP 指向工作目录 |
| 超时 | 默认 90s（演示 75s），超时强制 kill 并标记 `error_kind=timeout` |
| 环境变量白名单 | 仅传递 PATH/SYSTEMROOT/TEMP 等，**不继承 API Key 等任何凭据** |
| 产物收集 | 运行结束后扫描工作目录新文件（png/csv/json/md/py 等） |
| 错误分类 | `syntax` / `import` / `exception` / `timeout`（供修复策略区分） |
| 绘图支持 | 强制 `MPLBACKEND=Agg`，`MPLCONFIGDIR` 指向工作目录 |

**安全边界（重要，请评审）**：该沙箱**面向可信模型产出的分析代码，不是对抗性隔离**。
不主动授予网络能力，但**无法在内核层面阻断**；无内存/CPU 配额（只有超时）。
生产环境应替换为容器/虚拟机级隔离。此声明同时写在模块 docstring、README 与本文档。

#### 执行器（executor.py）

流程：

```
pick_executable_step(plan)          挑最适合落地的一步
   │  规则：优先「分析/计算/验证/统计/训练/拟合/模拟/检验/清洗/建模/可视化」类
   │        跳过「综述/检索/投稿/汇报/撰写」类
   ▼
生成代码（_gen_code_prompt）
   │  · 技能 steps  → 作为执行步骤
   │  · 技能 pitfalls → 作为必须避免的红线
   │  · 技能 verification → 作为验收清单
   │  · 环境约束：只允许本机已装库（numpy/matplotlib）
   │  · 规模约束：单文件 ≤250 行，超出用 TODO 标注
   │  · 诚实红线：模拟数据必须显式标注
   ▼
本地语法预检（ast.parse）          语法错不进沙箱，定位更准且更快
   ▼
沙箱执行（sandbox.run_python）
   ▼
失败？ → 修复（≤2 次）
   │  · 普通错误：带「真实错误输出 + 该技能已知陷阱」要求修复
   │  · 截断类错误（_looks_truncated）：要求「重写更精简的完整代码（≤200 行）」
   ▼
技能验收（_verify_with_skill）
   │  用 verification 逐条判定 → 要求引用产物中的具体证据、不得推测
   │  无证据时判 FAIL 并写"产物中未见"
   ▼
执行记账（_record_execution）
      写入 skill.stats（exec_*）+ 归档 out/exec_log/executions.jsonl
```

**token 预算演进（实测驱动）**：3000 → 7000 → **12000**
（一次 ML pipeline 任务生成 19475 字符代码，在 line 531 被截断：
`SyntaxError: '[' was never closed`，连续三次修复都失败——因为模型每次都在补同一份超长代码）。

**返回结构**（供前端展示与审计）：`code` / `final_ok` / `attempts[]`（每次的
stdout/stderr/error_kind/duration）/ `n_attempts` / `fixed`（尝试>1 **且最终成功**）/
`exhausted`（尝试耗尽）/ `truncated` / `artifacts[]` / `verification[]` /
`verification_passed` / `verify_skip_reason` / `skill_exec_stats` / `exec_record`。

**三种技能使用模式**（`mode` 参数，用于对照实验）：

| 模式 | 技能怎么被用 | 验收 |
|---|---|---|
| `contract`（默认） | steps 当步骤、pitfalls 当红线、verification 当验收标准；修复时带陷阱 | 有 |
| `prompt` | 只把能力与步骤当参考塞进提示词（"提示词塞技能"的常见做法） | 无 |
| `none` | 不给技能（裸模型） | 无 |

### 3.8 评估（judge.py）

- `score_plan(query, response, reference_points)`：LLM 作为评审打分，四个维度
  （`skill_grounding` / `executability` / `rigor` / `scientific_validity`）+ 加权总分 +
  参照点覆盖（`coverage` / `covered` / `n_points`）+ 评语。
- `reference_points_from_skills(lib, gold_names)`：从 gold 技能的 pitfalls/verification
  抽取参照点。

**已知严重局限（请评审）**：
1. **评价者与被评者是同一模型**（仅 `role` 标签不同，用于计费分账）——属自评；
2. **参照点与提示词同源**（都取自同一批技能）——覆盖度存在循环论证倾向；
3. 无 gold 时客观线（覆盖率）直接跳过；
4. 评分是"方案级"，不是"产物级"。

### 3.9 技能进化（evolver.py）

- 四种算子：`distill`（从轨迹蒸馏新技能）/ `mutate`（变异）/ `crossover`（交叉）/
  `regenerate`（再生）。
- **质量准入**（`assess_quality`）：命名合规 → 步骤数下限 → 与现有技能相似度阈值
  （`max(Jaccard, 0.9×重叠系数)`）→ 判定是否入库，未通过则记录理由。
- 新技能带 `generation` 与 `parent` 溯源；演化技能占比见上方实时接口。

**已知局限**：准入是启发式（关键词 + 相似度），**没有运行测试**；
`origin_task` 字段当前未写入（来源追溯不完整）。

### 3.10 产物层（artifacts.py）

三层产物：

| 层 | 函数 | 产出 | 说明 |
|---|---|---|---|
| 方案渲染 | `render_bundle()` | `report.html` + `plan.md` | 把执行方案渲染为自包含 HTML 报告与 Markdown；含步骤/参数/判据/风险/评估；页脚标注「方案与要点，非实验结论」 |
| 交付物生成 | `generate_deliverables()` | 按方案声明的清单生成 `*.md` / `*.py` / `*.csv` | 一次 LLM 调用；提示词写死诚实红线（实验结果数字须标注"示意值"）；内容 <120 字符视为失败 |
| 沙箱产物收集 | `collect_execution_artifacts()` | `stepN_*.png` / `*.csv` | 把沙箱真实产出的文件平铺复制到产物目录，供前端预览 |

**确定性**：产物带 **sha256 指纹**（内容）与**任务指纹**（`sha256(task)[:8]`）；
同一任务重复运行产物一致，便于审计。

**文件名安全化**：`safe_filename()` 保留中文与字母数字，剔除路径分隔符与非法字符，
补正确扩展名（防路径穿越；同时接口层另有 resolve 前缀校验兜底）。

### 3.11 LLM 与成本（llm.py）

- 客户端：httpx 连接池复用（按次新建会重复 TCP+TLS 握手）。
- **请求级成本账本**：`UsageLedger` + `contextvars`，按 `role` 分账
  （executor / judge / worker），并发请求互不串账。
- JSON 容错：`repair_truncated_json()` + `extract_json()`（长 JSON 截断是常见失败模式）。
- 模型：默认 DeepSeek（OpenAI 兼容协议）。

**已知局限**：定价为常量表，无法获知缓存命中/分时折扣时只标"估算"；
模型层未完全抽象（换供应商需改配置）。

---

## 4. API 清单（21 个端点，`server.py`）

### 4.1 只读端点

| 端点 | 方法 | 返回 | 说明 |
|---|---|---|---|
| `/api/health` | GET | `{ok, version, skills, evolved, model, api_key_configured, token_required, ui_version, library_path}` | 健康检查 + **前端缓存自愈用的版本戳** |
| `/api/stats` | GET | 技能库统计（规模/领域/质量分布/关系边） | 面板 KPI 数据源 |
| `/api/skills` | GET | `{skills:[{name, domain, tags, capability, quality, relations, stats, ...}]}` | 支持 `domain` / `q` 查询参数 |
| `/api/skill/{name}` | GET | 单技能完整信息 | |
| `/api/skill/{name}/raw` | GET | `{name, source, content}` | 返回 SKILL.md 原文（磁盘或现场渲染），供演示页「查看技能契约全文」 |
| `/api/graph` | GET | `{nodes:[{id, domain, generation, source, pulls, mean_reward}], edges:[{source, target, type}]}` | 星图数据源 |
| `/api/tasks` | GET | 评测任务列表（含 gold 标注） | |
| `/api/results` | GET | 三组实验结果 | 面板「实验结果」视图 |
| `/api/skills-index` | GET | 扁平索引文本 | 用于对照实验（"技能是否被激活"） |
| `/api/config` | GET | 非敏感运行配置（模型名、阈值等） | |
| `/api/artifact/{slug}/{fname}` | GET | 文件内容（**文本或二进制**，`?download=1` 触发下载） | 产物预览/下载；图片按 `image/png` 返回；含路径穿越校验 |

### 4.2 消耗模型额度 / 写盘的端点（受 `SKILLNET_TOKEN` 保护，默认不启用）

| 端点 | 方法 | 入参 | 返回 | 说明 |
|---|---|---|---|---|
| `/api/search` | POST | `{query, k, mode}` | `RetrievalResult.to_dict()` | 三档检索；含置信度分流与降级信息 |
| `/api/route` | POST | `{query, k}` | 任务级 Wiki + 编排 DAG | |
| `/api/run` | POST | `{query, skills, style}` | 执行结果 + 评分 | 技能驱动执行（生成方案）|
| `/api/evolve` | POST | `{query, ...}` | 进化记录（新技能 + 准入理由） | |
| `/api/demo` | POST | `{task, gold?, k}` | **七阶段闭环结果**（见第 5 节） | 演示页主接口 |
| `/api/execute_one` | POST | `{task, step, skill?, mode}` | 单步真实执行结果 | 用于对照实验与单步重跑；`mode ∈ {contract, prompt, none}` |
| `/api/adapters` | POST | — | 导出结果清单 | 跨框架技能目录导出 |

### 4.3 页面路由

| 路由 | 返回 | 说明 |
|---|---|---|
| `/` | `web/briefing.html` | 汇报演示页（首页） |
| `/graph` | `web/graph.html` | 交互式技能星图 |
| `/dashboard` | `web/index.html` | 完整面板 |
| `/static/*` | `web/` 目录 | 静态资源 |

### 4.4 鉴权与错误约定

- 可选令牌：设置 `SKILLNET_TOKEN` 后，上表中"受保护"端点要求请求头 `X-SkillNet-Token`
  （`secrets.compare_digest` 比较）。用途：防止服务暴露后额度被无限刷、技能库被写脏。
- 缺密钥（`require_llm`）：返回 **503** 并给出中文可执行提示，而不是静默返回空结果。
- 参数校验失败：FastAPI 默认 **422**。
- 产物路径非法：**400**；不存在：**404**。

---

## 5. 完整链路：一次闭环的七个阶段（`/api/demo`）

这是产品的核心链路。每个阶段都返回结构化数据，供前端分阶段可视化。

### 阶段 1 · 检索对比（三档同题对照）

- **处理**：同一 query 分别跑 `bm25` / `hybrid` / `fabric`，各返回 Top-K。
- **输出**：每档的 `selected` / `recall`（有 gold 时）/ `trace`（各通道召回数、
  融合权重、图扩展补入的技能、LLM 重排条数）/ `confidence` / `raw_bm25_top` /
  `decision` / `decision_reason`。
- **前端呈现**：三行对照表；命中 gold 的技能高亮绿；BM25 漏掉而 Fabric 补回的技能
  单独标出；每档右侧显示置信度徽章（可自动执行 / 建议确认 / 无匹配·直答）。

### 阶段 2 · 策略选择（LinUCB 历史反馈排序）

- **处理**：对检索候选池调 `SharedLinUCB.rank()`。
- **输出**：`[{name, priority, exploit, explore}]`（按优先级降序）。
- **前端呈现**：排序表（技能 / 预测收益 / 探索奖励 / 优先级），top-1 标绿；
  下方一行说明"预测来自历史反馈，探索奖励保证冷启动技能有机会"。

### 阶段 3 · 任务级 Wiki 路由与编排

- **处理**：`route_with_wiki()` 组织候选与证据，`Orchestrator.build_from_relations()` 出 DAG。
- **输出**：`wiki_size` / `skills` / `workflow`（边）/ `order`（拓扑序）/ `reason`（LLM 给的编排理由）。
- **前端呈现**：横向 DAG（技能名 + 箭头 + "执行产物"终点）；下方显示 wiki 规模与理由。

### 阶段 4 · 技能驱动执行与盲评

- **处理**：`ResearchAgent.run(task, skills)` 生成研究方案（一次 LLM 调用，返回 JSON：
  `approach` / `steps[{skill, action, key_params, expected_output, check}]` / `risks` / `artifacts`）；
  随后 `Judge.score_plan()` 盲评。
- **输出**：`skills` / `steps`（数量）/ `adoption`（技能采纳率=方案 step 里实际引用的技能比例）/
  `judge`（四维分 + 加权 + 覆盖 + 评语）/ `plan`（完整方案）。
- **前端呈现**：加载的技能契约 chips；四维评分条形图（**主观线**）；
  客观线（要点覆盖）单独分组并标注"可程序化"；采纳率、步骤数、盲评均分；
  盲评意见；**完整方案卡**（每步含调用技能、关键参数、预期产出、校验判据）。

### 阶段 5 · 真实执行（沙箱）—— 产品的核心差异点

- **处理**：`pick_executable_step()` 挑一步 → `execute_step()` 生成代码 → 语法预检 →
  沙箱运行 → 失败修复（≤2 次，带技能陷阱）→ 技能验收 → 记账。
- **输出**：见 3.7 的返回结构。
- **前端呈现**：
  - 尝试轨迹徽章（第1次 失败 → 第2次 成功，含耗时）
  - 修复/耗尽文案（三种情形，**不把失败说成成功**）
  - 截断提示（若检测到输出截断）
  - 该技能的历史执行统计（累计/成功/修复成功/最近错误类型）
  - 可展开的**完整代码**
  - **真实运行输出**（终端风格深色块）
  - **内联图像产物**（`<img>` 直接渲染沙箱生成的 PNG）+ 下载
  - 落盘数据文件清单
  - **技能验收清单**逐条 PASS/FAIL + 证据
  - 「跑三方对照」按钮 → 调 `/api/execute_one` 两次（mode=none / prompt），
    与本次 contract 结果组成三方对比表

### 阶段 6 · 反馈回流与技能蒸馏

- **处理**：把本次盲评奖励 `r = weighted/10` 写回 LinUCB（对所有采纳技能调
  `update(task, skill, r)`）→ 重新 `rank()` 得到更新后预测 → `SkillEvolver.distill()` 蒸馏新技能。
- **输出**：`feedback[{name, exploit_before, exploit_after, delta, nudged}]` /
  `reward` / `adopted` / `accepted`（是否入库）/ `name` / `generation` / `capability` /
  `library_size` / `records`。
- **前端呈现**：更新前→更新后预测对比表（上升绿、下降红，采纳技能标记）；
  新技能卡（含「查看技能契约全文」按钮，调 `/api/skill/{name}/raw`）。

### 阶段 7 · 本次产出

- **处理**：`render_bundle()` 渲染方案报告 → `generate_deliverables()` 按清单生成交付物 →
  `collect_execution_artifacts()` 收集沙箱产物 → `save_bundle()` 落盘。
- **输出**：`slug`（任务指纹）/ `digest`（产物指纹）/ `artifacts[]`（名称、类型、大小）/
  `declared`（方案声明交付物数）/ `generated`（实际生成数）/ `deliverable_error`。
- **前端呈现**：分两组展示——「方案声明的交付物（本次已生成内容）」与「过程文档」；
  顶部显示"声明 N 项 · 实际生成 M 项（全部兑现/未全部兑现）"；
  每项带「在线查看」（弹层：HTML 用 iframe 内联渲染，md/py/csv 用代码视图）与「下载」。

---

## 6. 前端实现

### 6.1 总体原则

- **零依赖**：三个页面均为**单文件 HTML + 内联 CSS + 原生 JS**，
  **不引入任何外部库或 CDN**（内网/离线可运行；也已避免外部资源加载失败）。
- **无构建**：不需要 npm/webpack，服务端静态托管即可。
- **数据全部来自 API**：页面上任何会变化的数字（技能数/领域数/关系边数）都通过
  `data-live` 占位 + 启动时从 `/api/graph` 填充，**不做硬编码**
  （曾有硬编码导致三处数字互相矛盾的教训，现有自检脚本专门检查）。

### 6.2 汇报演示页（`web/briefing.html`，932 行）

**结构与"组件"（HTML+CSS+JS 组合单元）**：

| 幕 | 组件 | 靠什么实现 |
|---|---|---|
| 顶部状态栏 | 服务/密钥指示灯、技能库规模、页面跳转 | `position:sticky` 固定；`boot()` 拉 `/api/health` 填充；`.dot.on/.off` 控制颜色 |
| **幕 1 · 问题** | 三张痛点卡 + 结论条 | CSS Grid 三列；引用论文实测数据（静态文案） |
| **幕 2 · 方案** | 五阶段闭环架构图 + 四论文拼图 | **内联 SVG**（自绘：矩形节点 + 箭头 marker + 虚线反馈回路 + 治理底座横条）；下方 4 张论文卡说明各缺什么 |
| **幕 3 · 现场演示** | 对话输入框 + 示例 chips + **七阶段时间线** + 成本条 | 见下方"演示流" |
| **幕 4 · 对比论文** | 9 行能力对照表 + 5 张独有卡 | HTML `<table>` + CSS Grid |
| **幕 5 · 强在哪** | 四方能力对照表 + 3 张独有能力卡 + 实测数字 + **「哪里不占优」** | 同上；数字为实测（硬编码但有出处） |
| **幕 6 · 工作量** | 8 格 KPI + 技能库构成说明 + 汇报脚本（可折叠） | CSS Grid；`<details>` 折叠 |

**演示流实现（幕 3）**：

```
用户输入问题 → runDemo()
   ├─ addUser(q)                     插入用户气泡
   ├─ addBot()                       插入"bot 面板"（内含 7 个阶段卡 + 成本条）
   ├─ fetch POST /api/demo           等待完整结果（最长 300s）
   ├─ 逐阶段播放动画：
   │    setStage(n, "running")       阶段圆点脉冲 + 卡内流光条（CSS animation）
   │    await tick(560ms)            让"执行中"状态可被感知
   │    inject(n, renderXxx(detail)) 注入该阶段渲染结果
   │    setStage(n, "done")          打勾弹入 + 内容上滑浮现（CSS keyframes）+ 顶部进度条推进
   └─ 成本条数字滚动（rollNum 用 requestAnimationFrame 缓动）
```

**关键渲染函数**（纯字符串拼接，无框架）：

| 函数 | 渲染内容 |
|---|---|
| `renderStage1(d, gold)` | 三档检索表 + 通道 trace + **置信度徽章**（`title` 提示完整理由）+ BM25 漏掉而被补回的技能 |
| `renderBandit(d)` | 策略排序表（预测/探索/优先级） |
| `renderStage2(d)` | 编排 DAG + wiki 规模 + 理由 |
| `renderStage3(d, gold)` | 技能契约 chips + 评分条形图（**主观/客观分列**）+ 方案卡（`renderPlan`） |
| `renderSandbox(d, slug)` | 见 5-阶段 5 的 9 项呈现；含**内联 `<img>`**（直接指向 `/api/artifact/...`） |
| `renderFeedback(d)` | 更新前后预测对比表 + 新技能卡（含"查看契约全文"按钮） |
| `renderArtifacts(d)` | 产物分两组卡片 + 在线查看/下载 |
| `renderPlan(plan)` | 方案逐步卡片（步骤/技能/参数/产出/校验） |
| `runCompare(btn)` | 三方对照：依次调 `execute_one(mode=none)` 与 `(mode=prompt)`，与本次 contract 结果组成对比表，并对每行标出最优列 |
| `openLayer()` / `previewArtifact()` / `viewSkillRaw()` | 弹层组件：HTML 用 `<iframe>` 内联渲染，文本用 `<pre>`；点击遮罩关闭 |

**缓存自愈机制**：页面内有 `const PAGE_VER = "..."`；启动时与 `/api/health.ui_version`
比对，不一致则带 `?v=` 参数强制刷新一次（`sessionStorage` 防死循环）。
这解决了"改了页面但浏览器跑旧 JS"导致的诡异故障（曾表现为产物 404）。

**安全**：所有插入 DOM 的动态文本都过 `esc()`（HTML 转义），防止模型输出破坏页面结构。

### 6.3 交互式技能星图（`web/graph.html`，463 行）

**这是唯一有持续动画的页面**，实现为一个**手写力导向引擎 + Canvas 2D 渲染**。

**物理模型**（`step()`，每帧一次，O(n²) 对 90 节点无压力）：

| 力 | 参数 | 作用 |
|---|---|---|
| 斥力（库仑） | `REP = 8200`，`d²` 衰减，>250000 平方距离忽略 | 节点互相推开 |
| 弹簧（边） | `LINK_LEN = {depend_on:82, compose_with:118, similar_to:165}`，系数 0.012 | 有关系就连在一起 |
| 中心引力 | `CENTER = 0.0013` | 防止飞散 |
| 阻尼 | `DAMP = 0.845` | 收敛 |
| 速度上限 | 每帧 8 | 防爆 |

**初始布局**：按领域分簇（每个领域一个角度），半径 330 + 抖动，避免全挤中心。

**渲染**（`draw()`）：

| 元素 | 实现 |
|---|---|
| 边 | 按类型着色分线型：`depend_on` 实线绿、`compose_with` 虚线蓝、`similar_to` 点线灰；聚焦时高亮加粗并做 **dash offset 流动动画** |
| 节点 | 径向渐变球体（白→领域色）+ 外圈径向渐变**光晕**；半径来自 `mean_reward`；**呼吸脉动**（正弦相位按坐标偏移，避免同步） |
| 演化技能 | 固定朱红色（与种子技能区分） |
| 标签 | **第二遍统一绘制**：先收集候选，按「聚焦 > 邻域 > 其他」和半径排序，用**屏幕分格占位**（44px 网格）避免压字；被遮挡的标签不画 |
| 视角 | 平移+缩放用**平滑插值**（每帧按 0.18 逼近目标值），产生惯性感 |

**交互**：

| 操作 | 实现 |
|---|---|
| 拖拽节点 | `mousedown` 命中节点 → 每帧把节点坐标设为鼠标世界坐标、`fixed=true`（脱离物理）；`mouseup` 释放回物理场 |
| 平移画布 | 拖空白处：按 `movementX/k` 平移视图 |
| 缩放 | `wheel`：以**鼠标位置为锚点**计算新的 view 偏移（不是缩放中心） |
| 悬停 | `pick()` 命中检测（半径阈值 `max(18/k, r+6/k)`）→ 高亮该节点与**直接邻居**，其余 `globalAlpha` 降到 0.16；顶部提示框显示技能名/领域/奖励 |
| 点击 | 弹出技能卡片：领域、种子/演化、平均奖励、被调用次数、**沙箱执行统计**、五维质量、关联技能列表 |
| 控件 | 重置视角 / 暂停物理 / 显示标签 / 只看演化技能 |
| 截图支持 | `?frames=N` 参数：跑够 N 帧后停止 rAF（供无头浏览器截图；否则无限 rAF 会让 Edge 的虚拟时钟无法结束） |

**配色**：深空背景（径向渐变 `#0d1624 → #070b12`）；22 色领域调色板循环分配。

### 6.4 完整面板（`web/index.html`，984 行）

七个视图（`<section class="view">` + 左侧导航切换）：

| 视图 | 内容 | 渲染函数 |
|---|---|---|
| 概览 | KPI 卡（技能/领域/边/平均质量/演化数）、领域分布、质量分布、关系图（静态 SVG） | `renderMeta` / `renderDomains` / `renderQuality` / `renderGraph` |
| 演示 | 单任务执行入口（与 briefing 类似但简化） | — |
| 技能库 | 技能列表（按领域分组，可搜索） | `renderSkillList` |
| 检索 | 三档检索手动对照 | — |
| 执行 | 技能驱动执行（选择技能 + 风格） | — |
| 实验结果 | 三组实验数据（含 dev/heldout 区分） | — |
| 跨框架导出 | 一键导出四种格式 | — |

**注意**：概览页的关系图是**静态 SVG**（服务端数据 + 前端计算坐标后绘制）——
交互版是独立的 `/graph` 页面，两个页面互相有链接。

### 6.5 前端资产总览

| 文件 | 行数 | 说明 |
|---|---|---|
| `web/briefing.html` | 932 | 汇报演示页（六幕 + 七阶段演示流） |
| `web/index.html` | 984 | 完整面板（七视图） |
| `web/graph.html` | 463 | 交互式星图（力导向引擎） |
| 合计 | **2,379** | 全部零依赖、零构建 |

---

## 7. 数据与产物

### 7.1 落盘位置一览

| 路径 | 内容 | 生命周期 |
|---|---|---|
| `data/library.json` | 技能库快照（含演化技能与 stats） | 持久；删除即回到干净种子库 |
| `out/demo_artifacts/{slug}/` | 一次闭环的全部产物（报告/方案/交付物/沙箱产物） | 每次任务一个目录，**无清理策略** |
| `out/demo_artifacts/{slug}/run/tryN/` | 沙箱每次尝试的工作目录（代码 + 产物 + `.mpl` 缓存） | 保留供人工复核 |
| `out/exec_log/executions.jsonl` | 执行归档（技能/任务/成败/尝试数/错误类型/错误尾巴） | 追加写，无轮转 |
| `out/exp1_retrieval_{dev,heldout}.json` 等 | 三组实验原始数据 | 结果证据，入库 |
| `out/manifest.json` | 实验数据清单（git commit / 模型 / 温度 / 权重 / 文件哈希） | 由 `scripts/build_report_data.py` 生成 |
| `seed/skills/*/SKILL.md` | 技能的 agentskills.io 规范导出 | 由 `export_skill_dirs()` 生成 |

### 7.2 产物命名与指纹

- **任务指纹**（`slug`）：`sha256(task)[:8]` → 同一任务重复运行落到同一目录（覆盖）。
- **产物指纹**（`digest`）：`sha256(markdown + html)[:12]` → 同任务重复运行产物一致，可审计。
- **沙箱产物命名**：`step{N}_{原文件名}`（如 `step2_figure.png`）。

### 7.3 元数据可追溯（`out/manifest.json`）

包含：`project_version` / `git_commit` / `generated_at` / 模型名与温度 /
检索权重 / 选择策略 / 定价版本 / **各结果文件 sha256** / **基准数据集 hash** /
数据集划分（dev / heldout）/ 报告口径规则（最终结论只能引用 heldout）。

---

## 8. 质量保障

### 8.1 三层自检（都可本地执行）

| 工具 | 项数 | 覆盖 | 命令 |
|---|---|---|---|
| `verify.py` | 31 | 面向交付者的组件自检（技能库、索引、检索、编排、老虎机、进化、适配器、持久化、并发、成本账本…） | `python verify.py` |
| `pytest tests/` | 11 | bandit 跨技能泛化 / task conditioning / 跨进程可复现 / 「A 必须是单个矩阵」结构护栏 / 检索分流政策（无关查询不得 auto、真实任务不得 direct、阈值边界、confidence 单调、分流不改变检索结果） | `python -m pytest tests/ -q` |
| `tools/selfcheck.py` | 18 | **页面可达性** / 接口 JSON 合法性 / `health` 与图谱数据一致性 / **页面硬编码数字 vs 真实值** / 产物预览（含中文名与图片）/ 路径穿越拦截 | `python tools/selfcheck.py`（需服务运行） |
| `tools/front_check.js` | 5 | 前端渲染自检（关键组件存在性、XSS 转义等） | `node tools/front_check.js` |

### 8.2 迭代机制（`docs/iteration-log.md`）

方法：每轮**先用四种视角反驳自己**——用户（点这里会怎样）、老板（有什么用）、
技术专家（实现站得住吗）、竞品（凭什么用你）→ 把反驳变成有证据的缺陷 →
修复 → 实测验证 → 记录遗留。当前已完成 R1（执行可靠性）、R2（执行可靠性闭环），
R3–R7 共 25 项待办已列清单。

### 8.3 实验与数据集治理

- **两套数据集**：`dev`（调参用，20 任务）/ `heldout`（冻结测试集，12 任务，
  措辞与标注路径与 dev 刻意不同源，词面 Jaccard 重合度仅 0.052）。
- **报告口径规则**：最终结论只能引用 heldout；dev 数字只能标注为调参结果。
- **已披露的不利结果**：dev 集编排完整度 92.5% → heldout 仅 25.0%，
  说明 dev 高分含过拟合——**主动披露，未修饰**。
- **统计口径**：实验三用配对 bootstrap（4000 次重采样）+ mean±std；
  当前结论是「LinUCB 与随机不可区分（95% CI 跨 0），仅验证闭环连通性」。

---

## 9. 目录结构

```
skillnet-demo/
├── run.py                     启动器（27 行）
├── server.py                  FastAPI 服务（850 行，21 个端点）
├── verify.py                  交付自检（31 项）
├── skillnet/                  核心库（16 模块，约 3,900 行）
│   ├── schema.py              数据模型
│   ├── catalog.py             技能库 + 关系图
│   ├── index.py               BM25 / 向量 / 融合
│   ├── retriever.py           三档检索 + 降级 + 置信度分流
│   ├── orchestrator.py        依赖编排
│   ├── bandit.py              共享 LinUCB
│   ├── agent.py               方案生成
│   ├── sandbox.py             代码执行沙箱
│   ├── executor.py            真实执行 + 修复循环 + 技能验收
│   ├── judge.py               评分
│   ├── evolver.py             技能进化
│   ├── artifacts.py           产物渲染 + 交付物生成
│   ├── adapters.py            跨框架导出
│   ├── llm.py                 LLM 客户端 + 成本账本
│   └── config.py              路径配置
├── seed/
│   ├── catalog_data.py        技能数据源（1,363 行，`S(...)` 条目）
│   └── skills/*/SKILL.md      技能目录导出
├── tasks/
│   ├── benchmark.json         dev 集（20 任务，含 gold）
│   └── heldout.json           冻结测试集（12 任务）
├── bench/run_bench.py         三组实验脚本（支持 --dataset dev/heldout）
├── web/                       前端（零依赖，共 2,379 行）
│   ├── briefing.html          汇报演示页
│   ├── graph.html             交互式星图
│   └── index.html             完整面板
├── tools/
│   ├── selfcheck.py           交付自检（18 项）
│   ├── front_check.js         前端渲染自检
│   └── import_member_skills.py 外部技能导入（幂等）
├── scripts/build_report_data.py  单一数据源生成
├── config/experiment.yaml     实验唯一配置源
├── docs/                      文档（本文件、说明文档、迭代日志、论文对照、变更记录）
└── report/                    技术报告（PDF + LaTeX 源）
```

---

## 10. 已实现 / 未实现（速查）

### 已实现并有验证
三档检索与降级可观测 · 置信度分流（32 任务零误杀）· 关系图扩展（BM25 66.7%→Fabric 100%，
单次实测）· 共享 LinUCB（跨技能泛化有 pytest 锁定）· 真实执行沙箱（Run→Validate→Fix）·
技能 verification 逐条验收（带证据）· 执行记账与失败归档 · 交付物生成（声明 N 项→生成 M 项）·
产物指纹 · 跨框架导出（4 种）· dev/heldout 治理 · 三层自检 · 迭代日志机制

### 未实现（已在第 11 节展开）
全流程分步执行 · 产物级程序化评估 · 独立评审（当前自评）· judge 与执行者异模型 ·
并发压测 · 沙箱资源配额 · 产物目录清理 · 成本预算上限 · 结构化日志 · 移动端适配 ·
技能审批工作流（candidate→approved→active）· 跨模型迁移验证

---

## 11. 已知缺陷与边界（请重点评审此节）

> 本节按「影响面」从大到小排列。每条给出：现象 → 证据/位置 → 后果 → 建议方向。

### 11.1 影响「结论可信度」的缺陷（最需要评审）

| # | 缺陷 | 证据 | 后果 |
|---|---|---|---|
| D1 | **评审与被评者是同一模型** | `judge.py` 调用 `chat(role="judge")`，但 `model` 与执行者相同（`llm.py:144`），role 仅用于计费分账 | 评分是自评，存在系统性偏乐观 |
| D2 | **参照点与提示词同源** | `reference_points_from_skills()` 从 gold 技能的 pitfalls/verification 抽点，而这些技能又注入执行提示词 | 「要点覆盖」存在循环论证倾向，不能称为"客观指标"（文档已改名 skill-derived coverage） |
| D3 | **对照实验是单次展示** | 演示页三方对照各跑 1 次 | 不是统计结论；要下判断需多任务多轮次（同实验三的 bootstrap 口径） |
| D4 | **执行成功 ≠ 结论正确** | 沙箱只验证"代码能跑通 + 技能清单条目", 不验证数值正确性 | 代码可能跑出错误但自洽的结果；模拟数据可能被当成结论（提示词要求标注，但无技术强制） |
| D5 | **技能验收仍是 LLM 判定** | `_verify_with_skill()` 用模型判定清单条目 | 虽强制要求引用产物证据，但仍是判断而非证明；图表存在性、CSV 行列数等本可程序化 |

### 11.2 影响「工程可靠性」的缺陷

| # | 缺陷 | 证据 | 后果 |
|---|---|---|---|
| D6 | **沙箱不是对抗性隔离** | `sandbox.py` 仅子进程 + 超时 + 环境变量白名单；无网络阻断、无内存/CPU 配额 | 面向可信代码可用；若技能来自不可信来源则风险高 |
| D7 | **执行只落地一步** | `pick_executable_step()` 只挑一步 | 方案里的其余步骤仍是文本，不是可执行产物 |
| D8 | **编排顺序未驱动执行** | `order` 只进展示字段与提示词 | 依赖图的价值未在执行层体现 |
| D9 | **未做并发压测** | 并发安全只有单元级验证（`verify.py` 的 2 写 4 读） | 多请求同时跑沙箱/进化的行为未验证 |
| D10 | **产物目录无清理** | `out/demo_artifacts/` 每次任务新增目录 | 长期运行会无限增长 |
| D11 | **无成本上限** | 一次闭环约 ¥0.13（实测 0.048–0.134） | 无预算保护，异常循环可能超支 |
| D12 | **无结构化日志与追踪** | 仅 `logging` 文本日志 | 线上问题定位困难 |

### 11.3 影响「用户可用性」的缺陷

| # | 缺陷 | 证据 | 后果 |
|---|---|---|---|
| D13 | **服务重启后策略清零** | LinUCB 的 A/b 不落盘 | 学习成果不跨重启（有意为之以避免演示污染，但生产不合理） |
| D14 | **首次打开无引导** | 无 onboarding，无"能问什么"提示 | 新用户不知道从哪开始 |
| D15 | **长任务无进度** | `/api/demo` 一次性返回，最长等待 60–90s | 期间用户只看到阶段卡在"执行中"，不知内部进度 |
| D16 | **两次运行覆盖同目录** | 任务指纹相同则覆盖 `demo_artifacts/{slug}/` | 无法对比同一任务的历史两次运行 |
| D17 | **移动端未适配** | CSS 只有简单的 `@media` 降级 | 小屏体验差 |

### 11.4 数据与技能库的缺陷

| # | 缺陷 | 证据 | 后果 |
|---|---|---|---|
| D18 | **技能库规模仍小** | 90 个（vs 论文 500k） | 检索难度低，绝对指标偏高；相对收益需在真实规模验证 |
| D19 | **导入技能的契约是"提炼"** | 24 个导入技能的 steps/pitfalls/verification 由脚本从原文提取，非作者确认 | 字段质量参差 |
| D20 | **`origin_task` 未写入** | schema 有此字段但 `_admit` 未填 | 演化技能来源追溯不完整 |
| D21 | **质量分是启发式** | `assess_quality` 用关键词 + 相似度 | 不代表真实可用性 |
| D22 | **技能扩容后未重跑实验** | 实验数据均为 51 技能/62 边条件 | 当前 90 技能/162 边的库没有对应实验数据（文档已标注，未篡改） |

### 11.5 我主动提出的质疑（供评审参考）

1. **"技能运维层"这个定位是否成立**？——本项目实际提供的是检索+执行+评估+进化四件事，
   把它们统称"运维"是否准确？还是应该拆成更明确的模块？
2. **关系图的价值是否被高估**？——实测只有单次任务对比（66.7%→100%），样本不足；
   且图扩展可能引入噪声（补入不相关技能）。
3. **"技能验收"是否是真差异化**？——Anthropic 官方 Skills 也支持脚本执行，
   我们的验收本质是"用技能里的清单做 LLM 检查"，是否足够构成壁垒？
4. **进化是否值得**？——蒸馏出的 15 个技能，其质量与种子技能相比如何？**没有做过对比评估**。
5. **演示价值 vs 产品价值**——页面做得再漂亮，核心仍是"检索 + 执行"两件事；
   是否应该在真实业务上先跑通一个窄场景（而非继续扩展功能）？

---

## 12. 如何运行与验证

```bash
# 1. 启动（本机依赖已装：fastapi/uvicorn/httpx/pydantic/numpy/matplotlib）
python run.py                    # → http://127.0.0.1:8848

# 2. 三个页面
#    http://127.0.0.1:8848/        汇报演示页（对话式闭环演示）
#    http://127.0.0.1:8848/graph   交互式技能星图
#    http://127.0.0.1:8848/dashboard 完整面板

# 3. 三层自检
python verify.py                         # 31 项
python -m pytest tests/ -q               # 11 项
python tools/selfcheck.py                # 18 项（需服务运行）
node tools/front_check.js                # 5 项

# 4. 无密钥模式（降级可观测验证）
mv .env .env.bak && python run.py        # fabric 会显式降级，LLM 相关端点返回 503
```

**验证要点（建议评审按此顺序）**：
1. 先跑 `selfcheck.py` 与 `verify.py`，确认基础健康；
2. 打开 `/graph`，拖拽几个节点与缩放，点击节点看详情（含执行统计）；
3. 在 `/` 输入一个科研任务，观察七阶段；**重点看阶段 5**（真实执行）与阶段 7（产物）；
4. 在 `/` 阶段 5 点「跑三方对照」，观察三种技能使用模式的差异；
5. 打开 `out/demo_artifacts/{slug}/` 目录，核对产物文件与页面显示是否一致；
6. 阅读 `docs/iteration-log.md`，看迭代方法是否成立。

---

## 13. 术语表

| 术语 | 含义 |
|---|---|
| Skill Contract | 技能契约：capability / inputs / outputs / use_when 四个字段 |
| 五维质量 | safety / completeness / executability / maintainability / cost_awareness |
| 类型化关系边 | `depend_on` / `compose_with` / `similar_to` / `belong_to` |
| Fabric | 本项目最高档检索：hybrid + 关系图扩展 + LLM 重排（沿用论文命名） |
| 置信度分流 | 按 BM25 原始分把查询分为 自动执行 / 建议确认 / 无匹配直答 |
| 技能验收 | 用技能 verification 清单逐条核对产物，要求引用证据 |
| 执行记账 | 把执行成败写入技能 stats 并归档，作为技能质量信号 |
| dev / heldout | 调参集 / 冻结测试集（后者只用于最终结论） |
| 产物指纹 | 产物内容的 sha256 前缀（同任务重复运行一致，可审计） |


## 能力自证端点（/api/capabilities）

对照表里承诺的每项能力都可以**自行核对**，不依赖文案：

```
GET /api/capabilities
→ library{s skills/domains/edges/seed/evolved}   实时库规模
→ linucb{generalization_ratio, near_delta, far_delta}   现场计算的跨技能泛化比
→ confidence_gating{auto_execute_threshold, manual_confirm_threshold, calibration}
→ quality_dimensions[]（五维）· evolver_operators[]（四算子）
→ framework_targets{}（四种导出落点）· ledger{} · statistics{} · reproducibility{}
```

页面「与 SkillNet 论文逐项对照」表的每个「展开」按钮都调用该端点渲染实时值、
实现位置、锁定测试与自核命令。
