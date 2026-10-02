import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv
import os

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 读取真实输入文件 ----------
def read_csv(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    return rows

clean_path = 'step1_clean_data.csv'
audit_path = 'step1_audit_log.csv'

if not os.path.exists(clean_path):
    raise FileNotFoundError('缺少 step1_clean_data.csv，请先运行前序步骤')

rows = read_csv(clean_path)
print('=== 输入数据概览 ===')
print('清洗后记录数:', len(rows))
print('字段:', list(rows[0].keys()))

# 自动识别剂量列与存活率列
cols = list(rows[0].keys())
dose_col = None
surv_col = None
for c in cols:
    lc = c.lower()
    if dose_col is None and ('dose' in lc or '剂量' in c):
        dose_col = c
    if surv_col is None and ('surv' in lc or '存活' in lc or 'viab' in lc or '抑制' in c):
        surv_col = c
if dose_col is None:
    dose_col = cols[0]
if surv_col is None:
    surv_col = cols[1]
print('剂量列:', dose_col, '| 存活率列:', surv_col)

dose = np.array([float(r[dose_col]) for r in rows])
surv = np.array([float(r[surv_col]) for r in rows])

# ---------- 1. 单变量分布与缺失率 ----------
print('\n=== 1. 单变量分布与缺失率 ===')
for c in cols:
    vals = [r[c] for r in rows]
    miss = sum(1 for v in vals if v is None or str(v).strip() == '')
    try:
        arr = np.array([float(v) for v in vals if str(v).strip() != ''])
        print(f'{c}: 缺失率={miss/len(vals):.2%}, min={arr.min():.4g}, '
              f'median={np.median(arr):.4g}, mean={arr.mean():.4g}, max={arr.max():.4g}')
    except ValueError:
        print(f'{c}: 缺失率={miss/len(vals):.2%} (非数值列)')

# ---------- 2. 按剂量分组统计 ----------
print('\n=== 2. 按剂量分组统计 (mean/SD/n) ===')
uniq_doses = sorted(set(dose))
group_stats = []
for d in uniq_doses:
    mask = dose == d
    vals = surv[mask]
    n = len(vals)
    mean = vals.mean()
    sd = vals.std(ddof=1) if n > 1 else 0.0
    group_stats.append((d, mean, sd, n))
    print(f'剂量={d:g}: n={n}, mean={mean:.4f}, SD={sd:.4f}')

# ---------- 3. 平台期覆盖判断 ----------
print('\n=== 3. 平台期覆盖判断 ===')
lowest = group_stats[0]
highest = group_stats[-1]
# 抑制率 = 1 - 存活率（若存活率已是百分比则归一）
def to_frac(x):
    return x/100.0 if x > 1.5 else x
low_inhib = 1 - to_frac(lowest[1])
high_inhib = 1 - to_frac(highest[1])
print(f'最低剂量 {lowest[0]:g} 抑制率={low_inhib:.2%} (要求<=5%): {"满足" if low_inhib<=0.05 else "不满足"}')
print(f'最高剂量 {highest[0]:g} 抑制率={high_inhib:.2%} (要求>=95%): {"满足" if high_inhib>=0.95 else "不满足"}')
plateau_ok = (low_inhib <= 0.05) and (high_inhib >= 0.95)
print('平台期覆盖:', '完整' if plateau_ok else '不完整 -> 建议补充低/高剂量点')

# ---------- 4. 低置信点与样本量差异 ----------
print('\n=== 4. 低置信剂量点 (n<3) 与组间样本量差异 ===')
low_conf = [g for g in group_stats if g[3] < 3]
if low_conf:
    for g in low_conf:
        print(f'  低置信: 剂量={g[0]:g}, n={g[3]} -> 建议补做重复实验')
else:
    print('  无 n<3 的低置信剂量点')
ns = [g[3] for g in group_stats]
print(f'组间样本量: min={min(ns)}, max={max(ns)}, 极差={max(ns)-min(ns)}')
if max(ns) - min(ns) >= 3:
    print('  警告: 组间样本量差异较大，均值比较需谨慎（加权/配对分析）')
else:
    print('  组间样本量差异可接受')

# ---------- 5. 相关矩阵与共线性 ----------
print('\n=== 5. 相关矩阵与共线性特征对 (|r|>0.8) ===')
num_cols = []
num_data = []
for c in cols:
    try:
        arr = np.array([float(r[c]) for r in rows])
        num_cols.append(c)
        num_data.append(arr)
    except ValueError:
        continue
num_data = np.array(num_data)
corr = np.corrcoef(num_data)
print('数值特征:', num_cols)
collinear = []
for i in range(len(num_cols)):
    for j in range(i+1, len(num_cols)):
        r = corr[i, j]
        if abs(r) > 0.8:
            collinear.append((num_cols[i], num_cols[j], r))
            print(f'  共线性: {num_cols[i]} ~ {num_cols[j]}, r={r:.3f}')
if not collinear:
    print('  无 |r|>0.8 的共线性特征对')
print('注意: 相关系数仅反映线性关系，非线性剂量-响应需用曲线拟合解释')

# ---------- 6. 绘图 ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# 左: 剂量-响应散点 + 分组均值误差棒
ax = axes[0]
ax.scatter(dose, surv, alpha=0.5, label='原始数据点', color='steelblue')
gx = [g[0] for g in group_stats]
gy = [g[1] for g in group_stats]
ge = [g[2] for g in group_stats]
ax.errorbar(gx, gy, yerr=ge, fmt='o-', color='crimson', capsize=4, label='分组均值±SD')
for g in group_stats:
    if g[3] < 3:
        ax.scatter([g[0]], [g[1]], s=180, facecolors='none', edgecolors='orange',
                   linewidths=2, label='n<3 低置信' if g is low_conf[0] else None)
ax.set_xlabel('剂量')
ax.set_ylabel('存活率')
ax.set_title('剂量-响应散点与分组分布')
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

# 右: 各剂量组箱型/分布
ax2 = axes[1]
box_data = [surv[dose == d] for d in uniq_doses]
ax2.boxplot(box_data, labels=[f'{d:g}' for d in uniq_doses])
ax2.set_xlabel('剂量')
ax2.set_ylabel('存活率')
ax2.set_title('各剂量组分布 (箱型图)')
ax2.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print('\n图已保存: figure.png')

# ---------- 7. 落盘 ----------
with open('step2_group_stats.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['dose', 'mean', 'sd', 'n', 'low_confidence'])
    for g in group_stats:
        w.writerow([g[0], f'{g[1]:.6f}', f'{g[2]:.6f}', g[3], g[3] < 3])

with open('step2_corr_matrix.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['feature'] + num_cols)
    for i, c in enumerate(num_cols):
        w.writerow([c] + [f'{corr[i, j]:.6f}' for j in range(len(num_cols))])

print('已保存: step2_group_stats.csv, step2_corr_matrix.csv')

# ---------- 8. 风险项与处理建议 ----------
print('\n=== 风险项与处理建议 ===')
risks = []
if not plateau_ok:
    risks.append('平台期覆盖不完整 -> 补充最低/最高剂量实验点')
if low_conf:
    risks.append(f'{len(low_conf)} 个剂量组 n<3 -> 增加重复次数')
if max(ns) - min(ns) >= 3:
    risks.append('组间样本量差异大 -> 采用加权回归或配对设计')
if collinear:
    risks.append('存在共线性特征对 -> 建模时剔除或做正则化')
if not risks:
    risks.append('未发现显著风险项')
for r in risks:
    print(' -', r)