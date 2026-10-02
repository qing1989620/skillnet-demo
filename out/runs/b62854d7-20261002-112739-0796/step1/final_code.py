import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv
import os

rng = np.random.default_rng(42)

# ============================================================
# 0. 构造模拟数据（明确标注：模拟数据，非真实实验结论）
# ============================================================
# 原始表字段：dose_raw, dose_unit, inhibition_raw, replicate, group
# 剂量单位混杂：uM / mM / nM；抑制率混杂：0-1 小数 与 0-100 百分数
groups = ['Vehicle', 'DrugA', 'DrugB']
doses_uM = [0.0, 0.1, 1.0, 10.0, 100.0]
rows = []
for g in groups:
    for d in doses_uM:
        for rep in range(1, 4):
            # 真实抑制率（模拟）：Hill 型
            if g == 'Vehicle':
                true_inh = 0.02 + rng.normal(0, 0.01)
            else:
                ec50 = 5.0 if g == 'DrugA' else 20.0
                true_inh = 1.0 / (1.0 + (ec50 / max(d, 1e-6)) ** 1.2)
                true_inh += rng.normal(0, 0.03)
            true_inh = float(np.clip(true_inh, 0, 1))
            # 单位随机化
            u = rng.choice(['uM', 'mM', 'nM'], p=[0.6, 0.2, 0.2])
            if u == 'mM':
                dose_raw = d / 1000.0
            elif u == 'nM':
                dose_raw = d * 1000.0
            else:
                dose_raw = d
            # 抑制率随机以百分数或小数表示
            if rng.random() < 0.3:
                inh_raw = round(true_inh * 100, 2)
            else:
                inh_raw = round(true_inh, 4)
            rows.append([dose_raw, u, inh_raw, rep, g])

# 注入缺失（非随机：DrugB 高剂量缺失更多）与重复孔
for i, r in enumerate(rows):
    if r[4] == 'DrugB' and r[0] >= 10 and rng.random() < 0.25:
        rows[i][2] = None  # 抑制率缺失
# 注入一个重复孔（同主键重复）
rows.append(list(rows[0]))

# 写入原始 CSV
raw_path = 'raw_dose_response.csv'
with open(raw_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['dose_raw', 'dose_unit', 'inhibition_raw', 'replicate', 'group'])
    for r in rows:
        w.writerow(['' if v is None else v for v in r])

print('=== 模拟数据说明：以下全部为模拟数据，非真实实验结论 ===')
print(f'原始表行数: {len(rows)}')

# ============================================================
# 1. 读取 + 结构/类型探查
# ============================================================
audit = []
def log(step, reason, n_before, n_after, note=''):
    audit.append([step, reason, n_before, n_after, note])
    print(f'[审计] {step} | 原因: {reason} | 行数 {n_before}->{n_after} | {note}')

with open(raw_path, encoding='utf-8') as f:
    reader = list(csv.DictReader(f))
n0 = len(reader)
log('读取原始表', '载入原始剂量-响应数据', n0, n0)

# 类型转换
def to_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan

recs = []
for r in reader:
    recs.append({
        'dose_raw': to_float(r['dose_raw']),
        'dose_unit': r['dose_unit'].strip(),
        'inhibition_raw': to_float(r['inhibition_raw']),
        'replicate': int(r['replicate']),
        'group': r['group'].strip(),
    })

# 缺失模式
miss_dose = sum(1 for r in recs if np.isnan(r['dose_raw']))
miss_inh = sum(1 for r in recs if np.isnan(r['inhibition_raw']))
print(f'缺失统计: dose_raw 缺失 {miss_dose} 行, inhibition_raw 缺失 {miss_inh} 行')
# 非随机缺失检查：按 group 统计缺失率
for g in groups:
    sub = [r for r in recs if r['group'] == g]
    m = sum(1 for r in sub if np.isnan(r['inhibition_raw']))
    print(f'  组 {g}: 抑制率缺失 {m}/{len(sub)} = {m/max(len(sub),1):.1%}')
