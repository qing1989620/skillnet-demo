import os
import csv
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 读取真实文件（若不存在则用模拟数据并明确标注） ----------
def read_csv_simple(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.reader(f))
    if not rows:
        return None
    header = rows[0]
    data = [r for r in rows[1:] if any(c.strip() for c in r)]
    return header, data

clean = read_csv_simple('clean_data.csv')
SIMULATED = False

if clean is None:
    SIMULATED = True
    print("[警告] 未找到 clean_data.csv，使用【模拟数据】进行演示，结果不代表真实实验结论。")
    rng = np.random.default_rng(42)
    doses = [0.0, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]
    header = ['dose', 'response', 'replicate']
    data = []
    for d in doses:
        n = int(rng.integers(2, 6))
        top = 95.0
        bottom = 3.0
        ec50 = 5.0
        hill = 1.2
        true_resp = bottom + (top - bottom) / (1.0 + (ec50 / max(d, 1e-6)) ** hill)
        for r in range(n):
            val = true_resp + rng.normal(0, 3.0)
            val = float(np.clip(val, 0, 100))
            data.append([str(d), f"{val:.4f}", str(r)])
else:
    header, data = clean
    print(f"[信息] 已读取真实文件 clean_data.csv，共 {len(data)} 行，列：{header}")

# 定位剂量列与响应列
def find_col(header, candidates):
    for c in candidates:
        for i, h in enumerate(header):
            if h.strip().lower() == c:
                return i
    for i, h in enumerate(header):
        for c in candidates:
            if c in h.strip().lower():
                return i
    return None

dose_idx = find_col(header, ['dose', '剂量', 'conc', 'concentration'])
resp_idx = find_col(header, ['response', 'survival', '存活', '存活率', 'viability', 'rate'])
if dose_idx is None or resp_idx is None:
    dose_idx, resp_idx = 0, 1
    print(f"[警告] 未识别到剂量/响应列名，默认使用第 {dose_idx} 列与第 {resp_idx} 列。")

doses = []
resps = []
for r in data:
    try:
        d = float(r[dose_idx])
        v = float(r[resp_idx])
    except (ValueError, IndexError):
        continue
    if math.isnan(d) or math.isnan(v):
        continue
    doses.append(d)
    resps.append(v)

doses = np.array(doses, dtype=float)
resps = np.array(resps, dtype=float)
print(f"[信息] 有效数据点：{len(doses)}")

# ---------- 步骤1：单变量分布与缺失率 ----------
n_total = len(data)
n_valid = len(doses)
missing_rate = 1.0 - n_valid / max(n_total, 1)
print(f"\n[1] 单变量分布与缺失率")
print(f"    总行数={n_total}, 有效行数={n_valid}, 缺失/无效率={missing_rate:.2%}")
print(f"    剂量范围: min={doses.min():.4f}, max={doses.max():.4f}, 唯一剂量数={len(np.unique(doses))}")
print(f"    响应范围: min={resps.min():.4f}, max={resps.max():.4f}, 均值={resps.mean():.4f}, SD={resps.std(ddof=1):.4f}")
q = np.percentile(resps, [25, 50, 75])
print(f"    响应分位数: Q1={q[0]:.3f}, 中位数={q[1]:.3f}, Q3={q[2]:.3f}")

# ---------- 步骤2：按剂量分组统计 ----------
uniq_doses = np.unique(doses)
group_stats = []
for d in uniq_doses:
    mask = doses == d
    vals = resps[mask]
    n = len(vals)
    mean = vals.mean()
    sd = vals.std(ddof=1) if n > 1 else 0.0
    group_stats.append((d, n, mean, sd))

print(f"\n[2] 按剂量分组统计（均值/SD/n）")
print(f"    {'剂量':>10} {'n':>4} {'均值':>10} {'SD':>10} {'低置信(n<3)':>12}")
low_conf = []
for d, n, mean, sd in group_stats:
    flag = "是" if n < 3 else ""
    if n < 3:
        low_conf.append(d)
    print(f"    {d:>10.4f} {n:>4d} {mean:>10.4f} {sd:>10.4f} {flag:>12}")

# ---------- 步骤3：检查最低/最高剂量是否接近 0 / 100% ----------
print(f"\n[3] 剂量-响应边界检查（Bottom/Top 可识别性）")
min_dose = uniq_doses.min()
max_dose = uniq_doses.max()
min_dose_mean = group_stats[0][2]
max_dose_mean = group_stats[-1][2]
print(f"    最低剂量={min_dose:.4f}, 该组均值响应={min_dose_mean:.4f}")
print(f"    最高剂量={max_dose:.4f}, 该组均值响应={max_dose_mean:.4f}")

