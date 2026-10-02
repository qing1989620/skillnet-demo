# -*- coding: utf-8 -*-
"""
剂量-响应数据清洗与审计（模拟数据，非真实实验结论）
仅使用 numpy + matplotlib
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

rng = np.random.default_rng(42)

# ---------------- 1. 构造原始数据（模拟数据） ----------------
# 原始剂量单位混杂：nM / ug/mL / uM
raw_dose = np.array([0, 0, 0, 1, 1, 1, 10, 10, 10, 100, 100, 100,
                     1000, 1000, 1000, 10000, 10000, 10000,
                     1, 10, 100, 1000, 100, 100], dtype=float)
raw_unit = ['uM']*18 + ['nM', 'nM', 'nM', 'nM', 'ug/mL', 'ug/mL']
# 抑制率：部分以百分数给出（>1），部分为小数
raw_inhib = np.array([0.02, 0.05, 0.01, 0.12, 0.15, 0.11, 0.30, 0.33, 0.28,
                      0.55, 0.58, 0.52, 0.78, 0.80, 0.75, 0.92, 0.94, 0.90,
                      0.10, 0.29, 0.53, 0.77, 55.0, 58.0], dtype=float)
raw_rep = [1, 2, 3]*8
raw_grp = ['A']*12 + ['B']*12
# 注入缺失与异常
raw_inhib = raw_inhib.copy()
raw_inhib[5] = np.nan          # 随机缺失
raw_inhib[19] = np.nan         # 非随机缺失（低剂量组系统性缺失）
raw_inhib[13] = 1.85           # 业务异常：抑制率>1 且非百分数口径
raw_dose[22] = -100.0          # 业务异常：负剂量

raw = {'dose': raw_dose, 'unit': raw_unit, 'inhib': raw_inhib,
       'replicate': raw_rep, 'group': raw_grp}
n_raw = len(raw['dose'])
print("=== 模拟数据（非真实实验结论）===")
print(f"原始行数: {n_raw}")

# ---------------- 2. 单位统一为 uM ----------------
# 换算规则：1 nM = 1e-3 uM；1 ug/mL 按分子量 300 g/mol 近似 -> 1 ug/mL ≈ 3.333 uM
UNIT_TO_UM = {'uM': 1.0, 'nM': 1e-3, 'ug/mL': 1000.0/300.0}
dose_uM = np.array([d * UNIT_TO_UM[u] for d, u in zip(raw['dose'], raw['unit'])])
print(f"单位换算规则: {UNIT_TO_UM}")

# ---------------- 3. 抑制率统一为 0-1 小数 ----------------
inhib = raw['inhib'].copy()
pct_mask = np.isfinite(inhib) & (inhib > 1.0) & (inhib <= 100.0)
n_pct = int(pct_mask.sum())
inhib[pct_mask] = inhib[pct_mask] / 100.0
print(f"百分数口径转小数: {n_pct} 行")

# ---------------- 4. 主键唯一性检查 ----------------
key = list(zip(dose_uM, raw['replicate'], raw['group']))
seen, dup_idx = {}, []
for i, k in enumerate(key):
    if k in seen:
        dup_idx.append(i)
    else:
        seen[k] = i
print(f"主键(dose×replicate×group)重复行数: {len(dup_idx)} -> {dup_idx}")

# ---------------- 5. 缺失模式 ----------------
miss = ~np.isfinite(inhib)
print(f"抑制率缺失行数: {int(miss.sum())}, 索引: {np.where(miss)[0].tolist()}")
# 区分随机/非随机：按剂量分层看缺失率
for d in np.unique(dose_uM):
    m = dose_uM == d
    if m.sum() > 0:
        rate = miss[m].mean()
        if rate > 0:
            print(f"  剂量 {d:.4g} uM 缺失率 {rate:.2f}")

# ---------------- 6. 业务规则异常标记（不删除） ----------------
flag = np.array(['ok'] * n_raw, dtype=object)
flag[dose_uM < 0] = 'dose_negative'
flag[np.isfinite(inhib) & ((inhib < 0) | (inhib > 1))] = 'inhib_out_of_range'
flag[miss] = 'missing_inhib'
print("异常/缺失标记统计:")
for f in np.unique(flag):
    print(f"  {f}: {int((flag == f).sum())}")

# ---------------- 7. 清洗后数据表（保留全部行，仅加标记） ----------------
log10dose = np.where(dose_uM > 0, np.log10(np.where(dose_uM > 0, dose_uM, 1)), np.nan)
clean = {
    'dose_uM': dose_uM, 'log10_dose': log10dose,
    'inhib_frac': inhib, 'replicate': raw['replicate'],
    'group': raw['group'], 'flag': flag,
}
# 清洗后主键唯一性（对有效行）
valid = flag == 'ok'
key_valid = list(zip(dose_uM[valid], raw['replicate'][valid] if False else np.array(raw['replicate'])[valid], np.array(raw['group'])[valid]))
print(f"清洗后有效行主键唯一: {len(key_valid) == len(set(key_valid))}")

# ---------------- 8. 分布变化记录 ----------------
def desc(x):
    x = x[np.isfinite(x)]
    return (len(x), float(np.min(x)), float(np.median(x)), float(np.max(x))) if len(x) else (0, np.nan, np.nan, np.nan)
print("抑制率分布(原始有效): n,min,median,max =", desc(raw['inhib']))
print("抑制率分布(统一口径后): n,min,median,max =", desc(inhib))
print("剂量分布(uM): n,min,median,max =", desc(dose_uM))

# ---------------- 9. 数据字典 ----------------
data_dict = [
    ("dose_uM", "统一后的剂量", "μM", "nM×1e-3; ug/mL×3.333"),
    ("log10_dose", "剂量对数", "log10(μM)", "dose_uM<=0 时为 NaN"),
    ("inhib_frac", "抑制率", "0-1 小数", ">1 且<=100 视为百分数已转小数"),
    ("replicate", "重复孔编号", "整数", "主键组成"),
    ("group", "实验分组", "字符串", "主键组成"),
    ("flag", "清洗标记", "枚举", "ok/missing_inhib/dose_negative/inhib_out_of_range"),
]
print("数据字典:")
for r in data_dict:
    print("  ", r)

# ---------------- 10. 出图 ----------------
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
ok = flag == 'ok'
axes[0].scatter(dose_uM[ok], inhib[ok], c='tab:blue', label='有效点')
bad = ~ok
axes[0].scatter(dose_uM[bad], np.where(np.isfinite(inhib[bad]), inhib[bad], 0.5),
                c='tab:red', marker='x', label='异常/缺失标记')
axes[0].set_xscale('symlog', linthresh=1)
axes[0].set_xlabel('剂量 (μM)'); axes[0].set_ylabel('抑制率 (0-1)')
axes[0].set_title('剂量-抑制率（模拟数据）'); axes[0].legend()
axes[1].hist(inhib[np.isfinite(inhib)], bins=12, color='tab:green', alpha=0.8)
axes[1].set_xlabel('抑制率 (0-1)'); axes[1].set_ylabel('频数')
axes[1].set_title('抑制率分布（统一口径后）')
plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("已保存 figure.png")

# ---------------- 11. 落盘 ----------------
with open('clean_data.csv', 'w', encoding='utf-8') as f:
    f.write("dose_uM,log10_dose,inhib_frac,replicate,group,flag\n")
    for i in range(n_raw):
        f.write(f"{dose_uM[i]},{log10dose[i]},{inhib[i]},{raw['replicate'][i]},{raw['group'][i]},{flag[i]}\n")

with open('audit_log.csv', 'w', encoding='utf-8') as f:
    f.write("step,action,rows_affected,reason\n")
    f.write(f"1,unit_to_uM,{n_raw},统一剂量单位\n")
    f.write(f"2,pct_to_frac,{n_pct},抑制率百分数转小数\n")
    f.write(f"3,dup_check,{len(dup_idx)},主键重复检测\n")
    f.write(f"4,missing_flag,{int(miss.sum())},缺失标记不删除\n")
    f.write(f"5,outlier_flag,{int((flag=='dose_negative').sum()+(flag=='inhib_out_of_range').sum())},业务规则异常标记\n")

with open('data_dictionary.csv', 'w', encoding='utf-8') as f:
    f.write("field,meaning,unit,rule\n")
    for r in data_dict:
        f.write(",".join(map(str, r)) + "\n")

print("已保存 clean_data.csv / audit_log.csv / data_dictionary.csv")