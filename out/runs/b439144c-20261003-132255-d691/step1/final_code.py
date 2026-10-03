# -*- coding: utf-8 -*-
"""
费马大定理的符号形式化与边界验证
--------------------------------
命题: 对 n >= 3, 方程 x^n + y^n = z^n 无非零整数解 (x,y,z in Z\{0})
边界: n=1 恒有解; n=2 为勾股数, 有无穷多解; n>=3 无解 (Wiles, 1995)
本脚本用有限枚举做"数值证据"检查, 不构成证明。
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ---------------- 1. 符号形式化 (以字符串/结构显式声明) ----------------
DOMAIN = {
    "x": "Z \\ {0}",
    "y": "Z \\ {0}",
    "z": "Z \\ {0}",
    "n": "Z, n >= 1",
}
PROPOSITION = "forall n>=3, forall x,y,z in Z\\{0}: x^n + y^n != z^n"
print("[符号形式化] 变量定义域:")
for k, v in DOMAIN.items():
    print(f"    {k} in {v}")
print("[符号形式化] 命题:", PROPOSITION)
print("[符号形式化] 边界: n=1 有解(如 1+1=2); n=2 勾股数有解; n>=3 无解\n")

# ---------------- 2. 有限枚举: 数值证据 (非证明) ----------------
LIMIT = 200          # |x|,|y|,|z| 的搜索上界
N_MAX = 6            # 检查 n = 1..6

def count_solutions(n, limit):
    """统计 |x|,|y|,|z| <= limit 内的非零整数解个数 (含符号组合)。"""
    vals = np.arange(-limit, limit + 1)
    vals = vals[vals != 0]                      # 排除 0, 满足 Z\{0}
    # 用集合加速: 预计算所有 z^n
    zpow = {}
    for z in vals:
        zpow[int(z) ** n] = zpow.get(int(z) ** n, 0) + 1
    cnt = 0
    for x in vals:
        for y in vals:
            s = int(x) ** n + int(y) ** n
            cnt += zpow.get(s, 0)
    return cnt

print(f"[枚举] 搜索范围 |x|,|y|,|z| <= {LIMIT}, 排除 0")
results = {}
for n in range(1, N_MAX + 1):
    c = count_solutions(n, LIMIT)
    results[n] = c
    tag = "有解" if c > 0 else "无解(范围内)"
    print(f"    n={n}: 解个数 = {c:>8d}   -> {tag}")

# ---------------- 3. 已知陷阱检查 ----------------
print("\n[陷阱检查]")
# 陷阱1: 忘记排除 0 -> 会引入 x=0 之类的平凡解
vals_all = np.arange(-LIMIT, LIMIT + 1)
zpow_all = {}
for z in vals_all:
    zpow_all[int(z) ** 3] = zpow_all.get(int(z) ** 3, 0) + 1
cnt_with_zero = 0
for x in vals_all:
    for y in vals_all:
        cnt_with_zero += zpow_all.get(int(x) ** 3 + int(y) ** 3, 0)
print(f"    n=3 若允许 0: 解个数={cnt_with_zero}, 排除 0 后={results[3]} "
      f"-> 差异 {cnt_with_zero - results[3]} (证明必须限定 Z\\{{0}})")
# 陷阱2: 浮点幂误差 -> 用整数幂
x, y, z, n = 3, 4, 5, 2
print(f"    浮点检查 3^2+4^2={3.0**2 + 4.0**2}, 5^2={5.0**2}, "
      f"相等? {3.0**2 + 4.0**2 == 5.0**2} (整数幂更安全)")
# 陷阱3: n=2 有解, 不能外推到 n>=3
print(f"    n=2 解个数={results[2]} > 0, 说明 n=2 与 n>=3 必须分开讨论")

# ---------------- 4. 出图 ----------------
ns = list(results.keys())
cs = [results[k] for k in ns]
fig, ax = plt.subplots(figsize=(7, 4.5))
colors = ['#4C72B0' if c > 0 else '#C44E52' for c in cs]
bars = ax.bar([str(k) for k in ns], cs, color=colors)
ax.set_xlabel("指数 n")
ax.set_ylabel("非零整数解个数 (|x|,|y|,|z| <= %d)" % LIMIT)
ax.set_title("费马方程 x^n + y^n = z^n 的有限枚举解数\n(数值证据, 非证明)")
for b, c in zip(bars, cs):
    ax.text(b.get_x() + b.get_width() / 2, c, str(c),
            ha='center', va='bottom', fontsize=9)
ax.axhline(0, color='gray', linewidth=0.8)
plt.tight_layout()
plt.savefig("figure.png", dpi=150)
print("\n[输出] 图已保存: figure.png")

# ---------------- 5. 落盘 CSV ----------------
with open("fermat_enum.csv", "w", encoding="utf-8") as f:
    f.write("n,solution_count,limit\n")
    for k in ns:
        f.write(f"{k},{results[k]},{LIMIT}\n")
print("[输出] 数据已保存: fermat_enum.csv")

print("\n[结论] 有限枚举显示 n=1,2 有解, n>=3 在搜索范围内无解;")
print("       这与费马大定理一致, 但枚举不构成数学证明 (Wiles 1995 给出证明)。")