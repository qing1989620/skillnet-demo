# E00 / Phase A 基线审计

审计日期：2026-11-04。源仓库：qing1989620/skillnet-demo。冻结生产基线：`0af2de6a9c8b129e174e3442b67c5f7cb4324db9`；交付版 `2026.10.14-complete.22`。

## 实际核验结果

| 项目 | 结果 | 范围 |
| --- | --- | --- |
| 官方严格交付校验 | 13,513 文件通过，零差异 | 使用原 `tools/verify_delivery.py --strict-runtime`，不是自创替代校验 |
| Skill 库 | 1,881 | 实际 `SkillLibrary.load()` 与 D0 快照 |
| 社区 Skill | 1,769 | 三个固定提交来源；每包登记文件全部重算哈希 |
| 登记社区文件 | 10,898 | 76,123,796 字节；包括 SKILL.md、资源和署名文件，不是独立 Skill 数 |
| 原项目完整回归 | 1,244 通过 | 首轮 1,243 + 1 个 SciPy 缺失跳过；安装依赖后最终重跑全量，无跳过 |
| 研究层测试 | 101 通过 | 假数据单测不充当研究样本 |
| 最终合并回归 | 1,345 通过 | 原项目 + 研究层，零失败、零跳过 |
| 原 `verify.py` | 31/31 通过 | 无 `--llm`，主要验证 76 个种子；不代表全库执行通过 |
| 前端原检查 | 5 个脚本退出 0 | front_check/check_web/product_check/briefing_check/showcase_check；非浏览器像素验收 |
| 原始产物复算 | conditional / semantic / guard 三工具均通过 | 只读取、重算既有文件；没有重新发出历史 API 请求 |
| 静态与类型检查 | ruff、format、mypy 通过 | mypy 检查 17 个研究源模块；动态测试 egress hook 不作静态类型主张 |
| 新付费调用 / 新 Skill 执行 | 0 / 0 | 用户旧密钥未使用；Mock 与可信仓库测试不算科研执行试次 |

Python 为 3.12.10，Windows x86_64，CPU 环境；实际检测到 RTX 4050 Laptop GPU，但本阶段不需要 GPU。Docker 命令不可用，受控 Skill 执行不具备准入条件。精确依赖随 `requirements-lock-win-py312.txt` 保存。

测试使用独立 worktree。其 `out/exec_log/executions.jsonl` 和 `out/verify_report.json` 被原测试更新，均为官方交付校验排除的运行日志；研究主 checkout 的冻结生产文件和历史证据没有被这些写操作覆盖。测试前后严格交付校验仍通过。测试进程去除继承凭证并阻断非回环 Python socket，不能把这个守卫称为 Docker 沙箱。

## 已核对的接口

- `SkillLibrary(skills=None)`、`SkillLibrary.load(path=None, *, include_community=True)`：读取种子、社区与运行/基线层；`save()` 会写正式状态，研究不调用。
- `assess_quality(skill)`：五维卡片启发式；`quality_score(quality)` 的 Good/Average/Poor 映射是 1/0.6/0.25，缺失/不识别等级按 0.6 回退。
- `Retriever(lib).build()`；`search(query, *, k=5, mode='fabric', pool=20, expand=True, rerank=True)`：原排序含质量先验。研究没有改动这些默认。
- `resources.package_manifest(skill)`、`read_resource(skill,path)`：登记清单、路径边界和 SHA；资源是只读数据，不导入包内模块。
- `judge.score_plan` 是方案评分，不能充当 Skill 质量真值；原 DeepSeek 账本的人民币固定价没有用于 OpenRouter。
- `reward_gates` 为十二门 AND、unknown 阻断；所有候选仍为 shadow，未写奖励、共享权重或正式评级。

真实参数、行号和源文件指纹位于每个 E00 输出中的 `repository_audit.json`。

## 旧检索重新运行

