import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 说明：本脚本使用【模拟数据】演示清洗流程，非真实实验结论。
# ============================================================
rng = np.random.default_rng(42)

# ---------- 1. 构造模拟原始数据（模拟数据） ----------
n = 120
dose_mM = rng.choice([0.0, 0.001, 0.01, 0.1, 1.0, 10.0], size=n)  # 原始单位 mM
replicate = rng.integers(1, 4, size=n)
group = rng.choice(['A', 'B'], size=n)
# 抑制率原始以百分数给出（0-100），含少量越界与缺失
true_inhib = 100 / (1 + np.exp(-(np.log10(dose_mM * 1000 + 1e-9) - 1.0)))
inhib_pct = true_inhib + rng.normal(0, 8, size=n)
inhib_pct = np.clip(inhib_pct, -5, 110)
# 人为制造缺失（非随机：高剂量更易缺失）
miss_mask = (dose_mM >= 1.0) & (rng.random(n) < 0.25)
inhib_pct = inhib_pct.astype(float)
inhib_pct[miss_mask] = np.nan
# 人为制造重复孔（主键冲突）
dup_idx = rng.choice(n, size=5, replace=False)
dose_mM = np.append(dose_mM, dose_mM[dup_idx])
replicate = np.append(replicate, replicate[dup_idx])
group = np.append(group, group[dup_idx])
inhib_pct = np.append(inhib_pct, inhib_pct[dup_idx] + rng.normal(0, 2, 5))
n = len(dose_mM)

raw = {
    'dose_mM': dose_mM, 'replicate': replicate,
    'group': group, 'inhibition_pct': inhib_pct
}
print("=== 步骤0：原始数据（模拟数据） ===")
print(f"原始行数: {n}")

# ---------- 2. 结构探查与主键唯一性 ----------
keys = list(zip(raw['dose_mM'], raw['replicate'], raw['group']))
from collections import Counter
key_counts = Counter(keys)
dup_keys = {k: c for k, c in key_counts.items() if c > 1}
print(f"\n=== 步骤1：主键唯一性检查 ===")
print(f"重复主键数: {len(dup_keys)}，涉及行数: {sum(dup_keys.values())}")
# 保留首次出现，标记重复孔
seen = set()
keep = np.ones(n, dtype=bool)
for i, k in enumerate(keys):
    if k in seen:
        keep[i] = False
    else:
        seen.add(k)
print(f"去重后行数: {keep.sum()}（保留首次出现，重复孔标记为 is_duplicate）")

# ---------- 3. 单位统一 ----------
dose_uM = raw['dose_mM'] * 1000.0
log10_dose = np.where(dose_uM > 0, np.log10(dose_uM), np.nan)
inhib_frac = raw['inhibition_pct'] / 100.0
print(f"\n=== 步骤2：单位统一 ===")
print(f"剂量 mM->μM 完成；log10_dose 非缺失数: {np.sum(~np.isnan(log10_dose))}")
print(f"抑制率 %->小数 完成；范围: [{np.nanmin(inhib_frac):.3f}, {np.nanmax(inhib_frac):.3f}]")

# ---------- 4. 缺失模式 ----------
miss = np.isnan(inhib_frac)
print(f"\n=== 步骤3：缺失模式 ===")
print(f"抑制率缺失数: {miss.sum()} / {n} ({miss.mean()*100:.1f}%)")
# 按剂量分组看缺失率，判断是否非随机
for d in sorted(set(raw['dose_mM'])):
    m = raw['dose_mM'] == d
    print(f"  剂量 {d} mM: 缺失率 {np.isnan(inhib_frac[m]).mean()*100:.1f}%")
print("结论：高剂量缺失率明显更高 -> 非随机缺失(MNAR)，不删除、不均值填补，仅标记。")

