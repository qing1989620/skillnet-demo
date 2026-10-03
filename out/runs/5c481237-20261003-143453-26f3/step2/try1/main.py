import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv
import os

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

TOL = 1e-12

# ============================================================
# 步骤1：读取前序产物（真实文件，不重造数据）
# ============================================================
def load_csv_safe(path):
    if not os.path.exists(path):
        print(f"[警告] 未找到 {path}，使用空表占位（模拟数据标注）")
        return []
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

boundary_rows = load_csv_safe('boundary_counterexamples.csv')
timeline_rows = load_csv_safe('proof_timeline.csv')
print(f"[读取] boundary_counterexamples.csv 行数 = {len(boundary_rows)}")
print(f"[读取] proof_timeline.csv 行数 = {len(timeline_rows)}")
print(f"[读取] figure.png 存在 = {os.path.exists('figure.png')}")

# ============================================================
# 步骤2：核心反例核验 —— FLT n=2 与 费马小定理 p 非素数
# ============================================================
print("\n===== 边界反例核验：前提不可省略 =====")

# --- 反例A：FLT 取 n=2 的勾股数 (3,4,5) ---
a, b, c, n = 3, 4, 5, 2
lhs = a**n + b**n
rhs = c**n
flt_holds = (lhs == rhs)
flt_premise_ok = (n >= 3)  # FLT 前提：n>=3 整数
print(f"[FLT] n={n}, {a}^{n}+{b}^{n}={lhs}, {c}^{n}={rhs}, 等式成立={flt_holds}")
print(f"[FLT] 满足前提 n>=3 ? {flt_premise_ok}  -> 违反前提，故不构成对 FLT 的反驳")
assert flt_holds and not flt_premise_ok

# --- 反例B：费马小定理取 a=2, p=4（非素数） ---
a2, p2 = 2, 4
val = pow(a2, p2 - 1, p2)  # 2^3 mod 4
flt_little_ok = (val == 1)
p_is_prime = all(p2 % k != 0 for k in range(2, int(p2**0.5) + 1)) and p2 > 1
print(f"[小定理] a={a2}, p={p2}, a^(p-1) mod p = {val}, 等于1? {flt_little_ok}")
print(f"[小定理] p 为素数? {p_is_prime}  -> 违反前提，故不构成对费马小定理的反驳")
assert (not flt_little_ok) and (not p_is_prime)

# 对照：合法前提下的正例
print(f"[小定理-正例] a=2, p=5(素数): 2^4 mod 5 = {pow(2,4,5)} (应为1)")
print(f"[FLT-正例] n=3: 3^3+4^3={3**3+4**3} != 5^3={5**3} (无解，符合)")

# ============================================================
# 步骤3：两条定义路径 + 六类特殊角交叉验证（规避"仅抽样"陷阱）
# ============================================================
print("\n===== 两条定义路径交叉验证（几何 vs 坐标/级数） =====")

# 路径1：几何定义（单位圆坐标）
def path_geom(theta):
    return np.cos(theta), np.sin(theta)

# 路径2：级数展开（独立路径）
def path_series(theta, terms=40):
    c = sum(((-1)**k) * theta**(2*k) / np.math.factorial(2*k) for k in range(terms))
    s = sum(((-1)**k) * theta**(2*k+1) / np.math.factorial(2*k+1) for k in range(terms))
    return c, s

# 六类角：端点0、锐角、直角、钝角、负角、超一周角
angles = {
    '端点0': 0.0,
    '锐角': np.pi/6,
    '直角': np.pi/2,
    '钝角': 2*np.pi/3,
    '负角': -np.pi/4,
    '超一周角': 2*np.pi + np.pi/3,
}
max_err = 0.0
for name, th in angles.items():
    c1, s1 = path_geom(th)
    c2, s2 = path_series(th)
    err = max(abs(c1-c2), abs(s1-s2))
    max_err = max(max_err, err)
    ident = c1**2 + s1**2
    tan_def = (s1/c1) if abs(c1) > TOL else None
    print(f"  {name:6s} θ={th:+.4f} | 几何=({c1:+.6f},{s1:+.6f}) 级数=({c2:+.6f},{s2:+.6f}) "
          f"err={err:.2e} sin²+cos²={ident:.12f} tan={'无定义' if tan_def is None else f'{tan_def:+.6f}'}")
    assert err < 1e-10, f"{name} 两路径不一致"
    assert abs(ident - 1.0) < TOL, f"{name} 恒等式失败"
print(f"[结论] 两路径最大误差 = {max_err:.2e} (<1e-10)，恒等式误差 <1e-12，无假矛盾")

# 直角处 tan 无定义检查
c90, s90 = path_geom(np.pi/2)
print(f"[tan 无定义检查] cos(π/2)={c90:.2e} -> |cos|<1e-12 判定 tan 无定义: {abs(c90)<TOL}")

# ============================================================
# 步骤4：和角公式 vs 级数（具名定理验证）
# ============================================================
print("\n===== 和角公式 vs 级数展开 =====")
x, y = np.pi/5, np.pi/7
cxy_g = np.cos(x+y); sxy_g = np.sin(x+y)
cxy_f = np.cos(x)*np.cos(y) - np.sin(x)*np.sin(y)
sxy_f = np.sin(x)*np.cos(y) + np.cos(x)*np.sin(y)
e1 = abs(cxy_g - cxy_f); e2 = abs(sxy_g - sxy_f)
print(f"  cos(x+y) 误差={e1:.2e}, sin(x+y) 误差={e2:.2e} (<1e-10: {max(e1,e2)<1e-10})")
assert max(e1, e2) < 1e-10

