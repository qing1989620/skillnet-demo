import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

import sys
import io

# 修复 Windows GBK 控制台无法输出 Unicode 符号（如 ⚠ ✓）的问题
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

# ============================================================
# 数据说明：以下为【模拟数据】，仅用于演示流程，非真实实验结论
# 设计：9 个剂量点，每组 3 次重复
# ============================================================
rng = np.random.default_rng(42)

doses = np.array([0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0])  # 9 个剂量点
n_rep = 3

# 用 4 参数 logistic 生成"真实"存活率，再叠加噪声
true_ic50 = 12.0
hill = 1.2
top, bottom = 100.0, 5.0
true_curve = bottom + (top - bottom) / (1.0 + (doses / true_ic50) ** hill)

noise_sd = 3.0
survival = np.zeros((len(doses), n_rep))
for i in range(len(doses)):
    survival[i, :] = true_curve[i] + rng.normal(0, noise_sd, n_rep)
survival = np.clip(survival, 0, 120)

# 人为注入一个质量问题：第 6 个剂量点（30.0）第 2 个重复缺失
survival[5, 1] = np.nan

print("=" * 60)
print("【模拟数据】剂量-存活率质量检查报告")
print("=" * 60)

# ---------- 1. 数据完整性 ----------
total_cells = survival.size
missing = int(np.isnan(survival).sum())
print(f"\n[1] 数据完整性")
print(f"  设计矩阵: {survival.shape[0]} 剂量点 x {survival.shape[1]} 重复 = {total_cells} 个观测")
print(f"  缺失值数量: {missing}  ({missing/total_cells*100:.1f}%)")
if missing > 0:
    miss_idx = np.argwhere(np.isnan(survival))
    for r, c in miss_idx:
        print(f"    缺失位置: 剂量={doses[r]} (第{r+1}行), 重复={c+1}")

# ---------- 2. 重复数与离散度 ----------
print(f"\n[2] 重复数与组内离散度")
print(f"  {'剂量':>8} {'有效n':>6} {'均值':>8} {'SD':>8} {'CV%':>8}")
means = np.full(len(doses), np.nan)
sds = np.full(len(doses), np.nan)
cvs = np.full(len(doses), np.nan)
for i in range(len(doses)):
    vals = survival[i, ~np.isnan(survival[i])]
    n = len(vals)
    m = vals.mean() if n > 0 else np.nan
    s = vals.std(ddof=1) if n > 1 else np.nan
    cv = (s / m * 100) if (n > 1 and m != 0) else np.nan
    means[i], sds[i], cvs[i] = m, s, cv
    print(f"  {doses[i]:>8.1f} {n:>6d} {m:>8.2f} {s:>8.2f} {cv:>8.1f}")

valid_cv = cvs[~np.isnan(cvs)]
print(f"  平均 CV% = {valid_cv.mean():.2f}%  (阈值 20%，超过则提示组内变异偏大)")
high_cv = np.where(cvs > 20)[0]
if len(high_cv) > 0:
    print(f"  [!] 高变异剂量点: {[float(doses[i]) for i in high_cv]}")
else:
    print(f"  [OK] 所有剂量点 CV% 均 <= 20%")

# ---------- 3. 单调性检查 ----------
print(f"\n[3] 单调性检查（存活率应随剂量单调不增）")
violations = []
for i in range(1, len(doses)):
    if not np.isnan(means[i]) and not np.isnan(means[i-1]):
        if means[i] > means[i-1]:
            violations.append((float(doses[i-1]), float(means[i-1]),
                               float(doses[i]), float(means[i])))
if len(violations) == 0:
    print("  [OK] 均值序列单调不增，无违反")
else:
    print(f"  [!] 发现 {len(violations)} 处单调性违反:")
    for d0, m0, d1, m1 in violations:
        print(f"    剂量 {d0}->{d1}: 均值 {m0:.2f} -> {m1:.2f} (上升 {m1-m0:.2f})")

