# -*- coding: utf-8 -*-
"""
费马大定理：符号形式化 + 边界情形对照 + 前提必要性核验 + 证明史脉络
仅使用 numpy / matplotlib（标准库 csv 用于落盘）
"""
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 1. 符号形式化命题
# ============================================================
FLT_STATEMENT = (
    "费马大定理 (FLT): 对任意整数 n>=3, 不存在整数 x,y,z 满足 "
    "x^n + y^n = z^n 且 x*y*z != 0。\n"
    "形式化: forall n in Z, n>=3 -> not exists (x,y,z) in (Z\\{0})^3 : x^n+y^n=z^n"
)
print("=" * 70)
print("[1] 符号形式化命题")
print(FLT_STATEMENT)

# 变量定义域与前提条件
DOMAIN_TABLE = [
    ("n", "整数", "n >= 3", "指数下界，排除 n=1,2 的平凡/勾股情形"),
    ("x", "非零整数", "x != 0", "排除平凡解 (0^n+...=...^n)"),
    ("y", "非零整数", "y != 0", "同上"),
    ("z", "非零整数", "z != 0", "同上"),
]
print("\n变量定义域与前提条件:")
for v, dom, pre, why in DOMAIN_TABLE:
    print(f"  {v:>2} | 定义域={dom:<8} | 前提={pre:<8} | 理由={why}")

# 边界情形对照表 (n=1, n=2, n>=3)
BOUNDARY_TABLE = [
    ("n = 1", "x + y = z", "有无穷多解", "平凡：任取 x,y 令 z=x+y", "不构成定理范围"),
    ("n = 2", "x^2 + y^2 = z^2", "有无穷多解(勾股数)", "如 (3,4,5),(5,12,13)", "不构成定理范围"),
    ("n >= 3", "x^n + y^n = z^n", "无解 (x*y*z!=0)", "Wiles 1995 证明", "定理本体"),
]
print("\n边界情形对照表:")
print(f"  {'情形':<8}{'方程':<22}{'解的存在性':<20}{'例证/依据':<22}{'地位'}")
for row in BOUNDARY_TABLE:
    print(f"  {row[0]:<8}{row[1]:<22}{row[2]:<20}{row[3]:<22}{row[4]}")

# ============================================================
# 2. 边界反例验证前提不可省略
# ============================================================
print("\n" + "=" * 70)
print("[2] 边界反例验证前提不可省略 (反例满足方程但违反前提)")

def check_equation(x, y, z, n):
    return x**n + y**n == z**n

# 反例 A: n=2 勾股数 (违反 n>=3)
pyth = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25)]
print("\n反例A: n=2 勾股数 (违反前提 n>=3)")
for (x, y, z) in pyth:
    ok = check_equation(x, y, z, 2)
    print(f"  {x}^2 + {y}^2 = {z}^2 ? {ok}  -> 违反 n>=3, 不构成对 FLT 的反驳")

# 反例 B: 含零解 (违反 x*y*z != 0)
print("\n反例B: 含零解 (违反 x*y*z != 0)")
zero_cases = [(0, 5, 5, 3), (3, 0, 3, 4), (0, 0, 0, 5)]
for (x, y, z, n) in zero_cases:
    ok = check_equation(x, y, z, n)
    print(f"  {x}^{n} + {y}^{n} = {z}^{n} ? {ok}  -> 违反非零前提, 不构成对 FLT 的反驳")

# 反例 C: n>=3 且非零，暴力搜索小范围确认无解 (验证性检查)
print("\n反例C: n>=3 且 x,y,z 非零, 小范围暴力搜索 (|x|,|y|,|z|<=60, n=3..6)")
found = []
for n in range(3, 7):
    for x in range(-60, 61):
        if x == 0:
            continue
        for y in range(-60, 61):
            if y == 0:
                continue
            s = x**n + y**n
            # 检查 s 是否为某非零整数的 n 次幂
            if s == 0:
                continue
            sign = 1 if s > 0 else -1
            r = int(round(abs(s) ** (1.0 / n)))
            for cand in (r - 1, r, r + 1):
                if cand != 0 and sign * (abs(cand) ** n) == s:
                    found.append((n, x, y, sign * cand))
print(f"  搜索范围内找到的解数量: {len(found)}  (预期 0, 与 FLT 一致)")
print("  结论: 边界反例均违反前提, 前提条件不可省略。")

# ============================================================
# 3. 证明史脉络 (按覆盖范围聚类, 含文献与年份)
# ============================================================
print("\n" + "=" * 70)
print("[3] 证明史脉络 (覆盖范围 / 结论强度 / 文献 / 年份)")

HISTORY = [
    ("n=4", "部分情形", "Fermat (方法: 无穷递降)", "约 1640 (书信/笔记)", "部分"),
    ("n=3", "部分情形", "Euler", "1770", "部分"),
    ("n=5", "部分情形", "Dirichlet & Legendre", "1825", "部分"),
    ("n=7", "部分情形", "Lamé", "1839", "部分"),
    ("正则素数 p", "无穷多情形", "Kummer (理想数理论)", "1847", "部分(覆盖无穷多但非全部)"),
    ("所有 n>=3", "全称命题", "Wiles (含 Taylor 补洞)", "1995 (Ann. of Math.)", "完整"),
]
print(f"  {'覆盖范围':<14}{'结论强度':<12}{'证明者/方法':<28}{'年份':<22}{'状态'}")
for row in HISTORY:
    print(f"  {row[0]:<14}{row[1]:<12}{row[2]:<28}{row[3]:<22}{row[4]}")

