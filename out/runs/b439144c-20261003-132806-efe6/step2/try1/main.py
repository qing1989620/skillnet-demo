import os
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 步骤 2：用边界反例验证前提不可省略
# 目标：选取满足方程但违反某一前提的实例，确认其不构成对定理的反驳
# ============================================================

# ---------- 1. 符号形式化命题 ----------
# 费马大定理 (FLT): 对任意整数 n>=3, 不存在非零整数 x,y,z 使 x^n + y^n = z^n
# 前提条件: n>=3, x,y,z 为非零整数
# 边界情形: n=1 有解 (如 1+1=2); n=2 有解 (勾股数 3,4,5)
# 注意区分: 费马小定理 (a^p ≡ a mod p), 费马素数猜想 (F_n=2^(2^n)+1 为素数)

print("=" * 70)
print("步骤2：边界反例验证前提不可省略")
print("=" * 70)

# ---------- 2. 读取前序产物 ----------
def load_csv_safe(path):
    """安全读取CSV，返回list of dict"""
    if not os.path.exists(path):
        print(f"[警告] 文件不存在: {path}，使用内置模拟数据")
        return None
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

boundary_cases = load_csv_safe('boundary_cases.csv')
misconceptions = load_csv_safe('misconceptions.csv')
proof_history = load_csv_safe('proof_history.csv')

if boundary_cases is None:
    # 模拟数据（明确标注）
    print("[模拟数据] boundary_cases.csv 不存在，使用内置模拟边界案例")
    boundary_cases = [
        {'n': '1', 'x': '1', 'y': '1', 'z': '2', 'equation_holds': 'True', 'violates_premise': 'n>=3', 'is_counterexample': 'False'},
        {'n': '2', 'x': '3', 'y': '4', 'z': '5', 'equation_holds': 'True', 'violates_premise': 'n>=3', 'is_counterexample': 'False'},
        {'n': '2', 'x': '5', 'y': '12', 'z': '13', 'equation_holds': 'True', 'violates_premise': 'n>=3', 'is_counterexample': 'False'},
        {'n': '2', 'x': '8', 'y': '15', 'z': '17', 'equation_holds': 'True', 'violates_premise': 'n>=3', 'is_counterexample': 'False'},
        {'n': '3', 'x': '0', 'y': '1', 'z': '1', 'equation_holds': 'True', 'violates_premise': 'x,y,z!=0', 'is_counterexample': 'False'},
    ]

# ---------- 3. 逐条核验边界反例 ----------
print("\n--- 边界反例逐条核验 ---")
print(f"{'n':>3} {'x':>5} {'y':>5} {'z':>5} {'方程成立':>8} {'违反前提':>12} {'构成反驳':>8}")
verified = []
for row in boundary_cases:
    n = int(row['n']); x = int(row['x']); y = int(row['y']); z = int(row['z'])
    lhs = x**n + y**n
    rhs = z**n
    eq_holds = (lhs == rhs)
    violates = row.get('violates_premise', '')
    # 关键判定：违反前提的实例不构成对定理的反驳
    is_counter = eq_holds and (n >= 3) and (x != 0 and y != 0 and z != 0)
    verified.append({'n': n, 'x': x, 'y': y, 'z': z, 'eq_holds': eq_holds,
                     'violates': violates, 'is_counterexample': is_counter})
    print(f"{n:>3} {x:>5} {y:>5} {z:>5} {str(eq_holds):>8} {violates:>12} {str(is_counter):>8}")

# 统计
n_total = len(verified)
n_eq_holds = sum(1 for v in verified if v['eq_holds'])
n_violates = sum(1 for v in verified if v['violates'])
n_counter = sum(1 for v in verified if v['is_counterexample'])
print(f"\n核验统计: 总案例={n_total}, 方程成立={n_eq_holds}, 违反前提={n_violates}, 构成反驳={n_counter}")
print(f"结论: 所有满足方程但违反前提的实例均不构成对费马大定理的反驳 (反驳数={n_counter})")

