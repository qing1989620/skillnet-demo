# -*- coding: utf-8 -*-
"""
数学建模：符号推导 + 数值交叉验证
问题（业务场景，模拟数据）：
  某工厂生产两种产品 x1, x2（单位：件），
  单位利润 c1=3, c2=5；
  资源约束：机器工时 2*x1 + 1*x2 <= 100，原料 1*x1 + 3*x2 <= 90；
  决策变量非负：x1>=0, x2>=0。
  目标：最大化利润 f(x) = c1*x1 + c2*x2。

本步骤：写出决策变量/目标/约束的符号形式，解析求导得到 KKT 最优性条件，
       保留中间推导，显式声明定义域与假设，并做数值交叉验证与边界检查。

注意：本文件不依赖 sympy（环境仅允许 numpy/matplotlib），
     因此用「解析手推 + 数值验证」的方式实现符号推导的等价效果，
     并在注释中完整保留符号推导的中间步骤。
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 1. 变量定义域与假设条件（显式声明）
# ============================================================
# 决策变量: x = (x1, x2) ∈ R^2
# 定义域:   x1 >= 0, x2 >= 0  (非负)
# 假设:
#   (A1) 线性规划(LP)，目标与约束均为线性 => 目标函数线性、约束集为凸多面体
#   (A2) 系数 c1=3, c2=5 > 0，故目标在可行域上单调递增，最优解必在边界
#   (A3) 可行域非空且有界（由两个资源约束 + 非负约束围成）
#   (A4) 变量为连续实数（非整数）；若为整数规划需另加整数约束
#   (A5) 不考虑奇点：LP 的 KKT 条件在最优顶点处成立（LICQ 满足）
ASSUMPTIONS = [
    "A1: 线性规划，目标与约束线性，可行域为凸多面体",
    "A2: c1=3>0, c2=5>0，目标单调递增，最优解在边界",
    "A3: 可行域非空有界",
    "A4: 变量为连续实数（非整数）",
    "A5: 最优顶点处 LICQ 成立，KKT 必要条件有效",
]

# 参数（模拟数据，非真实实验数据）
c1, c2 = 3.0, 5.0
a11, a12 = 2.0, 1.0   # 机器工时约束系数
b1 = 100.0
a21, a22 = 1.0, 3.0   # 原料约束系数
b2 = 90.0

print("=" * 60)
print("【1】变量定义域与假设条件（显式声明）")
print("=" * 60)
print("决策变量: x1 >= 0, x2 >= 0  (连续实数)")
print("目标: max f(x) = %.1f*x1 + %.1f*x2" % (c1, c2))
print("约束: %.1f*x1 + %.1f*x2 <= %.1f  (机器工时)" % (a11, a12, b1))
print("      %.1f*x1 + %.1f*x2 <= %.1f  (原料)" % (a21, a22, b2))
for a in ASSUMPTIONS:
    print("  " + a)

# ============================================================
# 2. 符号推导（保留中间步骤）
# ============================================================
print("\n" + "=" * 60)
print("【2】符号推导与 KKT 一阶最优性条件（保留中间步骤）")
print("=" * 60)

# 拉格朗日函数（符号形式）:
#   L(x, λ, μ) = c1*x1 + c2*x2
#                - λ1*(a11*x1 + a12*x2 - b1)
#                - λ2*(a21*x1 + a22*x2 - b2)
#                + μ1*x1 + μ2*x2
# 其中 λ1,λ2 >= 0 为不等式约束乘子, μ1,μ2 >= 0 为非负约束乘子
print("拉格朗日函数:")
print("  L = c1*x1 + c2*x2 - λ1*(a11*x1+a12*x2-b1) - λ2*(a21*x1+a22*x2-b2) + μ1*x1 + μ2*x2")

# 一阶条件 ∂L/∂x1 = 0, ∂L/∂x2 = 0:
#   c1 - λ1*a11 - λ2*a21 + μ1 = 0
#   c2 - λ1*a12 - λ2*a22 + μ2 = 0
print("一阶条件 ∂L/∂x1=0:  c1 - λ1*a11 - λ2*a21 + μ1 = 0")
print("一阶条件 ∂L/∂x2=0:  c2 - λ1*a12 - λ2*a22 + μ2 = 0")
print("互补松弛: λ1*(a11*x1+a12*x2-b1)=0, λ2*(a21*x1+a22*x2-b2)=0")
print("          μ1*x1=0, μ2*x2=0")
print("对偶可行: λ1,λ2,μ1,μ2 >= 0")

# 由于 c1,c2>0，最优解不可能在原点（x1=x2=0 时 μ1=c1>0, μ2=c2>0 但目标=0 非最优）
# 故 μ1=μ2=0，一阶条件退化为:
#   λ1*a11 + λ2*a21 = c1
#   λ1*a12 + λ2*a22 = c2
print("\n因 c1,c2>0，最优解不在原点 => μ1=μ2=0，一阶条件退化为:")
print("  λ1*a11 + λ2*a21 = c1")
print("  λ1*a12 + λ2*a22 = c2")

# 求解 λ（2x2 线性方程组）
A = np.array([[a11, a21], [a12, a22]])
cvec = np.array([c1, c2])
lam = np.linalg.solve(A, cvec)
print("解得 λ1=%.6f, λ2=%.6f" % (lam[0], lam[1]))

# 若 λ1,λ2 > 0，则两个约束均取等号（紧约束），解交点:
#   a11*x1 + a12*x2 = b1
#   a21*x1 + a22*x2 = b2
B = np.array([[a11, a12], [a21, a22]])
bvec = np.array([b1, b2])
x_star = np.linalg.solve(B, bvec)
print("两约束取等号，解得候选最优解 x* = (%.6f, %.6f)" % (x_star[0], x_star[1]))

# 检查 λ 与 x 的符号（KKT 可行性）
kkt_ok = (lam[0] > 0) and (lam[1] > 0) and (x_star[0] >= 0) and (x_star[1] >= 0)
print("KKT 乘子符号检查: λ1>0? %s, λ2>0? %s" % (lam[0] > 0, lam[1] > 0))
print("候选解非负检查: x1>=0? %s, x2>=0? %s" % (x_star[0] >= 0, x_star[1] >= 0))
print("=> KKT 条件满足? %s" % kkt_ok)

f_star = c1 * x_star[0] + c2 * x_star[1]
print("符号解目标值 f* = %.6f" % f_star)

# ============================================================
# 3. 数值交叉验证（在若干数值点比对）
# ============================================================
print("\n" + "=" * 60)
print("【3】数值交叉验证（模拟数据）")
print("=" * 60)

def f(x1, x2):
    return c1 * x1 + c2 * x2

def feasible(x1, x2, tol=1e-9):
    return (a11 * x1 + a12 * x2 <= b1 + tol) and \
           (a21 * x1 + a22 * x2 <= b2 + tol) and x1 >= -tol and x2 >= -tol

# 3.1 验证符号解可行且目标值一致
print("符号解 x*=(%.6f, %.6f), f*=%.6f" % (x_star[0], x_star[1], f_star))
print("符号解可行性: %s" % feasible(x_star[0], x_star[1]))

# 3.2 网格搜索数值最优解，与符号解比对
N = 2001
xs = np.linspace(0, b1 / a11, N)
ys = np.linspace(0, b2 / a22, N)
best_val, best_pt = -np.inf, None
for x1 in xs:
    for x2 in ys:
        if feasible(x1, x2):
            v = f(x1, x2)
            if v > best_val:
                best_val, best_pt = v, (x1, x2)
print("网格搜索最优: x=(%.6f, %.6f), f=%.6f" % (best_pt[0], best_pt[1], best_val))
print("符号解 vs 数值解 目标值差: %.6e" % abs(f_star - best_val))
print("符号解 vs 数值解 坐标差: %.6e, %.6e" % (abs(x_star[0]-best_pt[0]), abs(x_star[1]-best_pt[1])))

# 3.3 在若干随机可行点验证 KKT 一阶条件（梯度方向）
# 对 LP，最优解处目标梯度 c 应落在紧约束法锥内
grad = np.array([c1, c2])
# 紧约束法向量（指向可行域内部为负方向）
n1 = np.array([a11, a12])
n2 = np.array([a21, a22])
# 检查 grad = λ1*n1 + λ2*n2
recon = lam[0] * n1 + lam[1] * n2
print("梯度重构 c vs λ1*n1+λ2*n2: %s vs %s" % (grad, recon))
print("梯度重构误差: %.6e" % np.linalg.norm(grad - recon))

# ============================================================
# 4. 边界与奇点行为检查
# ============================================================
print("\n" + "=" * 60)
print("【4】边界与奇点行为检查")
print("=" * 60)

# 4.1 原点
print("原点 f(0,0)=%.6f (非最优，因 c>0)" % f(0, 0))
# 4.2 单约束边界点
x1_only = b1 / a11  # 仅机器约束紧
print("仅机器约束紧: x=(%.6f, 0), f=%.6f, 原料约束满足? %s"
      % (x1_only, f(x1_only, 0), a21 * x1_only <= b2))
x2_only = b2 / a22  # 仅原料约束紧
print("仅原料约束紧: x=(0, %.6f), f=%.6f, 机器约束满足? %s"
      % (x2_only, f(0, x2_only), a12 * x2_only <= b1))
# 4.3 检查是否退化（两约束平行 => 奇点）
det_B = a11 * a22 - a12 * a21
print("约束矩阵行列式 det=%.6f (非零 => 无平行退化奇点)" % det_B)
# 4.4 检查目标梯度是否与某约束法向平行（会导致多重最优）
cross1 = c1 * a12 - c2 * a11
cross2 = c1 * a22 - c2 * a21
print("梯度与约束1法向叉积=%.6f, 与约束2法向叉积=%.6f (非零 => 唯一最优)" % (cross1, cross2))

# ============================================================
# 5. 输出可直接用于代码的表达式
# ============================================================
print("\n" + "=" * 60)
print("【5】可直接用于代码的表达式")
print("=" * 60)
print("最优解: x1* = %.6f, x2* = %.6f" % (x_star[0], x_star[1]))
print("最优值: f* = %.6f" % f_star)
print("KKT 乘子: λ1* = %.6f, λ2* = %.6f" % (lam[0], lam[1]))
print("Python 表达式: x_star = np.array([%.6f, %.6f])" % (x_star[0], x_star[1]))

# ============================================================
# 6. 出图
# ============================================================
fig, ax = plt.subplots(figsize=(7, 6))
x1_line = np.linspace(0, b1 / a11, 200)
# 机器约束: a11*x1 + a12*x2 = b1 => x2 = (b1 - a11*x1)/a12
x2_machine = (b1 - a11 * x1_line) / a12
# 原料约束: a21*x1 + a22*x2 = b2 => x2 = (b2 - a21*x1)/a22
x2_material = (b2 - a21 * x1_line) / a22

ax.plot(x1_line, x2_machine, 'b-', label='机器工时约束')
ax.plot(x1_line, x2_material, 'g-', label='原料约束')
ax.fill_between(x1_line, 0, np.minimum(np.maximum(x2_machine, 0), np.maximum(x2_material, 0)),
                where=(np.minimum(np.maximum(x2_machine, 0), np.maximum(x2_material, 0)) >= 0),
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