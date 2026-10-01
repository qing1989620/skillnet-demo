import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv

np.random.seed(42)

# ============================================================
# 数据说明：以下为【模拟数据】，仅用于演示流程，非真实实验结论
# 结构：9 个剂量点，每组 3 次重复
# ============================================================
doses = np.array([0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0])
n_rep = 3
n_dose = len(doses)

# 模拟真实剂量-响应（4参数逻辑斯蒂），并注入噪声
top, bottom, ic50_true, hill = 100.0, 5.0, 25.0, 1.1
true_mean = bottom + (top - bottom) / (1.0 + (doses / ic50_true) ** hill)

# 注入少量异常：某剂量点重复间离散大、某点缺失
noise_scale = np.array([1.5, 1.5, 2.0, 2.0, 3.0, 12.0, 3.0, 2.0, 1.5])  # 30 剂量点离散大
survival = np.zeros((n_dose, n_rep))
for i in range(n_dose):
    survival[i, :] = true_mean[i] + np.random.normal(0, noise_scale[i], n_rep)
survival = np.clip(survival, 0, 120)

# 人为制造 1 个缺失值（模拟数据缺失）
survival[4, 2] = np.nan

# 展平为长表
records = []
for i in range(n_dose):
    for j in range(n_rep):
        records.append((doses[i], j + 1, survival[i, j]))

# ============================================================
# 1. 数据完整性检查
# ============================================================
print("=" * 60)
print("【数据说明】本数据为模拟数据，非真实实验结论")
print("=" * 60)

total_cells = n_dose * n_rep
missing_cells = int(np.isnan(survival).sum())
print("\n[1] 数据完整性")
print(f"  设计矩阵: {n_dose} 剂量点 x {n_rep} 重复 = {total_cells} 个观测")
print(f"  缺失值数量: {missing_cells}  缺失率: {missing_cells/total_cells*100:.2f}%")

# 每个剂量点的有效重复数
valid_per_dose = np.sum(~np.isnan(survival), axis=1)
print(f"  各剂量点有效重复数: {valid_per_dose.tolist()}")
uneven = np.where(valid_per_dose != n_rep)[0]
if len(uneven) > 0:
    for idx in uneven:
        print(f"  [风险] 剂量 {doses[idx]} 有效重复数={valid_per_dose[idx]} (<{n_rep})，组间样本量不一致")

# ============================================================
# 2. 单变量分布与离散度（规避"只看均值不看分布形态"）
# ============================================================
print("\n[2] 各剂量点分布形态（均值 / 标准差 / 变异系数CV / 极差）")
print(f"  {'剂量':>8} {'均值':>8} {'标准差':>8} {'CV%':>8} {'极差':>8} {'n':>3}")
mean_per_dose = np.nanmean(survival, axis=1)
std_per_dose = np.nanstd(survival, axis=1, ddof=1)
cv_per_dose = std_per_dose / np.abs(mean_per_dose) * 100
ptp_per_dose = np.nanmax(survival, axis=1) - np.nanmin(survival, axis=1)

for i in range(n_dose):
    print(f"  {doses[i]:>8.1f} {mean_per_dose[i]:>8.2f} {std_per_dose[i]:>8.2f} "
          f"{cv_per_dose[i]:>8.1f} {ptp_per_dose[i]:>8.2f} {valid_per_dose[i]:>3}")

# 高离散风险
high_cv = np.where(cv_per_dose > 15)[0]
if len(high_cv) > 0:
    for idx in high_cv:
        print(f"  [风险] 剂量 {doses[idx]} 的 CV={cv_per_dose[idx]:.1f}% (>15%)，重复间离散偏大")

# ============================================================
# 3. 单调性与平台期检查（规避"用相关系数解释非线性关系"）
# ============================================================
print("\n[3] 单调性与平台期检查")
diffs = np.diff(mean_per_dose)
print(f"  相邻剂量均值差: {np.round(diffs, 2).tolist()}")
non_mono = np.where(diffs > 0)[0]
if len(non_mono) == 0:
    print("  单调性: 均值随剂量单调不增，符合剂量-响应预期")
else:
    for idx in non_mono:
        print(f"  [风险] 剂量 {doses[idx]} -> {doses[idx+1]} 均值上升 {diffs[idx]:.2f}，非单调")

# 平台期：高剂量段变化幅度
high_plateau = np.abs(diffs[-3:])
print(f"  高剂量段(后3个区间)变化幅度: {np.round(high_plateau, 2).tolist()}")
if np.all(high_plateau < 3.0):
    print("  平台期: 高剂量段已趋于平台（变化<3%）")
else:
    print("  [提示] 高剂量段仍有明显变化，平台期可能未达到")

