# 科研复现审计报告（模拟数据）

> **重要声明**：本报告基于**模拟数据**，采用**固定阈值** score >= 0.5 判定阳性，
> 结果**不代表临床有效性**，仅用于科研复现流程与数据泄漏审计演示。

## 1. 队列审计（cohort_audit.csv）

| 检查项 | 计数 |
|---|---|
| raw_rows（原始行） | 14 |
| duplicate_rows（按 sample_id 去重删除行） | 1 |
| cross_split_subjects（跨 split 受试者数） | 1 |
| cross_split_rows（跨 split 受试者记录行） | 2 |
| missing_score_rows（删除跨 split 后缺失 score 行） | 1 |
| eligible_test_rows（合格 test 行） | 6 |

## 2. 留出集指标（heldout_metrics.csv）

固定阈值 score >= 0.5，仅使用清洗后的 test 行；阈值未在测试集上选择，未计算 AUROC。

| 指标 | 值 |
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

- **跨 split 泄漏**：同一 subject_id 同时出现在 train/validation/test 时，其记录会
  造成训练与评估信息重叠。本流程识别并删除全部跨 split 受试者记录
  （cross_split_subjects=1，
  cross_split_rows=2），以降低该风险。
- **重复记录泄漏**：sample_id 重复会导致同一观测被多次计入，本流程按 sample_id
  去重保留首次记录（duplicate_rows=1）。
- **阈值选择泄漏**：若在测试集上挑选阈值，会高估性能。本流程使用**固定阈值 0.5**，
  未在测试集上做任何阈值搜索。

## 4. 复用边界

- 本流程与结论仅适用于**模拟数据**的复现审计，**不代表临床有效性**，不可用于
  任何医学诊断或真实模型性能声明。
- 指标（accuracy/precision/recall/f1）依赖固定阈值 0.5 与当前清洗规则，
  更换阈值、清洗策略或数据分布后需重新计算，不可直接外推。
- 未计算 AUROC，避免引入阈值无关但可能被误读的排序性指标。
- 复用本脚本时须保持输入文件契约（cohort_audit.csv、heldout_metrics.csv 的列名与行集），
  否则应报错而非静默重造数据。

## 5. 图表

见 `figure.svg`：左为队列审计计数，中为混淆矩阵（标注 n 与阈值 0.5），
右为留出集指标条形图。