bottom_identifiable = min_dose_mean < 20.0
top_identifiable = max_dose_mean > 80.0
if bottom_identifiable:
    print("    Bottom 可识别（最低剂量响应 < 20%）")
else:
    print("    Bottom 不可靠识别，建议固定 Bottom=0 或 3%")
if top_identifiable:
    print("    Top 可识别（最高剂量响应 > 80%）")
else:
    print("    Top 不可靠识别，建议固定 Top=100%")

# ---------- 步骤4：相关矩阵与共线性检查（规避非线性误读） ----------
print(f"\n[4] 相关矩阵与共线性检查")
if len(doses) > 2:
    corr = np.corrcoef(doses, resps)[0, 1]
    print(f"    dose 与 response 的 Pearson 相关系数 = {corr:.4f}")
    print("    [陷阱规避] 剂量-响应通常为非线性（S型），Pearson 相关仅作参考，")
    print("    不能据此判断单调线性关系，需结合分组均值趋势判断。")
else:
    print("    数据点不足，跳过相关分析。")

# 检查分组均值是否单调（非线性趋势的简单判断）
means_seq = [g[2] for g in group_stats]
mono_inc = all(means_seq[i] <= means_seq[i+1] for i in range(len(means_seq)-1))
mono_dec = all(means_seq[i] >= means_seq[i+1] for i in range(len(means_seq)-1))
print(f"    分组均值单调递增={mono_inc}, 单调递减={mono_dec}")
if not (mono_inc or mono_dec):
    print("    [提示] 分组均值非单调，存在非线性/非单调响应，相关系数解释力有限。")

# ---------- 步骤5：候选特征与风险项 ----------
print(f"\n[5] 候选特征清单与风险项")
print(f"    候选特征: dose（剂量）")
print(f"    目标变量: response（存活率）")
risks = []
if missing_rate > 0.05:
    risks.append(f"缺失/无效率 {missing_rate:.2%} 偏高，建议核查数据采集")
if len(low_conf) > 0:
    risks.append(f"存在 {len(low_conf)} 个剂量组 n<3（剂量={low_conf}），置信度低，建议补实验或加权")
if not bottom_identifiable:
    risks.append("Bottom 不可识别，拟合时建议固定 Bottom")
if not top_identifiable:
    risks.append("Top 不可识别，拟合时建议固定 Top")
if not (mono_inc or mono_dec):
    risks.append("分组均值非单调，需检查异常点或非单调响应机制")
if len(risks) == 0:
    print("    未发现显著风险项。")
else:
    for i, r in enumerate(risks, 1):
        print(f"    风险{i}: {r}")

# ---------- 绘图 ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# 左图：单变量分布（响应直方图 + 剂量分布）
ax1 = axes[0]
ax1.hist(resps, bins=min(15, max(5, len(resps)//2)), color='steelblue', edgecolor='black', alpha=0.7)
ax1.set_xlabel('存活率 (%)')
ax1.set_ylabel('频数')
ax1.set_title('响应变量分布（全部数据）')
ax1.axvline(resps.mean(), color='red', linestyle='--', label=f'均值={resps.mean():.2f}')
ax1.legend()

# 右图：剂量-响应散点 + 分组均值±SD
ax2 = axes[1]
ax2.scatter(doses, resps, color='gray', alpha=0.5, s=25, label='原始数据点')
gx = [g[0] for g in group_stats]
gy = [g[2] for g in group_stats]
gsd = [g[3] for g in group_stats]
gn = [g[1] for g in group_stats]
ax2.errorbar(gx, gy, yerr=gsd, fmt='o-', color='darkorange', capsize=4, label='分组均值±SD')
for d, n, mean, sd in group_stats:
    if n < 3:
        ax2.scatter([d], [mean], color='red', s=120, marker='x', zorder=5)
ax2.scatter([], [], color='red', marker='x', s=120, label='n<3 低置信点')
ax2.set_xlabel('剂量')
ax2.set_ylabel('存活率 (%)')
ax2.set_title('剂量-响应散点与分组统计')
ax2.legend(fontsize=8)
ax2.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print(f"\n[输出] 图已保存为 figure.png")

# ---------- 落盘分组统计表 ----------
with open('dose_group_stats.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['dose', 'n', 'mean', 'sd', 'low_confidence'])
    for d, n, mean, sd in group_stats:
        w.writerow([f"{d:.6f}", n, f"{mean:.6f}", f"{sd:.6f}", "yes" if n < 3 else "no"])
print("[输出] 分组统计表已保存为 dose_group_stats.csv")

if SIMULATED:
    print("\n[重要声明] 本次运行使用【模拟数据】，所有统计与结论仅用于流程演示，不代表真实实验结果。")