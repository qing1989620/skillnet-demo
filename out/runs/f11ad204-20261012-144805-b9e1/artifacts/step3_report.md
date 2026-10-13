# 复现审计报告：清洗与固定阈值评估

> **声明**：本报告基于**模拟数据**，采用**固定阈值**（score >= 0.5）评估，
> **不代表临床有效性**，不构成医学诊断或真实模型性能结论。

## 1. 数据清洗审计（来源：cohort_audit.csv）

| 检查项 | 计数 |
|---|---|
| raw_rows | 14 |
| duplicate_rows | 1 |
| cross_split_subjects | 1 |
| cross_split_rows | 2 |
| missing_score_rows | 1 |
| eligible_test_rows | 6 |

清洗流程：按 sample_id 去重保留首次记录；识别同时出现在多个 split 的 subject_id
并删除其全部记录；随后删除 score 缺失记录（missing_score_rows 在删除跨 split 受试者后统计）。

## 2. 固定阈值指标（来源：heldout_metrics.csv）

仅使用清洗后的 test 行，阈值固定为 score >= 0.5 判为阳性，未在测试集上选择阈值，未计算 AUROC。

| 指标 | 数值 |
|---|---|
| n | 6 |
| tp | 2 |
| fp | 1 |
| tn | 2 |
| fn | 1 |
| accuracy | 0.6666666667 |
| precision | 0.6666666667 |
| recall | 0.6666666667 |
| f1 | 0.6666666667 |

## 3. 数据泄漏风险

同一 subject_id 同时出现在多个 split（cross_split_subjects=1，
涉及 cross_split_rows=2 行）会造成**受试者级数据泄漏**：
同一受试者的样本可能同时进入训练与测试，导致测试指标被高估、泛化能力被夸大。
本流程通过删除全部跨 split 受试者记录来阻断该泄漏路径。

## 4. 复用边界

- 本结果为**模拟数据**上的审计演示，**固定阈值**设定，**不代表临床有效性**。
- 阈值 0.5 为预先固定，未在测试集上调优；不得据此推断最优阈值或真实部署性能。
- 复用时应保持去重、跨 split 受试者剔除、缺失值处理与固定阈值的一致性；
  任何改动（如重新划分 split、调整阈值）都需重新审计并重新评估。
- 图 figure.svg 中数值与 cohort_audit.csv、heldout_metrics.csv 一致，可追溯。
