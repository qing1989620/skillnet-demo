# -*- coding: utf-8 -*-
"""
费马大定理证明史脉络梳理 —— 研究空白挖掘（research-gap-mining）
输入: fermat_enum.csv (前序产物, 枚举 n 与验证状态), figure.png (前序图, 本步覆盖)
输出: fermat_history_stages.csv, fermat_gap_topics.csv, figure.png
注意: 本步的"文献支撑数""可行性评分"等为基于史实的结构化整理,
      其中数值型评分标注为「模拟/主观评分」, 非真实实验测量。
"""
import os
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ---------------- 1. 读取前序产物 ----------------
enum_path = "fermat_enum.csv"
enum_rows = []
if os.path.exists(enum_path):
    with open(enum_path, "r", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        for r in rd:
            enum_rows.append(r)
    print(f"[读取] {enum_path}: {len(enum_rows)} 行, 字段={list(enum_rows[0].keys())}")
else:
    print(f"[警告] 未找到 {enum_path}, 使用空枚举集 (后续覆盖分析将标注为缺失)")

# 尝试解析 n 列
n_col = None
for cand in ["n", "N", "exponent", "指数"]:
    if enum_rows and cand in enum_rows[0]:
        n_col = cand
        break
enum_n = []
if n_col:
    for r in enum_rows:
        try:
            enum_n.append(int(float(r[n_col])))
        except Exception:
            pass
    enum_n = sorted(set(enum_n))
print(f"[解析] 前序枚举覆盖 n 个数 = {len(enum_n)}, 范围 = "
      f"{min(enum_n) if enum_n else 'NA'}..{max(enum_n) if enum_n else 'NA'}")

# ---------------- 2. 证明史阶段聚类 (史实整理) ----------------
# 每阶段: 名称, 年份, 代表工作, 覆盖 n 范围描述, 覆盖类型, 遗留缺口
stages = [
    dict(stage="S1 费马页边注", year=1637, work="Fermat 页边注",
         cover="n>=3 全称断言(无证明)", cover_type="断言",
         gap="无任何严格证明; n=3,4 亦未给出"),
    dict(stage="S2 费马 n=4", year=1640, work="Fermat 无穷递降法",
         cover="n=4 (及 4 的倍数)", cover_type="特例",
         gap="n=3 未解; 一般 n 无方法"),
    dict(stage="S3 欧拉 n=3", year=1770, work="Euler 代数数论雏形",
         cover="n=3", cover_type="特例",
         gap="n>=5 无覆盖; 方法不可推广"),
    dict(stage="S4 热尔曼索菲定理", year=1823, work="Sophie Germain 大定理",
         cover="p<100 且 p 不整除 xyz 的奇素数", cover_type="半一般",
         gap="p | xyz 情形未覆盖; 依赖辅助素数假设"),
    dict(stage="S5 库默尔理想数", year=1847, work="Kummer 理想数/正则素数",
         cover="所有正则素数 p (含大量 p<100)", cover_type="半一般",
         gap="非正则素数(如 37,59,67)未覆盖; 无统一框架"),
    dict(stage="S6 怀尔斯-泰勒", year=1994, work="Wiles-Taylor 模性提升",
         cover="全部 n>=3", cover_type="完全",
         gap="证明极长且依赖大量现代工具; 初等证明仍缺"),
]

# ---------------- 3. 覆盖缺口扫描 (方法/数据/场景三维) ----------------
# 每个 gap 需 >=2 篇文献支撑 (此处以史实文献条目计数, 非模拟)
gaps = [
    dict(gap_id="G1", dim="方法", desc="初等/自足证明缺失",
         refs=["Fermat 1637 页边注", "Wiles 1995 引言自述证明非初等"],
         maturity="低", data_avail="高", compute="低",
         verify="形式化验证 Lean/Coq 复现初等路径"),
    dict(gap_id="G2", dim="方法", desc="非正则素数统一处理框架",
         refs=["Kummer 1847", "Wiles 1995 模性提升"],
         maturity="中", data_avail="中", compute="中",
         verify="对 p=37,59,67 构造显式模性提升"),
    dict(gap_id="G3", dim="数据", desc="各阶段 n 覆盖范围量化数据集缺失",
         refs=["Ribenboim 1979 费马大定理讲义", "Edwards 1977 库默尔理想数"],
         maturity="低", data_avail="高", compute="低",
         verify="用 fermat_enum.csv 对齐阶段覆盖并统计缺口"),
    dict(gap_id="G4", dim="场景", desc="热尔曼定理辅助素数假设的边界场景",
         refs=["Germain 1823", "Laubenbacher 1996 热尔曼手稿研究"],
         maturity="中", data_avail="中", compute="中",
         verify="枚举 p<100 辅助素数存在性并标注失败点"),
    dict(gap_id="G5", dim="场景", desc="怀尔斯证明的模块化依赖最小化",
         refs=["Wiles 1995", "Taylor-Wiles 1995"],
         maturity="高", data_avail="低", compute="高",
         verify="依赖图裁剪 + 形式化验证子模块"),
]

# ---------------- 4. 可行性评估 (资源约束, 评分为模拟/主观) ----------------
def score(x):
    return {"高": 3, "中": 2, "低": 1}[x]

for g in gaps:
    g["n_refs"] = len(g["refs"])
    g["feasibility"] = round(
        0.4 * score(g["data_avail"]) + 0.3 * score(g["compute"]) + 0.3 * score(g["maturity"]), 2)
    g["novelty"] = round(4 - score(g["maturity"]), 2)  # 成熟度越低越新颖
    g["rank_score"] = round(g["novelty"] * g["feasibility"], 2)

gaps_sorted = sorted(gaps, key=lambda d: -d["rank_score"])

# ---------------- 5. 陷阱规避检查 ----------------
print("\n=== 陷阱规避检查 ===")
# 陷阱1: 没人做过 != 值得做 -> 检查每个 gap 是否有 >=2 文献支撑
bad = [g["gap_id"] for g in gaps if g["n_refs"] < 2]
print(f"[检查1] 文献支撑<2 的 gap: {bad if bad else '无'} (全部满足 >=2 篇)")
# 陷阱2: 负面结果/发表偏差 -> 显式记录失败/未覆盖阶段
neg = [s["stage"] for s in stages if s["cover_type"] != "完全"]
print(f"[检查2] 非完全覆盖阶段(负面/遗留): {len(neg)}/{len(stages)} -> {neg}")
# 陷阱3: 超出数据与算力 -> 高算力需求选题需标注
heavy = [g["gap_id"] for g in gaps if g["compute"] == "高"]
print(f"[检查3] 高算力需求 gap: {heavy if heavy else '无'} (需资源约束标注)")

# ---------------- 6. 阶段覆盖与缺口量化 ----------------
covered_n = set()
for s in stages:
    if s["cover_type"] == "完全":
        covered_n |= set(range(3, 101))
    elif s["cover_type"] == "半一般":
        covered_n |= set(range(3, 101, 2))  # 近似: 奇素数覆盖
    elif s["cover_type"] == "特例":
        covered_n |= {3, 4}
enum_set = set(enum_n)
if enum_set:
    gap_n = sorted(enum_set - covered_n)
    print(f"\n[覆盖] 前序枚举 n 中未被任何阶段覆盖: {len(gap_n)} 个 -> {gap_n[:20]}")
else:
    print("\n[覆盖] 前序枚举缺失, 跳过 n 级缺口统计")

# ---------------- 7. 出图 ----------------
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
ax1, ax2 = axes
years = [s["year"] for s in stages]
labels = [s["stage"] for s in stages]
ax1.plot(years, range(len(stages)), "o-", color="#2c7fb8", lw=2, ms=8)
for i, (y, l) in enumerate(zip(years, labels)):
    ax1.annotate(l, (y, i), textcoords="offset points", xytext=(6, 6), fontsize=9)
ax1.set_xlabel("年份"); ax1.set_ylabel("阶段序号")
ax1.set_title("费马大定理证明史阶段时间线")
ax1.grid(alpha=0.3)

gid = [g["gap_id"] for g in gaps_sorted]
rs = [g["rank_score"] for g in gaps_sorted]
ax2.barh(gid, rs, color="#f03b20", alpha=0.8)
ax2.set_xlabel("新颖性×可行性 排序分 (模拟/主观评分)")
ax2.set_title("候选选题排序 (含资源约束)")
ax2.grid(alpha=0.3, axis="x")
plt.tight_layout()
plt.savefig("figure.png", dpi=150)
print("\n[出图] figure.png 已保存")

# ---------------- 8. 落盘 ----------------
with open("fermat_history_stages.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(stages[0].keys()))
    w.writeheader(); w.writerows(stages)
with open("fermat_gap_topics.csv", "w", newline="", encoding="utf-8-sig") as f:
    fn = ["gap_id", "dim", "desc", "refs", "n_refs", "maturity",
          "data_avail", "compute", "verify", "feasibility", "novelty", "rank_score"]
    w = csv.DictWriter(f, fieldnames=fn)
    w.writeheader()
    for g in gaps_sorted:
        row = dict(g); row["refs"] = " | ".join(g["refs"]); w.writerow(row)
print("[落盘] fermat_history_stages.csv, fermat_gap_topics.csv")

print("\n=== 候选选题清单 (新颖性×可行性排序) ===")
for g in gaps_sorted:
    print(f"{g['gap_id']} [{g['dim']}] {g['desc']} | 文献={g['n_refs']} "
          f"| 可行性={g['feasibility']} 新颖性={g['novelty']} 排序分={g['rank_score']} "
          f"| 验证路径: {g['verify']}")