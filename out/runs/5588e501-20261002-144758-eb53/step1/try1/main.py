# -*- coding: utf-8 -*-
"""
数一备考闭环 - 步骤1：建立考点矩阵（模拟数据，非真实实验结论）
仅使用 numpy / matplotlib
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv
import os

rng = np.random.default_rng(42)

# ---------------- 1. 考纲章节与卷面分值（数一，总分150） ----------------
# 章节: (卷面分值, 来源教材)
CHAPTERS = {
    "高数-极限与连续": (14, "同济高数"),
    "高数-一元微分学": (20, "同济高数"),
    "高数-一元积分学": (20, "同济高数"),
    "高数-多元微分学": (14, "同济高数"),
    "高数-多元积分学": (14, "同济高数"),
    "高数-级数": (12, "同济高数"),
    "高数-常微分方程": (10, "同济高数"),
    "线代-行列式与矩阵": (10, "同济线代"),
    "线代-向量与方程组": (12, "同济线代"),
    "线代-特征值与二次型": (12, "同济线代"),
    "概率-随机变量与分布": (6, "浙大概率"),
    "概率-数字特征与大数定律": (6, "浙大概率"),
}
TOTAL = sum(v[0] for v in CHAPTERS.values())
assert TOTAL == 150, f"卷面总分核对失败: {TOTAL}"

# ---------------- 2. 知识点/题型池（模拟） ----------------
KNOW = {
    "高数-极限与连续": ["洛必达法则", "等价无穷小", "夹逼定理"],
    "高数-一元微分学": ["中值定理", "导数应用", "泰勒展开"],
    "高数-一元积分学": ["定积分计算", "反常积分", "积分中值"],
    "高数-多元微分学": ["偏导数", "方向导数", "极值判别"],
    "高数-多元积分学": ["二重积分", "三重积分", "曲线曲面积分"],
    "高数-级数": ["幂级数收敛域", "傅里叶级数", "数项级数判敛"],
    "高数-常微分方程": ["一阶线性", "二阶常系数", "欧拉方程"],
    "线代-行列式与矩阵": ["行列式计算", "矩阵秩", "逆矩阵"],
    "线代-向量与方程组": ["线性相关", "解的结构", "基础解系"],
    "线代-特征值与二次型": ["特征值计算", "相似对角化", "正定性"],
    "概率-随机变量与分布": ["分布函数", "常见分布", "边缘分布"],
    "概率-数字特征与大数定律": ["期望方差", "协方差", "大数定律"],
}
TYPES = ["选择", "填空", "解答"]

# ---------------- 3. 生成考点矩阵（模拟数据） ----------------
# 字段: 章节, 知识点, 题型, 出现年份, 分值, 掌握度1-5
YEARS = list(range(2015, 2025))  # 近10年
rows = []
for ch, (score, book) in CHAPTERS.items():
    kps = KNOW[ch]
    # 每章抽取 4~7 条记录
    n = rng.integers(4, 8)
    for _ in range(n):
        kp = kps[rng.integers(0, len(kps))]
        tp = TYPES[rng.integers(0, 3)]
        yr = int(YEARS[rng.integers(0, len(YEARS))])
        val = int(rng.choice([4, 5, 6, 8, 10, 12]))
        mastery = int(rng.integers(1, 6))
        rows.append([ch, kp, tp, yr, val, mastery])

# 掌握度标尺说明
MASTERY_SCALE = {5: "能独立限时做对", 4: "基本会但偶有失误", 3: "会做但慢/不稳",
                 2: "需看答案", 1: "完全不会"}

# ---------------- 4. 陷阱规避检查 ----------------
print("=" * 60)
print("【模拟数据】以下所有结果均为模拟数据，非真实实验结论")
print("=" * 60)

# 陷阱1: 各章分值合计与卷面总分误差<=2
ch_score = {ch: 0 for ch in CHAPTERS}
for r in rows:
    ch_score[r[0]] += r[4]
err = abs(sum(ch_score.values()) - TOTAL)
print(f"[检查1] 矩阵分值合计={sum(ch_score.values())}, 卷面总分={TOTAL}, 误差={err} (需<=2)")
print(f"        误差<=2 判定: {err <= 2}")

# 陷阱4: 掌握度分布（区分不会/会但慢）
m_arr = np.array([r[5] for r in rows])
print(f"[检查4] 掌握度分布: 1={np.sum(m_arr==1)} 2={np.sum(m_arr==2)} "
      f"3={np.sum(m_arr==3)} 4={np.sum(m_arr==4)} 5={np.sum(m_arr==5)}")
print(f"        '会但慢/不稳'(=3) 占比={np.mean(m_arr==3):.2%}")

# 验收: 各章分值占比合计=100%
print("\n[验收] 各章分值占比:")
tot = sum(ch_score.values())
pct_sum = 0.0
for ch, s in ch_score.items():
    p = s / tot * 100
    pct_sum += p
    print(f"  {ch:22s} 分值={s:3d} 占比={p:5.2f}%")
print(f"  占比合计={pct_sum:.2f}% (需=100%)")

# 验收: 随机抽3个高频知识点回溯真题年份题号
print("\n[验收] 随机抽3个高频知识点回溯:")
kp_count = {}
for r in rows:
    kp_count[r[1]] = kp_count.get(r[1], 0) + 1
hot = sorted(kp_count.items(), key=lambda x: -x[1])[:3]
for kp, c in hot:
    hits = [(r[0], r[3], r[2]) for r in rows if r[1] == kp]
    print(f"  知识点「{kp}」出现{c}次, 回溯: {hits[:3]}")

# 优先级分数 = 章节分值占比 × (6 - 平均掌握度)
print("\n[优先级] 章节优先级分数(降序):")
prio = []
for ch in CHAPTERS:
    sub = [r for r in rows if r[0] == ch]
    avg_m = np.mean([r[5] for r in sub])
    p = (ch_score[ch] / tot) * (6 - avg_m)
    prio.append((ch, p, avg_m))
prio.sort(key=lambda x: -x[1])
for ch, p, am in prio:
    print(f"  {ch:22s} 优先级={p:.4f} 平均掌握度={am:.2f}")

# 单章时间上限<=15% 检查（按优先级分配时间，归一化后检查）
w = np.array([p for _, p, _ in prio])
w = w / w.sum()
print(f"\n[检查] 单章时间占比上限<=15%: 最大占比={w.max():.2%} 判定={w.max()<=0.15}")

# ---------------- 5. 出图 ----------------
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
chs = list(ch_score.keys())
vals = [ch_score[c] for c in chs]
axes[0].barh(chs, vals, color='steelblue')
axes[0].set_xlabel("分值")
axes[0].set_title("各章分值分布（模拟数据）")
axes[0].invert_yaxis()

axes[1].hist(m_arr, bins=[0.5,1.5,2.5,3.5,4.5,5.5], edgecolor='black', color='coral')
axes[1].set_xticks([1,2,3,4,5])
axes[1].set_xlabel("掌握度")
axes[1].set_ylabel("记录数")
axes[1].set_title("掌握度分布（模拟数据）")
plt.tight_layout()
plt.savefig("figure.png", dpi=120)
print("\n[输出] figure.png 已保存")

# ---------------- 6. 落盘 ----------------
with open("exam_matrix.csv", "w", newline="", encoding="utf-8-sig") as f:
    wtr = csv.writer(f)
    wtr.writerow(["章节", "知识点", "题型", "出现年份", "分值", "掌握度"])
    wtr.writerows(rows)
print(f"[输出] exam_matrix.csv 已保存, 共{len(rows)}条记录")

with open("chapter_priority.csv", "w", newline="", encoding="utf-8-sig") as f:
    wtr = csv.writer(f)
    wtr.writerow(["章节", "分值", "占比%", "平均掌握度", "优先级分数", "时间占比%"])
    for (ch, p, am), ww in zip(prio, w):
        wtr.writerow([ch, ch_score[ch], round(ch_score[ch]/tot*100, 2),
                      round(am, 2), round(p, 4), round(ww*100, 2)])
print("[输出] chapter_priority.csv 已保存")
print("\n[提示] 后续步骤(错题台账/归因建模/套卷收敛)见 TODO")
# TODO: 步骤2 周计划闭环判据
# TODO: 步骤3 错题台账+数据字典+审计日志
# TODO: 步骤4 误差归因(样本>=100建模, <100仅描述统计)
# TODO: 步骤5 限时套卷收敛曲线
# TODO: 步骤6 反复出错知识点重学验证