# -*- coding: utf-8 -*-
"""
408 备考：考点矩阵 + 错题台账 + 误差归因 + 套卷收敛
注意：本脚本中所有数据均为【模拟数据】，仅用于演示流程与校验逻辑，
      不代表任何真实考试结论。
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

RNG = np.random.default_rng(42)  # 固定随机种子

# ============ 1. 考点矩阵（模拟数据） ============
# 章节 -> (卷面分值, 知识点列表)
CHAPTERS = {
    "数据结构": 45, "计算机组成原理": 45, "操作系统": 35, "计算机网络": 25,
}
TOTAL_SCORE = 150
TOPICS = {
    "数据结构": ["线性表", "树与二叉树", "图", "查找", "排序"],
    "计算机组成原理": ["数据的表示", "运算器", "存储系统", "指令系统", "CPU与流水线"],
    "操作系统": ["进程管理", "内存管理", "文件管理", "I/O管理"],
    "计算机网络": ["体系结构", "数据链路层", "网络层", "传输层", "应用层"],
}
QUESTION_TYPES = ["选择", "综合应用"]

# 生成矩阵行：章节-知识点-题型-出现年份-分值-掌握度
matrix_rows = []
for ch, topics in TOPICS.items():
    for tp in topics:
        for qt in QUESTION_TYPES:
            years = sorted(RNG.choice(range(2015, 2025), size=RNG.integers(2, 6), replace=False).tolist())
            score = int(RNG.integers(2, 9))
            mastery = int(RNG.integers(1, 6))
            matrix_rows.append([ch, tp, qt, ";".join(map(str, years)), score, mastery])

# 校验：各章分值合计 vs 卷面总分（误差<=2）
ch_sum = {ch: 0 for ch in CHAPTERS}
for r in matrix_rows:
    ch_sum[r[0]] += r[4]
# 归一化到卷面分值（模拟数据按比例缩放）
scale = TOTAL_SCORE / sum(ch_sum.values())
for r in matrix_rows:
    r[4] = round(r[4] * scale, 2)
ch_sum = {ch: 0.0 for ch in CHAPTERS}
for r in matrix_rows:
    ch_sum[r[0]] += r[4]
err = abs(sum(ch_sum.values()) - TOTAL_SCORE)
print("=== 考点矩阵校验 ===")
for ch, s in ch_sum.items():
    print(f"  {ch}: 分值合计={s:.2f} 占比={s/TOTAL_SCORE*100:.1f}%")
print(f"  卷面总分={TOTAL_SCORE} 误差={err:.2f} (要求<=2) -> {'通过' if err<=2 else '不通过'}")
assert err <= 2, "分值合计误差超限"

# 随机抽3个高频知识点回溯真题年份
print("\n=== 随机抽3个知识点回溯真题年份 ===")
idx = RNG.choice(len(matrix_rows), size=3, replace=False)
for i in idx:
    r = matrix_rows[i]
    print(f"  {r[0]} | {r[1]} | {r[2]} | 年份={r[3]} | 分值={r[4]} | 掌握度={r[5]}")

# ============ 2. 优先级排序 ============
print("\n=== 章节优先级（分值占比×(6-掌握度)） ===")
ch_mastery = {}
for ch in CHAPTERS:
    ms = [r[5] for r in matrix_rows if r[0] == ch]
    ch_mastery[ch] = np.mean(ms)
prio = []
for ch in CHAPTERS:
    p = (ch_sum[ch] / TOTAL_SCORE) * (6 - ch_mastery[ch])
    prio.append((ch, p, ch_mastery[ch]))
prio.sort(key=lambda x: -x[1])
for ch, p, m in prio:
    print(f"  {ch}: 优先级={p:.3f} 平均掌握度={m:.2f}")

# ============ 3. 错题台账（模拟数据） ============
N = 120  # 样本量>=100，可建模
ledger = []
for i in range(N):
    ch = RNG.choice(list(CHAPTERS.keys()))
    tp = RNG.choice(TOPICS[ch])
    qt = RNG.choice(QUESTION_TYPES)
    year = int(RNG.integers(2015, 2025))
    qno = int(RNG.integers(1, 41))
    correct = int(RNG.random() > 0.35)
    time_min = round(float(RNG.uniform(1, 15)), 1)
    cause = RNG.choice(["概念不清", "计算失误", "审题", "记忆", "待补"])
    ledger.append([f"{year}-{qno}", year, qno, ch, tp, qt, correct, time_min, cause])

# 主键唯一性检查
keys = [r[0] for r in ledger]
print("\n=== 错题台账校验 ===")
print(f"  记录数={len(ledger)} 主键唯一={len(set(keys))==len(keys)}")
print(f"  待补记录数={sum(1 for r in ledger if r[8]=='待补')} (保留不删除)")

# 各章错题数之和 = 总错题数
wrong = [r for r in ledger if r[6] == 0]
ch_wrong = {ch: 0 for ch in CHAPTERS}
for r in wrong:
    ch_wrong[r[3]] += 1
print(f"  总错题数={len(wrong)} 各章错题之和={sum(ch_wrong.values())} -> {'一致' if len(wrong)==sum(ch_wrong.values()) else '不一致'}")

# 随机抽5条回溯
print("  随机抽5条记录:")
for i in RNG.choice(len(ledger), size=5, replace=False):
    r = ledger[i]
    print(f"    {r[0]} | {r[3]} | {r[4]} | {r[5]} | 对错={r[6]} | 用时={r[7]}min | 错因={r[8]}")

# ============ 4. 误差归因（样本>=100，用简单逻辑回归） ============
print("\n=== 误差归因（逻辑回归基线，模拟数据） ===")
# 特征：章节one-hot + 用时
ch_list = list(CHAPTERS.keys())
X = np.zeros((N, len(ch_list) + 1))
y = np.zeros(N)
for i, r in enumerate(ledger):
    X[i, ch_list.index(r[3])] = 1
    X[i, -1] = r[7]
    y[i] = 1 - r[6]  # 1=做错

# 按时间划分前70%训练后30%验证
split = int(N * 0.7)
Xtr, Xte, ytr, yte = X[:split], X[split:], y[:split], y[split:]

# 简单逻辑回归（梯度下降）
w = np.zeros(X.shape[1])
lr, epochs = 0.01, 500
for _ in range(epochs):
    z = Xtr @ w
    p = 1 / (1 + np.exp(-z))
    grad = Xtr.T @ (p - ytr) / len(ytr)
    w -= lr * grad

def predict(X, w):
    return (1 / (1 + np.exp(-(X @ w))) > 0.5).astype(int)

# 各章错误率（人工统计）
print("  各章错误率（人工统计）:")
manual_err = {}
for ch in ch_list:
    sub = [r for r in ledger if r[3] == ch]
    er = sum(1 for r in sub if r[6] == 0) / len(sub)
    manual_err[ch] = er
    print(f"    {ch}: {er:.3f}")

# 模型验证集错误率排序
print("  模型验证集各章错误率排序:")
model_err = {}
for ch in ch_list:
    mask = Xte[:, ch_list.index(ch)] == 1
    if mask.sum() > 0:
        model_err[ch] = predict(Xte[mask], w).mean()
    else:
        model_err[ch] = 0.0
    print(f"    {ch}: {model_err[ch]:.3f}")

# Top3 重合检查
top_manual = sorted(manual_err, key=lambda x: -manual_err[x])[:3]
top_model = sorted(model_err, key=lambda x: -model_err[x])[:3]
overlap = len(set(top_manual) & set(top_model))
print(f"  Top3重合数={overlap} -> {'通过' if overlap>=2 else '需复核'}")

# 超时题清单（用时>10min）
print("\n  超时题清单（用时>10min）:")
for r in ledger:
    if r[7] > 10:
        print(f"    {r[0]} | {r[3]} | 用时={r[7]}min")

# ============ 5. 限时套卷收敛（模拟数据） ============
print("\n=== 限时套卷收敛（模拟数据） ===")
target = 0.75
scores = [0.68, 0.72, 0.76, 0.78, 0.77, 0.79]
for i, s in enumerate(scores, 1):
    print(f"  第{i}套: 正确率={s*100:.1f}% {'达标' if s>=target else '未达标'}")
# 连续3套波动<=5%且>=目标线
converged = False
for i in range(len(scores)-2):
    window = scores[i:i+3]
    if max(window)-min(window) <= 0.05 and min(window) >= target:
        converged = True
        print(f"  连续3套（第{i+1}-{i+3}套）波动={max(window)-min(window):.3f}<=0.05 且均>=目标线 -> 进入查漏阶段")
        break
if not converged:
    print("  尚未收敛，继续套卷训练")

# ============ 6. 反复出错知识点触发重学 ============
print("\n=== 反复出错知识点（错>=2次触发重学） ===")
topic_wrong = {}
for r in wrong:
    key = (r[3], r[4])
    topic_wrong[key] = topic_wrong.get(key, 0) + 1
for (ch, tp), cnt in topic_wrong.items():
    if cnt >= 2:
        print(f"  {ch} | {tp}: 错{cnt}次 -> 触发重学")

# ============ 7. 出图 ============
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
# 左：各章分值占比
chs = list(CHAPTERS.keys())
vals = [ch_sum[c] for c in chs]
axes[0].bar(chs, vals, color='steelblue')
axes[0].set_title('各章分值分布（模拟数据）')
axes[0].set_ylabel('分值')
axes[0].tick_params(axis='x', rotation=15)

# 右：套卷正确率趋势
axes[1].plot(range(1, len(scores)+1), [s*100 for s in scores], marker='o', color='coral')
axes[1].axhline(target*100, color='green', linestyle='--', label=f'目标线{target*100:.0f}%')
axes[1].set_title('套卷正确率趋势（模拟数据）')
axes[1].set_xlabel('套卷序号')
axes[1].set_ylabel('正确率(%)')
axes[1].legend()
plt.tight_layout()
plt.savefig('figure.png', dpi=100)
print("\n图已保存: figure.png")

# ============ 8. 落盘 CSV ============
import csv
with open('topic_matrix.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['章节', '知识点', '题型', '出现年份', '分值', '掌握度'])
    w.writerows(matrix_rows)

with open('error_ledger.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['主键', '年份', '题号', '章节', '知识点', '题型', '对错', '用时min', '错因'])
    w.writerows(ledger)

print("CSV已保存: topic_matrix.csv, error_ledger.csv")
print("\n【声明】以上所有数据均为模拟数据，仅用于演示备考流程与校验逻辑。")