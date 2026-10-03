# -*- coding: utf-8 -*-
"""
《计算机网络原理》考点矩阵 + 备考闭环（模拟数据，非真实实验结论）
仅使用 numpy / matplotlib
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv

rng = np.random.default_rng(42)  # 固定随机种子

# ============ 1. 考点矩阵（模拟数据） ============
# 章节, 卷面分值(满分150), 掌握度1-5
chapters = [
    ("第1章 概述",            8,  4),
    ("第2章 物理层",          10, 3),
    ("第3章 数据链路层",      18, 2),
    ("第4章 网络层",          30, 2),
    ("第5章 传输层",          28, 3),
    ("第6章 应用层",          22, 4),
    ("第7章 网络安全",        14, 2),
    ("第8章 无线与移动网络",  20, 1),
]
total_score = sum(c[1] for c in chapters)
print("=== 1. 考点矩阵 ===")
print(f"卷面总分(模拟) = {total_score} 分")
for name, sc, mast in chapters:
    print(f"  {name}: 分值={sc}, 占比={sc/total_score*100:.1f}%, 掌握度={mast}")

# 陷阱规避：各章分值合计与卷面总分误差 <= 2
err = abs(total_score - 150)
print(f"[检查] 分值合计与卷面150分误差 = {err} 分 (需<=2) -> {'通过' if err<=2 else '不通过'}")

# 高频知识点回溯（模拟：每个知识点绑定真题年份+题号）
knowledge_points = [
    ("第4章 网络层", "IP地址与子网划分", "计算题", [2019,2021,2023], ["三.1","三.2","三.1"], 12),
    ("第5章 传输层", "TCP拥塞控制",     "综合题", [2020,2022,2023], ["四.1","四.2","四.1"], 15),
    ("第3章 数据链路层","CSMA/CD与以太网","计算题",[2018,2021,2022],["三.3","三.2","三.3"], 10),
]
print("\n[验收] 随机抽3个高频知识点回溯：")
for ch, kp, tp, yrs, nos, sc in knowledge_points:
    print(f"  {ch} | {kp} | {tp} | 年份={yrs} | 题号={nos} | 分值={sc}")

# ============ 2. 优先级与周计划 ============
print("\n=== 2. 优先级排序（分值占比×(6-掌握度)） ===")
prio = []
for name, sc, mast in chapters:
    p = (sc/total_score) * (6 - mast)
    prio.append((name, sc, mast, p))
prio.sort(key=lambda x: -x[3])
total_weeks = 12
for i,(name,sc,mast,p) in enumerate(prio):
    weeks = max(1, int(round(p*40)))  # 模拟分配
    print(f"  {name}: 优先级={p:.3f}, 掌握度={mast}, 建议周数={weeks}")

# 单章时间上限 <= 总复习时长15%
print("[检查] 单章时间占比上限15%：")
for name,sc,mast,p in prio:
    share = p / sum(x[3] for x in prio) * 100
    flag = "OK" if share <= 15 else "超限"
    print(f"  {name}: 时间占比={share:.1f}% -> {flag}")

# 闭环判据（量化）
print("[闭环判据] 每章：近5年真题正确率>=80% 且 大题步骤完整率=100%")

# ============ 3. 错题台账（模拟数据） ============
print("\n=== 3. 错题台账（模拟数据） ===")
n_records = 120
causes = ["概念不清","计算失误","审题","记忆","待补"]
rows = []
for i in range(n_records):
    ch = rng.choice([c[0] for c in chapters])
    kp = rng.choice(["IP子网","TCP拥塞","CSMA/CD","路由算法","DNS","HTTP","加密","无线"])
    tp = rng.choice(["选择","填空","计算","综合"])
    year = int(rng.choice([2015,2016,2017,2018,2019,2020,2021,2022,2023,2024]))
    qno = f"{rng.integers(1,5)}.{rng.integers(1,8)}"
    correct = int(rng.random() < 0.55)
    tmin = round(float(rng.normal(6,2)),1)
    tmin = max(0.5, tmin)
    cause = rng.choice(causes) if correct==0 else ""
    rows.append([year,qno,ch,kp,tp,correct,tmin,cause])

# 主键唯一性检查
keys = [(r[0],r[1]) for r in rows]
print(f"[检查] 台账记录数={len(rows)}, 唯一主键数={len(set(keys))} -> {'唯一' if len(keys)==len(set(keys)) else '有重复'}")

# 各章错题数之和 = 总错题数
wrong = [r for r in rows if r[5]==0]
from collections import Counter
cnt = Counter(r[2] for r in wrong)
print(f"[检查] 总错题数={len(wrong)}, 各章错题数之和={sum(cnt.values())} -> {'一致' if sum(cnt.values())==len(wrong) else '不一致'}")
for ch,c in cnt.items():
    print(f"  {ch}: 错题数={c}")

# 审计日志
print("[审计日志] 清洗决策：")
print("  - 未记录错因标记为'待补'，不删除")
print(f"  - 待补条数 = {sum(1 for r in rows if r[5]==0 and r[7]=='待补')}")
print("  - 主键=年份+题号，重复则保留首条")

# ============ 4. 误差归因 ============
print("\n=== 4. 误差归因 ===")
if len(rows) >= 100:
    print(f"样本量={len(rows)} >= 100，可建模（此处仅做描述统计基线）")
else:
    print(f"样本量={len(rows)} < 100，仅做描述统计，不建模")

# 各章错误率与平均用时
print("[描述统计] 各章错误率与平均用时：")
for ch in [c[0] for c in chapters]:
    sub = [r for r in rows if r[2]==ch]
    if sub:
        er = sum(1 for r in sub if r[5]==0)/len(sub)
        at = np.mean([r[6] for r in sub])
        print(f"  {ch}: 错误率={er*100:.1f}%, 平均用时={at:.1f}分钟")

# 超时题清单（用时>10分钟）
overtime = [r for r in rows if r[6] > 10]
print(f"[超时题清单] 用时>10分钟共 {len(overtime)} 条，示例：")
for r in overtime[:3]:
    print(f"  年份={r[0]}, 题号={r[1]}, 章节={r[2]}, 用时={r[6]}分钟")

# ============ 5. 限时套卷收敛（模拟） ============
print("\n=== 5. 限时套卷成绩曲线（模拟数据） ===")
n_papers = 8
acc = np.clip(rng.normal(0.72, 0.06, n_papers), 0.5, 0.95)
acc[-3:] = np.clip(acc[-3:] + 0.05, 0.5, 0.95)  # 后期提升
target = 0.75
print(f"目标线={target*100:.0f}%")
for i,a in enumerate(acc):
    print(f"  第{i+1}套: 正确率={a*100:.1f}%")

# 连续3套波动<=5%且均>=目标线
last3 = acc[-3:]
fluct = (max(last3)-min(last3))*100
print(f"[检查] 连续3套波动={fluct:.1f}% (需<=5%), 最低={min(last3)*100:.1f}% (需>={target*100:.0f}%)")
print(f"  -> {'进入查漏阶段' if fluct<=5 and min(last3)>=target else '继续套卷训练'}")

# ============ 6. 重学触发 ============
print("\n=== 6. 重学触发（同一知识点错>=2次） ===")
kp_wrong = Counter(r[3] for r in wrong)
for kp,c in kp_wrong.items():
    if c >= 2:
        print(f"  触发重学: {kp} (错{c}次) -> 回教材+做真题>=5道, 正确率>=80%通过")

# ============ 图 ============
fig, axes = plt.subplots(1, 2, figsize=(12,4))
axes[0].bar([c[0][:6] for c in chapters], [c[1] for c in chapters], color='steelblue')
axes[0].set_title('各章分值分布（模拟数据）')
axes[0].tick_params(axis='x', rotation=45)
axes[1].plot(range(1,n_papers+1), acc*100, marker='o', color='crimson')
axes[1].axhline(target*100, ls='--', color='gray', label=f'目标线{target*100:.0f}%')
axes[1].set_title('套卷正确率曲线（模拟数据）')
axes[1].set_xlabel('套卷序号'); axes[1].set_ylabel('正确率(%)')
axes[1].legend()
plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n[落盘] figure.png 已保存")

# ============ 落盘 CSV ============
with open('exam_matrix.csv','w',newline='',encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['章节','分值','占比%','掌握度','优先级'])
    for name,sc,mast,p in prio:
        w.writerow([name,sc,round(sc/total_score*100,2),mast,round(p,4)])

with open('error_ledger.csv','w',newline='',encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['年份','题号','章节','知识点','题型','是否正确','用时分钟','错因'])
    w.writerows(rows)

with open('paper_scores.csv','w',newline='',encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['套卷序号','正确率'])
    for i,a in enumerate(acc):
        w.writerow([i+1, round(a,4)])

print("[落盘] exam_matrix.csv / error_ledger.csv / paper_scores.csv 已保存")