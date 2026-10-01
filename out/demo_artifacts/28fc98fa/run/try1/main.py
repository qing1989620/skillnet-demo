import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 注意：以下为【模拟数据】，仅用于演示 EDA 流程，非真实实验结论
# ============================================================
rng = np.random.default_rng(42)
doses = np.array([0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0])
true_ic50 = 1.2
hill = 1.1
bottom, top = 3.0, 97.0
reps = [3, 3, 4, 3, 5, 3, 3, 2, 3]  # 故意让某些点 n<3

records = []
for d, n in zip(doses, reps):
    frac = 1.0 / (1.0 + (true_ic50 / d) ** hill)
    mu = bottom + (top - bottom) * frac
    for _ in range(n):
        val = np.clip(mu + rng.normal(0, 4.0), 0, 100)
        records.append((d, val))

dose_arr = np.array([r[0] for r in records])
inh_arr = np.array([r[1] for r in records])
logdose_arr = np.log10(dose_arr)

print("=" * 70)
print("【模拟数据】说明：本脚本所有数值均为模拟生成，非真实实验结论")
print("=" * 70)
print(f"总样本数 N = {len(dose_arr)}，剂量水平数 = {len(doses)}")

# ------------------------------------------------------------
# 步骤1：单变量分布与缺失率排行
# ------------------------------------------------------------
print("\n--- 步骤1：单变量分布与缺失率 ---")
def describe(name, x):
    x = np.asarray(x, dtype=float)
    miss = np.isnan(x).mean()
    print(f"{name}: n={len(x)}, 缺失率={miss:.2%}, 均值={np.nanmean(x):.3f}, "
          f"SD={np.nanstd(x, ddof=1):.3f}, 中位数={np.nanmedian(x):.3f}, "
          f"min={np.nanmin(x):.3f}, max={np.nanmax(x):.3f}, "
          f"偏度={float(np.nanmean(((x-np.nanmean(x))/np.nanstd(x))**3)):.3f}")

describe("dose", dose_arr)
describe("log10(dose)", logdose_arr)
describe("inhibition(%)", inh_arr)

# ------------------------------------------------------------
# 步骤2：分组对比（按剂量），计算均值/SD/n
# ------------------------------------------------------------
print("\n--- 步骤2：按剂量分组统计 ---")
group_rows = []
low_conf_flags = []
for d in doses:
    vals = inh_arr[dose_arr == d]
    n = len(vals)
    m = vals.mean()
    sd = vals.std(ddof=1) if n > 1 else 0.0
    low_conf = n < 3
    low_conf_flags.append(low_conf)
    group_rows.append((d, np.log10(d), n, m, sd, low_conf))
    print(f"dose={d:>7.2f} | log10={np.log10(d):+.3f} | n={n} | "
          f"mean={m:6.2f} | SD={sd:5.2f} | {'低置信(n<3)' if low_conf else ''}")

# 保存分组统计
with open("dose_group_summary.csv", "w", encoding="utf-8") as f:
    f.write("dose,log10_dose,n,mean_inhibition,sd_inhibition,low_confidence\n")
    for d, ld, n, m, sd, lc in group_rows:
        f.write(f"{d},{ld:.6f},{n},{m:.6f},{sd:.6f},{int(lc)}\n")
print("已保存分组统计 -> dose_group_summary.csv")

# 保存清洗后明细
with open("cleaned_data.csv", "w", encoding="utf-8") as f:
    f.write("dose,log10_dose,inhibition\n")
    for d, ld, v in zip(dose_arr, logdose_arr, inh_arr):
        f.write(f"{d},{ld:.6f},{v:.6f}\n")
print("已保存清洗后明细 -> cleaned_data.csv")

# ------------------------------------------------------------
# 步骤3：单调性 / 平台期 / Bottom-Top 判断
# ------------------------------------------------------------
print("\n--- 步骤3：单调性、平台期与 Bottom/Top 判断 ---")
means = np.array([r[3] for r in group_rows])
diffs = np.diff(means)
mono_inc = np.all(diffs >= -1.0)  # 允许微小噪声
print(f"剂量-响应均值序列: {np.round(means,2).tolist()}")
print(f"相邻均值差: {np.round(diffs,2).tolist()}")
print(f"是否单调递增(容差1%): {mono_inc}")

lowest_mean = means[0]
highest_mean = means[-1]
print(f"最低剂量均值抑制率 = {lowest_mean:.2f}%  -> 接近0? {abs(lowest_mean) < 10}")
print(f"最高剂量均值抑制率 = {highest_mean:.2f}%  -> 接近100? {abs(highest_mean-100) < 10}")

# 平台期检测：末尾连续两点差异很小
plateau_tail = abs(diffs[-1]) < 3.0 and abs(diffs[-2]) < 3.0
print(f"高剂量端是否存在平台期(末两点差<3%): {plateau_tail}")

