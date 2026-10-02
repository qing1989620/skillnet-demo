import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv
import os

# ============================================================
# 说明：本脚本使用【模拟数据】演示剂量-存活率数据清洗流程。
# 所有数值均为人工构造，不代表任何真实实验结果。
# ============================================================

np.random.seed(42)

# ---------- 1. 构造模拟原始数据 ----------
# 字段: exp_id(实验批次), well_id(孔位), dose_uM(剂量), survival(存活率0-1), replicate(重复)
n = 120
exp_ids = np.repeat(['E1', 'E2', 'E3'], 40)
wells = [f'{r}{c}' for r in 'ABCDEFGH' for c in range(1, 6)][:40] * 3
doses = np.tile(np.array([0.0, 0.1, 1.0, 10.0, 100.0] * 8), 3)
survival = 1.0 / (1.0 + doses / 5.0) + np.random.normal(0, 0.05, n)
survival = np.clip(survival, 0, 1)

# 注入问题：缺失、异常、重复孔
survival[5] = np.nan          # 随机缺失
survival[10] = np.nan
survival[15] = np.nan
survival[20] = 1.8            # 越界异常
survival[25] = -0.3           # 越界异常
doses[30] = -1.0              # 负剂量异常
wells[35] = wells[0]          # 重复孔（主键冲突）

raw = {
    'exp_id': exp_ids,
    'well_id': wells,
    'dose_uM': doses,
    'survival': survival,
}

# ---------- 2. 结构与类型探查 ----------
print('=== 步骤1: 结构与类型探查 ===')
print(f'总行数: {n}')
for k, v in raw.items():
    print(f'  字段 {k}: dtype={np.array(v).dtype}, 非空={np.sum([x is not None and not (isinstance(x,float) and np.isnan(x)) for x in v])}')

# 主键唯一性检查 (exp_id + well_id)
keys = list(zip(raw['exp_id'], raw['well_id']))
from collections import Counter
key_counts = Counter(keys)
dup_keys = {k: c for k, c in key_counts.items() if c > 1}
print(f'主键(exp_id+well_id)重复数: {len(dup_keys)}')
for k, c in dup_keys.items():
    print(f'  重复主键 {k}: 出现 {c} 次')

# ---------- 3. 缺失模式标记 ----------
print('\n=== 步骤2: 缺失模式标记 ===')
surv_arr = np.array(raw['survival'], dtype=float)
dose_arr = np.array(raw['dose_uM'], dtype=float)
miss_mask = np.isnan(surv_arr)
print(f'survival 缺失行数: {miss_mask.sum()} / {n} ({miss_mask.sum()/n*100:.1f}%)')
# 检查缺失是否与剂量相关（非随机缺失判断）
if miss_mask.sum() > 0:
    miss_doses = dose_arr[miss_mask]
    obs_doses = dose_arr[~miss_mask]
    print(f'  缺失行剂量均值: {np.nanmean(miss_doses):.3f}, 观测行剂量均值: {np.nanmean(obs_doses):.3f}')
    print(f'  -> 缺失与剂量{"可能相关(非随机)" if abs(np.nanmean(miss_doses)-np.nanmean(obs_doses))>1 else "近似随机"}')
print('  规避措施: 不删除缺失行，仅标记，避免选择偏差')

# ---------- 4. 业务规则异常识别 ----------
print('\n=== 步骤3: 业务规则异常识别 ===')
anomaly_flags = np.zeros(n, dtype=int)
anomaly_reasons = [''] * n

# 规则1: 存活率必须在 [0,1]
mask_surv = (~np.isnan(surv_arr)) & ((surv_arr < 0) | (surv_arr > 1))
anomaly_flags[mask_surv] = 1
for i in np.where(mask_surv)[0]:
    anomaly_reasons[i] = f'survival={surv_arr[i]:.2f}越界[0,1]'

# 规则2: 剂量必须 >= 0
mask_dose = dose_arr < 0
anomaly_flags[mask_dose] = 1
for i in np.where(mask_dose)[0]:
    anomaly_reasons[i] = (anomaly_reasons[i] + ';' if anomaly_reasons[i] else '') + f'dose={dose_arr[i]:.2f}<0'

# 规则3: 重复孔标记
for i, k in enumerate(keys):
    if key_counts[k] > 1:
        anomaly_flags[i] = 1
        anomaly_reasons[i] = (anomaly_reasons[i] + ';' if anomaly_reasons[i] else '') + '重复孔'

