import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

rng = np.random.default_rng(42)

# ============ 1. 生成模拟原始数据（明确标注：模拟数据） ============
# 说明：以下全部为【模拟数据】，非真实实验结论
N = 240
dose_levels = np.array([0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0])
dose = rng.choice(dose_levels, size=N)
# 真实剂量-反应：logistic 存活率
true_surv = 1.0 / (1.0 + np.exp(0.55 * (dose - 4.0)))
surv = rng.binomial(1, true_surv).astype(float)
# 加入连续型存活率字段（重复测量均值）
surv_rate = np.clip(true_surv + rng.normal(0, 0.05, N), 0, 1)

sample_id = np.arange(1, N + 1)
batch = rng.choice(['A', 'B', 'C'], size=N)

raw = {
    'sample_id': sample_id,
    'dose_mg_per_kg': dose,
    'survival_rate': surv_rate,
    'survival_flag': surv,
    'batch': batch,
}

# 注入缺失（随机缺失 MCAR）
miss_idx = rng.choice(N, size=18, replace=False)
raw['survival_rate'] = raw['survival_rate'].astype(float)
raw['survival_rate'][miss_idx] = np.nan
# 注入非随机缺失（高剂量组更易缺失，MNAR）
high_dose_idx = np.where(dose >= 8.0)[0]
mnar_idx = rng.choice(high_dose_idx, size=8, replace=False)
raw['survival_flag'] = raw['survival_flag'].astype(float)
raw['survival_flag'][mnar_idx] = np.nan

# 注入异常值（业务规则：剂量为负、存活率>1 或 <0）
raw['dose_mg_per_kg'] = raw['dose_mg_per_kg'].astype(float)
raw['dose_mg_per_kg'][5] = -1.0
raw['survival_rate'][10] = 1.35
raw['survival_rate'][20] = -0.2

# 重复主键（模拟录入重复）
raw['sample_id'] = raw['sample_id'].astype(int)
raw['sample_id'][30] = raw['sample_id'][29]

print("=" * 60)
print("【模拟数据】原始数据生成完毕，共 %d 行" % N)
print("=" * 60)

# ============ 2. 结构与类型探查 ============
print("\n[步骤1] 结构与类型探查")
print("字段:", list(raw.keys()))
for k, v in raw.items():
    print("  %-18s dtype=%s" % (k, v.dtype))

# 主键唯一性
ids = raw['sample_id']
n_unique = len(np.unique(ids))
print("主键 sample_id: 总行数=%d, 唯一值=%d, 重复=%d" % (len(ids), n_unique, len(ids) - n_unique))

# ============ 3. 缺失模式标记 ============
print("\n[步骤2] 缺失模式分析")
for k in ['survival_rate', 'survival_flag']:
    v = raw[k]
    n_miss = int(np.sum(np.isnan(v)))
    print("  %-16s 缺失=%d (%.1f%%)" % (k, n_miss, 100.0 * n_miss / len(v)))

# 区分 MCAR / MNAR：按剂量分组看缺失率
dose_arr = raw['dose_mg_per_kg']
flag_miss = np.isnan(raw['survival_flag'])
print("  按剂量组 survival_flag 缺失率（判断 MNAR）:")
for d in dose_levels:
    m = dose_arr == d
    if m.sum() > 0:
        print("    dose=%.1f  n=%3d  缺失率=%.1f%%" % (d, m.sum(), 100.0 * flag_miss[m].mean()))

# ============ 4. 业务规则异常值识别 ============
print("\n[步骤3] 业务规则异常值识别")
bad_dose = dose_arr < 0
bad_rate = (~np.isnan(raw['survival_rate'])) & ((raw['survival_rate'] > 1.0) | (raw['survival_rate'] < 0.0))
print("  剂量<0 的行数: %d" % int(bad_dose.sum()))
print("  存活率越界(>1或<0) 的行数: %d" % int(bad_rate.sum()))

# ============ 5. 清洗（记录每步影响） ============
print("\n[步骤4] 清洗执行与审计日志")
audit = []

# 5.1 去重（保留首次出现）
keep = np.ones(N, dtype=bool)
seen = set()
for i, sid in enumerate(ids):
    if sid in seen:
        keep[i] = False
    else:
        seen.add(sid)
n_dup = int((~keep).sum())
audit.append(("去重(保留首次)", n_dup, "主键唯一性要求"))
print("  去重: 删除 %d 行" % n_dup)

# 5.2 异常值置为 NaN（不静默删除，标记后统一处理）
dose_clean = dose_arr.copy()
rate_clean = raw['survival_rate'].copy()
flag_clean = raw['survival_flag'].copy()

