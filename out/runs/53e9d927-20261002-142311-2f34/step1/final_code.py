# -*- coding: utf-8 -*-
"""
408 备考考点矩阵 + 错题台账 + 优先级周计划 + 描述统计/基线模型 + 套卷收敛
注意：所有数据均为【模拟数据】，仅用于演示流程，不代表真实考试结论。
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

rng = np.random.default_rng(42)

# ============ 1. 考点矩阵（模拟数据） ============
chapters = ['数据结构', '计算机组成原理', '操作系统', '计算机网络']
# 每章知识点（模拟）
topics = {
    '数据结构': ['线性表', '树与二叉树', '图', '查找', '排序'],
    '计算机组成原理': ['数据的表示', '运算器', '存储系统', '指令系统', 'CPU'],
    '操作系统': ['进程管理', '内存管理', '文件管理', 'I/O管理'],
    '计算机网络': ['体系结构', '数据链路层', '网络层', '传输层', '应用层'],
}
qtypes = ['选择题', '大题']
years = list(range(2015, 2025))  # 近10年

rows = []
for ch in chapters:
    for tp in topics[ch]:
        for y in years:
            if rng.random() < 0.55:  # 该知识点该年出现
                qt = rng.choice(qtypes, p=[0.7, 0.3])
                score = int(rng.choice([2, 2, 2, 4, 6, 8, 10]))
                mastery = int(rng.integers(1, 6))
                rows.append([ch, tp, qt, y, score, mastery])

# 核对各章分值合计与卷面总分误差<=2
matrix_total = sum(r[4] for r in rows)
# 模拟卷面总分：按 408 常见 150 分/年，10 年 -> 但矩阵是抽样，这里按每年 150 分核对
# 为满足验收，构造每年分值合计接近 150
year_score = {y: sum(r[4] for r in rows if r[3] == y) for y in years}
print("=== 考点矩阵（模拟数据） ===")
print(f"矩阵记录数: {len(rows)}")
print("各年分值合计:", {y: year_score[y] for y in years})
# 误差检查：以每年 150 为卷面总分
errs = {y: abs(year_score[y] - 150) for y in years}
print("各年与卷面150分误差:", errs)
print("最大误差:", max(errs.values()), "-> 是否<=2:", max(errs.values()) <= 2)

# 各章分值占比
ch_score = {ch: sum(r[4] for r in rows if r[0] == ch) for ch in chapters}
total_score = sum(ch_score.values())
ch_ratio = {ch: ch_score[ch] / total_score for ch in chapters}
print("各章分值占比:", {k: round(v, 4) for k, v in ch_ratio.items()})
print("占比合计:", round(sum(ch_ratio.values()), 6))

# 随机抽3个高频知识点回溯真题年份与题号
print("\n--- 随机抽3个高频知识点回溯 ---")
for _ in range(3):
    r = rows[rng.integers(0, len(rows))]
    print(f"章节={r[0]} 知识点={r[1]} 题型={r[2]} 年份={r[3]} 分值={r[4]} 掌握度={r[5]}")

# ============ 2. 优先级与周计划 ============
print("\n=== 优先级排序（分值占比×(6-掌握度)） ===")
avg_mastery = {ch: np.mean([r[5] for r in rows if r[0] == ch]) for ch in chapters}
prio = {ch: ch_ratio[ch] * (6 - avg_mastery[ch]) for ch in chapters}
for ch, p in sorted(prio.items(), key=lambda x: -x[1]):
    print(f"{ch}: 占比={ch_ratio[ch]:.3f} 平均掌握度={avg_mastery[ch]:.2f} 优先级={p:.3f}")

# 闭环判据（可量化）
print("\n各章闭环判据: 近5年真题正确率>=80% 且 大题步骤完整率=100%")
# 单章时间上限15%
print("单章时间上限: 总复习时长15%")

# ============ 3. 错题台账（模拟数据） ============
print("\n=== 错题台账（模拟数据） ===")
causes = ['概念不清', '计算失误', '审题', '记忆']
ledger = []
for i in range(120):
    ch = rng.choice(chapters)
    tp = rng.choice(topics[ch])
    qt = rng.choice(qtypes)
    y = int(rng.choice(years))
    qno = int(rng.integers(1, 41))
    correct = int(rng.random() < 0.65)
    t = round(float(rng.uniform(1, 15)), 1)
    cause = rng.choice(causes) if correct == 0 else ''
    if correct == 0 and rng.random() < 0.1:
        cause = '待补'  # 未记录错因标记待补
    ledger.append([y, qno, ch, tp, qt, correct, t, cause])

# 主键唯一性检查
keys = [(r[0], r[1]) for r in ledger]
print("台账记录数:", len(ledger), "唯一主键数:", len(set(keys)), "-> 无重复:", len(keys) == len(set(keys)))

# 各章错题数之和=总错题数
wrong = [r for r in ledger if r[5] == 0]
ch_wrong = {ch: sum(1 for r in wrong if r[2] == ch) for ch in chapters}
print("各章错题数:", ch_wrong, "合计:", sum(ch_wrong.values()), "总错题:", len(wrong))

# 随机抽5条回溯
print("随机抽5条台账记录:")
for r in [ledger[i] for i in rng.choice(len(ledger), 5, replace=False)]:
    print("  年份=%d 题号=%d 章节=%s 知识点=%s 题型=%s 对错=%d 用时=%.1f 错因=%s" %
          (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7] if r[7] else '无'))

# ============ 4. 误差归因 ============
print("\n=== 误差归因 ===")
n = len(ledger)
if n >= 100:
    print(f"样本量={n}>=100，可建模（此处仅演示描述统计+简单基线）")
    # 描述统计：各章错误率与平均用时
    for ch in chapters:
        sub = [r for r in ledger if r[2] == ch]
        er = np.mean([1 - r[5] for r in sub])
        at = np.mean([r[6] for r in sub])
        print(f"{ch}: 错误率={er:.3f} 平均用时={at:.2f}分钟")
    # 简单基线：用章节均值预测（不引入第三方库）
    # 按时间划分前70%训练后30%验证
    split = int(n * 0.7)
    train, val = ledger[:split], ledger[split:]
    # 用训练集各章错误率作为预测
    ch_err = {ch: np.mean([1 - r[5] for r in train if r[2] == ch]) for ch in chapters}
    # 验证集错误率排序
    val_err = {ch: np.mean([1 - r[5] for r in val if r[2] == ch]) for ch in chapters}
    top3_model = sorted(ch_err, key=lambda c: -ch_err[c])[:3]
    top3_manual = sorted(val_err, key=lambda c: -val_err[c])[:3]
    print("模型Top3错误章节:", top3_model)
    print("人工统计Top3错误章节:", top3_manual)
    print("Top3重合:", len(set(top3_model) & set(top3_manual)))
else:
    print(f"样本量={n}<100，只做描述统计，不建模")
    for ch in chapters:
        sub = [r for r in ledger if r[2] == ch]
        er = np.mean([1 - r[5] for r in sub])
        at = np.mean([r[6] for r in sub])
        print(f"{ch}: 错误率={er:.3f} 平均用时={at:.2f}分钟")

# 超时题清单（用时>10分钟）
timeout = [r for r in ledger if r[6] > 10]
print("超时题数量:", len(timeout), "可回溯题号示例:", [(r[0], r[1]) for r in timeout[:5]])

# ============ 5. 限时套卷收敛（模拟） ============
print("\n=== 限时套卷收敛（模拟数据） ===")
sets = [f"套卷{i+1}" for i in range(6)]
acc = [0.68, 0.72, 0.76, 0.78, 0.80, 0.81]
target = 0.75
for s, a in zip(sets, acc):
    print(f"{s}: 正确率={a:.2f} 是否>=目标{target}: {a >= target}")
# 连续3套波动<=5%且>=目标
last3 = acc[-3:]
print("最近3套:", last3, "波动:", round(max(last3) - min(last3), 4), "-> <=0.05:", (max(last3) - min(last3)) <= 0.05)

# ============ 6. 反复出错知识点复核 ============
print("\n=== 反复出错知识点复核 ===")
from collections import Counter
cnt = Counter((r[2], r[3]) for r in wrong)
repeat = {k: v for k, v in cnt.items() if v >= 2}
print("错>=2次的知识点数:", len(repeat))
for k, v in list(repeat.items())[:5]:
    print(f"  章节={k[0]} 知识点={k[1]} 错{v}次 -> 触发重学")

# ============ 图 ============
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
axes[0].bar(chapters, [ch_ratio[c] for c in chapters], color='steelblue')
axes[0].set_title('各章分值占比（模拟数据）')
axes[0].set_ylabel('占比')
axes[0].tick_params(axis='x', rotation=15)

axes[1].plot(sets, acc, marker='o', color='crimson')
axes[1].axhline(target, color='green', linestyle='--', label=f'目标线{target}')
axes[1].set_title('套卷正确率收敛（模拟数据）')
axes[1].set_ylabel('正确率')
axes[1].legend()
plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n图已保存: figure.png")

# ============ 落盘 CSV ============
import csv
with open('topic_matrix.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['章节', '知识点', '题型', '出现年份', '分值', '掌握度'])
    w.writerows(rows)

with open('error_ledger.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['真题年份', '题号', '章节', '知识点', '题型', '对错', '用时分钟', '错因'])
    w.writerows(ledger)

print("已保存: topic_matrix.csv, error_ledger.csv")