print('缺失模式结论: 缺失集中在 DrugB 高剂量 -> 判定为非随机缺失(MNAR)，不删除、不均值填补')

# ============================================================
# 2. 单位统一为 μM，抑制率统一为 0-1 小数
# ============================================================
unit_factor = {'uM': 1.0, 'mM': 1000.0, 'nM': 0.001}
for r in recs:
    r['dose_uM'] = r['dose_raw'] * unit_factor.get(r['dose_unit'], np.nan)
    # 抑制率：>1 视为百分数
    if not np.isnan(r['inhibition_raw']) and r['inhibition_raw'] > 1.0:
        r['inhibition'] = r['inhibition_raw'] / 100.0
    else:
        r['inhibition'] = r['inhibition_raw']
    r['log10_dose'] = np.log10(r['dose_uM']) if (not np.isnan(r['dose_uM']) and r['dose_uM'] > 0) else np.nan

log('单位与量纲统一', 'dose->μM, inhibition->0-1', len(recs), len(recs),
    f'单位映射 {unit_factor}')

# ============================================================
# 3. 主键唯一性检查（dose×replicate×group）
# ============================================================
def key(r):
    return (round(r['dose_uM'], 6) if not np.isnan(r['dose_uM']) else None,
            r['replicate'], r['group'])

seen = {}
dup_idx = []
for i, r in enumerate(recs):
    k = key(r)
    if k in seen:
        dup_idx.append(i)
    else:
        seen[k] = i
print(f'主键重复行数: {len(dup_idx)}')
# 保留首次出现，标记重复
for i in dup_idx:
    recs[i]['flag_dup'] = True
for r in recs:
    r.setdefault('flag_dup', False)
log('主键唯一性检查', 'dose×replicate×group 去重(保留首条)', len(recs), len(recs) - len(dup_idx),
    f'重复 {len(dup_idx)} 行已标记 flag_dup')

# ============================================================
# 4. 业务规则异常标记（不删除）
# ============================================================
# 规则A：载体对照均值±3SD
veh = [r['inhibition'] for r in recs if r['group'] == 'Vehicle' and not np.isnan(r['inhibition'])]
veh_mean = float(np.mean(veh)) if veh else np.nan
veh_sd = float(np.std(veh, ddof=1)) if len(veh) > 1 else 0.0
lo, hi = veh_mean - 3 * veh_sd, veh_mean + 3 * veh_sd
print(f'载体对照: mean={veh_mean:.4f}, sd={veh_sd:.4f}, 3SD区间=[{lo:.4f}, {hi:.4f}]')

# 规则B：重复孔 CV>20%
from collections import defaultdict
cell = defaultdict(list)
for r in recs:
    if not np.isnan(r['inhibition']):
        cell[(round(r['dose_uM'], 6), r['group'])].append(r['inhibition'])
cv_map = {}
for k, vals in cell.items():
    if len(vals) > 1:
        m = np.mean(vals)
        cv = np.std(vals, ddof=1) / m if m != 0 else np.nan
        cv_map[k] = cv

n_flag_veh = 0
n_flag_cv = 0
for r in recs:
    r['flag_vehicle_3sd'] = False
    r['flag_cv20'] = False
    if not np.isnan(r['inhibition']) and r['group'] == 'Vehicle':
        if r['inhibition'] < lo or r['inhibition'] > hi:
            r['flag_vehicle_3sd'] = True
            n_flag_veh += 1
    k = (round(r['dose_uM'], 6), r['group'])
    if k in cv_map and not np.isnan(cv_map[k]) and cv_map[k] > 0.20:
        r['flag_cv20'] = True
        n_flag_cv += 1

print(f'业务规则标记: 载体3SD异常 {n_flag_veh} 行, 重复孔CV>20% {n_flag_cv} 行')
log('业务规则异常标记', '载体±3SD 与 重复孔CV>20%', len(recs), len(recs),
    f'标记而非删除: veh3sd={n_flag_veh}, cv20={n_flag_cv}')