n_bad_dose = int(bad_dose.sum())
dose_clean[bad_dose] = np.nan
audit.append(("剂量<0置NaN", n_bad_dose, "业务规则: 剂量不可为负"))

n_bad_rate = int(bad_rate.sum())
rate_clean[bad_rate] = np.nan
audit.append(("存活率越界置NaN", n_bad_rate, "业务规则: 存活率∈[0,1]"))

# 5.3 缺失处理：不做均值填补（规避陷阱）
#     survival_rate 为 MCAR -> 保留 NaN，分析时按可用样本处理
#     survival_flag 为 MNAR -> 保留 NaN，不填补，避免引入偏差
n_miss_rate = int(np.sum(np.isnan(rate_clean)))
n_miss_flag = int(np.sum(np.isnan(flag_clean)))
audit.append(("survival_rate 保留NaN", n_miss_rate, "MCAR, 避免均值填补偏差"))
audit.append(("survival_flag 保留NaN", n_miss_flag, "MNAR, 禁止均值填补"))

# 5.4 应用去重
dose_clean = dose_clean[keep]
rate_clean = rate_clean[keep]
flag_clean = flag_clean[keep]
sid_clean = ids[keep]
batch_clean = raw['batch'][keep]

print("\n  审计日志:")
for step, n, reason in audit:
    print("    - %-24s 影响 %3d 行 | 原因: %s" % (step, n, reason))

# ============ 6. 清洗前后分布对比 ============
print("\n[步骤5] 关键字段分布变化")
def desc(name, arr):
    a = arr[~np.isnan(arr)]
    if len(a) == 0:
        print("  %-16s 无有效值" % name)
        return
    print("  %-16s n=%3d  mean=%.4f  std=%.4f  min=%.4f  max=%.4f"
          % (name, len(a), a.mean(), a.std(), a.min(), a.max()))

print("  清洗前:")
desc("dose", dose_arr)
desc("survival_rate", raw['survival_rate'])
print("  清洗后:")
desc("dose", dose_clean)
desc("survival_rate", rate_clean)

# ============ 7. 落盘 cleaned.csv ============
out = np.column_stack([sid_clean, dose_clean, rate_clean, flag_clean])
header = "sample_id,dose_mg_per_kg,survival_rate,survival_flag"
lines = [header]
for row in out:
    sid = int(row[0])
    d = "" if np.isnan(row[1]) else "%.4f" % row[1]
    r = "" if np.isnan(row[2]) else "%.4f" % row[2]
    f = "" if np.isnan(row[3]) else "%d" % int(row[3])
    lines.append("%d,%s,%s,%s" % (sid, d, r, f))
with open("cleaned.csv", "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

# 数据字典
with open("data_dictionary.csv", "w", encoding="utf-8") as fh:
    fh.write("field,unit,description\n")
    fh.write("sample_id,-,样本唯一标识(主键)\n")
    fh.write("dose_mg_per_kg,mg/kg,给药剂量\n")
    fh.write("survival_rate,ratio,存活率[0,1],MCAR缺失保留为空\n")
    fh.write("survival_flag,0/1,存活标志,MNAR缺失保留为空\n")

# 验收检查
print("\n[验收] 清洗后主键唯一: %s" % (len(np.unique(sid_clean)) == len(sid_clean)))
print("[验收] 清洗后行数: %d (原始 %d)" % (len(sid_clean), N))

# ============ 8. 出图 ============
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

# 左：清洗前后剂量分布
ax = axes[0]
ax.hist(dose_arr[~np.isnan(dose_arr)], bins=15, alpha=0.6, label='清洗前', color='steelblue')
ax.hist(dose_clean[~np.isnan(dose_clean)], bins=15, alpha=0.6, label='清洗后', color='orange')
ax.set_xlabel('剂量 (mg/kg)')
ax.set_ylabel('频数')
ax.set_title('剂量分布：清洗前后对比')
ax.legend()

# 右：剂量-存活率散点（清洗后）
ax = axes[1]
valid = (~np.isnan(dose_clean)) & (~np.isnan(rate_clean))
ax.scatter(dose_clean[valid], rate_clean[valid], s=18, alpha=0.6, color='green')
ax.set_xlabel('剂量 (mg/kg)')
ax.set_ylabel('存活率')
ax.set_title('剂量-存活率关系（清洗后，模拟数据）')
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('figure.png', dpi=120)
plt.close()

print("\n[落盘] cleaned.csv, data_dictionary.csv, figure.png")
print("注意：以上均为【模拟数据】，不代表真实实验结论。")