import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 1. 读取真实输入文件 ----------
DATA_FILE = 'clean_data.csv'
AUDIT_FILE = 'audit_log.txt'

if not os.path.exists(DATA_FILE):
    raise FileNotFoundError(f"缺少输入文件 {DATA_FILE}，请先运行前序步骤。")

# 读取 CSV（纯 numpy，不依赖 pandas）
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    header = f.readline().strip().split(',')
raw = np.genfromtxt(DATA_FILE, delimiter=',', skip_header=1, dtype=float)

if raw.ndim == 1:
    raw = raw.reshape(1, -1)

print("=== 输入文件 ===")
print(f"clean_data.csv 列名: {header}")
print(f"样本数: {raw.shape[0]}, 字段数: {raw.shape[1]}")

# 自动识别剂量列与存活率列
dose_idx = None
surv_idx = None
for i, name in enumerate(header):
    ln = name.lower()
    if dose_idx is None and ('dose' in ln or '剂量' in name):
        dose_idx = i
    if surv_idx is None and ('surv' in ln or '存活' in name or 'viab' in ln or '抑制' in name):
        surv_idx = i
if dose_idx is None:
    dose_idx = 0
if surv_idx is None:
    surv_idx = raw.shape[1] - 1

dose = raw[:, dose_idx]
surv = raw[:, surv_idx]
print(f"剂量列: {header[dose_idx]} | 存活率列: {header[surv_idx]}")

# ---------- 2. 单变量分布与缺失率 ----------
print("\n=== 单变量分布与缺失率 ===")
for i, name in enumerate(header):
    col = raw[:, i]
    miss = np.isnan(col).sum()
    miss_rate = miss / len(col) * 100
    valid = col[~np.isnan(col)]
    if len(valid) > 0:
        print(f"{name:>12s}: 缺失率={miss_rate:5.1f}%  min={valid.min():.4g} "
              f"median={np.median(valid):.4g} mean={valid.mean():.4g} "
              f"max={valid.max():.4g} sd={valid.std(ddof=1) if len(valid)>1 else 0:.4g}")

# 剔除缺失
mask = ~(np.isnan(dose) | np.isnan(surv))
dose, surv = dose[mask], surv[mask]
print(f"有效样本(剔除缺失后): {len(dose)}")

# ---------- 3. 按剂量分组统计 ----------
print("\n=== 按剂量分组统计 (mean / SD / n) ===")
uniq_doses = np.unique(dose)
groups = {}
for d in uniq_doses:
    vals = surv[dose == d]
    groups[d] = vals
    sd = vals.std(ddof=1) if len(vals) > 1 else 0.0
    print(f"剂量={d:>10.4g} | n={len(vals):>3d} | mean={vals.mean():.4f} | SD={sd:.4f}")

# ---------- 4. 平台期覆盖判断 ----------
# 抑制率 = 1 - 存活率（若存活率已是百分比则归一化）
s = surv.copy()
if s.max() > 1.5:
    s = s / 100.0
inhib = 1.0 - s

min_dose = uniq_doses.min()
max_dose = uniq_doses.max()
low_inhib = 1.0 - groups[min_dose].mean() if groups[min_dose].mean() <= 1.5 else 1.0 - groups[min_dose].mean()/100.0
high_inhib = 1.0 - groups[max_dose].mean() if groups[max_dose].mean() <= 1.5 else 1.0 - groups[max_dose].mean()/100.0

print("\n=== 平台期覆盖判断 ===")
print(f"最低剂量 {min_dose:.4g} 平均抑制率 = {low_inhib*100:.2f}%  (要求 ≤5%)  -> {'满足' if low_inhib<=0.05 else '不满足'}")
print(f"最高剂量 {max_dose:.4g} 平均抑制率 = {high_inhib*100:.2f}%  (要求 ≥95%) -> {'满足' if high_inhib>=0.95 else '不满足'}")
plateau_ok = (low_inhib <= 0.05) and (high_inhib >= 0.95)
print(f"平台期覆盖: {'完整' if plateau_ok else '不完整'}")

# ---------- 5. 低置信剂量点 & 组间样本量差异 ----------
print("\n=== 低置信剂量点 (n<3) ===")
low_conf = [d for d in uniq_doses if len(groups[d]) < 3]
if low_conf:
    for d in low_conf:
        print(f"  剂量={d:.4g}  n={len(groups[d])}  -> 低置信，建议补点或降权")
else:
    print("  无 n<3 的剂量点")

ns = np.array([len(groups[d]) for d in uniq_doses])
print(f"\n组间样本量: min={ns.min()} max={ns.max()} 极差={ns.max()-ns.min()} "
      f"CV={ns.std(ddof=1)/ns.mean()*100:.1f}%")
if ns.max() - ns.min() >= 3:
    print("  -> 组间样本量差异较大，均值比较需谨慎（避免只看均值）")
else:
    print("  -> 组间样本量相对均衡")

