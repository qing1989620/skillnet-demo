import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 1. 读取真实输入文件 ----------
def load_csv(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8-sig') as f:
        header = f.readline().strip().split(',')
    data = np.genfromtxt(path, delimiter=',', names=True, dtype=None, encoding='utf-8')
    return data, header

clean = load_csv('clean_data.csv')
audit = load_csv('audit_log.csv')
ddict = load_csv('data_dictionary.csv')

if clean is None:
    raise FileNotFoundError("clean_data.csv 未找到，请确认前序步骤产物已就位。")

data, header = clean
print("=== 输入文件检查 ===")
print("clean_data.csv 列名:", header)
print("样本量 n =", data.shape[0])
print("audit_log.csv 存在:", audit is not None)
print("data_dictionary.csv 存在:", ddict is not None)

# ---------- 2. 识别剂量列与响应列 ----------
def find_col(cols, keys):
    for c in cols:
        lc = c.lower()
        for k in keys:
            if k in lc:
                return c
    return None

dose_col = find_col(header, ['dose', 'conc', '剂量', '浓度'])
resp_col = find_col(header, ['surv', 'viab', 'inhib', 'response', '存活', '抑制', '响应'])
if dose_col is None or resp_col is None:
    # 退化：取前两列
    dose_col, resp_col = header[0], header[1]
print("\n剂量列 =", dose_col, "| 响应列 =", resp_col)

dose = np.asarray(data[dose_col], dtype=float)
resp = np.asarray(data[resp_col], dtype=float)

# 抑制率：若响应是存活率(0-1)，抑制率=1-存活；若已是抑制率则保留
if np.nanmax(resp) <= 1.0 and np.nanmin(resp) >= 0.0:
    inhib = 1.0 - resp
    resp_kind = "存活率(已转抑制率)"
else:
    inhib = resp.copy()
    resp_kind = "抑制率(原值)"
print("响应类型判定:", resp_kind)

# ---------- 3. 单变量分布与缺失率 ----------
print("\n=== 单变量分布与缺失率 ===")
for name, arr in [(dose_col, dose), (resp_col, resp)]:
    miss = np.isnan(arr).sum()
    valid = arr[~np.isnan(arr)]
    print(f"{name}: 缺失={miss} ({miss/len(arr)*100:.1f}%), "
          f"min={valid.min():.4g}, max={valid.max():.4g}, "
          f"mean={valid.mean():.4g}, median={np.median(valid):.4g}, "
          f"skew={float(((valid-valid.mean())**3).mean()/ (valid.std()**3+1e-12)):.3f}")

# ---------- 4. 按剂量分组：均值/SD/n ----------
print("\n=== 按剂量分组统计 ===")
uniq = np.unique(dose[~np.isnan(dose)])
rows = []
for d in uniq:
    m = (dose == d) & ~np.isnan(inhib)
    vals = inhib[m]
    n = vals.size
    mean = vals.mean() if n > 0 else np.nan
    sd = vals.std(ddof=1) if n > 1 else np.nan
    low_conf = n < 3
    rows.append((d, n, mean, sd, low_conf))
    flag = "  <-- n<3 低置信" if low_conf else ""
    print(f"剂量={d:.4g}: n={n}, mean抑制率={mean:.4f}, SD={sd if not np.isnan(sd) else float('nan'):.4f}{flag}")

rows_arr = np.array([(r[0], r[1], r[2], r[3]) for r in rows], dtype=float)
low_conf_mask = np.array([r[4] for r in rows])

# ---------- 5. Bottom/Top 固定判断 ----------
print("\n=== Bottom/Top 固定判断 ===")
d_min, d_max = uniq.min(), uniq.max()
low_vals = inhib[dose == d_min]
high_vals = inhib[dose == d_max]
low_mean = np.nanmean(low_vals)
high_mean = np.nanmean(high_vals)
print(f"最低剂量 {d_min:.4g} 平均抑制率 = {low_mean:.4f} (接近0? {'是' if abs(low_mean)<0.05 else '否'})")
print(f"最高剂量 {d_max:.4g} 平均抑制率 = {high_mean:.4f} (接近1? {'是' if abs(high_mean-1)<0.05 else '否'})")
fix_bottom = abs(low_mean) < 0.05
fix_top = abs(high_mean - 1.0) < 0.05
print(f"建议: Bottom {'固定=0' if fix_bottom else '自由拟合'}, Top {'固定=1' if fix_top else '自由拟合'}")

# ---------- 6. 相关矩阵（标注共线性） ----------
print("\n=== 相关矩阵与共线性 ===")
num_cols = []
num_mat = []
for c in header:
    try:
        v = np.asarray(data[c], dtype=float)
        if np.isnan(v).all():
            continue
        num_cols.append(c)
        num_mat.append(v)
    except (ValueError, TypeError):
        continue
if len(num_mat) >= 2:
    M = np.vstack(num_mat)
    valid_mask = ~np.isnan(M).any(axis=0)
    Mv = M[:, valid_mask]
    if Mv.shape[1] >= 2:
        C = np.corrcoef(Mv)
        print("数值列:", num_cols)
        for i in range(len(num_cols)):
            for j in range(i+1, len(num_cols)):
                r = C[i, j]
                tag = "  <-- 高共线(|r|>0.8)" if abs(r) > 0.8 else ""
                print(f"  corr({num_cols[i]}, {num_cols[j]}) = {r:.3f}{tag}")
        print("注意: 相关系数仅反映线性关系，非线性剂量-响应需用曲线拟合解释。")
    else:
        print("有效数值列不足，跳过相关矩阵。")
else:
    print("数值列不足，跳过相关矩阵。")

# ---------- 7. 目标变量分布与不平衡 ----------
print("\n=== 目标变量分布 ===")
bins = np.linspace(0, 1, 11)
hist, _ = np.histogram(inhib[~np.isnan(inhib)], bins=bins)
print("抑制率分箱计数(0-1, 10箱):", hist.tolist())
print("抑制率范围:", f"{np.nanmin(inhib):.4f} ~ {np.nanmax(inhib):.4f}")

# ---------- 8. 候选特征与风险项 ----------
print("\n=== 候选特征与风险项 ===")
print("候选特征: 剂量(dose) -> 抑制率(inhib)")
risks = []
if np.isnan(dose).any() or np.isnan(inhib).any():
    risks.append("存在缺失值，需插补或剔除")
if low_conf_mask.any():
    risks.append(f"{low_conf_mask.sum()} 个剂量组 n<3，置信度低，建议合并或加权")
if not fix_bottom:
    risks.append("最低剂量抑制率未接近0，Bottom 建议自由拟合")
if not fix_top:
    risks.append("最高剂量抑制率未接近100%，Top 建议自由拟合")
if not risks:
    risks.append("无明显风险项")
for r in risks:
    print(" -", r)

# ---------- 9. 绘图 ----------
fig, axes = plt.subplots(2, 2, figsize=(12, 9))

# (a) 剂量分布
ax = axes[0, 0]
ax.hist(dose[~np.isnan(dose)], bins=15, color='steelblue', edgecolor='k', alpha=0.8)
ax.set_title('剂量分布')
ax.set_xlabel('剂量')
ax.set_ylabel('频数')

# (b) 抑制率分布
ax = axes[0, 1]
ax.hist(inhib[~np.isnan(inhib)], bins=15, color='salmon', edgecolor='k', alpha=0.8)
ax.set_title('抑制率分布')
ax.set_xlabel('抑制率')
ax.set_ylabel('频数')

# (c) 剂量-响应散点 + 分组均值误差棒
ax = axes[1, 0]
ax.scatter(dose, inhib, s=18, alpha=0.5, color='gray', label='原始点')
means = rows_arr[:, 2]
sds = rows_arr[:, 3]
ns = rows_arr[:, 1]
err = np.where(np.isnan(sds), 0, sds)
ax.errorbar(rows_arr[:, 0], means, yerr=err, fmt='o-', color='crimson',
            capsize=4, label='分组均值±SD')
# 标记低置信点
if low_conf_mask.any():
    ax.scatter(rows_arr[low_conf_mask, 0], means[low_conf_mask],
               s=120, facecolors='none', edgecolors='blue', linewidths=2,
               label='n<3 低置信')
ax.set_title('剂量-响应散点与分组均值')
ax.set_xlabel('剂量')
ax.set_ylabel('抑制率')
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

# (d) 分组 n 柱状
ax = axes[1, 1]
ax.bar(range(len(uniq)), ns, color='mediumseagreen', edgecolor='k')
ax.axhline(3, color='red', linestyle='--', label='n=3 阈值')
ax.set_xticks(range(len(uniq)))
ax.set_xticklabels([f"{d:.3g}" for d in uniq], rotation=45, fontsize=7)
ax.set_title('各剂量组样本量 n')
ax.set_xlabel('剂量')
ax.set_ylabel('n')
ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print("\n图已保存: figure.png")

# ---------- 10. 落盘 ----------
out = np.column_stack([rows_arr, low_conf_mask.astype(int)])
np.savetxt('dose_group_summary.csv', out, delimiter=',',
           header='dose,n,mean_inhib,sd_inhib,low_conf_n_lt_3', comments='', fmt='%.6g')
print("分组统计已保存: dose_group_summary.csv")
print("\n[说明] 本步骤基于前序 clean_data.csv 真实产物；若该文件为模拟数据，结论仅作流程演示。")