# ---------- 4. 平台期检查 ----------
print(f"\n[4] 平台期检查（高剂量端是否趋于平台）")
# 取最高 3 个剂量点的均值，看变化幅度
tail_means = means[-3:]
tail_doses = doses[-3:]
print(f"  高剂量端均值: " + ", ".join([f"{d:.0f}->{m:.2f}" for d, m in zip(tail_doses, tail_means)]))
tail_range = np.nanmax(tail_means) - np.nanmin(tail_means)
print(f"  高剂量端均值极差 = {tail_range:.2f} (阈值 5.0)")
if tail_range <= 5.0:
    print("  [OK] 高剂量端已进入平台期")
else:
    print("  [!] 高剂量端尚未明显进入平台期，IC50 外推风险较高")

# 低剂量端平台（接近 100%）
head_means = means[:2]
head_range = np.nanmax(head_means) - np.nanmin(head_means)
print(f"  低剂量端均值极差 = {head_range:.2f} (阈值 5.0)")
if head_range <= 5.0:
    print("  [OK] 低剂量端接近 100% 平台")
else:
    print("  [!] 低剂量端未达平台，可能低估 top 参数")

# ---------- 5. 风险清单 ----------
print(f"\n[5] 风险清单")
risks = []
if missing > 0:
    risks.append(f"存在 {missing} 个缺失值，需确认是否随机缺失")
if len(high_cv) > 0:
    risks.append(f"{len(high_cv)} 个剂量点 CV% > 20%，组内变异偏大")
if len(violations) > 0:
    risks.append(f"{len(violations)} 处单调性违反，可能存在异常点或真实非单调效应")
if tail_range > 5.0:
    risks.append("高剂量端未达平台，IC50 估计可能不稳定")
if head_range > 5.0:
    risks.append("低剂量端未达平台，top 参数估计可能偏低")
if len(risks) == 0:
    print("  [OK] 未发现显著数据质量风险")
else:
    for k, r in enumerate(risks, 1):
        print(f"  {k}. {r}")

# ---------- 6. 保存 CSV ----------
import csv
csv_path = "dose_survival_data.csv"
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["dose"] + [f"rep{i+1}" for i in range(n_rep)] + ["mean", "sd", "cv_pct"])
    for i in range(len(doses)):
        row = [doses[i]] + [survival[i, j] for j in range(n_rep)] + [means[i], sds[i], cvs[i]]
        w.writerow(row)
print(f"\n[6] 数据表已保存: {csv_path}")

# ---------- 7. 出图 ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

# 左图：剂量-存活率关系（含重复散点与均值曲线）
ax = axes[0]
for j in range(n_rep):
    ax.scatter(doses, survival[:, j], s=30, alpha=0.5,
               label=f"重复 {j+1}" if j == 0 else None, color="tab:blue")
ax.errorbar(doses, means, yerr=sds, fmt="o-", color="tab:red",
            capsize=4, lw=2, label="均值 ± SD")
ax.set_xscale("log")
ax.set_xlabel("剂量 (log scale)")
ax.set_ylabel("细胞存活率 (%)")
ax.set_title("剂量-存活率关系（模拟数据）")
ax.axhline(50, color="gray", ls="--", lw=1, label="50% 参考线")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

# 右图：CV% 分布
ax2 = axes[1]
ax2.bar(range(len(doses)), cvs, color="tab:green", alpha=0.7)
ax2.axhline(20, color="red", ls="--", lw=1.5, label="CV% 阈值 20%")
ax2.set_xticks(range(len(doses)))
ax2.set_xticklabels([f"{d:.0f}" for d in doses], rotation=45)
ax2.set_xlabel("剂量")
ax2.set_ylabel("组内 CV (%)")
ax2.set_title("各剂量点组内变异系数")
ax2.legend(fontsize=8)
ax2.grid(alpha=0.3, axis="y")

plt.tight_layout()
plt.savefig("figure.png", dpi=150)
print(f"[7] 图已保存: figure.png")
print("\n" + "=" * 60)
print("注意：以上所有数据均为【模拟数据】，结论仅用于流程演示。")
print("=" * 60)