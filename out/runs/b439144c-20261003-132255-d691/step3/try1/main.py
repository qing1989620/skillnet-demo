# -*- coding: utf-8 -*-
"""
费马大定理 - 怀尔斯证明核心思想的可视化与量化说明
本步骤：解释怀尔斯证明的核心思想（Frey 曲线 + 模性 + Ribet 水平降低）

说明：
- 本脚本读取前序步骤产物（若存在），并生成一张示意图 figure.png。
- 由于费马大定理的证明本身是纯数学论证，无法用真实实验数据量化，
  因此图中涉及的"数值"均为示意性/模拟数据，已在注释与输出中明确标注。
"""

import os
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# ----------------------------------------------------------------------
# 1. 读取前序步骤产物（真实文件，若缺失则给出提示，不伪造）
# ----------------------------------------------------------------------
INPUT_FILES = [
    "fermat_enum.csv",
    "fermat_gap_topics.csv",
    "fermat_history_stages.csv",
]

def load_csv_safe(path):
    """安全读取 CSV，返回 (header, rows) 或 (None, None)。"""
    if not os.path.exists(path):
        print(f"[检查] 输入文件缺失: {path}")
        return None, None
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        print(f"[检查] 输入文件为空: {path}")
        return None, None
    header, data = rows[0], rows[1:]
    print(f"[检查] 读取 {path}: 表头={header}, 数据行数={len(data)}")
    return header, data


print("=" * 70)
print("步骤：怀尔斯证明核心思想 —— Frey 曲线 / 模性 / Ribet 水平降低")
print("=" * 70)

loaded = {}
for fp in INPUT_FILES:
    h, d = load_csv_safe(fp)
    loaded[fp] = (h, d)

# 已知陷阱检查：费马大定理要求 n >= 3，且 a,b,c 非零
print("\n[陷阱检查] 费马大定理前提：n >= 3 且 a,b,c 均为非零整数")
print("[陷阱检查] 若 n=1,2 则存在解（如 3+4=7, 3^2+4^2=5^2），不构成反例")
print("[陷阱检查] 怀尔斯证明针对的是半稳定椭圆曲线，非半稳定情形由后续工作补全")


# ----------------------------------------------------------------------
# 2. 核心思想的结构化描述（纯数学逻辑链，非实验数据）
# ----------------------------------------------------------------------
# 逻辑链（每一步都是数学定理，非模拟数据）：
#   (1) 假设费马大定理不成立：存在非零整数 a,b,c 与 n>=3 使 a^n + b^n = c^n
#   (2) Frey 构造半稳定椭圆曲线 E: y^2 = x(x - a^n)(x + b^n)
#       该曲线判别式 Δ = 16 (a^n b^n c^n)^2，导子 N = rad(abc)（半稳定）
#   (3) Serre 猜想 + Ribet 水平降低定理：若 E 模性成立，
#       则存在权 2、水平 2 的模形式，但 S_2(Γ_0(2)) = {0}，矛盾
#   (4) 怀尔斯证明半稳定椭圆曲线的模性（Taniyama-Shimura 的特例）
#   (5) 因此假设不成立，费马大定理成立

proof_chain = [
    ("假设反例存在", "存在非零整数 a,b,c, n>=3 使 a^n+b^n=c^n"),
    ("Frey 曲线构造", "E: y^2 = x(x-a^n)(x+b^n)，半稳定"),
    ("导子计算", "N(E) = rad(abc)，判别式 Δ = 16(abc)^{2n}"),
    ("模性定理", "E 是模的（怀尔斯，半稳定情形）"),
    ("Ribet 水平降低", "存在权2水平2的模形式"),
    ("矛盾", "S_2(Γ_0(2)) = {0}，不存在此类模形式"),
    ("结论", "费马大定理成立"),
]

print("\n[核心思想] 证明逻辑链（数学论证，非模拟数据）：")
for i, (step, desc) in enumerate(proof_chain, 1):
    print(f"  {i}. {step}: {desc}")


