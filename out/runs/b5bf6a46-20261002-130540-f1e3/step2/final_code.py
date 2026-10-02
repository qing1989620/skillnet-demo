import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 读取真实文件（若缺失则用模拟数据并明确标注） ----------
def load_csv(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8-sig') as f:
        header = f.readline().strip().split(',')
    data = np.genfromtxt(path, delimiter=',', names=True, dtype=None, encoding='utf-8')
    return data, header

clean = load_csv('clean_dose_response.csv')
if clean is None:
    print("[警告] 未找到 clean_dose_response.csv，使用模拟数据（模拟数据，非真实实验结论）")
    rng = np.random.default_rng(42)
    doses = np.array([0, 0.1, 0.3, 1, 3, 10, 30, 100])
    rows = []
    for d in doses:
        n = rng.integers(2, 6)
        top, bottom = 100.0, 2.0
        ic50 = 3.0
        surv = bottom + (top - bottom) / (1 + (d / ic50) ** 1.2)
        for _ in range(n):
            rows.append((d, float(np.clip(surv + rng.normal(0, 4), 0, 100))))
    arr = np.array(rows)
    dose = arr[:, 0]
    surv = arr[:, 1]
    SIMULATED = True
else:
    data, header = clean
    SIMULATED = False
    # 自动识别剂量列与存活率列
    cols = list(data.dtype.names)
    dose_col = None
    surv_col = None
    for c in cols:
        lc = c.lower()
        if dose_col is None and ('dose' in lc or 'conc' in lc):
            dose_col = c
        if surv_col is None and ('surv' in lc or 'viab' in lc or 'inhib' in lc or 'response' in lc):
            surv_col = c
    if dose_col is None:
        dose_col = cols[0]
    if surv_col is None:
        surv_col = cols[1]
    dose = np.asarray(data[dose_col], dtype=float)
    surv = np.asarray(data[surv_col], dtype=float)
    print(f"[信息] 读取真实数据: 剂量列='{dose_col}', 存活率列='{surv_col}', 记录数={len(dose)}")

# 若存活率为比例(0-1)，转为百分比
if np.nanmax(surv) <= 1.5:
    surv = surv * 100.0
    print("[信息] 存活率检测为比例，已转换为百分比")

# ---------- 1. 单变量分布与缺失率 ----------
print("\n===== 1. 单变量分布与缺失率 =====")
for name, v in [('dose', dose), ('survival', surv)]:
    miss = np.isnan(v).sum()
    print(f"{name}: n={len(v)}, 缺失={miss} ({miss/len(v)*100:.1f}%), "
          f"min={np.nanmin(v):.3f}, median={np.nanmedian(v):.3f}, "
          f"mean={np.nanmean(v):.3f}, max={np.nanmax(v):.3f}, "
          f"skew={float(np.nanmean(((v-np.nanmean(v))/np.nanstd(v))**3)):.3f}")

# ---------- 2. 按剂量分组统计 ----------
print("\n===== 2. 按剂量分组统计 (mean/SD/n) =====")
uniq = np.unique(dose[~np.isnan(dose)])
groups = []
for d in uniq:
    m = (dose == d) & ~np.isnan(surv)
    vals = surv[m]
    n = len(vals)
    mean = np.mean(vals) if n > 0 else np.nan
    sd = np.std(vals, ddof=1) if n > 1 else np.nan
    groups.append((d, n, mean, sd))
    flag = "  <-- n<3 低置信" if n < 3 else ""
    print(f"dose={d:>8.3f}  n={n:>2d}  mean={mean:7.3f}  SD={sd:7.3f}{flag}")

# ---------- 3. Bottom/Top 固定判断 ----------
print("\n===== 3. Bottom/Top 固定判断 =====")
low_dose = uniq.min()
high_dose = uniq.max()
low_vals = surv[(dose == low_dose) & ~np.isnan(surv)]
high_vals = surv[(dose == high_dose) & ~np.isnan(surv)]
low_mean = np.mean(low_vals) if len(low_vals) else np.nan
high_mean = np.mean(high_vals) if len(high_vals) else np.nan
print(f"最低剂量 {low_dose}: 均值={low_mean:.3f} (抑制率={100-low_mean:.3f}%)")
print(f"最高剂量 {high_dose}: 均值={high_mean:.3f} (抑制率={100-high_mean:.3f}%)")
fix_bottom = abs(100 - low_mean) <= 10
fix_top = abs(high_mean) <= 10
print(f"Bottom 是否需固定(最低剂量抑制率接近0, |100-mean|<=10): {fix_bottom}")
print(f"Top 是否需固定(最高剂量抑制率接近100, |mean|<=10): {fix_top}")

# ---------- 4. 低置信点标记 ----------
print("\n===== 4. 低置信剂量点 (n<3) =====")
low_conf = [g for g in groups if g[1] < 3]
if low_conf:
    for d, n, mean, sd in low_conf:
        print(f"  dose={d:.3f}, n={n}, mean={mean:.3f} -> 建议：合并邻近剂量或剔除")
else:
    print("  无 n<3 的剂量点")

# ---------- 5. 陷阱规避检查 ----------
print("\n===== 5. 已知陷阱规避检查 =====")
# 陷阱1: 只看均值不看分布形态
print("[陷阱1] 分布形态检查：")
for d, n, mean, sd in groups:
    vals = surv[dose == d]
    if len(vals) > 1:
        cv = sd / mean if mean != 0 else np.nan
        print(f"  dose={d:.3f}: CV={cv:.3f} (CV>0.3 提示离散大，均值代表性弱)")
# 陷阱2: 相关系数解释非线性
r = np.corrcoef(dose[~np.isnan(surv)], surv[~np.isnan(surv)])[0, 1]
print(f"[陷阱2] dose-survival Pearson r={r:.3f} -> 剂量-反应为非线性(S型)，"
      f"r 仅作参考，不可用于线性解释")
# 陷阱3: 分组样本量差异
ns = [g[1] for g in groups]
print(f"[陷阱3] 各组样本量: min={min(ns)}, max={max(ns)}, "
      f"极差={max(ns)-min(ns)} -> 组间 n 差异大时均值比较需谨慎")

# ---------- 6. 共线性/候选特征与风险项 ----------
print("\n===== 6. 候选特征与风险项 =====")
print("候选特征: dose (自变量), survival (因变量)")
print("风险项:")
if any(g[1] < 3 for g in groups):
    print("  - 存在 n<3 剂量点，需合并或剔除")
if not fix_bottom:
    print("  - 最低剂量抑制率偏离0，Bottom 建议自由拟合")
if not fix_top:
    print("  - 最高剂量抑制率偏离100，Top 建议自由拟合")
if max(ns) - min(ns) > 3:
    print("  - 组间样本量差异大，加权拟合更稳健")

# ---------- 7. 出图 ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# 左：分布图（剂量分布 + 存活率分布）
ax = axes[0]
ax.hist(dose, bins=15, alpha=0.6, color='steelblue', label='剂量分布')
ax.set_xlabel('剂量')
ax.set_ylabel('频数')
ax.set_title('剂量分布')
ax2 = ax.twinx()
ax2.hist(surv, bins=15, alpha=0.5, color='orange', label='存活率分布')
ax2.set_ylabel('频数')
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

# 右：分组对比（均值±SD，标注 n）
ax = axes[1]
ds = [g[0] for g in groups]
ms = [g[2] for g in groups]
sds = [g[3] if not np.isnan(g[3]) else 0 for g in groups]
ns_plot = [g[1] for g in groups]
ax.errorbar(ds, ms, yerr=sds, fmt='o-', capsize=4, color='darkred', label='mean±SD')
for d, m, n in zip(ds, ms, ns_plot):
    ax.annotate(f'n={n}', (d, m), textcoords="offset points", xytext=(0, 8),
                ha='center', fontsize=8)
ax.axhline(100, ls='--', color='gray', alpha=0.5)
ax.axhline(0, ls='--', color='gray', alpha=0.5)
ax.set_xlabel('剂量')
ax.set_ylabel('存活率 (%)')
ax.set_title('剂量-存活率分组对比 (标注 n)')
ax.legend()

plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print("\n[输出] 图已保存: figure.png")

# ---------- 8. 落盘 ----------
out = np.array([(g[0], g[1], g[2], g[3]) for g in groups],
               dtype=[('dose', 'f8'), ('n', 'i4'), ('mean', 'f8'), ('sd', 'f8')])
np.savetxt('group_summary.csv', out, delimiter=',',
           header='dose,n,mean,sd', comments='', fmt='%.6f')
print("[输出] 分组统计已保存: group_summary.csv")
print(f"\n[数据来源] {'模拟数据（非真实实验结论）' if SIMULATED else '真实数据 clean_dose_response.csv'}")