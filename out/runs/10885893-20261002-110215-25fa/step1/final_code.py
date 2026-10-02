# -*- coding: utf-8 -*-
"""
剂量-响应数据清洗与审计（模拟数据，非真实实验结论）
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

rng = np.random.default_rng(42)

# ---------- 1. 构造模拟原始数据（模拟数据，非真实实验） ----------
# 列: exp_id, compound, dose_raw, dose_unit, inhibition_raw, replicate
n = 240
compounds = ['CmpA', 'CmpB', 'CmpC']
units = ['uM', 'nM', 'mM']
rows = []
for i in range(n):
    c = compounds[i % 3]
    u = units[i % 3]
    if u == 'uM':
        dose = float(rng.choice([0.1, 1, 3, 10, 30, 100]))
    elif u == 'nM':
        dose = float(rng.choice([100, 1000, 3000, 10000, 30000, 100000]))
    else:
        dose = float(rng.choice([0.0001, 0.001, 0.003, 0.01, 0.03, 0.1]))
    # 抑制率 0-1 小数
    inh = 1.0 / (1.0 + np.exp(-(np.log10(dose * (1e-3 if u == 'nM' else (1e3 if u == 'mM' else 1.0))) + 1.5)))
    inh = float(np.clip(inh + rng.normal(0, 0.05), 0, 1))
    rows.append([f'E{i:04d}', c, dose, u, inh, (i % 3) + 1])

# 注入问题：缺失、重复孔、异常点、单位混用
rows[5][4] = np.nan                      # 随机缺失
rows[10][4] = np.nan
rows[15][4] = np.nan
rows[20][4] = np.nan
rows[30][4] = np.nan
rows[40][4] = np.nan
rows[50][4] = np.nan
rows[60][4] = np.nan
rows[70][4] = np.nan
rows[80][4] = np.nan
rows[90][4] = np.nan
rows[100][4] = np.nan
rows[110][4] = np.nan
rows[120][4] = np.nan
rows[130][4] = np.nan
rows[140][4] = np.nan
rows[150][4] = np.nan
rows[160][4] = np.nan
rows[170][4] = np.nan
rows[180][4] = np.nan
rows[190][4] = np.nan
rows[200][4] = np.nan
rows[210][4] = np.nan
rows[220][4] = np.nan
rows[230][4] = np.nan
rows[25][4] = 1.8                        # 异常点（>1）
rows[35][4] = -0.3                       # 异常点（<0）
rows[45][4] = 2.5                        # 异常点
rows[55][4] = -1.0                       # 异常点
rows[65][4] = 1.5                        # 异常点
rows[75][4] = -0.5                       # 异常点
rows[85][4] = 3.0                        # 异常点
rows[95][4] = -2.0                       # 异常点
rows[105][4] = 1.2                       # 异常点
rows[115][4] = -0.8                      # 异常点
rows[125][4] = 2.0                       # 异常点
rows[135][4] = -1.5                      # 异常点
rows[145][4] = 1.1                       # 异常点
rows[155][4] = -0.2                      # 异常点
rows[165][4] = 1.9                       # 异常点
rows[175][4] = -0.9                      # 异常点
rows[185][4] = 2.2                       # 异常点
rows[195][4] = -1.2                      # 异常点
rows[205][4] = 1.4                       # 异常点
rows[215][4] = -0.6                      # 异常点
rows[225][4] = 2.8                       # 异常点
rows[235][4] = -1.8                      # 异常点
rows.append(rows[0][:])                  # 重复孔（完全重复）
rows.append(rows[1][:])                  # 重复孔

raw = np.array(rows, dtype=object)
cols = ['exp_id', 'compound', 'dose_raw', 'dose_unit', 'inhibition_raw', 'replicate']

# ---------- 2. 结构与类型探查 ----------
print("=== 1. 结构与类型探查（模拟数据） ===")
print(f"原始行数: {raw.shape[0]}, 列数: {raw.shape[1]}")
print(f"列名: {cols}")
for j, c in enumerate(cols):
    vals = raw[:, j]
    n_missing = sum(1 for v in vals if v is None or (isinstance(v, float) and np.isnan(v)))
    print(f"  {c}: 缺失={n_missing}")

# 主键唯一性（exp_id + replicate 作为孔级主键）
keys = [f"{r[0]}|{r[5]}" for r in raw]
dup_keys = set([k for k in keys if keys.count(k) > 1])
print(f"孔级主键重复数: {len(dup_keys)} -> {sorted(dup_keys)}")

# ---------- 3. 单位统一为 μM ----------
print("\n=== 2. 单位统一为 μM ===")
unit_factor = {'uM': 1.0, 'nM': 1e-3, 'mM': 1e3}
dose_uM = []
for r in raw:
    dose_uM.append(float(r[2]) * unit_factor[r[3]])
dose_uM = np.array(dose_uM)
print(f"单位分布: {dict(zip(*np.unique(raw[:,3], return_counts=True)))}")
print(f"统一后剂量范围: [{dose_uM.min():.6g}, {dose_uM.max():.6g}] μM")

# ---------- 4. 缺失模式 ----------
print("\n=== 3. 缺失模式 ===")
inh = np.array([np.nan if (v is None or (isinstance(v, float) and np.isnan(v))) else float(v) for v in raw[:, 4]])
miss_mask = np.isnan(inh)
print(f"抑制率缺失数: {miss_mask.sum()} / {len(inh)} ({miss_mask.mean()*100:.1f}%)")
# 按化合物看缺失是否随机
for c in compounds:
    idx = np.array([r[1] == c for r in raw])
    print(f"  {c}: 缺失率={miss_mask[idx].mean()*100:.1f}%")
print("结论: 各化合物缺失率接近 -> 倾向随机缺失(MAR)，不删除、不均值填补")

# ---------- 5. 异常点识别（业务规则：抑制率须在[0,1]） ----------
print("\n=== 4. 异常点识别（业务规则） ===")
outlier_mask = (~miss_mask) & ((inh < 0) | (inh > 1))
print(f"越界异常点数: {outlier_mask.sum()}")
print(f"  低于0: {((~miss_mask) & (inh < 0)).sum()}, 高于1: {((~miss_mask) & (inh > 1)).sum()}")
print("处理: 标记为 outlier 而非删除（避免选择偏差）")

# ---------- 6. 组装干净表 ----------
clean = []
for i, r in enumerate(raw):
    flag = []
    if miss_mask[i]:
        flag.append('missing')
    if outlier_mask[i]:
        flag.append('outlier')
    clean.append([
        r[0], r[1], float(r[2]), r[3], dose_uM[i],
        np.log10(dose_uM[i]) if dose_uM[i] > 0 else np.nan,
        inh[i], r[5], ';'.join(flag) if flag else 'ok'
    ])
clean_cols = ['exp_id', 'compound', 'dose_raw', 'dose_unit', 'dose_uM',
              'log10_dose_uM', 'inhibition', 'replicate', 'qc_flag']

# 去重（保留首次出现）
seen = set()
dedup = []
for row in clean:
    k = f"{row[0]}|{row[7]}"
    if k in seen:
        continue
    seen.add(k)
    dedup.append(row)
print(f"\n=== 5. 去重 ===")
print(f"去重前: {len(clean)} 行, 去重后: {len(dedup)} 行, 移除: {len(clean)-len(dedup)} 行")

# 主键唯一性复核
keys2 = [f"{r[0]}|{r[7]}" for r in dedup]
print(f"清洗后主键唯一: {len(keys2) == len(set(keys2))}")

# ---------- 7. 分布变化 ----------
print("\n=== 6. 关键字段分布变化 ===")
valid_before = inh[~miss_mask]
valid_after = np.array([r[6] for r in dedup if r[8] == 'ok'])
print(f"抑制率(有效) 清洗前: n={len(valid_before)}, mean={np.nanmean(valid_before):.4f}, std={np.nanstd(valid_before):.4f}")
print(f"抑制率(ok)   清洗后: n={len(valid_after)}, mean={np.nanmean(valid_after):.4f}, std={np.nanstd(valid_after):.4f}")
print(f"异常点被标记未删除: {sum(1 for r in dedup if 'outlier' in r[8])} 行")

# ---------- 8. 审计日志 ----------
audit = [
    ['step', 'action', 'rows_affected', 'reason'],
    [1, 'unit_convert_to_uM', len(dedup), '统一剂量单位'],
    [2, 'dedup_by_exp_id_replicate', len(clean) - len(dedup), '重复孔'],
    [3, 'flag_missing', int(miss_mask.sum()), '缺失标记不删除'],
    [4, 'flag_outlier', int(outlier_mask.sum()), '业务规则[0,1]越界标记'],
]

# ---------- 9. 出图 ----------
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
axes[0].hist(valid_before, bins=20, alpha=0.6, label='清洗前(有效)', color='steelblue')
axes[0].hist(valid_after, bins=20, alpha=0.6, label='清洗后(ok)', color='orange')
axes[0].set_xlabel('抑制率'); axes[0].set_ylabel('频数')
axes[0].set_title('抑制率分布对比（模拟数据）'); axes[0].legend()

ok = [r for r in dedup if r[8] == 'ok']
xs = np.array([r[5] for r in ok]); ys = np.array([r[6] for r in ok])
axes[1].scatter(xs, ys, s=12, alpha=0.6, color='green')
axes[1].set_xlabel('log10(剂量 μM)'); axes[1].set_ylabel('抑制率')
axes[1].set_title('剂量-响应（清洗后，模拟数据）')
plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n图已保存: figure.png")

# ---------- 10. 落盘 ----------
with open('clean_data.csv', 'w', encoding='utf-8') as f:
    f.write(','.join(clean_cols) + '\n')
    for r in dedup:
        f.write(','.join(['' if (isinstance(v, float) and np.isnan(v)) else str(v) for v in r]) + '\n')

with open('audit_log.csv', 'w', encoding='utf-8') as f:
    for row in audit:
        f.write(','.join(str(x) for x in row) + '\n')

with open('data_dictionary.csv', 'w', encoding='utf-8') as f:
    f.write('field,unit,description\n')
    f.write('exp_id,-,实验编号\n')
    f.write('compound,-,化合物名\n')
    f.write('dose_raw,原始单位,原始剂量\n')
    f.write('dose_unit,-,原始单位(uM/nM/mM)\n')
    f.write('dose_uM,μM,统一剂量\n')
    f.write('log10_dose_uM,log10(μM),对数剂量\n')
    f.write('inhibition,0-1,抑制率小数\n')
    f.write('replicate,-,复孔编号\n')
    f.write('qc_flag,-,ok/missing/outlier\n')

print("已保存: clean_data.csv, audit_log.csv, data_dictionary.csv")
print("\n注: 以上均为模拟数据，不代表真实实验结论。")