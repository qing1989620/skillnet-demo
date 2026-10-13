# 科研复现审计报告

## 1. 数据来源声明
本报告全部基于**模拟数据**（synthetic / simulated data），由公开模拟科研预测数据生成，
**不涉及任何真实患者、真实实验或真实模型性能**。所有数值仅用于复现审计流程演示。

## 2. 阈值与评估口径
- 评估仅使用清洗后的 test 行。
- 阳性判定采用**固定阈值**：score >= 0.5。
- 阈值在评估前固定，**未使用测试集选择阈值**，未计算 AUROC。
- 结果**不代表临床有效性**，也不构成任何真实模型性能结论。

## 3. 队列审计结果（cohort_audit.csv）
| check | count |
|---|---|
| raw_rows | 14 |
| duplicate_rows | 1 |
| cross_split_subjects | 1 |
| cross_split_rows | 2 |
| missing_score_rows | 1 |
| eligible_test_rows | 6 |

处理顺序：按 sample_id 去重保留首次记录 → 识别跨 split 的 subject_id 并删除其全部记录
→ 在删除跨 split 受试者后统计并删除 score 缺失记录。

## 4. 留出集指标（heldout_metrics.csv，固定阈值 0.5）
| metric | value |
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

## 5. 数据泄漏风险
同一 subject_id 若同时出现在多个 split（如 train 与 test），其个体特征会跨越训练/评估边界，
导致**数据泄漏（data leakage）**：模型可能在训练阶段间接"见过"测试受试者，
使留出集指标被高估。本流程通过识别并删除全部跨 split 受试者记录来阻断该泄漏路径，
审计表中 cross_split_subjects = 1、
cross_split_rows = 2 即为被移除的泄漏来源。

## 6. 复用边界
- 本流程与结论**仅适用于本模拟数据集**，不可外推到真实临床场景。
- 固定阈值 0.5 为演示设定，不代表最优或临床推荐阈值。
- 任何复用须重新执行去重、跨 split 受试者剔除与缺失处理，并重新固定阈值。
- 严禁将本报告数值解读为临床有效性或真实模型性能证据。

## 7. 图注
figure.svg 左图为队列审计计数（模拟数据），右图为留出集混淆矩阵计数（固定阈值 0.5，模拟数据），
并标注样本量 n 与 accuracy/precision/recall/f1。坐标轴均从 0 起，未截断，未使用双轴。
