# -*- coding: utf-8 -*-
"""
数一备考闭环 - 步骤1：建立考点矩阵（含陷阱规避检查）
所有数据均为【模拟数据】，仅用于演示流程，不代表真实考试结论。
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

RNG = np.random.default_rng(42)  # 固定随机种子

# ---------- 1. 考纲章节与卷面分值（数一：高数/线代/概率）----------
# 卷面总分 150，各章目标分值（模拟，按数一常见分布）
CHAPTERS = [
    ("高等数学", "函数极限连续", 18),
    ("高等数学", "一元微分学", 22),
    ("高等数学", "一元积分学", 20),
    ("高等数学", "多元微分学", 12),
    ("高等数学", "多元积分学", 14),
    ("高等数学", "级数", 12),
    ("高等数学", "常微分方程", 10),
    ("线性代数", "行列式与矩阵", 8),
    ("线性代数", "向量与方程组", 10),
    ("线性代数", "特征值与二次型", 10),
    ("概率统计", "随机变量与分布", 8),
    ("概率统计", "数字特征与大数定律", 6),
]
TOTAL_SCORE = 150

# ---------- 2. 知识点-题型-年份-分值-掌握度 矩阵（模拟）----------
TYPES = ["选择", "填空", "解答"]
KNOWLEDGE = {
    "函数极限连续": ["极限计算", "连续性判定"],
    "一元微分学": ["导数计算", "中值定理", "单调极值"],
    "一元积分学": ["不定积分", "定积分应用", "反常积分"],
    "多元微分学": ["偏导与全微分", "极值条件"],
    "多元积分学": ["二重积分", "三重积分", "曲线曲面积分"],
    "级数": ["幂级数", "傅里叶级数", "数项级数"],
    "常微分方程": ["一阶方程", "高阶线性方程"],
    "行列式与矩阵": ["行列式计算", "矩阵运算"],
    "向量与方程组": ["线性相关", "解的结构"],
    "特征值与二次型": ["特征值", "二次型标准化"],
    "随机变量与分布": ["分布函数", "常见分布"],
    "数字特征与大数定律": ["期望方差", "大数定律"],
}
YEARS = list(range(2015, 2025))  # 近10年

rows = []
for ch, kp, ch_score in CHAPTERS:
    kps = KNOWLEDGE[kp]
    for k in kps:
        for y in YEARS:
            if RNG.random() < 0.55:  # 该知识点该年是否出现
                t = TYPES[RNG.integers(0, 3)]
                s = int(RNG.choice([4, 5, 6, 8, 10, 12]))
                mastery = int(RNG.integers(1, 6))  # 1-5
                rows.append([ch, kp, k, t, y, s, mastery])

# ---------- 3. 陷阱规避检查 ----------
print("=" * 60)
print("【模拟数据】考点矩阵构建与陷阱规避检查")
print("=" * 60)

# 陷阱1：各章分值合计 vs 卷面总分，误差≤2
ch_sum = {}
for ch, kp, s in CHAPTERS:
    ch_sum[kp] = ch_sum.get(kp, 0) + s
total = sum(ch_sum.values())
err = abs(total - TOTAL_SCORE)
print(f"[陷阱1] 各章分值合计={total}, 卷面总分={TOTAL_SCORE}, 误差={err} -> {'通过' if err<=2 else '不通过'}")

# 各章分值占比合计=100%
ratios = {k: v / total * 100 for k, v in ch_sum.items()}
print(f"[验收] 各章分值占比合计={sum(ratios.values()):.2f}% (应=100%)")

# 单章时间占比≤15%（时间上限按分值占比近似，此处用分值占比代理）
over = [k for k, r in ratios.items() if r > 15]
print(f"[陷阱4] 单章时间占比>15%的章节: {over if over else '无'} -> {'通过' if not over else '需调整'}")

# 陷阱2：错因固定4类（此处仅声明口径，台账在步骤3）
CAUSES = ["概念不清", "计算失误", "审题", "记忆"]
print(f"[陷阱2] 错因固定4类: {CAUSES}")

# 陷阱5：样本量检查（矩阵行数）
print(f"[陷阱5] 矩阵样本量={len(rows)} 条 (>=100 可建模，<100 仅描述统计)")

# 随机抽3个高频知识点回溯真题年份与题号
print("\n[验收] 随机抽3个高频知识点回溯:")
for _ in range(3):
    idx = RNG.integers(0, len(rows))
    r = rows[idx]
    print(f"  {r[1]} - {r[2]} - {r[3]} - {r[4]}年 - 第{idx+1}题 - 分值{r[5]} - 掌握度{r[6]}")

# ---------- 4. 落盘 ----------
import csv
with open("exam_matrix.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["章节", "知识点", "题型", "出现年份", "分值", "掌握度"])
    w.writerows(rows)

with open("chapter_score.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["章节", "分值", "占比%"])
    for k, v in ch_sum.items():
        w.writerow([k, v, round(ratios[k], 2)])

# ---------- 5. 出图 ----------
fig, ax = plt.subplots(figsize=(10, 5))
ks = list(ch_sum.keys())
vs = [ch_sum[k] for k in ks]
ax.barh(ks, vs, color="#4C72B0")
ax.axvline(15, color="red", linestyle="--", label="15%上限")
ax.set_xlabel("分值")
ax.set_title("【模拟数据】数一各章分值分布")
ax.legend()
plt.tight_layout()
plt.savefig("figure.png", dpi=120)
print("\n已保存: exam_matrix.csv, chapter_score.csv, figure.png")