使用仓库附带的 dense-onnx 编码器，明确无 LLM 密钥，k=5/pool=20；每个结果重复两次，并检查 shadow disabled 的 canonical-equivalent 一致性。共 192 个任务/候选框/模式记录，384 次搜索；重复不增加独立样本数。

| 候选框 / 旧任务集 | BM25 Recall@5 | Hybrid Recall@5 | Fabric 图扩展 Recall@5 |
| --- | ---: | ---: | ---: |
| 原 benchmark 种子 76 / 20 题 | 0.800000 | 0.725000 | 0.791667 |
| 原 benchmark 种子 76 / 12 题 heldout | 0.708333 | 0.770833 | 0.770833 |
| 完整交付库 1,881 / 20 题 | 0.741667 | 0.691667 | 0.800000 |
| 完整交付库 1,881 / 12 题 heldout | 0.652778 | 0.715278 | 0.784722 |

Fabric 的 LLM 重排为 **not_run**，结果自身也带 degraded 标记；上述图扩展数字不是完整付费 Fabric 的复现。旧 benchmark/heldout 已经历史可见，不能再当本轮 D5/D6 新盲测。两种候选框的差异也不能归因于新研究方法，本轮并未测量 A7/A9 的真实收益。

## 历史主张的证据边界

| 历史主张 | 状态 | 本轮独立证据与限制 |
| --- | --- | --- |
| 发布版、1,881 Skill、10,898 登记文件 | reproduced | 原校验工具和只读 D0 均支持 |
| 首轮 Gym 35.94% → 59.53% | reproduced（保存行的算术） | 从 64 行、32 题、14 家族的独立复查 CSV 重新平均为 0.359375 / 0.5953125；两次确定性重复不当作 64 题，没有重新训练模型或获取上游完整语料 |
| 外部 75 题 55.93% → 50.16% | not_run（新执行） | 保留仓库负结果；本轮没有完整外部特征/候选源，未重新运行模型评估 |
| 条件收益 48 次历史模型调用、2,684 次登记程序执行 | reproduced（保存产物） | 原核验工具重算首轮 2,504 + 新边界 180 份执行产物，API 决策为历史记录，不是本轮调用 |
| 自然语言 24 任务、144 次历史请求、139 次执行、257 输出文件 | reproduced（保存产物） | 原 public-audit 重新解包只读数据并复算，与归档报告一致；未运行 ZIP 内程序 |
| Glass guard 96 动作，44 可执行 / 52 不可执行 | reproduced（保存产物） | 原 guard 核验重算，误拦/漏拦/判据不一致均为 0，仅限归档范围，不是任意输入安全证明 |
| README 10 月 13 日的 1,086 测试 | version_mismatch | 属历史日期计数；当前提交有 1,244 个原测试，不能覆盖旧记录冒充当时结果 |
| Docker、远端 CI、S1 生产联调、浏览器像素验收 | not_run | 本机没有对应条件；旧 CI 声明不冒充本轮实测 |

没有发现需要改生产代码才能通过 E00 的故障。`not_run` 不等于历史主张被否证，保存产物算术通过也不等于已重新获取历史在线模型行为。

## 本轮应继续研究的实际缺口

D0 有 1,770 项缺失旧评级、15 项含非标准旧等级；已有有效旧等级与重新计算的启发式至少一维不同的项目有 69 项。这些数目分别报告，缺失不计作错误评级。全文静态线索涉及 23 项，全部仍需上下文人审，不能充当高风险 gold。

数据近重得到 25 个阈值内配对、1,871 个词级内容簇；来源/内容连接组为 1,612、157、112。D1=200，D2=200 的未标注模板已生成，但 D2 的 112 个派生卡片 / 88 个原文造成材料类型混杂，正式质量实验暂未准入。

最终本地复算入口：`python -m research.skill_quality.cli verify --run-id 20261104-phase-a-v3`。完整 E00、检索、验证与 D0 原始输出保留于 `out/research/skill-quality/`；公开 PR 仅含研究源码、协议和派生汇总，不含第三方完整正文或任何真实凭证。