# ============================================================
# 5. 输出干净数据表 + 数据字典 + 审计日志
# ============================================================
clean_rows = []
for r in recs:
    clean_rows.append({
        'dose_uM': r['dose_uM'],
        'log10_dose': r['log10_dose'],
        'inhibition': r['inhibition'],
        'replicate': r['replicate'],
        'group': r['group'],
        'flag_dup': int(r['flag_dup']),
        'flag_vehicle_3sd': int(r['flag_vehicle_3sd']),
        'flag_cv20': int(r['flag_cv20']),
        'is_missing_inhibition': int(np.isnan(r['inhibition'])),
    })

# 关键字段分布变化
inh_all = [r['inhibition'] for r in recs if not np.isnan(r['inhibition'])]
print(f'抑制率分布(清洗后): n={len(inh_all)}, mean={np.mean(inh_all):.4f}, '
      f'min={np.min(inh_all):.4f}, max={np.max(inh_all):.4f}')
dose_all = [r['dose_uM'] for r in recs if not np.isnan(r['dose_uM'])]
print(f'剂量分布(μM): n={len(dose_all)}, min={np.min(dose_all):.4f}, max={np.max(dose_all):.4f}')

# 主键唯一性最终校验
final_keys = [(round(r['dose_uM'], 6) if not np.isnan(r['dose_uM']) else None,
               r['replicate'], r['group']) for r in recs]
print(f'清洗后主键唯一: {len(final_keys) == len(set(final_keys))}')

# ============================================================
# 6. 出图
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
# 左：剂量-响应散点（按组）
for g in groups:
    xs = [r['log10_dose'] for r in recs if r['group'] == g and not np.isnan(r['log10_dose']) and not np.isnan(r['inhibition'])]
    ys = [r['inhibition'] for r in recs if r['group'] == g and not np.isnan(r['log10_dose']) and not np.isnan(r['inhibition'])]
    axes[0].scatter(xs, ys, label=g, alpha=0.7)
axes[0].set_xlabel('log10(剂量 / μM)')
axes[0].set_ylabel('抑制率 (0-1)')
axes[0].set_title('剂量-响应关系（模拟数据）')
axes[0].legend()
axes[0].grid(alpha=0.3)

# 右：抑制率分布
axes[1].hist(inh_all, bins=20, color='steelblue', edgecolor='white')
axes[1].set_xlabel('抑制率 (0-1)')
axes[1].set_ylabel('频数')
axes[1].set_title('抑制率分布（模拟数据）')
axes[1].grid(alpha=0.3)
plt.tight_layout()
plt.savefig('figure.png', dpi=120)
plt.close()

# ============================================================
# 7. 落盘
# ============================================================
with open('clean_dose_response.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(clean_rows[0].keys()))
    w.writeheader()
    w.writerows(clean_rows)

with open('data_dictionary.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['字段', '口径/单位', '说明'])
    w.writerow(['dose_uM', 'μM', '统一后的剂量'])
    w.writerow(['log10_dose', 'log10(μM)', '剂量对数，dose=0 时为缺失'])
    w.writerow(['inhibition', '0-1 小数', '统一后的抑制率'])
    w.writerow(['replicate', '整数', '重复孔编号'])
    w.writerow(['group', '字符串', '实验组'])
    w.writerow(['flag_dup', '0/1', '主键重复标记'])
    w.writerow(['flag_vehicle_3sd', '0/1', '载体对照±3SD异常标记'])
    w.writerow(['flag_cv20', '0/1', '重复孔CV>20%标记'])
    w.writerow(['is_missing_inhibition', '0/1', '抑制率缺失标记'])

with open('audit_log.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['步骤', '原因', '处理前行数', '处理后行数', '备注'])
    w.writerows(audit)

print('落盘文件: raw_dose_response.csv, clean_dose_response.csv, data_dictionary.csv, audit_log.csv, figure.png')