# ---------- 5. 业务规则异常标记 ----------
# 规则1：载体对照(剂量=0)均值±3SD
ctrl = (raw['dose_mM'] == 0) & (~miss)
ctrl_mean = np.nanmean(inhib_frac[ctrl])
ctrl_sd = np.nanstd(inhib_frac[ctrl])
lo, hi = ctrl_mean - 3*ctrl_sd, ctrl_mean + 3*ctrl_sd
flag_ctrl = (~miss) & ((inhib_frac < lo) | (inhib_frac > hi))
print(f"\n=== 步骤4：业务规则异常标记 ===")
print(f"载体对照均值={ctrl_mean:.3f}, SD={ctrl_sd:.3f}, 3SD区间=[{lo:.3f},{hi:.3f}]")
print(f"规则1(对照±3SD)标记异常: {flag_ctrl.sum()} 行")

# 规则2：重复孔 CV>20%
flag_cv = np.zeros(n, dtype=bool)
for k in key_counts:
    idx = [i for i, kk in enumerate(keys) if kk == k]
    vals = inhib_frac[idx]
    vals = vals[~np.isnan(vals)]
    if len(vals) >= 2:
        cv = np.std(vals) / (np.mean(vals) + 1e-9)
        if cv > 0.20:
            for i in idx:
                flag_cv[i] = True
print(f"规则2(重复孔CV>20%)标记异常: {flag_cv.sum()} 行")

# ---------- 6. 组装干净数据表 ----------
clean = {
    'dose_uM': dose_uM, 'log10_dose': log10_dose,
    'replicate': raw['replicate'], 'group': raw['group'],
    'inhibition_frac': inhib_frac,
    'is_duplicate': ~keep,
    'is_missing': miss,
    'flag_ctrl_3sd': flag_ctrl,
    'flag_cv20': flag_cv,
}
print(f"\n=== 步骤5：清洗后主键唯一性验证 ===")
final_keys = list(zip(clean['dose_uM'], clean['replicate'], clean['group']))
print(f"清洗后主键唯一: {len(final_keys) == len(set(final_keys))}")

# ---------- 7. 审计日志 ----------
log = [
    "步骤0: 原始行数=%d (模拟数据)" % n,
    "步骤1: 重复主键=%d, 去重后=%d" % (len(dup_keys), keep.sum()),
    "步骤2: 单位统一 mM->μM, %->小数",
    "步骤3: 缺失=%d (MNAR, 仅标记不删除)" % miss.sum(),
    "步骤4: 规则1标记=%d, 规则2标记=%d" % (flag_ctrl.sum(), flag_cv.sum()),
    "步骤5: 清洗后主键唯一=%s" % (len(final_keys) == len(set(final_keys))),
]
print("\n=== 审计日志 ===")
for l in log:
    print(l)

# ---------- 8. 出图 ----------
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
ax = axes[0]
valid = ~miss
ax.scatter(clean['log10_dose'][valid], clean['inhibition_frac'][valid],
           c='steelblue', alpha=0.6, label='正常')
ax.scatter(clean['log10_dose'][flag_ctrl], clean['inhibition_frac'][flag_ctrl],
           c='red', marker='x', s=80, label='对照±3SD异常')
ax.scatter(clean['log10_dose'][flag_cv], clean['inhibition_frac'][flag_cv],
           c='orange', marker='^', s=80, label='CV>20%异常')
ax.set_xlabel('log10(剂量 μM)'); ax.set_ylabel('抑制率(小数)')
ax.set_title('剂量-反应散点（模拟数据）'); ax.legend(); ax.grid(alpha=0.3)

ax2 = axes[1]
ax2.hist(clean['inhibition_frac'][valid], bins=20, color='teal', alpha=0.7)
ax2.set_xlabel('抑制率(小数)'); ax2.set_ylabel('频数')
ax2.set_title('抑制率分布（模拟数据）'); ax2.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n图已保存: figure.png")

# ---------- 9. 落盘 ----------
import csv
with open('clean_data.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(list(clean.keys()))
    for i in range(n):
        w.writerow([clean[k][i] for k in clean])
with open('audit_log.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(log))
print("已保存: clean_data.csv, audit_log.txt")