# ---------- 4. 误解对照表核验 ----------
print("\n--- 常见误解对照核验 ---")
if misconceptions is None:
    print("[模拟数据] misconceptions.csv 不存在，使用内置模拟误解表")
    misconceptions = [
        {'misconception': '费马大定理=费马小定理', 'distinction': 'FLT: x^n+y^n=z^n无正整数解(n>=3); 小定理: a^p≡a(mod p)'},
        {'misconception': 'FLT=费马素数猜想', 'distinction': 'FLT关于方程无解; 素数猜想关于F_n=2^(2^n)+1的素性'},
        {'misconception': '无解=无法验证', 'distinction': 'FLT是已证真命题, 与算法可解性/计算复杂度无关'},
        {'misconception': '怀尔斯演讲即完整证明', 'distinction': '1993宣布, 1994发现漏洞, 1995补全正式发表'},
    ]
for m in misconceptions:
    print(f"  误解: {m['misconception']}")
    print(f"    区分: {m['distinction']}")

# ---------- 5. 证明完整性状态核验 ----------
print("\n--- 证明完整性状态核验 ---")
if proof_history is None:
    print("[模拟数据] proof_history.csv 不存在，使用内置模拟证明史")
    proof_history = [
        {'stage': 'n=4', 'author': 'Fermat', 'year': '1637', 'coverage': 'n=4', 'status': '部分情形'},
        {'stage': 'n=3', 'author': 'Euler', 'year': '1770', 'coverage': 'n=3', 'status': '部分情形'},
        {'stage': '正则素数', 'author': 'Kummer', 'year': '1847', 'coverage': '正则素数', 'status': '部分情形'},
        {'stage': '全部n>=3', 'author': 'Wiles', 'year': '1995', 'coverage': '全部n>=3', 'status': '全称命题'},
    ]
for p in proof_history:
    print(f"  {p['stage']}: {p['author']} ({p['year']}) 覆盖={p['coverage']} 强度={p['status']}")

# 完整性三节点检查
print("\n  证明完整性三节点:")
print("    宣布年份: 1993 (Wiles 在剑桥演讲宣布证明)")
print("    漏洞发现: 1994 (审稿发现 Euler 系统构造缺陷)")
print("    补全年份: 1994 (Wiles 与 Taylor 合作修补)")
print("    正式发表: 1995 (Annals of Mathematics)")

# ---------- 6. 生成图 ----------
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# 左图: 边界案例分类
labels = ['方程成立\n且违反前提', '方程成立\n且满足前提', '方程不成立']
counts = [n_eq_holds - n_counter, n_counter, n_total - n_eq_holds]
colors = ['#ff9999', '#66b3ff', '#99ff99']
axes[0].bar(labels, counts, color=colors, edgecolor='black')
axes[0].set_title('边界反例分类核验', fontsize=13)
axes[0].set_ylabel('案例数')
for i, c in enumerate(counts):
    axes[0].text(i, c + 0.05, str(c), ha='center', fontsize=11)

# 右图: 证明史覆盖范围时间线
years = [1637, 1770, 1847, 1995]
names = ['Fermat\nn=4', 'Euler\nn=3', 'Kummer\n正则素数', 'Wiles\n全部n>=3']
axes[1].plot(years, [1, 2, 3, 4], 'o-', color='#3333cc', markersize=10, linewidth=2)
for y, n, name in zip(years, [1, 2, 3, 4], names):
    axes[1].annotate(name, (y, n), textcoords="offset points", xytext=(0, 12),
                     ha='center', fontsize=9)
axes[1].set_title('费马大定理证明史覆盖范围', fontsize=13)
axes[1].set_xlabel('年份')
axes[1].set_yticks([1, 2, 3, 4])
axes[1].set_yticklabels(['n=4', 'n=3', '正则素数', '全部n>=3'])
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('figure.png', dpi=150, bbox_inches='tight')
print("\n[已保存] figure.png")

# ---------- 7. 落盘 ----------
with open('boundary_verification.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['n', 'x', 'y', 'z', 'equation_holds', 'violates_premise', 'is_counterexample'])
    for v in verified:
        writer.writerow([v['n'], v['x'], v['y'], v['z'], v['eq_holds'], v['violates'], v['is_counterexample']])
print("[已保存] boundary_verification.csv")

print("\n" + "=" * 70)
print("步骤2完成：边界反例均不构成对费马大定理的反驳")
print("=" * 70)