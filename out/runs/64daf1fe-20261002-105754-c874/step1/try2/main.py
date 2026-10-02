# -*- coding: utf-8 -*-
"""
数学建模：符号推导 + 数值交叉验证（精简可运行版）
问题：max f = 3*x1 + 5*x2
      s.t. 2*x1 + x2 <= 100, x1 + 3*x2 <= 90, x1,x2 >= 0
环境仅允许 numpy/matplotlib，用解析手推 + 数值验证实现符号推导等价效果。
"""

import sys
import io

# 关键修复：强制 stdout 使用 UTF-8，避免 Windows GBK 编码无法输出 ∂ 等字符
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 1. 定义域与假设
# ============================================================
# 决策变量 x=(x1,x2) ∈ R^2, x1>=0, x2>=0
# A1: LP，目标与约束线性，可行域为凸多面体
# A2: c1=3>0, c2=5>0，目标单调递增，最优解在边界
# A3: 可行域非空有界
# A4: 变量连续实数
# A5: 最优顶点处 LICQ 成立，KKT 有效
c1, c2 = 3.0, 5.0
a11, a12, b1 = 2.0, 1.0, 100.0
a21, a22, b2 = 1.0, 3.0, 90.0

print("=" * 60)
print("[1] 定义域与假设")
print("=" * 60)
print("决策变量: x1 >= 0, x2 >= 0 (连续实数)")
print("目标: max f = %.1f*x1 + %.1f*x2" % (c1, c2))
print("约束: %.1f*x1 + %.1f*x2 <= %.1f (机器工时)" % (a11, a12, b1))
print("      %.1f*x1 + %.1f*x2 <= %.1f (原料)" % (a21, a22, b2))

# ============================================================
# 2. 符号推导（KKT）
# ============================================================
print("\n" + "=" * 60)
print("[2] 符号推导与 KKT 一阶最优性条件")
print("=" * 60)
# L = c1*x1 + c2*x2 - l1*(a11*x1+a12*x2-b1) - l2*(a21*x1+a22*x2-b2) + m1*x1 + m2*x2
print("拉格朗日: L = c1*x1+c2*x2 - l1*(a11*x1+a12*x2-b1) - l2*(a21*x1+a22*x2-b2) + m1*x1 + m2*x2")
print("一阶条件 dL/dx1=0: c1 - l1*a11 - l2*a21 + m1 = 0")
print("一阶条件 dL/dx2=0: c2 - l1*a12 - l2*a22 + m2 = 0")
print("互补松弛: l1*(a11*x1+a12*x2-b1)=0, l2*(a21*x1+a22*x2-b2)=0, m1*x1=0, m2*x2=0")
print("对偶可行: l1,l2,m1,m2 >= 0")
print("因 c1,c2>0，最优解不在原点 => m1=m2=0，一阶条件退化为:")
print("  l1*a11 + l2*a21 = c1")
print("  l1*a12 + l2*a22 = c2")

A = np.array([[a11, a21], [a12, a22]])
cvec = np.array([c1, c2])
lam = np.linalg.solve(A, cvec)
print("解得 l1=%.6f, l2=%.6f" % (lam[0], lam[1]))

B = np.array([[a11, a12], [a21, a22]])
bvec = np.array([b1, b2])
x_star = np.linalg.solve(B, bvec)
print("两约束取等号，候选最优解 x* = (%.6f, %.6f)" % (x_star[0], x_star[1]))

kkt_ok = (lam[0] > 0) and (lam[1] > 0) and (x_star[0] >= 0) and (x_star[1] >= 0)
print("KKT 乘子符号: l1>0? %s, l2>0? %s" % (lam[0] > 0, lam[1] > 0))
print("候选解非负: x1>=0? %s, x2>=0? %s" % (x_star[0] >= 0, x_star[1] >= 0))
print("=> KKT 条件满足? %s" % kkt_ok)

f_star = c1 * x_star[0] + c2 * x_star[1]
print("符号解目标值 f* = %.6f" % f_star)

# ============================================================
# 3. 数值交叉验证
# ============================================================
print("\n" + "=" * 60)
print("[3] 数值交叉验证")
print("=" * 60)

def f(x1, x2):
    return c1 * x1 + c2 * x2

def feasible(x1, x2, tol=1e-9):
    return (a11 * x1 + a12 * x2 <= b1 + tol) and \
           (a21 * x1 + a22 * x2 <= b2 + tol) and x1 >= -tol and x2 >= -tol

print("符号解 x*=(%.6f, %.6f), f*=%.6f" % (x_star[0], x_star[1], f_star))
print("符号解可行性: %s" % feasible(x_star[0], x_star[1]))

