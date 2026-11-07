# E02：原五维启发式对照协议（未产生人类准确率结果）

版本：E02-draft-v1，2026-11-04。共同输入是固定 Skill UID、卡片 SHA 与原始全文 SHA。D1 可用于开发，D2 尚无标签；当前来源/材料类型问题见 PROTOCOL_REVIEW。

1. **S0-stored**：原样读取 `Skill.quality` 并调用 `quality_score`，复现生产先验。空字典保留为空，其 0.6 是默认先验，不是评价真值。
2. **S0-recomputed**：原样调用当前 `assess_quality(skill)`、`quality_score(...)`，输出等级及原理由。它只读取旧卡片字段，不冒充全文审查。两个 S0 均保留，不能替换后仍称“旧默认”。
3. **新画像**：八维 0–4，unknown/not_applicable/invalid 单独记。观察状态要有有效证据；缺失不能补零。
4. **预设尺度**：旧 Good/Average/Poor 的原权重为 1/0.6/0.25；诊断用线性映射为 4/2.4/1。它是数值预测，可计算 MAE，但不能直接将 2.4 当成人工 ordinal 类别计算 κ。若需离散映射，只能在 D1 选定后另行冻结。
5. **共同维度**：旧 completeness → completeness、executability → static_executability、maintainability → maintainability、cost_awareness → cost_awareness。只在相同适用且人工可观察的子层比较，报告全部覆盖分母。旧 safety 不映射成 safety_documentation；用独立安全裁决对旧 safety 另测错误接受/拒绝。
6. **不可比较的维度**：contract_consistency、verification_quality、provenance_license 和 safety_documentation 在旧五维中没有同构预测。标 unavailable，不能补分后宣称新方法八维平均误差更小。
7. **样本与盲法**：两位真实独立标注者，先 D1 的 20 例训练；D2 禁止看算法输出/历史分。分歧完成后由第三人仲裁，报告仲裁前 κ、未知比例、每维混淆矩阵、工时和专家复核范围。
8. **主要终点**：目标 D1 选择的 80% 自动覆盖率阈值；D2 报实际覆盖、MAE、有效证据、风险护栏及 CI。正式共同主终点通过规则尚未冻结，因此现在不做显著性结论。
9. **独立性**：来源/内容簇切分；跨来源近重不得拆开；家族重复不能当独立样本。当前只有三个连接组，需补来源或缩小主张。
10. **报告边界**：E02 目前是协议与材料准备，`human_gold_items=0`。不能将另一模型、Mock、多数票或规则扫描输出写成“人工 gold”。
