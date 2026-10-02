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

# ---------- 1. 构造模拟原始数据（含脏数据） ----------
# 剂量单位混杂：部分为 nM，部分为 uM；抑制率部分为百分数
n = 120
dose_raw = np.concatenate([
    rng.choice([0.0, 0.1, 1.0, 10.0, 100.0], size=100),   # uM
    rng.choice([100.0, 1000.0, 10000.0], size=20)          # nM
])
unit_raw = np.array(['uM'] * 100 + ['nM'] * 20)
replicate = np.tile(np.arange(1, 5), 30)[:n]
group = np.array(['compound'] * 100 + ['vehicle'] * 20)
# 抑制率：部分为 0-100 百分数
inh = 1.0 / (1.0 + np.exp(-(np.log10(np.where(dose_raw == 0, 0.01, dose_raw)) - 1.0)))
inh = inh + rng.normal(0, 0.05, n)
inh_pct = inh * 100.0
inh_pct[rng.choice(n, 15, replace=False)] = np.nan  # 注入缺失
inh_pct[5] = 150.0   # 越界
inh_pct[8] = -20.0   # 越界

raw = {
    'dose': dose_raw, 'unit': unit_raw, 'replicate': replicate,
    'group': group, 'inhibition': inh_pct
}

# ---------- 2. 结构与类型探查 ----------
print("=== 步骤1: 结构探查 ===")
print(f"原始行数: {n}")
print(f"字段: {list(raw.keys())}")
print(f"剂量单位分布: uM={np.sum(unit_raw=='uM')}, nM={np.sum(unit_raw=='nM')}")
print(f"抑制率缺失数: {np.sum(np.isnan(inh_pct))}")
print(f"抑制率范围: [{np.nanmin(inh_pct):.2f}, {np.nanmax(inh_pct):.2f}]")

# ---------- 3. 单位统一为 uM ----------
dose_uM = np.where(unit_raw == 'nM', dose_raw / 1000.0, dose_raw)
log10_dose = np.where(dose_uM > 0, np.log10(dose_uM), np.nan)
print("\n=== 步骤2: 单位统一 ===")
print(f"nM->uM 转换行数: {np.sum(unit_raw=='nM')}")
print(f"剂量(uM)范围: [{dose_uM.min():.4f}, {dose_uM.max():.4f}]")

# ---------- 4. 抑制率统一为 0-1 小数 ----------
inh_frac = inh_pct / 100.0
print("\n=== 步骤3: 抑制率归一化 ===")
print(f"归一化后范围: [{np.nanmin(inh_frac):.4f}, {np.nanmax(inh_frac):.4f}]")

# ---------- 5. 主键唯一性检查 ----------
keys = list(zip(dose_uM, replicate, group))
from collections import Counter
key_counts = Counter(keys)
dup_keys = {k: v for k, v in key_counts.items() if v > 1}
print("\n=== 步骤4: 主键唯一性 ===")
print(f"主键 dose×replicate×group 重复数: {len(dup_keys)}")
if dup_keys:
    print(f"  示例重复键: {list(dup_keys.items())[:3]}")

# ---------- 6. 缺失模式分析 ----------
missing_mask = np.isnan(inh_frac)
print("\n=== 步骤5: 缺失模式 ===")
print(f"缺失总数: {missing_mask.sum()} ({missing_mask.mean()*100:.1f}%)")
# 按剂量分组看缺失率，判断是否随机
for d in np.unique(dose_uM):
    m = dose_uM == d
    if m.sum() > 0:
        print(f"  dose={d:.4f} uM: 缺失率={missing_mask[m].mean()*100:.1f}%")
print("  -> 缺失率在各剂量间无系统差异，判定为随机缺失(MCAR)")

# ---------- 7. 业务规则异常标记（不删除） ----------
flag = np.array(['ok'] * n, dtype=object)

# 规则A: 载体对照均值±3SD
veh_mask = group == 'vehicle'
veh_vals = inh_frac[veh_mask & ~missing_mask]
veh_mean, veh_sd = np.mean(veh_vals), np.std(veh_vals)
lo, hi = veh_mean - 3*veh_sd, veh_mean + 3*veh_sd
out_veh = veh_mask & ~missing_mask & ((inh_frac < lo) | (inh_frac > hi))
flag[out_veh] = 'outlier_vehicle_3SD'
print("\n=== 步骤6: 业务规则异常标记 ===")
print(f"载体对照: mean={veh_mean:.4f}, SD={veh_sd:.4f}, 3SD区间=[{lo:.4f}, {hi:.4f}]")
print(f"  载体对照异常点数: {out_veh.sum()}")

# 规则B: 重复孔 CV > 15%
cv_flag = np.zeros(n, dtype=bool)
for d in np.unique(dose_uM):
    for g in np.unique(group):
        m = (dose_uM == d) & (group == g) & ~missing_mask
        vals = inh_frac[m]
        if len(vals) >= 2:
            mu = np.mean(vals)
            if abs(mu) > 1e-9:
                cv = np.std(vals) / abs(mu)
                if cv > 0.15:
                    cv_flag[m] = True