# ---------- 6. 相关矩阵 & 共线性标注 ----------
print("\n=== 相关矩阵 (|r|>0.8 标注共线性) ===")
# 数值列（剔除全 NaN 列）
num_cols = []
num_data = []
for i, name in enumerate(header):
    col = raw[:, i]
    if np.isnan(col).all():
        continue
    num_cols.append(name)
    num_data.append(col)
num_data = np.array(num_data)

n_feat = len(num_cols)
corr = np.full((n_feat, n_feat), np.nan)
for i in range(n_feat):
    for j in range(n_feat):
        a, b = num_data[i], num_data[j]
        m = ~(np.isnan(a) | np.isnan(b))
        if m.sum() > 2:
            corr[i, j] = np.corrcoef(a[m], b[m])[0, 1]

collinear_pairs = []
for i in range(n_feat):
    for j in range(i+1, n_feat):
        r = corr[i, j]
        if not np.isnan(r) and abs(r) > 0.8:
            collinear_pairs.append((num_cols[i], num_cols[j], r))
            print(f"  共线性: {num_cols[i]} <-> {num_cols[j]}  r={r:.3f}")

if not collinear_pairs:
    print("  未发现 |r|>0.8 的共线性特征对")

# 陷阱规避：相关系数不能解释非线性关系
print("\n[陷阱规避] 相关系数仅度量线性关系；剂量-响应常为非线性(S型)，")
print("           上述 r 仅作共线性筛查，不作为剂量-效应因果解释。")

# ---------- 7. 绘图 ----------
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

# 左：剂量-响应散点 + 分组均值±SD
ax = axes[0]
ax.scatter(dose, s, alpha=0.5, s=25, color='steelblue', label='个体观测')
means = np.array([groups[d].mean() for d in uniq_doses])
sds = np.array([groups[d].std(ddof=1) if len(groups[d]) > 1 else 0 for d in uniq_doses])
if s.max() > 1.5:
    means_plot = means / 100.0
    sds_plot = sds / 100.0
else:
    means_plot = means
    sds_plot = sds
ax.errorbar(uniq_doses, means_plot, yerr=sds_plot, fmt='o-', color='crimson',
            capsize=4, label='分组均值±SD')
# 标注低置信点
for d in low_conf:
    ax.axvline(d, color='orange', ls='--', alpha=0.6)
    ax.text(d, ax.get_ylim()[1]*0.95, f'n={len(groups[d])}', color='orange',
            fontsize=8, ha='center')
ax.set_xlabel('剂量')
ax.set_ylabel('存活率')
ax.set_title('剂量-响应散点与分组均值')
ax.legend()
ax.grid(alpha=0.3)

# 右：分组分布（箱线图）
ax2 = axes[1]
box_data = [groups[d] if groups[d].max() <= 1.5 else groups[d]/100.0 for d in uniq_doses]
bp = ax2.boxplot(box_data, labels=[f'{d:.3g}' for d in uniq_doses], patch_artist=True)
for patch in bp['boxes']:
    patch.set_facecolor('lightsteelblue')
ax2.set_xlabel('剂量')
ax2.set_ylabel('存活率')
ax2.set_title('各剂量组分布 (箱线图)')
ax2.grid(alpha=0.3)
plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')

plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print("\n已保存图: figure.png")

# ---------- 8. 候选特征清单与风险项 ----------
print("\n=== 候选特征清单 ===")
print(f"  剂量特征: {header[dose_idx]}")
print(f"  响应特征: {header[surv_idx]}")
print(f"  其他数值特征: {[c for c in num_cols if c not in (header[dose_idx], header[surv_idx])]}")

print("\n=== 风险项与处理建议 ===")
risks = []
if low_conf:
    risks.append(f"低置信剂量点 {[f'{d:.3g}' for d in low_conf]} (n<3): 建议补点或加权")
if ns.max() - ns.min() >= 3:
    risks.append(f"组间样本量极差={ns.max()-ns.min()}: 建议分层分析或加权")
if collinear_pairs:
    risks.append(f"共线性特征对 {len(collinear_pairs)} 组: 建议剔除或降维")
if not plateau_ok:
    risks.append("平台期覆盖不完整: 建议扩展剂量范围")
if not risks:
    risks.append("未发现显著风险项")
for r in risks:
    print(f"  - {r}")

# ---------- 9. 落盘 ----------
# 分组统计表
with open('group_stats.csv', 'w', encoding='utf-8') as f:
    f.write('dose,n,mean,sd\n')
    for d in uniq_doses:
        vals = groups[d]
        sd = vals.std(ddof=1) if len(vals) > 1 else 0.0
        f.write(f'{d},{len(vals)},{vals.mean()},{sd}\n')
print("\n已保存: group_stats.csv")

# 相关矩阵
with open('corr_matrix.csv', 'w', encoding='utf-8') as f:
    f.write(',' + ','.join(num_cols) + '\n')
    for i, name in enumerate(num_cols):
        row = [name] + [f'{corr[i,j]:.4f}' if not np.isnan(corr[i,j]) else 'nan'
                        for j in range(n_feat)]
        f.write(','.join(row) + '\n')
print("已保存: corr_matrix.csv")