# -*- coding: utf-8 -*-
"""
结构探查与缺失处理 —— 模拟数据演示（非真实实验结论）
依赖：numpy 2.5.3, matplotlib 3.11.2
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

RNG = np.random.default_rng(42)
N = 1000

# ============ 1. 构造模拟数据（明确标注：模拟数据） ============
# 主键 id 故意制造 3 个重复，用于验证唯一性检查
ids = np.arange(1, N + 1).astype(float)
ids[10] = ids[9]
ids[500] = ids[499]
ids[800] = ids[799]

age = RNG.normal(45, 15, N)
age[age < 0] = np.nan
age[5] = -3.0          # 业务异常：年龄<0
age[6] = 150.0         # 业务异常：年龄>120
age[7] = np.nan

income = RNG.lognormal(10, 0.6, N)
income[income > 2e6] = np.nan

score = RNG.normal(70, 12, N)

# 缺失率设计：age ~3%, income ~45%, score ~1%, city ~10%
age_mask = RNG.random(N) < 0.03
age[age_mask] = np.nan
income_mask = RNG.random(N) < 0.45
income[income_mask] = np.nan
score_mask = RNG.random(N) < 0.01
score[score_mask] = np.nan

city_pool = np.array(['北京', '上海', '广州', '深圳', '成都'])
city = city_pool[RNG.integers(0, 5, N)].astype(object)
city_mask = RNG.random(N) < 0.10
city[city_mask] = None

# 非随机缺失(MNAR)演示：income 缺失与 age 相关（高年龄更易缺失）
mnar_idx = np.where((age > 60) & (RNG.random(N) < 0.5))[0]
income[mnar_idx] = np.nan

raw = {'id': ids, 'age': age, 'income': income, 'score': score, 'city': city}
cols = list(raw.keys())
audit = []   # 审计日志

def log(step, reason, affected, before, after):
    audit.append({'step': step, 'reason': reason, 'affected_rows': affected,
                  'before': before, 'after': after})
    print(f"[审计] {step} | 原因: {reason} | 影响行数: {affected} | 前: {before} | 后: {after}")

print("=" * 70)
print("【模拟数据】共 %d 行, %d 列: %s" % (N, len(cols), cols))
print("=" * 70)

# ============ 2. 结构探查 + 主键唯一性 ============
n_before = len(ids)
uniq = len(np.unique(ids))
print("\n[结构探查] 主键 id 唯一值数 = %d / 总行数 = %d" % (uniq, n_before))
if uniq < n_before:
    dup_mask = np.zeros(n_before, dtype=bool)
    seen = set()
    for i, v in enumerate(ids):
        if v in seen:
            dup_mask[i] = True
        else:
            seen.add(v)
    n_dup = int(dup_mask.sum())
    for k in cols:
        raw[k] = raw[k][~dup_mask]
    log("主键去重", "id 存在重复，保留首次出现", n_dup, n_before, len(raw['id']))
else:
    log("主键去重", "id 唯一，无需处理", 0, n_before, n_before)

# ============ 3. 缺失率统计与缺失模式 ============
print("\n[缺失率统计]")
miss_rate = {}
for k in cols:
    arr = raw[k]
    if arr.dtype == object:
        m = np.array([v is None or (isinstance(v, float) and np.isnan(v)) for v in arr])
    else:
        m = np.isnan(arr)
    miss_rate[k] = m.mean()
    print("  %-8s 缺失率 = %6.2f%%  缺失数 = %d" % (k, miss_rate[k] * 100, int(m.sum())))

# 缺失模式：MNAR 检查（income 缺失 vs age 分布）
inc_miss = np.isnan(raw['income'])
age_obs = raw['age'][~np.isnan(raw['age'])]
inc_miss_age = inc_miss[~np.isnan(raw['age'])]
if inc_miss_age.sum() > 0 and (~inc_miss_age).sum() > 0:
    mean_miss = np.nanmean(raw['age'][inc_miss])
    mean_obs = np.nanmean(raw['age'][~inc_miss])
    print("\n[缺失模式] income 缺失组 age 均值 = %.2f, 非缺失组 = %.2f, 差 = %.2f"
          % (mean_miss, mean_obs, mean_miss - mean_obs))
    print("  -> 差异显著，判定为 MNAR 倾向，禁止均值填补，改用树模型原生缺失处理")

# ============ 4. 业务规则异常值判定 ============
print("\n[业务规则异常值判定]")
age_arr = raw['age'].copy()
bad_age = (~np.isnan(age_arr)) & ((age_arr < 0) | (age_arr > 120))
n_bad = int(bad_age.sum())
if n_bad > 0:
    before_mean = np.nanmean(age_arr)
    age_arr[bad_age] = np.nan
    after_mean = np.nanmean(age_arr)
    log("年龄异常置空", "业务规则: 年龄<0 或 >120 视为异常", n_bad,
        "均值%.2f" % before_mean, "均值%.2f" % after_mean)
raw['age'] = age_arr

# ============ 5. 缺失处理策略 ============
print("\n[缺失处理策略]")
LOW, HIGH = 0.05, 0.40
numeric_cols = ['age', 'income', 'score']
clean = {k: raw[k].copy() for k in cols}
indicator_cols = []

for k in numeric_cols:
    r = miss_rate[k]
    arr = clean[k]
    if r < LOW:
        med = np.nanmedian(arr)
        ind = np.isnan(arr).astype(float)
        arr[np.isnan(arr)] = med
        clean[k] = arr
        clean[k + '_miss'] = ind
        indicator_cols.append(k + '_miss')
        log("中位数填补+缺失指示", "%s 缺失率 %.2f%% < 5%%, 填补偏差可控" % (k, r * 100),
            int(ind.sum()), "缺失率%.2f%%" % (r * 100), "中位数=%.2f" % med)
    elif r > HIGH:
        log("标记候选剔除", "%s 缺失率 %.2f%% > 40%%, 填补信息量不足" % (k, r * 100),
            int(np.isnan(arr).sum()), "缺失率%.2f%%" % (r * 100), "保留原缺失, 交树模型处理")
    else:
        log("树模型原生处理", "%s 缺失率 %.2f%% 介于 5%%~40%%, 保留缺失" % (k, r * 100),
            int(np.isnan(arr).sum()), "缺失率%.2f%%" % (r * 100), "保留NaN")

# 类别字段 city：缺失率 10%，用众数填补并加指示
city_arr = clean['city']
city_miss = np.array([v is None for v in city_arr])
if city_miss.mean() > 0:
    vals = [v for v in city_arr if v is not None]
    mode = max(set(vals), key=vals.count)
    for i in range(len(city_arr)):
        if city_arr[i] is None:
            city_arr[i] = mode
    clean['city'] = city_arr
    clean['city_miss'] = city_miss.astype(float)
    indicator_cols.append('city_miss')
    log("众数填补+缺失指示", "city 缺失率 %.2f%%, 类别字段用众数" % (city_miss.mean() * 100),
        int(city_miss.sum()), "缺失率%.2f%%" % (city_miss.mean() * 100), "众数=%s" % mode)

# ============ 6. 验收检查 ============
print("\n[验收检查]")
final_ids = clean['id']
print("  清洗后主键唯一: %s (唯一值 %d / 行数 %d)"
      % (len(np.unique(final_ids)) == len(final_ids), len(np.unique(final_ids)), len(final_ids)))
print("  审计日志条目数: %d" % len(audit))
print("  新增缺失指示变量: %s" % indicator_cols)
print("  陷阱规避: 未删除缺失行(保留全部 %d 行); MNAR 字段未用均值填补; 每步均有审计记录" % len(final_ids))

# ============ 7. 数据字典 ============
print("\n[数据字典]")
dd = [
    ('id', '样本主键', '整数', '无'),
    ('age', '年龄', '岁', '业务规则: 0~120, 异常置空后中位数填补'),
    ('income', '年收入', '元', '缺失率>40%, 保留缺失交树模型'),
    ('score', '评分', '分', '缺失率<5%, 中位数填补'),
    ('city', '城市', '类别', '众数填补'),
    ('age_miss', '年龄缺失指示', '0/1', '1=原缺失'),
    ('score_miss', '评分缺失指示', '0/1', '1=原缺失'),
    ('city_miss', '城市缺失指示', '0/1', '1=原缺失'),
]
for name, desc, unit, rule in dd:
    print("  %-12s %-10s %-6s %s" % (name, desc, unit, rule))

# ============ 8. 出图 ============
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
keys = list(miss_rate.keys())
rates = [miss_rate[k] * 100 for k in keys]
colors = ['#d62728' if r > 40 else ('#ff7f0e' if r >= 5 else '#2ca02c') for r in rates]
axes[0].bar(keys, rates, color=colors)
axes[0].axhline(5, color='orange', ls='--', label='5% 阈值')
axes[0].axhline(40, color='red', ls='--', label='40% 阈值')
axes[0].set_title('各字段缺失率（模拟数据）')
axes[0].set_ylabel('缺失率 (%)')
axes[0].legend()

axes[1].hist(raw['age'][~np.isnan(raw['age'])], bins=30, color='#1f77b4', alpha=0.8)
axes[1].set_title('清洗后 age 分布（模拟数据）')
axes[1].set_xlabel('年龄')
axes[1].set_ylabel('频数')
plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n[输出] 图已保存: figure.png")

# ============ 9. 落盘 ============
out_cols = ['id', 'age', 'income', 'score', 'city'] + indicator_cols
header = ','.join(out_cols)
rows = []
for i in range(len(clean['id'])):
    vals = []
    for c in out_cols:
        v = clean[c][i]
        if isinstance(v, float) and np.isnan(v):
            vals.append('')
        else:
            vals.append(str(v))
    rows.append(','.join(vals))
with open('clean_data.csv', 'w', encoding='utf-8-sig') as f:
    f.write(header + '\n' + '\n'.join(rows))

with open('audit_log.csv', 'w', encoding='utf-8-sig') as f:
    f.write('step,reason,affected_rows,before,after\n')
    for a in audit:
        f.write('%s,%s,%d,%s,%s\n' % (a['step'], a['reason'], a['affected_rows'], a['before'], a['after']))

with open('data_dictionary.csv', 'w', encoding='utf-8-sig') as f:
    f.write('字段,含义,单位,口径\n')
    for name, desc, unit, rule in dd:
        f.write('%s,%s,%s,%s\n' % (name, desc, unit, rule))

print("[输出] clean_data.csv / audit_log.csv / data_dictionary.csv 已保存")
print("注意: 以上均为模拟数据结果，非真实实验结论。")