print(f'异常点总数: {anomaly_flags.sum()} (标记而非删除)')
for i in np.where(anomaly_flags)[0]:
    print(f'  行{i}: {anomaly_reasons[i]}')

# ---------- 5. 单位统一 ----------
print('\n=== 步骤4: 单位统一 ===')
# 剂量统一为 log10(μM+1) 便于分析，同时保留原始 μM
dose_log = np.where(dose_arr >= 0, np.log10(dose_arr + 1), np.nan)
print(f'剂量单位: μM -> log10(μM+1)')
print(f'  原始剂量范围: [{np.nanmin(dose_arr):.2f}, {np.nanmax(dose_arr):.2f}] μM')
print(f'  log10范围: [{np.nanmin(dose_log):.3f}, {np.nanmax(dose_log):.3f}]')
print(f'存活率范围: [{np.nanmin(surv_arr):.3f}, {np.nanmax(surv_arr):.3f}] (0-1小数)')

# ---------- 6. 审计日志 ----------
print('\n=== 步骤5: 审计日志 ===')
audit = []
audit.append(('原始行数', n))
audit.append(('主键重复数', len(dup_keys)))
audit.append(('缺失行数', int(miss_mask.sum())))
audit.append(('异常标记数', int(anomaly_flags.sum())))
audit.append(('删除行数', 0))
audit.append(('清洗后行数', n))
for a in audit:
    print(f'  {a[0]}: {a[1]}')
print('  关键字段分布变化: 未删除任何行，分布不变；异常点仅标记')

# ---------- 7. 输出干净数据表 ----------
clean_rows = []
for i in range(n):
    clean_rows.append({
        'exp_id': raw['exp_id'][i],
        'well_id': raw['well_id'][i],
        'dose_uM': dose_arr[i],
        'dose_log10': dose_log[i],
        'survival': surv_arr[i],
        'is_missing': int(miss_mask[i]),
        'is_anomaly': int(anomaly_flags[i]),
        'anomaly_reason': anomaly_reasons[i],
    })

# ---------- 8. 出图 ----------
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
# 左图: 剂量-存活率散点（标记异常）
ok = (~miss_mask) & (anomaly_flags == 0)
axes[0].scatter(dose_log[ok], surv_arr[ok], c='steelblue', label='正常点', alpha=0.7)
if anomaly_flags.sum() > 0:
    axes[0].scatter(dose_log[anomaly_flags == 1], surv_arr[anomaly_flags == 1],
                    c='red', marker='x', s=80, label='异常点(标记)')
axes[0].set_xlabel('log10(剂量+1) [μM]')
axes[0].set_ylabel('存活率')
axes[0].set_title('剂量-存活率散点（模拟数据）')
axes[0].legend()
axes[0].grid(alpha=0.3)

# 右图: 缺失与异常统计
cats = ['正常', '缺失', '异常']
vals = [int((~miss_mask & (anomaly_flags == 0)).sum()), int(miss_mask.sum()), int(anomaly_flags.sum())]
axes[1].bar(cats, vals, color=['steelblue', 'orange', 'red'])
axes[1].set_ylabel('行数')
axes[1].set_title('数据质量分布（模拟数据）')
for i, v in enumerate(vals):
    axes[1].text(i, v + 0.5, str(v), ha='center')
plt.tight_layout()
plt.savefig('figure.png', dpi=100)
print('\n图已保存: figure.png')

# ---------- 9. 落盘 ----------
with open('clean_data.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=list(clean_rows[0].keys()))
    writer.writeheader()
    writer.writerows(clean_rows)
print('干净数据已保存: clean_data.csv')

with open('audit_log.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['项目', '数值'])
    writer.writerows(audit)
print('审计日志已保存: audit_log.csv')

# 数据字典
data_dict = [
    ('exp_id', '实验批次编号', '字符串'),
    ('well_id', '孔位编号', '字符串'),
    ('dose_uM', '剂量', 'μM'),
    ('dose_log10', '剂量对数变换', 'log10(μM+1)'),
    ('survival', '存活率', '0-1小数'),
    ('is_missing', '是否缺失', '0/1'),
    ('is_anomaly', '是否异常', '0/1'),
    ('anomaly_reason', '异常原因', '字符串'),
]
with open('data_dictionary.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['字段', '口径', '单位'])
    writer.writerows(data_dict)
print('数据字典已保存: data_dictionary.csv')