# -*- coding: utf-8 -*-
"""
费马大定理核心思想 —— 步骤1：形式化命题 + 边界情形对照表
技能：math-theorem-explainer
本文件只实现最核心的可运行路径：形式化、边界反例核验、误解对照、证明史时间线。
"""
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 1. 符号形式化命题
# ============================================================
PROPOSITION = {
    "name": "费马大定理 (Fermat's Last Theorem, FLT)",
    "statement": "对任意整数 n>=3，方程 x^n + y^n = z^n 不存在满足 x,y,z 均为非零整数的解。",
    "formal": "∀n∈Z, n>=3: ¬∃(x,y,z)∈(Z\\{0})^3 使得 x^n + y^n = z^n",
    "domain": {
        "n": "整数, n >= 3",
        "x,y,z": "非零整数 (Z\\{0})",
    },
    "premises": [
        "n 为整数且 n >= 3",
        "x, y, z 均为非零整数（排除 0 以避免平凡解）",
        "方程形式严格为 x^n + y^n = z^n（非 x^n + y^n = z^m 等变体）",
    ],
}

# 边界情形对照表：n=1, n=2, n>=3
BOUNDARY_TABLE = [
    {"n": "n = 1", "equation": "x + y = z",
     "solution_status": "有无穷多非零整数解",
     "example": "x=1, y=2, z=3",
     "is_FLT_scope": "否（n<3，不在定理范围）"},
    {"n": "n = 2", "equation": "x^2 + y^2 = z^2",
     "solution_status": "有无穷多非零整数解（勾股数）",
     "example": "x=3, y=4, z=5",
     "is_FLT_scope": "否（n=2，不在定理范围）"},
    {"n": "n >= 3", "equation": "x^n + y^n = z^n",
     "solution_status": "无任何非零整数解（费马大定理）",
     "example": "不存在",
     "is_FLT_scope": "是（定理覆盖范围）"},
]

# ============================================================
# 2. 边界反例验证：前提不可省略
# ============================================================
def check_counterexample(x, y, z, n):
    """核验 (x,y,z,n) 是否满足方程，以及是否满足 FLT 前提。"""
    lhs = x**n + y**n
    rhs = z**n
    satisfies_eq = (lhs == rhs)
    satisfies_premise = (n >= 3) and (x != 0) and (y != 0) and (z != 0)
    return {
        "x": x, "y": y, "z": z, "n": n,
        "lhs": lhs, "rhs": rhs,
        "satisfies_equation": satisfies_eq,
        "satisfies_FLT_premise": satisfies_premise,
        "is_valid_counterexample_to_FLT": satisfies_eq and satisfies_premise,
    }

# 边界反例：勾股数 (3,4,5) n=2 —— 满足方程但违反 n>=3 前提
ce1 = check_counterexample(3, 4, 5, 2)
# 边界反例：n=1 的 (1,2,3) —— 满足方程但违反 n>=3 前提
ce2 = check_counterexample(1, 2, 3, 1)
# 对照：n=3 的 (3,4,5) —— 不满足方程
ce3 = check_counterexample(3, 4, 5, 3)

# ============================================================
# 3. 误解对照表（规避「名称相似定理混淆」陷阱）
# ============================================================
MISCONCEPTION_TABLE = [
    {"混淆项": "费马大定理 (FLT)",
     "陈述": "n>=3 时 x^n+y^n=z^n 无非零整数解",
     "与FLT关系": "本体",
     "区分要点": "关于指数 n>=3 的无解性"},
    {"混淆项": "费马小定理 (Fermat's Little Theorem)",
     "陈述": "若 p 为素数且 gcd(a,p)=1，则 a^(p-1) ≡ 1 (mod p)",
     "与FLT关系": "名称相似，内容无关",
     "区分要点": "模算术中的同余性质，非丢番图方程"},
    {"混淆项": "费马素数猜想 (Fermat Prime Conjecture)",
     "陈述": "形如 F_n = 2^(2^n)+1 的数均为素数",
     "与FLT关系": "名称相似，内容无关",
     "区分要点": "已被欧拉用 F_5=641×6700417 证伪"},
    {"混淆项": "费马大定理的『无解』",
     "陈述": "无解 ≠ 无法验证 ≠ 计算不可判定",
     "与FLT关系": "语义澄清",
     "区分要点": "FLT 是已证的真命题，与算法可解性/复杂度无关"},
]

# ============================================================
# 4. 证明史脉络（覆盖范围聚类 + 时间节点）
# ============================================================
PROOF_HISTORY = [
    {"阶段": "n=4", "覆盖范围": "n=4 全部情形",
     "结论强度": "部分情形", "归属": "费马 (Fermat)",
     "年份": 1637, "文献": "费马手稿旁注（后由他人整理）"},
    {"阶段": "n=3", "覆盖范围": "n=3 全部情形",
     "结论强度": "部分情形", "归属": "欧拉 (Euler)",
     "年份": 1770, "文献": "Euler, 'Vollständige Anleitung zur Algebra'"},
    {"阶段": "正则素数", "覆盖范围": "所有正则素数 p 的 n=p",
     "结论强度": "部分情形（覆盖无穷多但非全部）", "归属": "库默尔 (Kummer)",
     "年份": 1847, "文献": "Kummer, 'Beweis des Fermat'schen Satzes...'"},
    {"阶段": "全部 n>=3", "覆盖范围": "所有 n>=3",
     "结论强度": "全称命题", "归属": "怀尔斯 (Wiles) + 泰勒 (Taylor)",
     "年份": 1995, "文献": "Wiles, Annals of Mathematics 141 (1995) 443-551"},
]

