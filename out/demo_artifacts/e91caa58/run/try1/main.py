import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

rng = np.random.default_rng(42)

# ============================================================
# 模拟数据（明确标注：以下为模拟数据，非真实实验结论）
# ============================================================
# 真实 IC50 = 10 (uM)，Hill 斜率 = 1.2，Bottom=3%，Top=98%
TRUE_IC50 = 10.0
TRUE_HILL = 1.2
TRUE_BOTTOM = 3.0
TRUE_TOP = 98.0

doses = np.array([0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0])
# 每个剂量的重复数：故意让 0.3 和 30 只有 2 个重复（低置信）
n_reps = {0.1: 4, 0.3: 2, 1.0: 4, 3.0: 3, 10.0: 4, 30.0: 2, 100.0: 4, 300.0: 3}

def hill(d, ic50, hill, bottom, top):
    return bottom + (top - bottom) / (1.0 + (ic50 / d) ** hill)

records = []  # (dose, inhibition)
for d in doses:
    mu = hill(d, TRUE_IC50, TRUE_HILL, TRUE_BOTTOM, TRUE_TOP)
    sd = 2.5  # 实验噪声
    for _ in range(n_reps[d]):
        val = np.clip(mu + rng.normal(0, sd), 0, 100)
        records.append((d, val))

dose_arr = np.array([r[0] for r in records])
inh_arr = np.array([r[1] for r in records])

print("=" * 70)
print("【重要声明】本脚本使用模拟数据（simulated data），")
print("           所有数值结果仅用于演示分析流程，不代表真实实验结论。")
print("=" * 70)

# ============================================================
# 步骤 1：单变量分布与缺失率
# ============================================================
print("\n--- 步骤1：单变量分布与缺失率 ---")
n_total = len(dose_arr)
n_missing_dose = int(np.sum(~np.isfinite(dose_arr)))
n_missing_inh = int(np.sum(~np.isfinite(inh_arr)))
print(f"总记录数: {n_total}")
print(f"dose 缺失数: {n_missing_dose} ({n_missing_dose/n_total*100:.2f}%)")
print(f"inhibition 缺失数: {n_missing_inh} ({n_missing_inh/n_total*100:.2f}%)")
print(f"inhibition 分布: min={np.min(inh_arr):.2f}, "
      f"Q1={np.percentile(inh_arr,25):.2f}, median={np.median(inh_arr):.2f}, "
      f"Q3={np.percentile(inh_arr,75):.2f}, max={np.max(inh_arr):.2f}, "
      f"mean={np.mean(inh_arr):.2f}, SD={np.std(inh_arr, ddof=1):.2f}")
# 偏度/峰度（避免只看均值不看分布形态）
skew = float(np.mean(((inh_arr - np.mean(inh_arr)) / np.std(inh_arr, ddof=1)) ** 3))
kurt = float(np.mean(((inh_arr - np.mean(inh_arr)) / np.std(inh_arr, ddof=1)) ** 4) - 3)
print(f"inhibition 偏度={skew:.3f}, 超额峰度={kurt:.3f}  "
      f"(|偏度|>1 或 |峰度|>3 提示分布非正态，需注意)")

# ============================================================
# 步骤 2：按剂量分组统计（n, mean, SD）
# ============================================================
print("\n--- 步骤2：按剂量分组统计 ---")
group_rows = []
for d in doses:
    vals = inh_arr[dose_arr == d]
    n = len(vals)
    mean_v = float(np.mean(vals))
    sd_v = float(np.std(vals, ddof=1)) if n > 1 else float('nan')
    sem_v = sd_v / np.sqrt(n) if n > 1 else float('nan')
    low_conf = n < 3
    group_rows.append({
        'dose': d, 'n': n, 'mean': mean_v, 'sd': sd_v,
        'sem': sem_v, 'low_confidence': low_conf
    })

print(f"{'dose':>8} {'n':>4} {'mean':>8} {'SD':>8} {'SEM':>8} {'低置信':>8}")
for r in group_rows:
    print(f"{r['dose']:>8.2f} {r['n']:>4d} {r['mean']:>8.2f} "
          f"{r['sd']:>8.2f} {r['sem']:>8.2f} "
          f"{'是' if r['low_confidence'] else '否':>8}")