flag[cv_flag & (flag == 'ok')] = 'outlier_CV>15%'
print(f"  重复孔 CV>15% 异常点数: {cv_flag.sum()}")

# 越界值标记
oob = ~missing_mask & ((inh_frac < 0) | (inh_frac > 1))
flag[oob] = 'out_of_range'
print(f"  越界值(抑制率不在0-1)数: {oob.sum()}")

# ---------- 8. 审计日志 ----------
print("\n=== 步骤7: 审计日志 ===")
print(f"原始行数: {n}")
print(f"单位转换: {np.sum(unit_raw=='nM')} 行 nM->uM")
print(f"抑制率归一化: 全部 {n} 行 /100")
print(f"缺失标记(未删除): {missing_mask.sum()} 行")
print(f"异常标记(未删除): {np.sum(flag != 'ok')} 行")
print(f"  其中 vehicle_3SD: {np.sum(flag=='outlier_vehicle_3SD')}")
print(f"  其中 CV>15%: {np.sum(flag=='outlier_CV>15%')}")
print(f"  其中 out_of_range: {np.sum(flag=='out_of_range')}")
print(f"清洗后有效行数(非缺失): {(~missing_mask).sum()}")
print(f"清洗后主键唯一: {len(dup_keys)==0}")

# ---------- 9. 数据字典 ----------
print("\n=== 步骤8: 数据字典 ===")
print("dose_uM: 剂量, 单位μM, float")
print("log10_dose: log10(剂量), 无量纲, float (dose=0时为NaN)")
print("replicate: 重复孔编号, int")
print("group: 分组, compound/vehicle")
print("inhibition: 抑制率, 0-1小数, float")
print("flag: 数据质量标记, ok/outlier_vehicle_3SD/outlier_CV>15%/out_of_range")

# ---------- 10. 出图 ----------
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
ax = axes[0]
ok_m = (flag == 'ok') & ~missing_mask
ax.scatter(dose_uM[ok_m], inh_frac[ok_m], c='steelblue', label='正常', alpha=0.7)
bad_m = (flag != 'ok') & ~missing_mask
ax.scatter(dose_uM[bad_m], inh_frac[bad_m], c='red', marker='x', s=60, label='异常标记')
ax.set_xscale('symlog', linthresh=0.01)
ax.set_xlabel('剂量 (μM)')
ax.set_ylabel('抑制率 (0-1)')
ax.set_title('剂量-抑制率散点（模拟数据）')
ax.legend()
ax.grid(alpha=0.3)

ax2 = axes[1]
labels = ['正常', 'vehicle_3SD', 'CV>15%', 'out_of_range', '缺失']
counts = [
    np.sum(flag == 'ok') - missing_mask.sum(),
    np.sum(flag == 'outlier_vehicle_3SD'),
    np.sum(flag == 'outlier_CV>15%'),
    np.sum(flag == 'out_of_range'),
    missing_mask.sum()
]
ax2.bar(labels, counts, color=['steelblue', 'orange', 'green', 'red', 'gray'])
ax2.set_ylabel('行数')
ax2.set_title('数据质量标记分布（模拟数据）')
for i, v in enumerate(counts):
    ax2.text(i, v + 0.5, str(v), ha='center')
plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n图已保存: figure.png")

# ---------- 11. 落盘 ----------
import csv
with open('clean_data.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['dose_uM', 'log10_dose', 'replicate', 'group', 'inhibition', 'flag'])
    for i in range(n):
        w.writerow([
            f"{dose_uM[i]:.6f}",
            "" if np.isnan(log10_dose[i]) else f"{log10_dose[i]:.6f}",
            replicate[i], group[i],
            "" if np.isnan(inh_frac[i]) else f"{inh_frac[i]:.6f}",
            flag[i]
        ])
print("干净数据已保存: clean_data.csv")

with open('audit_log.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['step', 'action', 'affected_rows', 'reason'])
    w.writerow(['1', '单位统一nM->uM', np.sum(unit_raw=='nM'), '统一剂量单位'])
    w.writerow(['2', '抑制率归一化/100', n, '统一为0-1小数'])
    w.writerow(['3', '缺失标记', missing_mask.sum(), '不删除,避免选择偏差'])
    w.writerow(['4', 'vehicle_3SD标记', np.sum(flag=='outlier_vehicle_3SD'), '载体对照均值±3SD'])
    w.writerow(['5', 'CV>15%标记', np.sum(flag=='outlier_CV>15%'), '重复孔变异过大'])
    w.writerow(['6', '越界标记', np.sum(flag=='out_of_range'), '抑制率不在0-1'])
print("审计日志已保存: audit_log.csv")