# 相关系数仅作参考，明确其局限
r = np.corrcoef(np.log10(doses), mean_per_dose)[0, 1]
print(f"  log10(剂量) 与 均值 的 Pearson r = {r:.3f}")
print("  [规避] 相关系数仅反映线性关联，剂量-响应为非线性，不能据此判断关系强弱")

# ============================================================
# 4. 组间基线可比性（0 剂量附近基线）
# ============================================================
print("\n[4] 组间基线可比性")
baseline = survival[0, :]
print(f"  最低剂量 {doses[0]} 的存活率: {np.round(baseline, 2).tolist()}")
print(f"  基线均值={np.nanmean(baseline):.2f}, 标准差={np.nanstd(baseline, ddof=1):.2f}")
if np.nanmean(baseline) > 95:
    print("  基线接近 100%，组间基线可比性良好")
else:
    print("  [风险] 基线偏离 100%，可能存在系统偏差")

# ============================================================
# 5. 共线性 / 特征关系（剂量为唯一自变量，检查 log 变换）
# ============================================================
print("\n[5] 特征关系与共线性")
log_dose = np.log10(doses)
print(f"  剂量与 log10(剂量) 的 Pearson r = {np.corrcoef(doses, log_dose)[0,1]:.3f}")
print("  [说明] 剂量与 log10(剂量) 高度共线，建模时二者只取其一（推荐 log 剂量）")
print("  候选特征: [log10_dose]；目标变量: survival_rate")

# ============================================================
# 6. 风险清单汇总
# ============================================================
print("\n[6] 风险清单与处理建议")
risks = []
if missing_cells > 0:
    risks.append(f"缺失值 {missing_cells} 个 -> 建议：对缺失点补做实验或用重复均值插补并标注")
if len(uneven) > 0:
    risks.append("组间样本量不一致 -> 建议：补齐缺失重复，分析时使用加权或混合效应模型")
if len(high_cv) > 0:
    risks.append(f"高离散剂量点 {[float(doses[i]) for i in high_cv]} -> 建议：检查操作误差，增加重复数")
if len(non_mono) > 0:
    risks.append("存在非单调点 -> 建议：核查异常值，考虑稳健拟合")
if not np.all(high_plateau < 3.0):
    risks.append("高剂量平台期未达 -> 建议：延长剂量范围以确定上下渐近线")
if len(risks) == 0:
    print("  未发现显著风险")
else:
    for k, rk in enumerate(risks, 1):
        print(f"  {k}. {rk}")

# ============================================================
# 7. 保存数据表为 CSV
# ============================================================
with open("dose_survival_data.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["dose", "replicate", "survival_rate", "note"])
    for d, rep, s in records:
        note = "模拟数据"
        if np.isnan(s):
            note = "模拟数据-缺失"
        w.writerow([d, rep, "" if np.isnan(s) else round(s, 4), note])
print("\n[输出] 数据表已保存: dose_survival_data.csv")

# ============================================================
# 8. 出图（1 张图，多子图）
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))

# 子图1：剂量-响应散点 + 均值折线（含误差棒）
ax = axes[0]
for i in range(n_dose):
    ax.scatter([doses[i]] * n_rep, survival[i, :], color='steelblue', alpha=0.6, s=40)
ax.errorbar(doses, mean_per_dose, yerr=std_per_dose, fmt='o-', color='crimson',
            capsize=4, label='均值±标准差')
ax.set_xscale('log')
ax.set_xlabel('剂量 (log scale)')
ax.set_ylabel('细胞存活率 (%)')
ax.set_title('剂量-存活率关系（模拟数据）')
ax.legend()
ax.grid(alpha=0.3)

# 子图2：各剂量点分布（箱线图，规避只看均值）
ax = axes[1]
box_data = [survival[i, ~np.isnan(survival[i, :])] for i in range(n_dose)]
bp = ax.boxplot(box_data, labels=[f"{d:g}" for d in doses], patch_artist=True)
for patch in bp['boxes']:
    patch.set_facecolor('lightblue')
ax.set_xlabel('剂量')
ax.set_ylabel('细胞存活率 (%)')
ax.set_title('各剂量点分布形态（模拟数据）')
ax.grid(alpha=0.3, axis='y')

# 子图3：CV 柱状图（离散度风险）
ax = axes[2]
colors = ['crimson' if c > 15 else 'seagreen' for c in cv_per_dose]
ax.bar([f"{d:g}" for d in doses], cv_per_dose, color=colors)
ax.axhline(15, color='orange', linestyle='--', label='CV=15% 警戒线')
ax.set_xlabel('剂量')
ax.set_ylabel('变异系数 CV (%)')
ax.set_title('各剂量点离散度（模拟数据）')
ax.legend()
ax.grid(alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig("figure.png", dpi=150)
print("[输出] 图已保存: figure.png")
print("\n" + "=" * 60)
print("注意：以上所有数值均基于模拟数据，不代表真实实验结论")
print("=" * 60)