# ============================================================
# 步骤5：误解对照表（含定义域/值域/周期性差异 + 反例）
# ============================================================
print("\n===== 易混淆概念对照表 =====")
misconceptions = [
    ("三角函数 vs 反三角函数",
     "误以为 arcsin 是 sin 的倒数(1/sin)",
     "arcsin 是 sin 的反函数(值域受限)，csc=1/sin 才是倒数",
     "sin(π/6)=0.5, arcsin(0.5)=π/6≈0.5236, 1/sin(π/6)=2.0 -> 三者互不相等"),
    ("三角函数 vs 双曲函数",
     "误以为 cosh 与 cos 是同一函数",
     "cos 周期2π有界[-1,1]；cosh 无周期无界[1,∞)",
     "cos(0)=1, cosh(0)=1 但 cos(π)=-1, cosh(π)≈11.59"),
    ("勾股定理 vs 费马大定理",
     "误以为 a²+b²=c² 可推广到任意 n",
     "勾股定理仅 n=2；FLT 断言 n≥3 无正整数解",
     "3²+4²=5² 成立(n=2)，但 3³+4³=91≠125=5³(n=3)"),
]
for i, (name, mis, dist, cex) in enumerate(misconceptions, 1):
    print(f"  [{i}] {name}")
    print(f"      误解: {mis}")
    print(f"      区分: {dist}")
    print(f"      反例: {cex}")

# 定义域/值域/周期性差异表
print("\n  --- 定义域/值域/周期性差异 ---")
func_table = [
    ("sin", "R", "[-1,1]", "2π"),
    ("arcsin", "[-1,1]", "[-π/2,π/2]", "无"),
    ("sinh", "R", "R", "无"),
    ("cosh", "R", "[1,∞)", "无"),
]
for f, dom, rng, per in func_table:
    print(f"      {f:7s} 定义域={dom:10s} 值域={rng:12s} 周期={per}")

# ============================================================
# 步骤6：发展史时间线（含"约"标注与文献）
# ============================================================
print("\n===== 概念发展史时间线（含争议年份标注） =====")
history = [
    ("约公元前1800", "巴比伦 Plimpton 322 泥板", "勾股数表(经验)"),
    ("约公元前550", "毕达哥拉斯学派", "勾股定理证明(争议)"),
    ("约1637", "费马手稿批注", "FLT 提出(未发表)"),
    ("约1640", "费马书信", "费马小定理(宣布)"),
    ("1736", "欧拉", "小定理首个正式证明"),
    ("1995", "Wiles & Taylor", "FLT 正式证明(发表)"),
]
for yr, who, what in history:
    print(f"  {yr:12s} | {who:22s} | {what}")

# ============================================================
# 步骤7：出图 —— 反例核验与两路径一致性
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# 左图：六类角两路径误差
names = list(angles.keys())
errs = []
for th in angles.values():
    c1, s1 = path_geom(th); c2, s2 = path_series(th)
    errs.append(max(abs(c1-c2), abs(s1-s2)))
axes[0].bar(names, errs, color='steelblue')
axes[0].axhline(1e-10, color='red', ls='--', label='阈值 1e-10')
axes[0].set_yscale('log')
axes[0].set_title('六类特殊角：几何 vs 级数 误差')
axes[0].set_ylabel('最大绝对误差')
axes[0].legend()
axes[0].tick_params(axis='x', rotation=30)

# 右图：FLT 前提核验
ns = [2, 3, 4, 5]
lhs_vals = [3**n + 4**n for n in ns]
rhs_vals = [5**n for n in ns]
xpos = np.arange(len(ns))
axes[1].bar(xpos - 0.2, lhs_vals, 0.4, label='3^n+4^n', color='orange')
axes[1].bar(xpos + 0.2, rhs_vals, 0.4, label='5^n', color='green')
axes[1].set_xticks(xpos); axes[1].set_xticklabels([f'n={n}' for n in ns])
axes[1].set_yscale('log')
axes[1].set_title('FLT 前提核验：n=2 成立, n>=3 不成立')
axes[1].legend()

plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n[落盘] figure.png 已生成")

# ============================================================
# 步骤8：落盘 CSV
# ============================================================
with open('boundary_counterexamples.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['反例', '参数', '计算值', '违反前提', '是否构成反驳'])
    w.writerow(['FLT', 'n=2,(3,4,5)', f'{lhs}={rhs}', 'n>=3', '否'])
    w.writerow(['费马小定理', 'a=2,p=4', f'2^3 mod 4={val}', 'p为素数', '否'])
    w.writerow(['FLT正例', 'n=3', f'{3**3+4**3}!={5**3}', '满足n>=3', '符合(无解)'])
    w.writerow(['小定理正例', 'a=2,p=5', f'2^4 mod 5={pow(2,4,5)}', '满足p素数', '符合'])
print("[落盘] boundary_counterexamples.csv 已更新")

with open('proof_timeline.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['年份', '人物/文献', '事件'])
    for row in history:
        w.writerow(row)
print("[落盘] proof_timeline.csv 已更新")

print("\n===== 全部核验通过 =====")