import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv, os

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 读取真实输入文件 ----------
def read_csv(path):
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

clean = read_csv('step1_clean_data.csv')
audit = read_csv('step1_audit_log.csv')
ddict = read_csv('step1_data_dictionary.csv')

print("=== 输入文件概览 ===")
print(f"clean_data 行数: {len(clean)}, 列: {list(clean[0].keys())}")
print(f"audit_log 行数: {len(audit)}")
print(f"data_dictionary 行数: {len(ddict)}")

# ---------- 自动识别剂量列与响应列 ----------
cols = list(clean[0].keys())
def find_col(cands):
    for c in cols:
        for k in cands:
            if k.lower() in c.lower():
                return c
    return None

dose_col = find_col(['dose', 'conc', '剂量', '浓度'])
resp_col = find_col(['viab', 'surv', 'response', '存活', '抑制'])
if dose_col is None or resp_col is None:
    # 回退：取前两列
    dose_col, resp_col = cols[0], cols[1]
print(f"剂量列: {dose_col} | 响应列: {resp_col}")

# ---------- 解析数值 ----------
def to_float(x):
    try:
        return float(x)
    except:
        return np.nan

doses = np.array([to_float(r[dose_col]) for r in clean])
resp = np.array([to_float(r[resp_col]) for r in clean])

# 缺失率排行（单变量质量检查）
print("\n=== 缺失率排行 ===")
miss = []
for c in cols:
    n_miss = sum(1 for r in clean if r[c] is None or str(r[c]).strip() == '' or str(r[c]).lower() == 'nan')
    miss.append((c, n_miss / len(clean)))
for c, m in sorted(miss, key=lambda x: -x[1]):
    print(f"  {c}: 缺失率 {m:.3f}")

# ---------- 按剂量分组统计 ----------
uniq = sorted(set(doses[~np.isnan(doses)]))
groups = {}
for d in uniq:
    mask = doses == d
    vals = resp[mask]
    vals = vals[~np.isnan(vals)]
    groups[d] = vals

print("\n=== 按剂量分组统计 (均值/SD/n) ===")
rows = []
for d in uniq:
    v = groups[d]
    n = len(v)
    mean = float(np.mean(v)) if n > 0 else np.nan
    sd = float(np.std(v, ddof=1)) if n > 1 else np.nan
    rows.append((d, mean, sd, n))
    print(f"  剂量={d:g}  n={n}  mean={mean:.3f}  SD={sd:.3f}")

# ---------- 检查最低/最高剂量是否接近 0 / 100 ----------
low_d = uniq[0]
high_d = uniq[-1]
low_mean = rows[0][1]
high_mean = rows[-1][1]
print("\n=== Bottom/Top 固定判断 ===")
print(f"最低剂量 {low_d:g} 均值={low_mean:.3f} -> 是否接近0: {abs(low_mean) < 10}")
print(f"最高剂量 {high_d:g} 均值={high_mean:.3f} -> 是否接近100: {abs(high_mean - 100) < 10}")
fix_bottom = abs(low_mean) < 10
fix_top = abs(high_mean - 100) < 10
print(f"建议: Bottom {'固定为0' if fix_bottom else '自由拟合'}, Top {'固定为100' if fix_top else '自由拟合'}")

# ---------- 低置信点 (n<3) 与样本量差异 ----------
low_conf = [d for d in uniq if len(groups[d]) < 3]
ns = [len(groups[d]) for d in uniq]
print("\n=== 低置信与样本量差异 ===")
print(f"n<3 的剂量点: {low_conf}")
print(f"组间样本量: min={min(ns)}, max={max(ns)}, 极差={max(ns)-min(ns)}")
if max(ns) - min(ns) >= 3:
    print("警告: 组间样本量差异较大，均值比较需谨慎（规避'忽略分组样本量差异'陷阱）")

# ---------- 分布形态检查（规避只看均值） ----------
print("\n=== 分布形态检查（规避只看均值） ===")
for d in uniq:
    v = groups[d]
    if len(v) >= 2:
        sk = float(np.mean(((v - np.mean(v)) / (np.std(v) + 1e-9)) ** 3))
        print(f"  剂量={d:g} 偏度={sk:.3f} 范围=[{v.min():.2f},{v.max():.2f}]")

# ---------- 相关矩阵（标注共线性，规避非线性误读） ----------
num_cols = [c for c in cols if all(to_float(r[c]) is not None and not np.isnan(to_float(r[c])) for r in clean)]
print("\n=== 数值列相关矩阵 ===")
if len(num_cols) >= 2:
    M = np.array([[to_float(r[c]) for c in num_cols] for r in clean])
    C = np.corrcoef(M.T)
    for i in range(len(num_cols)):
        for j in range(i+1, len(num_cols)):
            r = C[i, j]
            flag = " <-- 高共线" if abs(r) > 0.8 else ""
            print(f"  {num_cols[i]} vs {num_cols[j]}: r={r:.3f}{flag}")
    print("注意: 相关系数仅反映线性关系，剂量-响应常为非线性，勿据此下结论")

# ---------- 目标变量分布 / 类别不平衡 ----------
print("\n=== 目标变量分布 ===")
print(f"响应值: min={np.nanmin(resp):.2f}, max={np.nanmax(resp):.2f}, mean={np.nanmean(resp):.2f}, std={np.nanstd(resp):.2f}")

# ---------- 候选特征与风险项 ----------
print("\n=== 候选特征清单 ===")
print(f"  剂量特征: {dose_col}")
print(f"  响应特征: {resp_col}")
print("\n=== 风险项与处理建议 ===")
risks = []
if low_conf:
    risks.append(f"低置信剂量点 {low_conf} (n<3): 建议合并或加权，拟合时降低权重")
if max(ns) - min(ns) >= 3:
    risks.append("组间样本量差异大: 建议用加权回归或分层分析")
if not fix_bottom:
    risks.append("最低剂量未接近0: Bottom 建议自由拟合")
if not fix_top:
    risks.append("最高剂量未接近100: Top 建议自由拟合")
if not risks:
    risks.append("无明显风险项")
for r in risks:
    print(f"  - {r}")

# ---------- 绘图 ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# 左: 剂量-响应散点 + 均值误差棒
ax = axes[0]
ax.scatter(doses, resp, alpha=0.4, s=18, color='steelblue', label='原始数据点')
means = [r[1] for r in rows]
sds = [r[2] if not np.isnan(r[2]) else 0 for r in rows]
ax.errorbar(uniq, means, yerr=sds, fmt='o-', color='crimson', capsize=4, label='均值±SD')
for d in low_conf:
    ax.axvline(d, color='orange', ls='--', alpha=0.5)
    ax.text(d, ax.get_ylim()[1]*0.95, 'n<3', color='orange', fontsize=8, rotation=90)
ax.set_xlabel(f'剂量 ({dose_col})')
ax.set_ylabel(f'响应 ({resp_col})')
ax.set_title('剂量-响应散点与均值')
ax.legend()
ax.grid(alpha=0.3)

# 右: 各剂量分布箱线
ax2 = axes[1]
data_list = [groups[d] for d in uniq]
ax2.boxplot(data_list, labels=[f'{d:g}' for d in uniq])
ax2.set_xlabel('剂量')
ax2.set_ylabel('响应分布')
ax2.set_title('各剂量组分布（箱线）')
ax2.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n已保存 figure.png")

# ---------- 落盘 ----------
with open('step2_group_stats.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['dose', 'mean', 'sd', 'n', 'low_confidence'])
    for d, m, s, n in rows:
        w.writerow([d, m, s, n, d in low_conf])
print("已保存 step2_group_stats.csv")