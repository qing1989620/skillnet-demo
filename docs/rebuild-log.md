# 重构日志（Rebuild Log）

> 方法：Observe → Attack → Prioritize → Implement → Measure → Compare → Keep/Reject → Red Team
> 铁律：**没有 measurement / screenshot / benchmark / test 的成果不计分**；不利结果必须保留。

---

## Round 0 · Baseline（2026-10-02 10:17–10:35）

**Observe（真实运行 + 测量，非估计）**

| 项 | 数据 | 来源 |
|---|---|---|
| 代码规模 | Python 17,554 行 + 前端 2,379 行 | `wc -l` |
| 测试 | verify 31/31（5.2s）· pytest 11/11（26.2s）· selfcheck 18/18（0.39s）· front 5/5（0.15s） | `out/baseline/*.txt` |
| 首页截图 | 1440×900 / 1280×800 / 1024×768 / 390×844 | `out/baseline/home_*.png` |
| 星图 / 面板截图 | 1440×900 / 1440×1500 | `out/baseline/graph_*.png`、`dashboard_*.png` |
| 端到端时长 | p50 **47.5s** / max 77.8s（n=3） | `out/baseline/profile.json` |
| 单次成本 | 平均 **¥0.1398**（区间 0.114–0.179） | 同上 |
| tokens | 平均 **33,772** | 同上 |
| LLM 调用 | **8–9 次/run**，其中 executor 3–4 次（生成代码+修复） | 账本 `by_role` |
| 成本大头 | executor ¥0.07–0.13（占总额 60–80%） | 同上 |
| 沙箱占比 | 1.7–19.3s（**总时长的大头是 LLM 串行等待**） | 同上 |

**Attack（首屏审读，看的是像素不是代码）**

| # | 问题 | 证据 |
|---|---|---|
| B1 | **首屏是"解释产品"而非"产品在运行"**：全是文字叙述（问题/方案），没有一个实时数据、没有一个可点入口 | `home_1440x900.png` |
| B2 | **无主 CTA**：用户 10 秒后不知道下一步做什么 | 同上 |
| B3 | **移动端顶栏崩溃**：品牌/状态/导航挤压成竖排；痛点卡第 3 张被裁切（水平溢出） | `home_390x844.png` |
| B4 | **无运行状态**：没有执行成功率、总运行数、健康/降级状态 | 首屏 + `/api/health` 只有 skills/evolved |
| B5 | **等待期无反馈**：47s 只有阶段卡"执行中"，无真实进度 | profile + 前端代码（`await tick()` 为假节奏） |

**Prioritize（只做影响最大的）**
1. B5 + 后端断裂（只执行一步）→ **Run Runtime + 多步 DAG + 事件流**（P0）
2. B1/B2/B4 → 首屏重做（Mission Control：运行状态 + 主 CTA）
3. B3 → 响应式修复

**Implement（Round 0 已落地代码）**

| 新增 | 作用 | 行数 |
|---|---|---|
| `skillnet/runtime.py` | Run / RunStep / ExecutionAttempt / Artifact / ProgrammaticCheck / VerificationResult / TraceEvent + RunStore（不覆盖历史）+ Budget 守卫 + 事件总线 | ~430 |
| `skillnet/checks.py` | **Verification L1**：文件存在/非空、CSV 表头与行数与列数一致、JSON、PNG IHDR 尺寸、Python 可编译、数值范围；**L2**：技能 machine-readable 断言（`[artifact_exists] *.csv` / `[csv_columns] a,b` / `[numeric_range] score 0 1` / `[min_rows] 5` / `[image_min] w h` / `[json_keys] ...`） | ~250 |
| `skillnet/pipeline.py` | **多步 DAG 真实执行**：前序产物复制进后序沙箱目录（文件系统级）；失败重试；上游失败阻断下游；每步 L1/L2/L3 验收；事件流 | ~300 |

**Measure（Round 0 验证结果）**

两步骤真实任务（data-cleaning → eda-profiling）：

```
Run 状态 COMPLETED | 34.2s | ¥0.0868 | 17,569 tokens
[0] done  1 次通过  产物 3 个（cleaned.csv 4.8KB / data_dictionary.csv / figure.png）
           L1/L2 检查 18/19 · L3 技能验收 3/3
[1] done  2 次尝试（失败→修复成功）  输入 = 第 1 步的 3 个文件
           产物 3 个（figure.png 91KB ...）· L1/L2 检查 19/19
★ 关键验证：第二步代码中真的出现输入文件名 = True（前序产物进入后序，非提示词级）
事件流 58 条（step.started / code.generating / step.attempt / artifact.created / check.result）
Run 落盘成功（同任务重跑不会覆盖）
```

**Compare（before → after）**

| 指标 | 重构前 | 重构后 |
|---|---|---|
| DAG 步骤被真实执行的个数 | 1 | **2+（按方案步骤数，受 max_steps 限制）** |
| 前序产物进入后序输入 | 不存在 | **文件系统级真实（已验证）** |
| 每步验收层数 | 1（仅 LLM） | **3（L1 确定性 / L2 技能断言 / L3 LLM）** |
| 运行标识 | 无 | `run_id` / `step` / `attempt` 贯穿 |
| 运行历史 | 覆盖同目录 | **独立 run_id + 落盘 + 可列表** |
| 事件流（供实时推送） | 无 | **58 条/run，含每步尝试与产物** |
| 预算守卫 | 无 | cost / calls / seconds / attempts 四项 |

**Reviewer attack（下一轮必须回应）**

- **冷酷用户**：我还是要等 47 秒才看到东西——你的实时呢？→ **Round 1 必须做 SSE**
- **Principal Engineer**：`pipeline` 仍顺序执行，"独立节点可并发"只是注释，没实现
- **ML/Eval**：L3 仍是同模型自评；L1/L2 只覆盖产物形态，不校验数值正确性
- **投资人**：这些是"把断掉的链路接上"，不是新壁垒；壁垒要靠 L2 断言生态与进化治理
- **竞品 PM**：Langfuse/E2B 已在做 trace 与沙箱，你的 3 个新模块加起来约 980 行，他们各是成熟产品

**Decision**：KEEP（有实测支撑，且修的是最严重的产品断裂）

---

## Round 1 计划（下一步）

**P0 剩余**
1. API：`/api/runs`（列表）· `/api/runs/{id}`（详情）· `/api/runs/{id}/stream`（**SSE 实时事件**）· `/api/runs/{id}/cancel`（取消）
2. 前端 Run 视图：Live Run（真实事件驱动，替换假 `tick()` 动画）+ Run 历史 + Run 对比
3. 首屏重做（Mission Control）：实时运行状态 + 主 CTA
4. 响应式修复（390px）
5. 成本预算与取消接入 UI

**P1**
6. eval 维度对比（contract / prompt / none + seed vs evolved）
7. 星图升级为 Capability Topology（默认任务相关子图 + 筛选/下钻）
8. 进化治理状态机（CANDIDATE→VALIDATING→APPROVED→ACTIVE）

**已知不做**（见 competitive-audit 第 5 节）
自建完整 observability 平台 / microVM 隔离 / 通用 eval 平台
