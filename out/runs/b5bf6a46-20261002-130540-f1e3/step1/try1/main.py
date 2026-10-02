import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv
import os

# ============================================================
# 模拟数据生成（明确标注：以下为模拟数据，非真实实验结论）
# ============================================================
rng = np.random.default_rng(42)
N = 120
# 剂量单位混杂：部分为 uM，部分为 log10(uM)
dose_raw = np.concatenate([
    rng.uniform(0.1, 100, 80),          # uM
    rng.uniform(-1, 2, 40)              # log10(uM)
])
dose_unit = ['uM'] * 80 + ['log10(uM)'] * 40
# 抑制率：部分为 0-1 小数，部分为百分数(0-100)
inh_raw = np.concatenate([
    rng.uniform(0, 1, 90),
    rng.uniform(0, 100, 30)
])
inh_unit = ['fraction'] * 90 + ['percent'] * 30
# 主键：compound_id + well
compound_ids = [f'C{i:03d}' for i in rng.integers(1, 6, N)]
wells = [f'{r}{c}' for r in 'ABCD' for c in range(1, 7)]
well_col = [wells[i % len(wells)] for i in range(N)]

# 注入问题：重复孔、缺失、异常点
inh_raw = inh_raw.astype(float)
inh_raw[5] = np.nan          # 随机缺失
inh_raw[10] = np.nan         # 随机缺失
inh_raw[15] = np.nan         # 随机缺失
inh_raw[20] = 1.5            # 异常：抑制率 >1
inh_raw[25] = -0.3           # 异常：抑制率 <0
dose_raw[30] = -5.0          # 异常：负剂量
dose_raw[35] = np.nan        # 剂量缺失

# 构造重复主键（compound_id + well 重复）
compound_ids[40] = compound_ids[0]
well_col[40] = well_col[0]

# ============================================================
# 写入原始 CSV
# ============================================================
raw_path = 'raw_dose_response.csv'
with open(raw_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['compound_id', 'well', 'dose', 'dose_unit', 'inhibition', 'inhibition_unit'])
    for i in range(N):
        w.writerow([compound_ids[i], well_col[i], dose_raw[i], dose_unit[i],
                    inh_raw[i], inh_unit[i]])
print(f'[模拟数据] 原始表已写入 {raw_path}，共 {N} 行')

# ============================================================
# 审计日志
# ============================================================
audit = []
def log(step, reason, affected, before, after):
    audit.append({'step': step, 'reason': reason, 'affected_rows': affected,
                  'before': before, 'after': after})
    print(f'[审计] {step} | 原因: {reason} | 影响行数: {affected} | 前: {before} | 后: {after}')

# ============================================================
# 1. 读取与结构探查
# ============================================================
rows = []
with open(raw_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)
print(f'\n[结构探查] 总行数: {len(rows)}')
print(f'[结构探查] 字段: {list(rows[0].keys())}')

# 主键唯一性检查
keys = [(r['compound_id'], r['well']) for r in rows]
dup_keys = set(k for k in keys if keys.count(k) > 1)
print(f'[主键检查] 重复主键数: {len(dup_keys)} -> {sorted(dup_keys)[:5]}')
log('主键唯一性检查', 'compound_id+well 应唯一', len(dup_keys),
    f'{len(rows)}行', f'{len(dup_keys)}个重复主键')

# ============================================================
# 2. 单位统一：剂量 -> uM，抑制率 -> 0-1 小数
# ============================================================
dose_uM = []
for r in rows:
    d = float(r['dose']) if r['dose'] not in ('', 'nan') else np.nan
    if r['dose_unit'] == 'log10(uM)' and not np.isnan(d):
        d = 10 ** d
    dose_uM.append(d)

inh_frac = []
for r in rows:
    v = float(r['inhibition']) if r['inhibition'] not in ('', 'nan') else np.nan
    if r['inhibition_unit'] == 'percent' and not np.isnan(v):
        v = v / 100.0
    inh_frac.append(v)

n_dose_conv = sum(1 for r in rows if r['dose_unit'] == 'log10(uM)')
n_inh_conv = sum(1 for r in rows if r['inhibition_unit'] == 'percent')
log('剂量单位统一', 'log10(uM)->uM', n_dose_conv, 'log10(uM)', 'uM')
log('抑制率单位统一', 'percent->fraction', n_inh_conv, 'percent', 'fraction')

# ============================================================
# 3. 缺失模式标记（不删除！）
# ============================================================
miss_dose = [i for i, d in enumerate(dose_uM) if np.isnan(d)]
miss_inh = [i for i, v in enumerate(inh_frac) if np.isnan(v)]
print(f'\n[缺失模式] 剂量缺失: {len(miss_dose)} 行, 抑制率缺失: {len(miss_inh)} 行')
print(f'[缺失模式] 缺失行索引: dose={miss_dose}, inh={miss_inh}')
print('[缺失模式] 判定: 缺失比例低(<5%)，标记为缺失但不删除，避免选择偏差')
log('缺失模式标记', '标记缺失不删除，避免选择偏差',
    len(miss_dose) + len(miss_inh), '未标记', '标记为 missing')

# ============================================================
# 4. 业务规则异常识别（标记而非删除）
# ============================================================
flags = ['ok'] * len(rows)
for i in range(len(rows)):
    d = dose_uM[i]
    v = inh_frac[i]
    reasons = []
    if not np.isnan(d) and d <= 0:
        reasons.append('dose<=0')
    if not np.isnan(v) and (v < 0 or v > 1):
        reasons.append('inh_out_of_0_1')
    if reasons:
        flags[i] = ';'.join(reasons)

