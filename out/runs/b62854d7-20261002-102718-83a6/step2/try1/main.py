import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv
import os

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 读取真实前序产物 ----------
def read_csv(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

clean = read_csv('step1_clean_data.csv')
audit = read_csv('step1_audit_log.csv')
ddict = read_csv('step1_data_dictionary.csv')

print("=== 输入文件概览 ===")
print("clean_data 行数:", len(clean), "列:", list(clean[0].keys()) if clean else [])
print("audit_log 行数:", len(audit))
print("data_dictionary 行数:", len(ddict))

# ---------- 自动识别列名 ----------
cols = list(clean[0].keys())
def find_col(cands):
    for c in cols:
        for k in cands:
            if k.lower() in c.lower():
                return c
    return None

dose_col = find_col(['dose', '剂量', 'conc', '浓度'])
resp_col = find_col(['survival', '存活', 'response', '响应', 'viab', '抑制'])
print("识别剂量列:", dose_col, "| 响应列:", resp_col)

# ---------- 数值化 ----------
def to_float(x):
    try:
        return float(x)
    except:
        return np.nan

doses = np.array([to_float(r[dose_col]) for r in clean])
resps = np.array([to_float(r[resp_col]) for r in clean])
mask = ~(np.isnan(doses) | np.isnan(resps))
doses, resps = doses[mask], resps[mask]
print("有效数据点:", len(doses))

# ---------- 按剂量分组统计 ----------
uniq = np.unique(doses)
rows = []
for d in uniq:
    v = resps[doses == d]
    rows.append((d, len(v), float(np.mean(v)), float(np.std(v, ddof=1)) if len(v) > 1 else 0.0))
rows.sort(key=lambda r: r[0])

print("\n=== 分组统计 (剂量, n, mean, SD) ===")
for d, n, m, s in rows:
    flag = "  <-- n<3 低置信" if n < 3 else ""
    print(f"dose={d:>10.4g}  n={n:>3d}  mean={m:8.4f}  SD={s:8.4f}{flag}")

ns = np.array([r[1] for r in rows])
print("\n组间样本量: min=%d max=%d 极差=%d 变异系数=%.3f" %
      (ns.min(), ns.max(), ns.max() - ns.min(), ns.std() / ns.mean() if ns.mean() else 0))

# ---------- 最低/最高剂量抑制率检查 (Bottom/Top 是否固定) ----------
low_d, high_d = rows[0], rows[-1]
low_mean, high_mean = low_d[2], high_d[2]
print("\n=== Bottom/Top 固定判断 ===")
print("最低剂量 mean=%.4f (n=%d)" % (low_mean, low_d[1]))
print("最高剂量 mean=%.4f (n=%d)" % (high_mean, high_d[1]))
# 假设响应为存活率(0~1)或抑制率；统一按比例判断
def near(a, b, tol=0.10):
    return abs(a - b) <= tol
bottom_fix = near(low_mean, 0.0, 0.10)
top_fix = near(high_mean, 1.0, 0.10)
print("最低剂量接近0? %s -> Bottom %s" % (bottom_fix, "建议固定=0" if bottom_fix else "建议自由拟合"))
print("最高剂量接近1(100%)? %s -> Top %s" % (top_fix, "建议固定=1" if top_fix else "建议自由拟合"))

# ---------- 陷阱规避检查 ----------
print("\n=== 陷阱规避检查 ===")
# 1. 只看均值不看分布: 报告偏度/极值
for d, n, m, s in rows:
    v = resps[doses == d]
    if n >= 2:
        sk = float(np.mean(((v - m) / (s if s > 0 else 1)) ** 3))
        print(f"dose={d:>10.4g} 偏度={sk:6.3f} min={v.min():.3f} max={v.max():.3f} (分布形态检查)")
# 2. 相关系数解释非线性: 计算线性相关并声明局限
if len(doses) > 2 and np.std(doses) > 0 and np.std(resps) > 0:
    r = float(np.corrcoef(doses, resps)[0, 1])
    print("剂量-响应 Pearson r=%.4f (仅线性参考, 非线性关系不可用r解释)" % r)
# 3. 组间样本量差异
print("组间样本量差异: max/min=%.2f, 已在上方标注 n<3 点" % (ns.max() / ns.min() if ns.min() else float('inf')))

# ---------- 出图 ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# 左: 剂量-响应散点 + 分组均值误差棒
ax = axes[0]
ax.scatter(doses, resps, s=18, alpha=0.4, color='steelblue', label='原始点')
md = [r[0] for r in rows]
mm = [r[2] for r in rows]
ms = [r[3] for r in rows]
ax.errorbar(md, mm, yerr=ms, fmt='o-', color='crimson', capsize=4, label='分组均值±SD')
for d, n, m, s in rows:
    if n < 3:
        ax.annotate('n<3', (d, m), textcoords="offset points", xytext=(0, 8),
                    ha='center', fontsize=8, color='darkorange')
ax.set_xlabel('剂量'); ax.set_ylabel('响应')
ax.set_title('剂量-响应散点与分组均值'); ax.legend(); ax.grid(alpha=0.3)

# 右: 分组分布箱线
ax2 = axes[1]
data = [resps[doses == d] for d in uniq]
bp = ax2.boxplot(data, positions=range(len(uniq)), widths=0.6, patch_artist=True)
for patch in bp['boxes']:
    patch.set_facecolor('lightsteelblue')
ax2.set_xticks(range(len(uniq)))
ax2.set_xticklabels([f"{d:.3g}\n(n={r[1]})" for d, r in zip(uniq, rows)], fontsize=8)
ax2.set_xlabel('剂量 (n)'); ax2.set_ylabel('响应')
ax2.set_title('各剂量组分布'); ax2.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print("\n已保存 figure.png")

# ---------- 落盘 ----------
with open('step2_group_stats.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['dose', 'n', 'mean', 'sd', 'low_confidence'])
    for d, n, m, s in rows:
        w.writerow([d, n, m, s, int(n < 3)])

with open('step2_risk_items.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['risk_item', 'detail', 'suggestion'])
    w.writerow(['Bottom固定', f'最低剂量mean={low_mean:.4f}',
                '固定Bottom=0' if bottom_fix else '自由拟合Bottom'])
    w.writerow(['Top固定', f'最高剂量mean={high_mean:.4f}',
                '固定Top=1' if top_fix else '自由拟合Top'])
    w.writerow(['低置信点', f'n<3的剂量数={int((ns<3).sum())}', '拟合时降权或剔除'])
    w.writerow(['样本量差异', f'max/min={ns.max()/ns.min() if ns.min() else float("inf"):.2f}',
                '加权拟合或分层分析'])
print("已保存 step2_group_stats.csv, step2_risk_items.csv")