# ----------------------------------------------------------------------
# 3. 量化示意：Frey 曲线导子随 (a,b,c) 的变化（模拟数据）
# ----------------------------------------------------------------------
# 注意：以下为【模拟数据】，用于示意导子 N = rad(abc) 的增长趋势，
#       并非真实费马反例（费马反例不存在）。
np.random.seed(42)
n_samples = 200
# 模拟互素三元组 (a,b,c)，仅用于展示 rad(abc) 的量级
a_sim = np.random.randint(1, 50, n_samples)
b_sim = np.random.randint(1, 50, n_samples)
c_sim = a_sim + b_sim  # 模拟 c = a + b（非真实费马关系）

def rad(x):
    """radical: 不同素因子的乘积"""
    r = 1
    d = 2
    while d * d <= x:
        if x % d == 0:
            r *= d
            while x % d == 0:
                x //= d
        d += 1
    if x > 1:
        r *= x
    return r

N_sim = np.array([rad(int(a) * int(b) * int(c)) for a, b, c in zip(a_sim, b_sim, c_sim)])
print(f"\n[模拟数据] 导子 N=rad(abc) 示意：样本数={n_samples}, "
      f"均值={N_sim.mean():.1f}, 最大={N_sim.max()}, 最小={N_sim.min()}")
print("[模拟数据] 说明：真实费马反例不存在，此处仅示意导子量级增长")


# ----------------------------------------------------------------------
# 4. 生成示意图 figure.png
# ----------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

# 左图：证明逻辑链流程图
ax = axes[0]
ax.axis('off')
ax.set_title("怀尔斯证明逻辑链（数学论证）", fontsize=13, fontweight='bold')
y_pos = np.linspace(0.92, 0.08, len(proof_chain))
colors = plt.cm.Blues(np.linspace(0.35, 0.85, len(proof_chain)))
for i, ((step, desc), y) in enumerate(zip(proof_chain, y_pos)):
    ax.text(0.5, y, f"{i+1}. {step}", ha='center', va='center',
            fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.4', facecolor=colors[i],
                      edgecolor='navy', alpha=0.85))
    if i < len(proof_chain) - 1:
        ax.annotate('', xy=(0.5, y_pos[i+1] + 0.03), xytext=(0.5, y - 0.03),
                    arrowprops=dict(arrowstyle='->', color='gray', lw=1.5))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)

# 右图：导子 N=rad(abc) 分布（模拟数据）
ax2 = axes[1]
ax2.hist(N_sim, bins=25, color='steelblue', edgecolor='black', alpha=0.75)
ax2.set_xlabel("导子 N = rad(abc)（模拟数据）", fontsize=11)
ax2.set_ylabel("频数", fontsize=11)
ax2.set_title("Frey 曲线导子量级示意（模拟数据）", fontsize=13, fontweight='bold')
ax2.grid(alpha=0.3)
ax2.axvline(N_sim.mean(), color='red', linestyle='--', lw=2,
            label=f"均值={N_sim.mean():.0f}")
ax2.legend(fontsize=10)

plt.tight_layout()
plt.savefig("figure.png", dpi=150, bbox_inches='tight')
plt.close()
print("\n[输出] 已保存示意图: figure.png")


# ----------------------------------------------------------------------
# 5. 落盘：证明逻辑链 CSV
# ----------------------------------------------------------------------
with open("wiles_proof_chain.csv", "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["序号", "步骤", "说明"])
    for i, (step, desc) in enumerate(proof_chain, 1):
        writer.writerow([i, step, desc])
print("[输出] 已保存: wiles_proof_chain.csv")

# 落盘：模拟导子数据（明确标注模拟）
with open("frey_conductor_sim.csv", "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["a_sim", "b_sim", "c_sim", "N_rad_abc", "note"])
    for a, b, c, N in zip(a_sim, b_sim, c_sim, N_sim):
        writer.writerow([int(a), int(b), int(c), int(N), "模拟数据"])
print("[输出] 已保存: frey_conductor_sim.csv（模拟数据）")

print("\n" + "=" * 70)
print("结论：怀尔斯通过证明半稳定椭圆曲线的模性，结合 Ribet 水平降低定理，")
print("      导出与 S_2(Γ_0(2))={0} 的矛盾，从而证明费马大定理。")
print("=" * 70)