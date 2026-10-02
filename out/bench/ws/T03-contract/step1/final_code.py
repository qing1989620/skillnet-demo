# -*- coding: utf-8 -*-
"""
GNN 在药物发现中的应用 —— PRISMA 式文献综述流程（可复现骨架）
注意：本脚本中的检索命中数、筛选计数、抽取字段均为【模拟数据】，
      仅用于演示可复现流程与自洽性检查，不代表真实文献计量结果。
      真实执行时需替换为 PubMed / Web of Science / Scopus / IEEE Xplore 等
      数据库的真实检索结果，并逐条核验 DOI。
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv
import os

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

OUT_DIR = "."

# ============================================================
# 步骤 1：概念矩阵（PICO 式拆解）+ 同义词
# ============================================================
concept_matrix = {
    "C1_方法": ["graph neural network", "GNN", "message passing neural network",
                "graph convolutional network", "graph attention network"],
    "C2_任务": ["drug discovery", "drug design", "molecular property prediction",
                "virtual screening", "drug-target interaction", "ADMET"],
    "C3_对象": ["molecule", "protein", "compound", "ligand", "target"],
}
print("=" * 70)
print("【步骤1】概念矩阵与同义词（模拟数据）")
for k, v in concept_matrix.items():
    print(f"  {k}: {len(v)} 个同义词 -> {v}")

# ============================================================
# 步骤 2：多数据库可复现检索式（规避陷阱：单一数据库覆盖偏差）
# ============================================================
databases = ["PubMed", "Web of Science", "Scopus", "IEEE Xplore"]
# 模拟各库命中数（真实执行时应由数据库返回）
hits = {"PubMed": 412, "Web of Science": 538, "Scopus": 601, "IEEE Xplore": 187}
total_hits = sum(hits.values())
print("\n" + "=" * 70)
print("【步骤2】多数据库检索命中数（模拟数据）")
for db, n in hits.items():
    print(f"  {db:18s}: {n}")
print(f"  合计命中: {total_hits}")
print(f"  覆盖数据库数: {len(databases)} (>=3 满足要求，规避单一库偏差)")

# 去重（模拟：跨库重复率 22%）
dup_rate = 0.22
duplicates = int(round(total_hits * dup_rate))
after_dedup = total_hits - duplicates
print(f"  跨库重复(模拟 {dup_rate:.0%}): {duplicates} -> 去重后: {after_dedup}")

# ============================================================
# 步骤 3：两轮筛选（标题-摘要 -> 全文），逐级记录数量
# ============================================================
# 标题-摘要轮排除
excl_ta = {"非药物发现场景": 210, "非GNN方法": 168, "综述/评论": 74, "非英文": 22}
ta_excluded = sum(excl_ta.values())
after_ta = after_dedup - ta_excluded
# 全文轮排除
excl_ft = {"无实验验证": 96, "数据不可获取": 41, "重复发表": 18, "方法描述不足": 33}
ft_excluded = sum(excl_ft.values())
included = after_ta - ft_excluded

print("\n" + "=" * 70)
print("【步骤3】PRISMA 两轮筛选（模拟数据）")
print(f"  去重后进入标题-摘要筛选: {after_dedup}")
for k, v in excl_ta.items():
    print(f"    排除[{k}]: {v}")
print(f"  标题-摘要排除合计: {ta_excluded} -> 进入全文: {after_ta}")
for k, v in excl_ft.items():
    print(f"    排除[{k}]: {v}")
print(f"  全文排除合计: {ft_excluded} -> 最终纳入: {included}")

# 自洽性检查（验收清单要求）
assert after_dedup == total_hits - duplicates
assert after_ta == after_dedup - ta_excluded
assert included == after_ta - ft_excluded
assert included > 0
print(f"  [自洽性检查] 通过: {total_hits} - {duplicates} - {ta_excluded} - {ft_excluded} = {included}")

# ============================================================
# 步骤 4：逐篇结构化抽取（模拟数据，含 DOI 可回溯字段）
# ============================================================
# 模拟纳入文献的结构化抽取表（DOI 为示例格式，真实执行须核验）
records = [
    {"id": 1, "year": 2018, "task": "分子性质预测", "gnn": "MPNN",
     "dataset": "QM9", "sample": 133885, "conclusion": "GNN优于指纹方法",
     "limitation": "仅小分子", "doi": "10.1021/acs.jcim.8b00001"},
    {"id": 2, "year": 2019, "task": "药物-靶点相互作用", "gnn": "GCN",
     "dataset": "Davis", "sample": 30056, "conclusion": "端到端预测有效",
     "limitation": "泛化性弱", "doi": "10.1093/bioinformatics/btz0002"},
    {"id": 3, "year": 2020, "task": "虚拟筛选", "gnn": "GAT",
     "dataset": "DUD-E", "sample": 102000, "conclusion": "富集因子提升",
     "limitation": "假阳性高", "doi": "10.1021/acs.jcim.0c00003"},
    {"id": 4, "year": 2021, "task": "ADMET预测", "gnn": "GIN",
     "dataset": "Tox21", "sample": 7831, "conclusion": "多任务学习增益",
     "limitation": "标签噪声", "doi": "10.1021/acs.jcim.1c00004"},
    {"id": 5, "year": 2022, "task": "分子生成", "gnn": "GraphVAE",
     "dataset": "ZINC", "sample": 250000, "conclusion": "生成有效性提升",
     "limitation": "合成可及性差", "doi": "10.1021/acs.jcim.2c00005"},
    {"id": 6, "year": 2023, "task": "药物-靶点相互作用", "gnn": "HGNN",
     "dataset": "BindingDB", "sample": 45000, "conclusion": "异构图建模更优",
     "limitation": "计算开销大", "doi": "10.1093/bioinformatics/btad0006"},
]
print("\n" + "=" * 70)
print(f"【步骤4】结构化抽取（模拟数据，纳入 {len(records)} 篇示例）")
for r in records:
    print(f"  [{r['id']}] {r['year']} | {r['task']:12s} | {r['gnn']:8s} | "
          f"n={r['sample']:>6d} | DOI={r['doi']}")

# DOI 核验检查（规避陷阱：引用未核验）
def doi_format_ok(doi):
    return doi.startswith("10.") and "/" in doi
bad = [r["id"] for r in records if not doi_format_ok(r["doi"])]
print(f"  [DOI 格式核验] 不合规条目: {bad if bad else '无'} (真实执行须逐条访问 DOI 解析)")

# ============================================================
# 步骤 5：主题聚类综合 + 证据强度 + 结论冲突标注
# ============================================================
themes = {}
for r in records:
    themes.setdefault(r["task"], []).append(r)
print("\n" + "=" * 70)
print("【步骤5】主题聚类综合（模拟数据）")
for t, rs in themes.items():
    years = [r["year"] for r in rs]
    strength = "强" if len(rs) >= 2 else "弱(单篇)"
    print(f"  主题[{t}]: {len(rs)} 篇, 年份 {min(years)}-{max(years)}, 证据强度={strength}")

# 冲突检测：同一主题下结论方向是否一致（模拟）
conflict = []
for t, rs in themes.items():
    concl = set(r["conclusion"] for r in rs)
    if len(concl) > 1 and len(rs) > 1:
        conflict.append(t)
print(f"  [结论冲突标注] 存在潜在冲突的主题: {conflict if conflict else '无'}")

# 研究空白（切入点）识别：主题覆盖 vs 任务缺口
all_tasks = ["分子性质预测", "药物-靶点相互作用", "虚拟筛选", "ADMET预测",
             "分子生成", "逆合成", "多靶点药物", "耐药性预测"]
covered = set(themes.keys())
gaps = [t for t in all_tasks if t not in covered]
print(f"  [研究空白/切入点候选] 未被纳入文献覆盖的任务: {gaps}")

# ============================================================
# 出图：PRISMA 漏斗 + 主题分布
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

stages = ["检索命中", "去重后", "标题摘要后", "全文后(纳入)"]
counts = [total_hits, after_dedup, after_ta, included]
axes[0].bar(stages, counts, color=["#4C72B0", "#55A868", "#C44E52", "#8172B2"])
for i, c in enumerate(counts):
    axes[0].text(i, c + 10, str(c), ha="center", fontsize=10)
axes[0].set_title("PRISMA 筛选漏斗（模拟数据）")
axes[0].set_ylabel("文献数量")
axes[0].tick_params(axis="x", rotation=15)

theme_names = list(themes.keys())
theme_counts = [len(themes[t]) for t in theme_names]
axes[1].barh(theme_names, theme_counts, color="#4C72B0")
for i, c in enumerate(theme_counts):
    axes[1].text(c + 0.05, i, str(c), va="center", fontsize=10)
axes[1].set_title("纳入文献主题分布（模拟数据）")
axes[1].set_xlabel("文献数")

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "figure.png"), dpi=150)
plt.close()

# ============================================================
# 落盘：CSV 数据表
# ============================================================
with open(os.path.join(OUT_DIR, "prisma_counts.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["stage", "count"])
    for s, c in zip(stages, counts):
        w.writerow([s, c])

with open(os.path.join(OUT_DIR, "extraction_table.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(records[0].keys()))
    w.writeheader()
    for r in records:
        w.writerow(r)

print("\n" + "=" * 70)
print("【落盘文件】figure.png, prisma_counts.csv, extraction_table.csv")
print("【重要声明】以上所有计数与文献条目均为模拟数据，仅演示可复现流程；")
print("            真实综述须替换为数据库真实检索结果并逐条核验 DOI。")
print("=" * 70)