# 候选模型建议
if abs(lowest_mean) < 10 and abs(highest_mean - 100) < 10:
    model_suggest = "4PL 或 固定 Bottom=0/Top=100 的 3PL"
elif abs(lowest_mean) < 10:
    model_suggest = "固定 Bottom=0 的 3PL"
elif abs(highest_mean - 100) < 10:
    model_suggest = "固定 Top=100 的 3PL"
else:
    model_suggest = "自由 4PL（Bottom/Top 均需估计）"
print(f"候选模型形式建议: {model_suggest}")

# ------------------------------------------------------------
# 步骤4：共线性检查（log10(dose) 与 dose 不共存）
# ------------------------------------------------------------
print("\n--- 步骤4：共线性检查 ---")
corr_dose_log = np.corrcoef(dose_arr, logdose_arr)[0, 1]
print(f"corr(dose, log10(dose)) = {corr_dose_log:.4f}")
print("结论：dose 与 log10(dose) 高度共线，二者不得同时进入同一模型（IC50 拟合应使用 log10(dose) 作为自变量）。")

# 相关系数仅用于线性关系提示，非线性关系需用散点/拟合判断
corr_log_inh = np.corrcoef(logdose_arr, inh_arr)[0, 1]
print(f"corr(log10(dose), inhibition) = {corr_log_inh:.4f}（仅作线性提示，剂量-响应为非线性 S 型）")

# ------------------------------------------------------------
# 步骤5：风险项与处理建议
# ------------------------------------------------------------
print("\n--- 步骤5：风险项清单与处理建议 ---")
risks = []
n_low = sum(low_conf_flags)
if n_low > 0:
    risks.append(f"{n_low} 个剂量点 n<3（低置信），建议增加重复或加权/剔除")
if not mono_inc:
    risks.append("均值序列非严格单调，可能存在噪声或非单调效应，需核查异常点")
if abs(lowest_mean) >= 10:
    risks.append(f"最低剂量抑制率 {lowest_mean:.1f}% 未接近0，Bottom 不宜固定为0")
if abs(highest_mean - 100) >= 10:
    risks.append(f"最高剂量抑制率 {highest_mean:.1f}% 未接近100，Top 不宜固定为100")
if not plateau_tail:
    risks.append("高剂量端未见明显平台期，Top 估计可能不稳定，建议扩展剂量范围")
risks.append("dose 与 log10(dose) 共线，模型仅保留 log10(dose)")

for i, r in enumerate(risks, 1):
    print(f"风险{i}: {r}")

# ------------------------------------------------------------
# 出图：剂量-响应散点 + 分组均值±SD + 分布直方图
# ------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))

# 图1：剂量-响应散点（log 轴）
ax = axes[0]
ax.scatter(dose_arr, inh_arr, s=25, alpha=0.5, color='steelblue', label='个体观测(模拟)')
gm = np.array([r[3] for r in group_rows])
gs = np.array([r[4] for r in group_rows])
ax.errorbar(doses, gm, yerr=gs, fmt='o-', color='crimson', capsize=4,
            label='分组均值±SD')
for d, m, lc in zip(doses, gm, low_conf_flags):
    if lc:
        ax.scatter([d], [m], s=180, facecolors='none', edgecolors='orange',
                   linewidths=2, label='低置信(n<3)' if d == doses[low_conf_flags.index(True)] else '')
ax.set_xscale('log')
ax.set_xlabel('剂量 (log 轴)')
ax.set_ylabel('抑制率 (%)')
ax.set_title('剂量-响应关系（模拟数据）')
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

# 图2：抑制率分布
ax = axes[1]
ax.hist(inh_arr, bins=15, color='seagreen', alpha=0.75, edgecolor='black')
ax.axvline(inh_arr.mean(), color='red', ls='--', label=f'均值={inh_arr.mean():.1f}')
ax.axvline(np.median(inh_arr), color='blue', ls=':', label=f'中位数={np.median(inh_arr):.1f}')
ax.set_xlabel('抑制率 (%)')
ax.set_ylabel('频数')
ax.set_title('抑制率分布（模拟数据）')
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

# 图3：各剂量重复数
ax = axes[2]
ns = [r[2] for r in group_rows]
colors = ['orange' if r[5] else 'steelblue' for r in group_rows]
ax.bar([str(d) for d in doses], ns, color=colors, edgecolor='black')
ax.axhline(3, color='red', ls='--', label='n=3 阈值')
ax.set_xlabel('剂量')
ax.set_ylabel('重复数 n')
ax.set_title('各剂量重复数（橙色=低置信）')
ax.legend(fontsize=8)
ax.grid(alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n已保存图 -> figure.png")
print("\n【提醒】以上所有数值均为模拟数据，不可作为真实实验结论。")