import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv

# ============================================================
# 说明：本脚本使用【模拟数据】演示剂量-存活率数据的质量检查流程。
# 模拟数据不代表任何真实实验结果，仅用于验证分析代码。
# ============================================================
rng = np.random.default_rng(42)

# 9 个剂量点（对数等间距），每组 3 次重复
doses = np.array([0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0])
n_rep = 3
n_dose = len(doses)

# 模拟真实 IC50 曲线（4 参数 logistic 的简化形式）
IC50_true = 25.0
hill = 1.2
top = 100.0
bottom = 5.0

def survival(d):
    return bottom + (top - bottom) / (1.0 + (d / IC50_true) ** hill)

# 生成带噪声的重复数据
records = []
for d in doses:
    mu = survival(d)
    for r in range(n_rep):
        val = mu + rng.normal(0, 3.0)
        val = float(np.clip(val, 0.0, 120.0))
        records.append((d, r + 1, val))

# 人为注入一个缺失值和一个异常值，用于演示质量检查
records[4] = (records[4][0], records[4][1], np.nan)   # 缺失
records[13] = (records[13][0], records[13][1], 999.0)  # 异常

# 落盘原始数据
with open('dose_response_raw.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['dose', 'replicate', 'survival_pct'])
    for rec in records:
        w.writerow(rec)

print('=' * 60)
print('【模拟数据】剂量-存活率数据质量检查报告')
print('=' * 60)

# ---------- 1. 数据完整性 ----------
dose_arr = np.array([r[0] for r in records])
rep_arr = np.array([r[1] for r in records])
surv_arr = np.array([r[2] for r in records], dtype=float)

n_total = len(records)
n_missing = int(np.sum(np.isnan(surv_arr)))
print(f'\n[1] 数据完整性')
print(f'  总记录数: {n_total}')
print(f'  缺失值数量: {n_missing}  (缺失率 {n_missing/n_total*100:.2f}%)')
print(f'  唯一剂量点数: {len(np.unique(dose_arr))}  (预期 9)')

# 每个剂量的重复数
print(f'  各剂量点重复数:')
rep_counts = {}
for d in np.unique(dose_arr):
    mask = dose_arr == d
    valid = int(np.sum(~np.isnan(surv_arr[mask])))
    rep_counts[d] = valid
    print(f'    剂量 {d:>8.1f}: 有效重复 {valid}/{n_rep}')

# ---------- 2. 异常值检查 ----------
print(f'\n[2] 异常值检查 (基于 3*IQR 规则)')
valid_mask = ~np.isnan(surv_arr)
v = surv_arr[valid_mask]
q1, q3 = np.percentile(v, [25, 75])
iqr = q3 - q1
lo, hi = q1 - 3 * iqr, q3 + 3 * iqr
outliers = np.where(valid_mask & ((surv_arr < lo) | (surv_arr > hi)))[0]
print(f'  IQR = {iqr:.2f}, 正常范围 [{lo:.2f}, {hi:.2f}]')
print(f'  检出异常值数量: {len(outliers)}')
for idx in outliers:
    print(f'    剂量 {dose_arr[idx]:.1f}, 重复 {int(rep_arr[idx])}, 存活率 {surv_arr[idx]:.2f}')

# ---------- 3. 单调性与平台期 ----------
print(f'\n[3] 单调性与平台期检查')
dose_means = []
dose_stds = []
for d in np.unique(dose_arr):
    mask = (dose_arr == d) & valid_mask
    if np.sum(mask) > 0:
        dose_means.append(np.mean(surv_arr[mask]))
        dose_stds.append(np.std(surv_arr[mask], ddof=1) if np.sum(mask) > 1 else 0.0)
    else:
        dose_means.append(np.nan)
        dose_stds.append(np.nan)
dose_means = np.array(dose_means)
dose_stds = np.array(dose_stds)

# 单调性：存活率应随剂量增加而下降
diffs = np.diff(dose_means)
n_increase = int(np.sum(diffs > 0))
print(f'  相邻剂量均值差分: {np.round(diffs, 2)}')
print(f'  非单调上升次数: {n_increase}  (理想为 0)')

# 平台期：高剂量段均值变化幅度
if len(dose_means) >= 3:
    tail_change = abs(dose_means[-1] - dose_means[-3])
    print(f'  高剂量段(最后3点)均值变化幅度: {tail_change:.2f}')
    print(f'  是否达到平台期(变化<5%): {"是" if tail_change < 5 else "否"}')

# 变异系数
print(f'  各剂量点变异系数(CV):')
for i, d in enumerate(np.unique(dose_arr)):
    if not np.isnan(dose_stds[i]) and dose_means[i] != 0:
        cv = dose_stds[i] / abs(dose_means[i]) * 100
        print(f'    剂量 {d:>8.1f}: CV = {cv:.2f}%')

# ---------- 4. 风险清单 ----------
print(f'\n[4] 风险清单')
risks = []
if n_missing > 0:
    risks.append(f'存在 {n_missing} 个缺失值，需插补或剔除')
if len(outliers) > 0:
    risks.append(f'存在 {len(outliers)} 个异常值，需复核或剔除')
if n_increase > 0:
    risks.append(f'存在 {n_increase} 处非单调上升，可能为噪声或实验误差')
if len(np.unique(dose_arr)) < 9:
    risks.append('剂量点不足 9 个')
if not risks:
    risks.append('未发现明显数据质量问题')
for i, r in enumerate(risks, 1):
    print(f'  {i}. {r}')

# ---------- 5. 出图 ----------
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

# 左图：剂量-存活率散点 + 均值曲线
ax = axes[0]
for d in np.unique(dose_arr):
    mask = (dose_arr == d) & valid_mask
    ax.scatter(np.full(np.sum(mask), d), surv_arr[mask],
               alpha=0.6, s=40, color='steelblue', label='重复数据' if d == doses[0] else '')
ax.plot(np.unique(dose_arr), dose_means, 'o-', color='crimson',
        linewidth=2, markersize=6, label='剂量均值')
ax.errorbar(np.unique(dose_arr), dose_means, yerr=dose_stds,
            fmt='none', ecolor='crimson', capsize=4, alpha=0.7)
ax.set_xscale('log')
ax.set_xlabel('剂量 (log scale)')
ax.set_ylabel('存活率 (%)')
ax.set_title('剂量-存活率关系图（模拟数据）')
ax.legend()
ax.grid(alpha=0.3)

# 右图：各剂量点变异系数
ax2 = axes[1]
cvs = []
for i in range(len(dose_means)):
    if not np.isnan(dose_stds[i]) and dose_means[i] != 0:
        cvs.append(dose_stds[i] / abs(dose_means[i]) * 100)
    else:
        cvs.append(0.0)
ax2.bar(range(len(cvs)), cvs, color='teal', alpha=0.7)
ax2.axhline(y=15, color='red', linestyle='--', label='CV=15% 警戒线')
ax2.set_xticks(range(len(cvs)))
ax2.set_xticklabels([f'{d:.1f}' for d in np.unique(dose_arr)], rotation=45)
ax2.set_xlabel('剂量')
ax2.set_ylabel('变异系数 CV (%)')
ax2.set_title('各剂量点重复变异系数（模拟数据）')
ax2.legend()
ax2.grid(alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('figure.png', dpi=150, bbox_inches='tight')
print(f'\n[5] 图表已保存: figure.png')
print(f'    原始数据已保存: dose_response_raw.csv')

# ---------- 6. 汇总表落盘 ----------
with open('dose_summary.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['dose', 'n_valid', 'mean_survival', 'std_survival', 'cv_pct'])
    for i, d in enumerate(np.unique(dose_arr)):
        cv = (dose_stds[i] / abs(dose_means[i]) * 100) if (not np.isnan(dose_stds[i]) and dose_means[i] != 0) else 0.0
        w.writerow([d, rep_counts[d], round(dose_means[i], 3) if not np.isnan(dose_means[i]) else '',
                    round(dose_stds[i], 3) if not np.isnan(dose_stds[i]) else '', round(cv, 3)])
print(f'    汇总表已保存: dose_summary.csv')

print('\n' + '=' * 60)
print('注意：以上所有结果均基于【模拟数据】，不代表真实实验结论。')
print('=' * 60)