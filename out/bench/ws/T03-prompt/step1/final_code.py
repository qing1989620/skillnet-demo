# -*- coding: utf-8 -*-
"""
GNN 在药物发现中的应用 —— PRISMA 式文献计量梳理（可运行骨架）
注意：本脚本中所有文献条目、命中数、筛选数量均为【模拟数据】，
      仅用于演示 PRISMA 流程与产出结构，不代表真实检索结果。
      真实综述需在 PubMed / Web of Science / Scopus / IEEE Xplore 等库执行检索式。
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

RNG = np.random.default_rng(42)

# ---------- 1. 概念矩阵（研究问题拆解） ----------
concept_matrix = {
    "P_任务域": ["drug discovery", "drug design", "virtual screening",
                "ADMET prediction", "drug-drug interaction", "molecular property prediction"],
    "I_方法":   ["graph neural network", "GNN", "message passing neural network",
                "graph convolutional network", "graph attention network", "MPNN"],
    "O_产出":   ["binding affinity", "bioactivity", "toxicity", "solubility",
                "permeability", "hit identification"],
}
print("=" * 70)
print("[1] 概念矩阵（P/I/O）—— 用于构造可复现检索式")
for k, v in concept_matrix.items():
    print(f"  {k}: {len(v)} 个同义词 -> {v}")

# 检索式示例（布尔逻辑）
query = ('("graph neural network" OR GNN OR "message passing neural network") '
         'AND ("drug discovery" OR "virtual screening" OR "ADMET")')
print(f"\n  示例检索式: {query}")

# ---------- 2. 多数据库检索命中数（模拟数据） ----------
databases = ["PubMed", "Web of Science", "Scopus", "IEEE Xplore"]
hits = {"PubMed": 812, "Web of Science": 1043, "Scopus": 1267, "IEEE Xplore": 356}
print("\n" + "=" * 70)
print("[2] 多库检索命中数【模拟数据】")
total_hits = 0
for db in databases:
    print(f"  {db:<16}: {hits[db]:>5} 条")
    total_hits += hits[db]
print(f"  {'合计':<16}: {total_hits:>5} 条（去重前）")

# 去重（模拟：约 22% 重叠）
dup_rate = 0.22
n_dedup = int(round(total_hits * (1 - dup_rate)))
print(f"  去重后（模拟重叠率 {dup_rate:.0%}）: {n_dedup} 条")

# ---------- 3. PRISMA 两轮筛选（模拟数据） ----------
n_title_abs_excluded = int(round(n_dedup * 0.63))   # 标题摘要排除
n_fulltext = n_dedup - n_title_abs_excluded
n_fulltext_excluded = int(round(n_fulltext * 0.41)) # 全文排除
n_included = n_fulltext - n_fulltext_excluded

print("\n" + "=" * 70)
print("[3] PRISMA 筛选流程【模拟数据】")
print(f"  识别(Identification)      : {total_hits}")
print(f"  去重(Screening-dup)       : {n_dedup}")
print(f"  标题摘要排除              : {n_title_abs_excluded}")
print(f"  进入全文评估              : {n_fulltext}")
print(f"  全文排除                  : {n_fulltext_excluded}")
print(f"  最终纳入(Included)        : {n_included}")

# 一致性检查（已知陷阱：筛选数量必须自洽）
assert n_dedup - n_title_abs_excluded == n_fulltext
assert n_fulltext - n_fulltext_excluded == n_included
print("  [检查] 筛选数量自洽性: 通过 (无负数/无断链)")

# ---------- 4. 结构化抽取表（模拟数据） ----------
n_tasks = ["分子性质预测", "虚拟筛选", "ADMET", "DDI预测", "亲和力预测"]
years = np.arange(2017, 2025)
# 模拟：各任务逐年发文量（增长趋势）
task_trend = {}
for i, t in enumerate(n_tasks):
    base = 3 + i * 2
    growth = np.array([base * (1.55 ** (y - 2017)) for y in years])
    task_trend[t] = np.round(growth + RNG.normal(0, 1.5, len(years))).clip(min=0).astype(int)

print("\n" + "=" * 70)
print("[4] 主题聚类逐年发文量【模拟数据】")
header = "任务\\年份  " + "".join([f"{y:>6}" for y in years])
print("  " + header)
for t in n_tasks:
    row = "".join([f"{v:>6}" for v in task_trend[t]])
    print(f"  {t:<10}{row}")

# 证据强度与冲突标注（模拟）
evidence = {
    "分子性质预测": ("强", "多数据集一致"),
    "虚拟筛选":     ("中", "基准差异大"),
    "ADMET":        ("中", "标签噪声争议"),
    "DDI预测":      ("弱", "数据泄漏风险"),
    "亲和力预测":   ("中", "泛化性存疑"),
}
print("\n  证据强度与冲突标注【模拟数据】:")
for t, (s, note) in evidence.items():
    print(f"    {t:<10} 强度={s}  备注={note}")

# ---------- 5. 研究空白识别（切入点） ----------
print("\n" + "=" * 70)
print("[5] 潜在研究空白（基于模拟趋势的启发式推断，非真实结论）")
gaps = [
    "跨域泛化：训练/测试分布偏移下的 GNN 稳健性缺乏系统评测",
    "可解释性：注意力/子图解释与化学机理的因果对齐研究稀少",
    "数据泄漏：分子骨架切分(scaffold split)未成为标准协议",
    "多模态融合：3D 构象 + 序列 + 知识图谱的统一图建模不足",
    "不确定性量化：药物发现高风险决策下的校准方法缺失",
]
for i, g in enumerate(gaps, 1):
    print(f"  G{i}. {g}")

# ---------- 6. 出图 ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# 左：PRISMA 漏斗
stages = ["识别", "去重", "标题摘要", "全文评估", "纳入"]
counts = [total_hits, n_dedup, n_fulltext, n_fulltext, n_included]
axes[0].barh(stages[::-1], counts[::-1], color="#4C72B0")
for i, v in enumerate(counts[::-1]):
    axes[0].text(v + 20, i, str(v), va="center", fontsize=9)
axes[0].set_title("PRISMA 筛选漏斗【模拟数据】")
axes[0].set_xlabel("文献数量")

# 右：主题趋势
for t in n_tasks:
    axes[1].plot(years, task_trend[t], marker="o", label=t)
axes[1].set_title("GNN 药物发现主题发文趋势【模拟数据】")
axes[1].set_xlabel("年份")
axes[1].set_ylabel("发文量")
axes[1].legend(fontsize=8)
axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig("figure.png", dpi=150)
print("\n[6] 图已保存: figure.png")

# ---------- 7. 落盘 CSV ----------
import csv
with open("prisma_counts.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["stage", "count", "note"])
    w.writerow(["identification", total_hits, "模拟数据"])
    w.writerow(["dedup", n_dedup, "模拟数据"])
    w.writerow(["title_abs_excluded", n_title_abs_excluded, "模拟数据"])
    w.writerow(["fulltext_assessed", n_fulltext, "模拟数据"])
    w.writerow(["fulltext_excluded", n_fulltext_excluded, "模拟数据"])
    w.writerow(["included", n_included, "模拟数据"])

with open("topic_trend.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["task"] + [str(y) for y in years])
    for t in n_tasks:
        w.writerow([t] + list(task_trend[t]))

print("[7] CSV 已保存: prisma_counts.csv, topic_trend.csv")
print("\n[提示] 以上全部为模拟数据，真实综述须替换为实际检索与筛选结果。")