# 保存分组统计 CSV
with open('group_stats.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['dose', 'n', 'mean', 'sd', 'sem', 'low_confidence'])
    w.writeheader()
    for r in group_rows:
        w.writerow(r)
print("已保存: group_stats.csv")

# ============================================================
# 步骤 3：平台期覆盖判断
# ============================================================
print("\n--- 步骤3：平台期覆盖判断 ---")
min_dose = min(doses)
max_dose = max(doses)
min_mean = [r['mean'] for r in group_rows if r['dose'] == min_dose][0]
max_mean = [r['mean'] for r in group_rows if r['dose'] == max_dose][0]

print(f"最低剂量 {min_dose} 的平均抑制率 = {min_mean:.2f}%")
print(f"最高剂量 {max_dose} 的平均抑制率 = {max_mean:.2f}%")

bottom_covered = min_mean <= 5.0
top_covered = max_mean >= 95.0

if bottom_covered and top_covered:
    model_choice = "4PL（Bottom/Top 自由拟合）"
    reason = "最低剂量抑制率≤5% 且最高剂量≥95%，覆盖平台期"
elif bottom_covered and not top_covered:
    model_choice = "3PL（固定 Top=100）"
    reason = "最低剂量覆盖 Bottom，但最高剂量未达 95%，固定 Top=100"
elif not bottom_covered and top_covered:
    model_choice = "3PL（固定 Bottom=0）"
    reason = "最高剂量覆盖 Top，但最低剂量未≤5%，固定 Bottom=0"
else:
    model_choice = "3PL（固定 Bottom=0 且 Top=100）"
    reason = "两端均未覆盖平台期，固定 Bottom=0 且 Top=100"

print(f"Bottom 覆盖: {'是' if bottom_covered else '否'} (判据 ≤5%)")
print(f"Top 覆盖:    {'是' if top_covered else '否'} (判据 ≥95%)")
print(f"模型形式建议: {model_choice}")
print(f"理由: {reason}")

# ============================================================
# 步骤 4：低置信剂量点标记
# ============================================================
print("\n--- 步骤4：低置信剂量点标记 (n<3) ---")
low_conf_doses = [r['dose'] for r in group_rows if r['low_confidence']]
if low_conf_doses:
    print(f"低置信剂量点: {low_conf_doses}")
    print("处理建议: 这些点均值不稳定，拟合时应降低权重或剔除；"
          "若保留，建议在报告中标注 n 值。")
else:
    print("无低置信剂量点（所有剂量 n≥3）")

# ============================================================
# 步骤 5：共线性检查（log10(dose) 与 dose）
# ============================================================
print("\n--- 步骤5：共线性检查 ---")
log_dose = np.log10(dose_arr)
# Pearson 相关（注意：仅用于检测线性共线性，不用于解释非线性剂量-响应关系）
corr_dose_logdose = float(np.corrcoef(dose_arr, log_dose)[0, 1])
print(f"corr(dose, log10(dose)) = {corr_dose_logdose:.4f}")
print("结论: dose 与 log10(dose) 高度共线（|r|>0.9），"
      "两者不可同时进入模型，应二选一。")
print("建议: 剂量-响应建模使用 log10(dose) 作为自变量（Hill 方程标准形式），"
      "避免共线性。")
print("注意: 相关系数仅反映单调线性关联，不能用于解释非线性剂量-响应关系；"
      "本步骤仅用于共线性检测。")

# ============================================================
# 步骤 6：绘图
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

# 左图：剂量-响应散点 + 分组均值±SD
ax = axes[0]
ax.scatter(dose_arr, inh_arr, s=28, alpha=0.45, color='steelblue',
           label='原始数据点（模拟）', zorder=2)
means = [r['mean'] for r in group_rows]
sds = [r['sd'] for r in group_rows]
ns = [r['n'] for r in group_rows]
ax.errorbar(doses, means, yerr=sds, fmt='o-', color='crimson',
            capsize=4, linewidth=1.8, markersize=7,
            label='分组均值 ± SD', zorder=3)
# 标记低置信点
for r in group_rows:
    if r['low_confidence']:
        ax.scatter([r['dose']], [r['mean']], s=180, facecolors='none',
                   edgecolors='orange', linewidths=2.2, zorder=4,
                   label='低置信 (n<3)' if r['dose'] == low_conf_doses[0] else None)
ax.set_xscale('log')
ax.set_xlabel('剂量 (log scale)')
ax.set_ylabel('抑制率 (%)')
ax.set_title('剂量-响应散点与分组均值')
ax.axhline(0, color='gray', linestyle=':', linewidth=0.8)
ax.axhline(100, color='gray', linestyle=':', linewidth=0.8)
ax.axhline(5, color='green', linestyle='--', linewidth=0.8, alpha=0.6)
ax.axhline(95, color='green', linestyle='--', linewidth=0.8, alpha=0.6)
ax.legend(fontsize=9)
ax.grid(alpha=0.3)

# 右图：各剂量抑制率分布（箱线图风格用散点+均值）
ax2 = axes[1]
positions = np.arange(len(doses))
for i, d in enumerate(doses):
    vals = inh_arr[dose_arr == d]
    jitter = rng.uniform(-0.12, 0.12, size=len(vals))
    ax2.scatter(np.full(len(vals), i) + jitter, vals, s=30, alpha=0.6,
                color='steelblue')
    ax2.plot([i - 0.25, i + 0.25], [np.mean(vals)] * 2, color='crimson',
             linewidth=2.5)
    if len(vals) > 1:
        ax2.plot([i, i], [np.mean(vals) - np.std(vals, ddof=1),
                          np.mean(vals) + np.std(vals, ddof=1)],
                 color='crimson', linewidth=1.2)
    if len(vals) < 3:
        ax2.text(i, 105, 'n<3', ha='center', fontsize=8, color='orange')
ax2.set_xticks(positions)
ax2.set_xticklabels([f'{d:g}' for d in doses], rotation=45)
ax2.set_xlabel('剂量')
ax2.set_ylabel('抑制率 (%)')
ax2.set_title('各剂量抑制率分布')
ax2.axhline(5, color='green', linestyle='--', linewidth=0.8, alpha=0.6)
ax2.axhline(95, color='green', linestyle='--', linewidth=0.8, alpha=0.6)
ax2.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print("\n已保存: figure.png")

# ============================================================
# 步骤 7：EDA 报告汇总
# ============================================================
print("\n" + "=" * 70)
print("EDA 报告汇总")
print("=" * 70)
print(f"1. 数据规模: {n_total} 条记录, {len(doses)} 个剂量水平")
print(f"2. 缺失率: dose={n_missing_dose/n_total*100:.2f}%, "
      f"inhibition={n_missing_inh/n_total*100:.2f}%")
print(f"3. 抑制率分布: mean={np.mean(inh_arr):.2f}%, "
      f"SD={np.std(inh_arr, ddof=1):.2f}%, "
      f"偏度={skew:.3f}, 峰度={kurt:.3f}")
print(f"4. 平台期: Bottom覆盖={bottom_covered}, Top覆盖={top_covered}")
print(f"5. 模型建议: {model_choice}")
print(f"6. 低置信剂量点 (n<3): {low_conf_doses if low_conf_doses else '无'}")
print(f"7. 共线性: corr(dose, log10(dose))={corr_dose_logdose:.4f} "
      f"→ 二者不可同时入模")
print("\n风险项与处理建议:")
print("  [风险1] 低置信剂量点均值不稳定 → 拟合时降权或剔除，报告中标注 n")
print("  [风险2] dose 与 log10(dose) 共线 → 仅用 log10(dose) 进入 Hill 模型")
print("  [风险3] 若分布偏度/峰度异常 → 检查是否存在离群点，考虑稳健拟合")
print("  [风险4] 相关系数不能解释非线性剂量-响应 → 仅用于共线性检测")
print("  [风险5] 分组样本量不均 → 拟合权重应反映 n 差异")
print("\n【再次声明】以上均为模拟数据分析结果，非真实实验结论。")