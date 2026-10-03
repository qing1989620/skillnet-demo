# -*- coding: utf-8 -*-
"""
费马大定理核心思想 —— 边界反例清单构造与核验
本步骤：构造边界反例清单（n=2 勾股数、n=1 平凡解、x/y 为负、z=0 等），
逐条标注违反哪条前提，并代入原方程 x^n + y^n = z^n 核验是否构成对定理的反驳。

注意：费马大定理（FLT）的严格陈述为：
  对整数 n >= 3，不存在正整数 x, y, z 满足 x^n + y^n = z^n。
因此所有"反例"必然违反某条前提（n>=3 / 正整数 / 非零）。
本代码逐条核验并标注违反的前提。
"""
import os
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

TOL = 1e-12

# ----------------------------------------------------------------------
# 1. 读取前序产物（真实文件，若缺失则明确报错，不伪造）
# ----------------------------------------------------------------------
def load_csv_safe(path):
    if not os.path.exists(path):
        print(f"[警告] 未找到输入文件 {path}，本步骤将仅使用内置边界清单。")
        return None
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

boundary_in = load_csv_safe("boundary_cases.csv")
proof_hist = load_csv_safe("proof_history.csv")
print(f"[输入] boundary_cases.csv 行数 = {0 if boundary_in is None else len(boundary_in)}")
print(f"[输入] proof_history.csv 行数 = {0 if proof_hist is None else len(proof_hist)}")

# ----------------------------------------------------------------------
# 2. 费马大定理的形式化定义（两条等价路径）
#    路径A（代数/整数路径）：FLT_A: ∀n∈Z, n>=3 → ¬∃(x,y,z)∈Z_{>0}^3, x^n+y^n=z^n
#    路径B（几何/曲线路径）：FLT_B: 曲线 a^n+b^n=1 在 n>=3 时无正有理点(a,b)
#    两路径在 n 为整数、x,y,z 为正整数、欧氏整数环前提下等价。
# ----------------------------------------------------------------------
def flt_residual(x, y, z, n):
    """返回 x^n + y^n - z^n 的残差（用整数/浮点混合，n 为整数时用精确整数）。"""
    if isinstance(n, int) and n >= 0:
        return int(x) ** n + int(y) ** n - int(z) ** n
    return float(x) ** n + float(y) ** n - float(z) ** n

def check_premises(x, y, z, n):
    """检查是否满足 FLT 的全部前提，返回违反前提的列表。"""
    viol = []
    if not (isinstance(n, int) and n >= 3):
        viol.append("n>=3 且 n 为整数")
    if not (isinstance(x, int) and x > 0):
        viol.append("x 为正整数")
    if not (isinstance(y, int) and y > 0):
        viol.append("y 为正整数")
    if not (isinstance(z, int) and z > 0):
        viol.append("z 为正整数")
    return viol

# ----------------------------------------------------------------------
# 3. 构造边界反例清单
#    每条：名称、x、y、z、n、说明
# ----------------------------------------------------------------------
cases = [
    # n=2 勾股数：违反 n>=3
    ("勾股数(3,4,5), n=2", 3, 4, 5, 2, "n=2 属毕达哥拉斯方程，非 FLT 范围"),
    ("勾股数(5,12,13), n=2", 5, 12, 13, 2, "n=2 属毕达哥拉斯方程，非 FLT 范围"),
    # n=1 平凡解：违反 n>=3
    ("平凡解(1,1,2), n=1", 1, 1, 2, 1, "n=1 时 x+y=z 恒有解，非 FLT 范围"),
    # x 为负：违反 x 为正整数
    ("x 为负 (-3,4,5), n=2", -3, 4, 5, 2, "x<0 违反正整数前提"),
    ("x 为负 (-1,2,3), n=3", -1, 2, 3, 3, "x<0 违反正整数前提"),
    # y 为负：违反 y 为正整数
    ("y 为负 (3,-4,5), n=2", 3, -4, 5, 2, "y<0 违反正整数前提"),
    # z=0：违反 z 为正整数
    ("z=0 (0,0,0), n=3", 0, 0, 0, 3, "z=0 违反正整数前提"),
    ("z=0 (1,1,0), n=3", 1, 1, 0, 3, "z=0 违反正整数前提"),
    # 零解：违反正整数
    ("零解 (0,0,0), n=3", 0, 0, 0, 3, "全零违反正整数前提"),
    # n=0：违反 n>=3
    ("n=0 (1,1,1)", 1, 1, 1, 0, "n=0 违反 n>=3"),
    # n 为负：违反 n>=3
    ("n=-1 (1,1,1)", 1, 1, 1, -1, "n<0 违反 n>=3"),
    # 真正满足前提的候选（应无解，残差非零）
    ("候选 (1,1,1), n=3", 1, 1, 1, 3, "满足全部前提，残差应为非零"),
    ("候选 (2,3,4), n=3", 2, 3, 4, 3, "满足全部前提，残差应为非零"),
]