# ============================================================
# 4. 核心证明思想逻辑链 (可追溯到定理名与年份)
# ============================================================
print("\n" + "=" * 70)
print("[4] 核心证明思想逻辑链 (每步追溯到定理名与年份)")
LOGIC_CHAIN = [
    ("假设存在非零解 a^n+b^n=c^n", "反证法起点", "-", "-"),
    ("构造 Frey 曲线 y^2=x(x-a^n)(x+b^n)", "Frey 1986", "Frey", "1986"),
    ("该曲线若存在则非模形式", "Serre 猜想 / Ribet 定理", "Ribet", "1990"),
    ("所有有理椭圆曲线均为模形式", "Taniyama-Shimura-Weil 猜想(半稳定情形)", "Wiles", "1995"),
    ("矛盾: 曲线既非模形式又必为模形式", "矛盾点", "Wiles", "1995"),
]
print(f"  {'步骤':<40}{'依据定理':<32}{'归属':<10}{'年份'}")
for step, thm, who, yr in LOGIC_CHAIN:
    print(f"  {step:<40}{thm:<32}{who:<10}{yr}")

# ============================================================
# 5. 常见误解对照表 + 名称相似定理区分
# ============================================================
print("\n" + "=" * 70)
print("[5] 常见误解对照表 (含名称相似定理区分)")

MISCONCEPTIONS = [
    ("费马大定理 vs 费马小定理",
     "小定理: a^p ≡ a (mod p), p 素数; 大定理: x^n+y^n=z^n 无解",
     "两者陈述与领域完全不同, 不可混淆"),
    ("费马大定理 vs 费马素数猜想",
     "素数猜想: F_n=2^(2^n)+1 为素数 (已被 Euler 反例 F_5 推翻)",
     "一个是方程无解, 一个是素数性猜想"),
    ("'无解' = '无法验证'",
     "FLT 是已证真命题 (Wiles 1995), 与算法可解性无关",
     "无解是数学事实, 非计算不可判定"),
    ("FLT 提供求解算法",
     "FLT 只断言不存在解, 不提供任何算法",
     "不涉及计算复杂度, 非构造性结论"),
    ("全部由 Wiles 完成",
     "n=3,4,5,7 及正则素数情形由 Euler/Dirichlet/Lamé/Kummer 等完成",
     "Wiles 完成的是全称命题的最终证明"),
]
print(f"  {'误解':<28}{'区分陈述':<52}{'核验结论'}")
for a, b, c in MISCONCEPTIONS:
    print(f"  {a:<28}{b:<52}{c}")

# ============================================================
# 6. 证明完整性状态 (宣布 / 漏洞 / 补全 / 发表)
# ============================================================
print("\n" + "=" * 70)
print("[6] 证明完整性状态 (宣布 / 漏洞 / 补全 / 发表)")
COMPLETENESS = [
    ("宣布", "1993-06", "Wiles 在剑桥演讲宣布证明"),
    ("漏洞发现", "1993-12", "审稿发现 Euler 系统构造存在缺陷"),
    ("补全", "1994-09", "Wiles 与 Taylor 合作修补 (Taylor-Wiles 方法)"),
    ("正式发表", "1995-05", "Annals of Mathematics 141(3), 443-551"),
]
for stage, date, desc in COMPLETENESS:
    print(f"  {stage:<8}{date:<12}{desc}")
print("  注意: 1993 演讲不等于完整证明, 必须标注补全与发表节点。")

# ============================================================
# 落盘: CSV 数据表 + 图
# ============================================================
# CSV 1: 边界情形对照表
with open("boundary_cases.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["情形", "方程", "解的存在性", "例证/依据", "地位"])
    for row in BOUNDARY_TABLE:
        w.writerow(row)

# CSV 2: 证明史脉络
with open("proof_history.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["覆盖范围", "结论强度", "证明者/方法", "年份", "状态"])
    for row in HISTORY:
        w.writerow(row)

# CSV 3: 误解对照表
with open("misconceptions.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["误解", "区分陈述", "核验结论"])
    for row in MISCONCEPTIONS:
        w.writerow(row)

# 图: 证明史覆盖范围时间线 (模拟数据标注: 年份为真实文献年份)
fig, ax = plt.subplots(figsize=(10, 5))
labels = [h[0] for h in HISTORY]
years = [1640, 1770, 1825, 1839, 1847, 1995]
colors = ['#4C72B0'] * 5 + ['#C44E52']
ax.barh(labels, years, color=colors)
for i, (lab, yr) in enumerate(zip(labels, years)):
    ax.text(yr + 20, i, str(yr), va='center', fontsize=9)
ax.set_xlabel("年份 (真实文献年份)")
ax.set_title("费马大定理证明史: 覆盖范围与年份 (蓝色=部分情形, 红色=全称命题)")
ax.set_xlim(0, 2200)
plt.tight_layout()
plt.savefig("figure.png", dpi=120)
plt.close()

print("\n" + "=" * 70)
print("[落盘文件] boundary_cases.csv, proof_history.csv, misconceptions.csv, figure.png")
print("全部步骤完成。")