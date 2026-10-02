import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 读取真实输入文件 ----------
def load_csv(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8-sig') as f:
        header = f.readline().strip().split(',')
    arr = np.genfromtxt(path, delimiter=',', names=True, dtype=None, encoding='utf-8')
    return arr, header

clean = None
clean_header = None
if os.path.exists('clean_data.csv'):
    clean, clean_header = load_csv('clean_data.csv')
    print(f"[输入] clean_data.csv 已读取, 列: {clean_header}, 行数: {len(clean)}")
else:
    print("[警告] 未找到 clean_data.csv, 使用模拟数据（模拟数据，非真实实验结论）")
    rng = np.random.default_rng(42)
    doses = np.array([0.0, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0])
    rows = []
    for d in doses:
        n = int(rng.integers(2, 6))
        top, bottom = 98.0, 2.0
        ic50 = 8.0
        surv = bottom + (top - bottom) / (1.0 + (d / ic50) ** 1.3)
        for _ in range(n):
            rows.append((d, float(np.clip(surv + rng.normal(0, 4), 0, 100))))
    clean = np.array(rows, dtype=[('dose', 'f8'), ('survival', 'f8')])
    clean_header = ['dose', 'survival']

# 自动识别剂量列与存活率列
dose_col = None
surv_col = None
for c in clean_header:
    lc = c.lower()
    if dose_col is None and ('dose' in lc or 'conc' in lc or '剂量' in c):
        dose_col = c
    if surv_col is None and ('surv' in lc or 'inhib' in lc or '存活' in c or '抑制' in c or 'response' in lc):
        surv_col = c
if dose_col is None:
    dose_col = clean_header[0]
if surv_col is None:
    surv_col = clean_header[-1]
print(f"[识别] 剂量列='{dose_col}', 响应列='{surv_col}'")

dose = np.asarray(clean[dose_col], dtype=float)
surv = np.asarray(clean[surv_col], dtype=float)

# ---------- 1. 单变量分布与缺失率 ----------
print("\n===== 1. 单变量分布与缺失率 =====")
for name, v in [(dose_col, dose), (surv_col, surv)]:
    miss = np.isnan(v).sum()
    vv = v[~np.isnan(v)]
    print(f"{name}: n={len(v)}, 缺失={miss} ({miss/len(v)*100:.1f}%), "
          f"min={vv.min():.3f}, q25={np.percentile(vv,25):.3f}, "
          f"median={np.median(vv):.3f}, q75={np.percentile(vv,75):.3f}, "
          f"max={vv.max():.3f}, mean={vv.mean():.3f}, sd={vv.std(ddof=1):.3f}, "
          f"skew={float(((vv-vv.mean())**3).mean()/ (vv.std()+1e-12)**3):.3f}")

# ---------- 2. 按剂量分组统计 ----------
print("\n===== 2. 按剂量分组: mean / SD / n =====")
uniq = np.unique(dose[~np.isnan(dose)])
grp_mean, grp_sd, grp_n = [], [], []
for d in uniq:
    m = (dose == d) & ~np.isnan(surv)
    vals = surv[m]
    grp_mean.append(vals.mean() if len(vals) else np.nan)
    grp_sd.append(vals.std(ddof=1) if len(vals) > 1 else np.nan)
    grp_n.append(len(vals))
grp_mean = np.array(grp_mean); grp_sd = np.array(grp_sd); grp_n = np.array(grp_n)
for d, mu, sd, n in zip(uniq, grp_mean, grp_sd, grp_n):
    flag = "  <-- n<3 低置信" if n < 3 else ""
    print(f"dose={d:>8.4g}: mean={mu:7.3f}, SD={sd:7.3f}, n={n}{flag}")

low_conf = uniq[grp_n < 3]
print(f"[低置信剂量点] n<3 的剂量: {low_conf.tolist() if len(low_conf) else '无'}")

# ---------- 3. Bottom/Top 是否需固定 ----------
print("\n===== 3. Bottom/Top 检查 =====")
dmin, dmax = uniq.min(), uniq.max()
i_min = int(np.argmin(uniq)); i_max = int(np.argmax(uniq))
low_inhib = grp_mean[i_min]
high_inhib = grp_mean[i_max]
print(f"最低剂量 {dmin:.4g} 处抑制率均值 = {low_inhib:.3f}%")
print(f"最高剂量 {dmax:.4g} 处抑制率均值 = {high_inhib:.3f}%")
fix_bottom = abs(low_inhib) <= 5.0
fix_top = abs(high_inhib - 100.0) <= 5.0
print(f"Bottom 是否可固定为 0: {'是' if fix_bottom else '否'} (|最低抑制率|<=5%)")
print(f"Top 是否可固定为 100: {'是' if fix_top else '否'} (|最高抑制率-100|<=5%)")

# ---------- 4. log10(dose) 与 dose 共存检查 ----------
print("\n===== 4. log10(dose) 与 dose 共存检查 =====")
has_dose = dose_col is not None
log_cols = [c for c in clean_header if 'log' in c.lower()]
print(f"原始 dose 列存在: {has_dose}; 检测到 log 相关列: {log_cols if log_cols else '无'}")
if has_dose and log_cols:
    print("[风险] dose 与 log10(dose) 共存, 存在共线性, 建模时二者只保留其一")
else:
    print("[OK] 未发现 dose 与 log10(dose) 同时作为独立特征共存")

# ---------- 5. 相关矩阵与共线性标注 ----------
print("\n===== 5. 相关矩阵与共线性 =====")
num_cols = []
num_data = []
for c in clean_header:
    try:
        v = np.asarray(clean[c], dtype=float)
        if not np.all(np.isnan(v)):
            num_cols.append(c); num_data.append(v)
    except (ValueError, TypeError):
        continue
if len(num_cols) >= 2:
    M = np.vstack(num_data)
    valid = ~np.isnan(M).any(axis=0)
    Mv = M[:, valid]
    if Mv.shape[1] >= 2:
        C = np.corrcoef(Mv)
        print("相关系数矩阵:")
        print("        " + "  ".join(f"{c[:8]:>8}" for c in num_cols))
        for i, c in enumerate(num_cols):
            print(f"{c[:8]:>8} " + "  ".join(f"{C[i,j]:8.3f}" for j in range(len(num_cols))))
        print("[共线性 |r|>0.9 的特征对]:")
        found = False
        for i in range(len(num_cols)):
            for j in range(i+1, len(num_cols)):
                if abs(C[i, j]) > 0.9:
                    print(f"  {num_cols[i]} <-> {num_cols[j]}: r={C[i,j]:.3f}")
                    found = True
        if not found:
            print("  无")
        print("[提示] 相关系数仅反映线性关系, 剂量-响应为非线性, 不可用 r 解释其关系")
else:
    print("数值列不足, 跳过相关矩阵")

# ---------- 6. 目标变量分布与风险项 ----------
print("\n===== 6. 目标变量分布与风险项 =====")
sv = surv[~np.isnan(surv)]
print(f"响应变量范围: [{sv.min():.3f}, {sv.max():.3f}], 均值={sv.mean():.3f}, SD={sv.std(ddof=1):.3f}")
out_of_range = ((sv < 0) | (sv > 100)).sum()
print(f"越界(不在0-100)样本数: {out_of_range}")
print("[风险项与处理建议]")
if len(low_conf):
    print(f"  - 低置信剂量点 n<3: {low_conf.tolist()} -> 建议合并或加权, 拟合时降低权重")
if not fix_bottom:
    print(f"  - 最低剂量抑制率 {low_inhib:.2f}% 偏离0 -> 建议 Bottom 作为自由参数拟合")
if not fix_top:
    print(f"  - 最高剂量抑制率 {high_inhib:.2f}% 偏离100 -> 建议 Top 作为自由参数拟合")
if out_of_range:
    print(f"  - 存在 {out_of_range} 个越界响应值 -> 建议截断或复核原始记录")
print("  - 剂量-响应为非线性, 建议用 4 参数 logistic 拟合, 勿用线性相关解释")

# ---------- 7. 绘图 ----------
fig, axes = plt.subplots(2, 2, figsize=(12, 9))

ax = axes[0, 0]
ax.hist(dose[~np.isnan(dose)], bins=15, color='steelblue', edgecolor='black')
ax.set_title(f'剂量分布 ({dose_col})'); ax.set_xlabel('dose'); ax.set_ylabel('频数')

ax = axes[0, 1]
ax.hist(surv[~np.isnan(surv)], bins=15, color='seagreen', edgecolor='black')
ax.set_title(f'响应分布 ({surv_col})'); ax.set_xlabel('survival/inhibition'); ax.set_ylabel('频数')

ax = axes[1, 0]
ax.errorbar(uniq, grp_mean, yerr=grp_sd, fmt='o', color='crimson',
            ecolor='gray', capsize=4, label='mean ± SD')
for d, mu, n in zip(uniq, grp_mean, grp_n):
    if n < 3:
        ax.scatter([d], [mu], s=120, facecolors='none', edgecolors='orange',
                   linewidths=2, label='n<3 低置信' if d == low_conf[0] else None)
ax.set_title('剂量-响应散点 (mean ± SD)')
ax.set_xlabel('dose'); ax.set_ylabel('response')
ax.legend(fontsize=8); ax.grid(alpha=0.3)

ax = axes[1, 1]
ax.scatter(dose, surv, s=18, alpha=0.6, color='navy', label='原始点')
ax.plot(uniq, grp_mean, '-o', color='crimson', label='分组均值')
ax.axhline(0, color='gray', ls='--', lw=1)
ax.axhline(100, color='gray', ls='--', lw=1)
ax.set_title('剂量-响应总览'); ax.set_xlabel('dose'); ax.set_ylabel('response')
ax.legend(fontsize=8); ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n[输出] figure.png 已保存")

# ---------- 落盘 ----------
out = np.column_stack([uniq, grp_mean, grp_sd, grp_n])
np.savetxt('dose_group_summary.csv', out, delimiter=',',
           header='dose,mean,sd,n', comments='', fmt='%.6g')
print("[输出] dose_group_summary.csv 已保存")