n_anom = sum(1 for f in flags if f != 'ok')
print(f'\n[异常识别] 业务规则标记异常行数: {n_anom}')
for i, f in enumerate(flags):
    if f != 'ok':
        print(f'  行{i}: {f} (dose={dose_uM[i]}, inh={inh_frac[i]})')
log('业务规则异常标记', 'dose<=0 或 inh不在[0,1]，标记不删除', n_anom,
    '未标记', f'{n_anom}行标记异常')

# ============================================================
# 5. 重复孔处理：保留首次出现，后续标记为 duplicate
# ============================================================
seen = set()
dup_flag = [''] * len(rows)
for i, k in enumerate(keys):
    if k in seen:
        dup_flag[i] = 'duplicate'
    else:
        seen.add(k)
n_dup = sum(1 for d in dup_flag if d == 'duplicate')
print(f'\n[重复孔] 标记重复行数: {n_dup}')
log('重复孔标记', 'compound_id+well 重复，保留首次，后续标记', n_dup,
    f'{len(rows)}行', f'{n_dup}行标记duplicate')

# ============================================================
# 6. 输出干净数据表（含标记列，不删除任何行）
# ============================================================
clean_path = 'clean_dose_response.csv'
with open(clean_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['compound_id', 'well', 'dose_uM', 'inhibition_frac',
                'missing_flag', 'anomaly_flag', 'duplicate_flag'])
    for i in range(len(rows)):
        mf = []
        if i in miss_dose:
            mf.append('dose_missing')
        if i in miss_inh:
            mf.append('inh_missing')
        w.writerow([rows[i]['compound_id'], rows[i]['well'],
                    dose_uM[i], inh_frac[i],
                    ';'.join(mf) if mf else 'ok',
                    flags[i], dup_flag[i]])
print(f'\n[输出] 干净数据表已写入 {clean_path}，共 {len(rows)} 行（未删除任何行）')

# ============================================================
# 7. 审计日志落盘
# ============================================================
audit_path = 'audit_log.csv'
with open(audit_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['step', 'reason', 'affected_rows', 'before', 'after'])
    w.writeheader()
    for a in audit:
        w.writerow(a)
print(f'[输出] 审计日志已写入 {audit_path}，共 {len(audit)} 条')

# ============================================================
# 8. 数据字典
# ============================================================
dict_path = 'data_dictionary.csv'
with open(dict_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['字段', '口径', '单位', '说明'])
    w.writerow(['compound_id', '化合物编号', '-', '主键之一'])
    w.writerow(['well', '孔位', '-', '主键之一'])
    w.writerow(['dose_uM', '统一后剂量', 'μM', 'log10(uM)已转10^x'])
    w.writerow(['inhibition_frac', '统一后抑制率', '0-1小数', 'percent已除100'])
    w.writerow(['missing_flag', '缺失标记', '-', 'dose_missing/inh_missing/ok'])
    w.writerow(['anomaly_flag', '异常标记', '-', '业务规则标记，不删除'])
    w.writerow(['duplicate_flag', '重复标记', '-', 'duplicate表示重复孔'])
print(f'[输出] 数据字典已写入 {dict_path}')

# ============================================================
# 9. 分布变化解释 + 图
# ============================================================
valid_dose = [d for d in dose_uM if not np.isnan(d)]
valid_inh = [v for v in inh_frac if not np.isnan(v)]
print(f'\n[分布] 剂量(μM): n={len(valid_dose)}, min={min(valid_dose):.3f}, '
      f'max={max(valid_dose):.3f}, mean={np.mean(valid_dose):.3f}')
print(f'[分布] 抑制率(0-1): n={len(valid_inh)}, min={min(valid_inh):.3f}, '
      f'max={max(valid_inh):.3f}, mean={np.mean(valid_inh):.3f}')
print('[分布解释] 单位统一后剂量跨度增大(log10->uM)，抑制率统一到0-1区间')

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
axes[0].hist(valid_dose, bins=20, color='steelblue', edgecolor='black')
axes[0].set_title('统一后剂量分布 (μM)')
axes[0].set_xlabel('剂量 (μM)')
axes[0].set_ylabel('频数')
axes[1].hist(valid_inh, bins=20, color='salmon', edgecolor='black')
axes[1].set_title('统一后抑制率分布 (0-1)')
axes[1].set_xlabel('抑制率')
axes[1].set_ylabel('频数')
plt.tight_layout()
plt.savefig('figure.png', dpi=100)
print('[输出] 图已保存 figure.png')

# ============================================================
# 10. 验收清单打印
# ============================================================
print('\n===== 验收清单 =====')
print(f'1. 清洗后主键唯一: {len(seen)} 个唯一主键 / {len(rows)} 行')
print(f'2. 审计日志可复现: {len(audit)} 条记录已落盘')
print(f'3. 关键字段分布变化: 剂量单位统一{n_dose_conv}行, 抑制率统一{n_inh_conv}行')
print(f'4. 缺失未删除: {len(miss_dose)+len(miss_inh)} 行标记保留')
print(f'5. 异常未删除: {n_anom} 行标记保留')
print(f'6. 重复孔未删除: {n_dup} 行标记保留')