# ----------------------------------------------------------------------
# 4. 逐条核验：代入原方程 + 标注违反前提 + 是否构成反驳
# ----------------------------------------------------------------------
rows = []
n_refuted = 0
for name, x, y, z, n, note in cases:
    viol = check_premises(x, y, z, n)
    try:
        res = flt_residual(x, y, z, n)
    except Exception as e:
        res = float("nan")
    # 是否"形式上"满足方程（残差为0）
    eq_holds = (abs(res) < TOL) if not np.isnan(res) else False
    # 是否构成对 FLT 的反驳：必须满足全部前提 且 方程成立
    is_refute = (len(viol) == 0) and eq_holds
    if is_refute:
        n_refuted += 1
    rows.append({
        "case": name, "x": x, "y": y, "z": z, "n": n,
        "residual": res, "equation_holds": eq_holds,
        "violated_premises": "; ".join(viol) if viol else "无（满足全部前提）",
        "refutes_FLT": is_refute, "note": note,
    })

print("\n===== 边界反例清单核验 =====")
print(f"{'案例':<26}{'残差':>14}{'方程成立':>10}{'违反前提':>28}{'构成反驳':>10}")
for r in rows:
    print(f"{r['case']:<26}{r['residual']:>14}{str(r['equation_holds']):>10}"
          f"{r['violated_premises']:>28}{str(r['refutes_FLT']):>10}")
print(f"\n[结论] 构成对 FLT 反驳的案例数 = {n_refuted}（应为 0）")

# ----------------------------------------------------------------------
# 5. 陷阱规避检查
# ----------------------------------------------------------------------
print("\n===== 已知陷阱规避检查 =====")
# 陷阱1：把局部定义误当全局定义 —— 检查 n=2 案例是否被正确标注为"违反 n>=3"
n2_cases = [r for r in rows if r["n"] == 2]
n2_ok = all("n>=3" in r["violated_premises"] for r in n2_cases)
print(f"[陷阱1] n=2 勾股数均标注违反 n>=3 前提: {n2_ok}")

# 陷阱2：数值核验仅抽样 —— 本步骤覆盖 n=0,1,2,3,-1 与 x/y/z 正负零端点
n_vals = sorted(set(r["n"] for r in rows))
print(f"[陷阱2] 覆盖的 n 取值集合 = {n_vals}（含端点与越界值）")

# 陷阱3：定义等价性未附加条件 —— 显式声明隐含假设
print("[陷阱3] 隐含假设声明：FLT 在整数环 Z、欧氏几何、n 为整数前提下成立；"
      "n 为实数/复数时命题形式不同，不在本清单范围。")

# 陷阱4：历史年份争议 —— 从 proof_history.csv 读取并标注
if proof_hist:
    print("[陷阱4] 历史年份（来自 proof_history.csv，含争议标注）：")
    for h in proof_hist[:6]:
        print("   ", {k: h[k] for k in list(h.keys())[:4]})
else:
    print("[陷阱4] proof_history.csv 缺失，历史年份核验跳过（不伪造）。")

# ----------------------------------------------------------------------
# 6. 出图：残差绝对值（对数刻度）对比，标注是否构成反驳
# ----------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 6))
labels = [r["case"] for r in rows]
res_abs = [max(abs(r["residual"]), 1e-16) for r in rows]
colors = ["#d62728" if r["refutes_FLT"] else "#1f77b4" for r in rows]
bars = ax.barh(range(len(rows)), res_abs, color=colors)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels(labels, fontsize=8)
ax.set_xscale("log")
ax.set_xlabel("|x^n + y^n - z^n| 残差绝对值（对数刻度）")
ax.set_title("费马大定理边界反例清单：残差核验（红色=构成反驳，蓝色=违反前提）")
ax.axvline(TOL, color="green", linestyle="--", label=f"容差 {TOL}")
ax.legend()
plt.tight_layout()
plt.savefig("figure.png", dpi=150)
plt.close()
print("\n[输出] figure.png 已生成")

# ----------------------------------------------------------------------
# 7. 落盘：边界反例清单 CSV
# ----------------------------------------------------------------------
out_csv = "boundary_refutation_check.csv"
with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"[输出] {out_csv} 已生成，共 {len(rows)} 条记录")