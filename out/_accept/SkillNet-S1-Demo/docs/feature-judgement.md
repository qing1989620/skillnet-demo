# 功能审判（Keep / Fix / Demote / Kill）

> 日期：2026-10-02　｜　判据：**这个功能能不能回答"专业用户为什么因此选择我们"**？
> 不能回答的一律不能算亮点。

---

## KEEP — 有真实价值，保留并加强

| 功能 | 为什么保留 | 现成证据 |
|---|---|---|
| Skill Contract（能力/输入/输出/时机 + steps/pitfalls/verification） | 它是"技能是资产而不是提示词"的唯一载体；执行、验收、修复全都依赖它 | 执行阶段把它作为代码生成约束与验收标准，实测产出真实图表（`figure.png` 90KB） |
| 类型化关系图（4 类边 / 162 条） | 技能之间有关系才有"组合"与"影响分析" | 规范化逻辑有注释与验证（消除矛盾边 22 条） |
| 三档检索 + 降级可观测 | 离线可用是硬需求；静默降级是坑 | 缺密钥时显式返回 `degraded/components/reason` |
| 置信度分流 | 产品化决策逻辑，避免"硬套技能" | 42 条查询标定，32 条真实任务零误杀（有 pytest） |
| 真实执行沙箱 | 与"写方案的 LLM"的分水岭 | 实测 1.9s 跑出图表；失败修复循环真实触发过 |
| 技能 verification 验收 | **潜在独占能力**：observability 产品不评"能力是否合格" | 验收带证据（`SEED=42；stratified_kfold(y,5,SEED)`） |
| 执行记账（`exec_*`） | 让"技能可靠性"成为可观测信号 | `executions.jsonl` 归档；页面展示成功率 |
| 产物层 + 指纹 | 产物必须可核对、可审计 | `report.html` + `plan.md` + sha256 指纹 |
| dev / heldout 治理 | 没有它所有数字都不可信 | 主动披露 dev→heldout 编排完整度 92.5%→25.0% |
| 三层自检（65 项） | 交付可信度的基础 | verify 31 / pytest 11 / selfcheck 18 / front 5 全绿 |

## FIX — 方向正确，但实现没有兑现承诺

| 功能 | 现状问题 | 修复方向 | 优先级 |
|---|---|---|---|
| **多步执行** | Orchestrator 输出 DAG，但 Runtime **只执行一步**——这是最大产品断裂 | DAG 节点成为可执行 step：前序产物→后序输入；依赖顺序；失败重试；上游失败阻断下游；每步独立验收 | **P0** |
| **可观测性 / 进度** | `/api/demo` 一次性返回，最长 60–90s 白等；无 run/step/attempt 标识 | Run 状态机 + SSE 事件流（`step.started` / `stdout` / `artifact.created` / `verification.result`）；结构化 trace | **P0** |
| **Verification 分层** | 全部交给 LLM 判定（`_verify_with_skill`），本可程序化的（文件存在、表头、数值范围、退出码）也走模型 | 三层：① 确定性校验（代码）② 技能声明的 machine-readable 断言 ③ LLM 语义复核 | **P0** |
| **LinUCB** | 实现与测试都在，但**收益未在 heldout 证实**（实验三结论：与随机不可区分） | 降级为 `Experimental adaptive ranking`；补 heldout 上"有/无策略"对比；测不出收益就不当卖点 | P1 |
| **关系图扩展** | 只有单次任务对比（BM25 66.7%→Fabric 100%），样本不足；且可能引入噪声 | 在 heldout 上重跑 Recall@K / Precision@K / nDCG；量化 graph expansion 噪声 | P1 |
| **Evolution** | 蒸馏 16 个技能，但**没有任何"比种子技能更好"的证据**；生成即入库 | 加治理状态机（CANDIDATE→VALIDATING→APPROVED→ACTIVE→DEPRECATED）；只有对比证明提升才 ACTIVE；否则标 experimental | P1 |
| **评估** | judge 与执行者同模型（自评）；参照点与提示词同源 | 引入确定性证据（产物检查）降低对 judge 的依赖；judge 提示显式标注局限；异模型 judge 作为可选 | P1 |
| **Run 历史** | 同任务重复运行**覆盖**同目录，无法对比 | Run ID 独立（同 task 指纹分组）；支持 compare / rerun / cancel | P1 |
| **成本** | 无预算上限 | 每 Run 设 max cost / max calls / max attempts / max time；超限进入 `BUDGET_EXCEEDED` | P1 |

## DEMOTE — 可以留，但不能再当核心卖点

| 功能 | 为什么降级 |
|---|---|
| **技能星图** | 当前是"漂亮但无信息价值"的展示：不能做依赖探索、影响分析、健康度、失败热点、使用频率筛选。降级为探索视图；升级为 **Capability Topology**（默认只画当前任务相关子图 + 支持筛选/下钻）后才可回到卖点 |
| **五阶段动画** | 演示效果好，但那是"演示能力"不是"产品能力"；不能用来掩盖等待 |
| **三方对照实验** | 单次展示，**不是统计结论**——页面上已标注；要成为卖点必须多任务多轮次 |
| **论文对照表** | 叙事材料，非产品能力 |

## KILL — 复杂度大于价值，删除或合并

| 项 | 理由 | 处理 |
|---|---|---|
| `web/index.html` 的「演示」视图 | 与 briefing 演示页功能重复，且是静态表单，无独立价值 | 删除视图，改为跳链 |
| `web/index.html` 的「执行」视图 | 同上（选技能+风格的表单），briefing 的对话式已覆盖 | 删除视图，改为跳链 |
| `/api/skills-index`（扁平索引） | 仅用于对照实验的"技能是否被激活"，但该实验已用更精确的 adoption 指标 | 保留但标注为实验用途，不进 UI |
| `out/_sbx_test` / `out/_exec_test` 等测试残留 | 开发残留，污染产物目录 | 清理 + 加入 .gitignore |
| 星图的「只看演化技能」按钮 | 使用频率极低，且演化技能本可高亮而非过滤 | 合并进统一的筛选控件 |

---

## 审判方法说明

每一条判定都必须能回答：
1. **它解决谁的什么问题**（具体用户 + 具体场景）
2. **有什么证据证明有效**（measurement / artifact / test / screenshot）
3. **删掉它会损失什么**（若答不出，就该删）

判为 KEEP/FIX 的功能，其"修复方向"已进入 `docs/rebuild-log.md` 的轮次计划。
