import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv

# ============================================================
# 注意：以下为【模拟数据】，仅用于演示清洗流程，非真实实验结论
# ============================================================
rng = np.random.default_rng(42)

def make_raw():
    rows = []
    doses = [0.0, 0.1, 1.0, 10.0, 100.0]  # μM
    for exp in ['E1', 'E2']:
        for d in doses:
            for rep in range(3):
                # 真实抑制率口径 0-1
                true_inh = 1.0 / (1.0 + np.exp(-(np.log10(d + 1e-9) + 0.5)))
                val = float(np.clip(true_inh + rng.normal(0, 0.05), 0, 1))
                rows.append({'exp_id': exp, 'well': f'{exp}-{d}-{rep}',
                             'dose_uM': d, 'inhibition': val})
    # 注入问题：重复孔主键、缺失、异常、单位混入
    rows.append(dict(rows[0]))                       # 完全重复孔
    rows[3]['inhibition'] = None                     # 缺失
    rows[7]['inhibition'] = None                     # 缺失
    rows[10]['inhibition'] = 1.85                    # 越界异常
    rows[12]['inhibition'] = -0.30                   # 越界异常
    rows[15]['dose_uM'] = -5.0                       # 负剂量异常
    return rows

raw = make_raw()
print(f"[模拟数据] 原始记录数 = {len(raw)}")

# ---------- 1. 结构与类型探查 ----------
fields = ['exp_id', 'well', 'dose_uM', 'inhibition']
print("字段:", fields)

# 主键唯一性检查（well 作为孔主键）
keys = [r['well'] for r in raw]
dup_keys = set(k for k in keys if keys.count(k) > 1)
print(f"重复主键数 = {len(dup_keys)} -> {sorted(dup_keys)}")

# ---------- 2. 去重（保留首次出现，记录审计） ----------
seen, clean = set(), []
dup_removed = 0
for r in raw:
    if r['well'] in seen:
        dup_removed += 1
        continue
    seen.add(r['well'])
    clean.append(dict(r))
print(f"[审计] 去重删除行数 = {dup_removed}")

# ---------- 3. 缺失模式标记（不删除、不均值填补） ----------
miss_idx = [i for i, r in enumerate(clean) if r['inhibition'] is None]
print(f"[审计] inhibition 缺失行数 = {len(miss_idx)} (标记为 missing, 不填补)")
for i in miss_idx:
    clean[i]['flag_missing'] = 1
for i, r in enumerate(clean):
    r.setdefault('flag_missing', 0)

# ---------- 4. 业务规则异常识别（标记而非删除） ----------
for r in clean:
    flags = []
    if r['dose_uM'] is not None and r['dose_uM'] < 0:
        flags.append('neg_dose')
    if r['inhibition'] is not None and not (0.0 <= r['inhibition'] <= 1.0):
        flags.append('out_of_range')
    r['flag_anomaly'] = ';'.join(flags) if flags else ''
n_anom = sum(1 for r in clean if r['flag_anomaly'])
print(f"[审计] 业务规则异常行数 = {n_anom}")

# ---------- 5. 单位统一：剂量统一为 log10 μM ----------
# 规则：dose_uM 保留原值，新增 dose_log10uM；负剂量置空并标记
for r in clean:
    d = r['dose_uM']
    if d is None or d < 0:
        r['dose_log10uM'] = None
    else:
        r['dose_log10uM'] = round(float(np.log10(d + 1e-9)), 4)
print("[审计] 剂量单位统一为 log10 μM（dose_log10uM），负剂量置空")

# ---------- 6. 分布变化对比（清洗前后） ----------
def dist(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return (0, 0, 0)
    return (round(float(np.min(v)), 3), round(float(np.mean(v)), 3), round(float(np.max(v)), 3))

before = dist([r['inhibition'] for r in raw])
after = dist([r['inhibition'] for r in clean])
print(f"inhibition 分布 清洗前(min/mean/max) = {before}")
print(f"inhibition 分布 清洗后(min/mean/max) = {after}")

# ---------- 7. 数据字典 ----------
data_dict = [
    ('exp_id', '实验批次编号', 'str', '-'),
    ('well', '孔主键(唯一)', 'str', '-'),
    ('dose_uM', '原始剂量', 'float', 'μM'),
    ('dose_log10uM', '统一剂量', 'float', 'log10 μM'),
    ('inhibition', '抑制率', 'float', '0-1 小数'),
    ('flag_missing', '缺失标记', 'int', '1=缺失'),
    ('flag_anomaly', '异常标记', 'str', '业务规则'),
]
print("数据字典:")
for f in data_dict:
    print("  ", f)

# ---------- 8. 落盘 ----------
out_fields = ['exp_id', 'well', 'dose_uM', 'dose_log10uM',
              'inhibition', 'flag_missing', 'flag_anomaly']
with open('clean_dose_response.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=out_fields)
    w.writeheader()
    for r in clean:
        w.writerow({k: r.get(k, '') for k in out_fields})

with open('audit_log.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['step', 'action', 'rows_affected', 'reason'])
    w.writerow(['1', '去重', dup_removed, '主键 well 重复'])
    w.writerow(['2', '缺失标记', len(miss_idx), '不删除不填补，避免选择偏差'])
    w.writerow(['3', '异常标记', n_anom, '业务规则: 负剂量/越界'])
    w.writerow(['4', '单位统一', len(clean), 'dose_uM -> log10 μM'])

# ---------- 9. 可视化 ----------
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
doses = sorted(set(r['dose_uM'] for r in clean if r['dose_uM'] is not None and r['dose_uM'] >= 0))
means, stds = [], []
for d in doses:
    vals = [r['inhibition'] for r in clean
            if r['dose_uM'] == d and r['inhibition'] is not None
            and 0 <= r['inhibition'] <= 1]
    means.append(np.mean(vals) if vals else np.nan)
    stds.append(np.std(vals) if vals else np.nan)
axes[0].errorbar(doses, means, yerr=stds, marker='o', capsize=4, color='steelblue')
axes[0].set_xscale('symlog', linthresh=0.1)
axes[0].set_xlabel('剂量 (μM)')
axes[0].set_ylabel('抑制率 (0-1)')
axes[0].set_title('剂量-反应曲线 (模拟数据)')
axes[0].grid(alpha=0.3)

inh = [r['inhibition'] for r in clean if r['inhibition'] is not None]
axes[1].hist(inh, bins=12, color='salmon', edgecolor='k', alpha=0.8)
axes[1].set_xlabel('抑制率 (0-1)')
axes[1].set_ylabel('频数')
axes[1].set_title('抑制率分布 (模拟数据)')
axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("已保存: clean_dose_response.csv, audit_log.csv, figure.png")