# 网格搜索（用向量化加速，避免双重 Python 循环过慢）
N = 2001
xs = np.linspace(0, b1 / a11, N)
ys = np.linspace(0, b2 / a22, N)
X1, X2 = np.meshgrid(xs, ys)
mask = (a11 * X1 + a12 * X2 <= b1 + 1e-9) & \
       (a21 * X1 + a22 * X2 <= b2 + 1e-9) & \
       (X1 >= -1e-9) & (X2 >= -1e-9)
F = c1 * X1 + c2 * X2
F_masked = np.where(mask, F, -np.inf)
idx = np.unravel_index(np.argmax(F_masked), F_masked.shape)
best_val = F_masked[idx]
best_pt = (X1[idx], X2[idx])
print("网格搜索最优: x=(%.6f, %.6f), f=%.6f" % (best_pt[0], best_pt[1], best_val))
print("目标值差: %.6e" % abs(f_star - best_val))
print("坐标差: %.6e, %.6e" % (abs(x_star[0] - best_pt[0]), abs(x_star[1] - best_pt[1])))

grad = np.array([c1, c2])
n1 = np.array([a11, a12])
n2 = np.array([a21, a22])
recon = lam[0] * n1 + lam[1] * n2
print("梯度重构 c vs l1*n1+l2*n2: %s vs %s" % (grad, recon))
print("梯度重构误差: %.6e" % np.linalg.norm(grad - recon))

# ============================================================
# 4. 边界与奇点检查
# ============================================================
print("\n" + "=" * 60)
print("[4] 边界与奇点行为检查")
print("=" * 60)
print("原点 f(0,0)=%.6f (非最优，因 c>0)" % f(0, 0))
x1_only = b1 / a11
print("仅机器约束紧: x=(%.6f, 0), f=%.6f, 原料约束满足? %s"
      % (x1_only, f(x1_only, 0), a21 * x1_only <= b2))
x2_only = b2 / a22
print("仅原料约束紧: x=(0, %.6f), f=%.6f, 机器约束满足? %s"
      % (x2_only, f(0, x2_only), a12 * x2_only <= b1))
det_B = a11 * a22 - a12 * a21
print("约束矩阵行列式 det=%.6f (非零 => 无平行退化奇点)" % det_B)
cross1 = c1 * a12 - c2 * a11
cross2 = c1 * a22 - c2 * a21
print("梯度与约束1法向叉积=%.6f, 与约束2法向叉积=%.6f (非零 => 唯一最优)" % (cross1, cross2))

# ============================================================
# 5. 可直接用于代码的表达式
# ============================================================
print("\n" + "=" * 60)
print("[5] 可直接用于代码的表达式")
print("=" * 60)
print("最优解: x1* = %.6f, x2* = %.6f" % (x_star[0], x_star[1]))
print("最优值: f* = %.6f" % f_star)
print("KKT 乘子: l1* = %.6f, l2* = %.6f" % (lam[0], lam[1]))
print("Python 表达式: x_star = np.array([%.6f, %.6f])" % (x_star[0], x_star[1]))

# ============================================================
# 6. 出图
# ============================================================
fig, ax = plt.subplots(figsize=(7, 6))
x1_line = np.linspace(0, b1 / a11, 200)
x2_machine = (b1 - a11 * x1_line) / a12
x2_material = (b2 - a21 * x1_line) / a22
ax.plot(x1_line, x2_machine, 'b-', label='机器工时约束')
ax.plot(x1_line, x2_material, 'g-', label='原料约束')
upper = np.minimum(np.maximum(x2_machine, 0), np.maximum(x2_material, 0))
ax.fill_between(x1_line, 0, upper, where=(upper >= 0),
                color='lightgray', alpha=0.5, label='可行域')
ax.plot(x_star[0], x_star[1], 'r*', markersize=15, label='符号最优解')
ax.plot(best_pt[0], best_pt[1], 'ko', markersize=8, fillstyle='none', label='数值最优解')
ax.set_xlabel('x1 (产品1产量)')
ax.set_ylabel('x2 (产品2产量)')
ax.set_title('线性规划可行域与最优解（模拟数据）')
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_xlim(0, b1 / a11 * 1.1)
ax.set_ylim(0, b2 / a22 * 1.1)
plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n图已保存: figure.png")

# ============================================================
# 7. 落盘 CSV
# ============================================================
import csv
with open('kkt_results.csv', 'w', newline='', encoding='utf-8-sig') as fp:
    w = csv.writer(fp)
    w.writerow(['项目', '数值'])
    w.writerow(['x1_star', x_star[0]])
    w.writerow(['x2_star', x_star[1]])
    w.writerow(['f_star', f_star])
    w.writerow(['lambda1', lam[0]])
    w.writerow(['lambda2', lam[1]])
    w.writerow(['grid_best_x1', best_pt[0]])
    w.writerow(['grid_best_x2', best_pt[1]])
    w.writerow(['grid_best_f', best_val])
    w.writerow(['grad_recon_err', np.linalg.norm(grad - recon)])
print("结果已保存: kkt_results.csv")