# 证明完整性状态（规避「误称演讲即完整证明」陷阱）
COMPLETENESS_STATUS = {
    "宣布年份": 1993,
    "宣布场合": "怀尔斯在剑桥 Newton Institute 演讲",
    "漏洞发现": "1993 年审稿过程中发现关键引理（Euler system）存在漏洞",
    "补洞合作": "1994 年与 Richard Taylor 合作修补",
    "补全年份": 1994,
    "正式发表年份": 1995,
    "发表期刊": "Annals of Mathematics, 141 (1995), 443-551",
    "结论": "1993 年演讲不是完整证明；完整证明以 1995 年正式发表为准",
}

# ============================================================
# 5. 输出关键结果
# ============================================================
print("=" * 70)
print("【1】形式化命题")
print("=" * 70)
print("名称:", PROPOSITION["name"])
print("陈述:", PROPOSITION["statement"])
print("形式化:", PROPOSITION["formal"])
print("定义域:", PROPOSITION["domain"])
print("前提条件:")
for p in PROPOSITION["premises"]:
    print("  -", p)

print()
print("=" * 70)
print("【2】边界情形对照表 (n=1 / n=2 / n>=3)")
print("=" * 70)
for row in BOUNDARY_TABLE:
    print(f"  {row['n']:8s} | {row['equation']:20s} | {row['solution_status']:30s} | 在FLT范围: {row['is_FLT_scope']}")

print()
print("=" * 70)
print("【3】边界反例核验（前提不可省略）")
print("=" * 70)
for ce in [ce1, ce2, ce3]:
    print(f"  (x,y,z,n)=({ce['x']},{ce['y']},{ce['z']},{ce['n']}) | "
          f"满足方程: {ce['satisfies_equation']} | "
          f"满足FLT前提: {ce['satisfies_FLT_premise']} | "
          f"构成FLT反例: {ce['is_valid_counterexample_to_FLT']}")
print("  结论: 勾股数 (3,4,5) 与 (1,2,3) 满足方程但违反 n>=3 前提，")
print("        因此不构成对费马大定理的反驳，证明前提条件不可省略。")

print()
print("=" * 70)
print("【4】误解对照表")
print("=" * 70)
for m in MISCONCEPTION_TABLE:
    print(f"  [{m['混淆项']}]")
    print(f"    陈述: {m['陈述']}")
    print(f"    与FLT关系: {m['与FLT关系']} | 区分要点: {m['区分要点']}")

print()
print("=" * 70)
print("【5】证明史脉络（覆盖范围聚类）")
print("=" * 70)
for h in PROOF_HISTORY:
    print(f"  {h['阶段']:10s} | 覆盖: {h['覆盖范围']:25s} | "
          f"强度: {h['结论强度']:20s} | {h['归属']} ({h['年份']})")

print()
print("=" * 70)
print("【6】证明完整性状态（规避『演讲即证明』陷阱）")
print("=" * 70)
for k, v in COMPLETENESS_STATUS.items():
    print(f"  {k}: {v}")

# ============================================================
# 6. 落盘：CSV + 图
# ============================================================
# CSV 1: 边界情形对照表
with open("boundary_cases.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["n", "equation", "solution_status", "example", "is_FLT_scope"])
    writer.writeheader()
    writer.writerows(BOUNDARY_TABLE)

# CSV 2: 证明史
with open("proof_history.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["阶段", "覆盖范围", "结论强度", "归属", "年份", "文献"])
    writer.writeheader()
    writer.writerows(PROOF_HISTORY)

# 图：证明史时间线（覆盖范围 vs 年份）
fig, ax = plt.subplots(figsize=(10, 5))
years = [h["年份"] for h in PROOF_HISTORY]
labels = [h["阶段"] for h in PROOF_HISTORY]
strengths = [h["结论强度"] for h in PROOF_HISTORY]
colors = ["#4C72B0", "#4C72B0", "#DD8452", "#C44E52"]
ax.scatter(years, [1]*len(years), s=300, c=colors, zorder=3)
for i, (yr, lb, st) in enumerate(zip(years, labels, strengths)):
    ax.annotate(f"{lb}\n({yr})\n{st}", (yr, 1), textcoords="offset points",
                xytext=(0, 25 if i % 2 == 0 else -55), ha="center", fontsize=9)
ax.set_xlim(1600, 2020)
ax.set_ylim(0.5, 1.5)
ax.set_yticks([])
ax.set_xlabel("年份")
ax.set_title("费马大定理证明史时间线（按覆盖范围聚类）")
ax.grid(axis="x", linestyle="--", alpha=0.4)
plt.tight_layout()
plt.savefig("figure.png", dpi=150)
plt.close()

print()
print("=" * 70)
print("已落盘: boundary_cases.csv, proof_history.csv, figure.png")
print("=" * 70)