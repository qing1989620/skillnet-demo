import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv
import os
import glob

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def locate(name):
    if os.path.exists(name):
        return name
    here = os.path.dirname(os.path.abspath(__file__))
    cands = []
    for base in [here, os.path.dirname(here), os.getcwd(),
                 os.path.dirname(os.getcwd())]:
        cands.append(os.path.join(base, name))
        cands.append(os.path.join(base, 'step1', name))
        cands.append(os.path.join(base, '..', 'step1', name))
    for c in cands:
        if os.path.exists(c):
            return c
    for base in [here, os.getcwd()]:
        for root, _, files in os.walk(base):
            if name in files:
                return os.path.join(root, name)
    return None


def read_csv(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


clean_path = locate('step1_clean_data.csv')
audit_path = locate('step1_audit_log.csv')
ddict_path = locate('step1_data_dictionary.csv')

if clean_path is None:
    for base in [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]:
        hits = glob.glob(os.path.join(base, '**', '*clean*.csv'), recursive=True)
        if hits:
            clean_path = hits[0]
            break

if clean_path is None:
    raise FileNotFoundError(
        "未找到 step1_clean_data.csv。当前目录: %s\n目录内容: %s" %
        (os.getcwd(), os.listdir(os.getcwd()))
    )

print("使用 clean 文件:", clean_path)
clean = read_csv(clean_path)
audit = read_csv(audit_path) if audit_path else []
ddict = read_csv(ddict_path) if ddict_path else []

print("=== 输入文件概览 ===")
print("clean_data 行数:", len(clean), "列:", list(clean[0].keys()) if clean else [])
print("audit_log 行数:", len(audit))
print("data_dictionary 行数:", len(ddict))

if not clean:
    raise ValueError("clean_data 为空，无法继续分析")

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

if dose_col is None or resp_col is None:
    numeric_cols = []
    for c in cols:
        try:
            float(clean[0][c])
            numeric_cols.append(c)
        except Exception:
            pass
    if len(numeric_cols) >= 2:
        dose_col = dose_col or numeric_cols[0]
        resp_col = resp_col or numeric_cols[1]
        print("兜底识别剂量列:", dose_col, "| 响应列:", resp_col)
    else:
        raise ValueError("无法识别剂量/响应列，列名: %s" % cols)


def to_float(x):
    try:
        return float(x)
    except Exception:
        return np.nan


doses = np.array([to_float(r.get(dose_col, '')) for r in clean])
resps = np.array([to_float(r.get(resp_col, '')) for r in clean])
mask = ~(np.isnan(doses) | np.isnan(resps))
doses, resps = doses[mask], resps[mask]
print("有效数据点:", len(doses))

if len(doses) == 0:
    raise ValueError("无有效数值数据点")

uniq = np.unique(doses)
rows = []
for d in uniq:
    v = resps[doses == d]
    rows.append((float(d), int(len(v)), float(np.mean(v)),
                 float(np.std(v, ddof=1)) if len(v) > 1 else 0.0))
rows.sort(key=lambda r: r[0])

print("\n=== 分组统计 (剂量, n, mean, SD) ===")
for d, n, m, s in rows:
    flag = "  <-- n<3 低置信" if n < 3 else ""
    print("dose=%10.4g  n=%3d  mean=%8.4f  SD=%8.4f%s" % (d, n, m, s, flag))

ns = np.array([r[1] for r in rows])
print("\n组间样本量: min=%d max=%d 极差=%d 变异系数=%.3f" %
      (ns.min(), ns.max(), ns.max() - ns.min(),
       ns.std() / ns.mean() if ns.mean() else 0))

low_d, high_d = rows[0], rows[-1]
low_mean, high_mean = low_d[2], high_d[2]
print("\n=== Bottom/Top 固定判断 ===")
print("最低剂量 mean=%.4f (n=%d)" % (low_mean, low_d[1]))
print("最高剂量 mean=%.4f (n=%d)" % (high_mean, high_d[1]))


def near(a, b, tol=0.10):
    return abs(a - b) <= tol


bottom_fix = near(low_mean, 0.0, 0.10)
top_fix = near(high_mean, 1.0, 0.10)
print("最低剂量接近0? %s -> Bottom %s" % (bottom_fix, "建议固定=0" if bottom_fix else "建议自由拟合"))
print("最高剂量接近1(100%%)? %s -> Top %s" % (top_fix, "建议固定=1" if top_fix else "建议自由拟合"))

print("\n=== 陷阱规避检查 ===")
for d, n, m, s in rows:
    v = resps[doses == d]
    if n >= 2:
        sk = float(np.mean(((v - m) / (s if s > 0 else 1)) ** 3))
        print("dose=%10.4g 偏度=%6.3f min=%.3f max=%.3f (分布形态检查)" %
              (d, sk, v.min(), v.max()))

if len(doses) > 2 and np.std(doses) > 0 and np.std(resps) > 0:
    r = float(np.corrcoef(doses, resps)[0, 1])
    print("剂量-响应 Pearson r=%.4f (仅线性参考, 非线性关系不可用r解释)" % r)

print("组间样本量差异: max/min=%.2f, 已在上方标注 n<3 点" %
      (ns.max() / ns.min() if ns.min() else float('inf')))

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

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
ax.set_xlabel('剂量')
ax.set_ylabel('响应')
ax.set_title('剂量-响应散点与分组均值')
ax.legend()
ax.grid(alpha=0.3)

ax2 = axes[1]
data = [resps[doses == d] for d in uniq]
bp = ax2.boxplot(data, positions=range(len(uniq)), widths=0.6, patch_artist=True)
for patch in bp['boxes']:
    patch.set_facecolor('lightsteelblue')
ax2.set_xticks(range(len(uniq)))
ax2.set_xticklabels(["%.3g\n(n=%d)" % (d, r[1]) for d, r in zip(uniq, rows)], fontsize=8)
ax2.set_xlabel('剂量 (n)')
ax2.set_ylabel('响应')
ax2.set_title('各剂量组分布')
ax2.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print("\n已保存 figure.png")

with open('step2_group_stats.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['dose', 'n', 'mean', 'sd', 'low_confidence'])
    for d, n, m, s in rows:
        w.writerow([d, n, m, s, int(n < 3)])

with open('step2_risk_items.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['risk_item', 'detail', 'suggestion'])
    w.writerow(['Bottom固定', '最低剂量mean=%.4f' % low_mean,
                '固定Bottom=0' if bottom_fix else '自由拟合Bottom'])
    w.writerow(['Top固定', '最高剂量mean=%.4f' % high_mean,
                '固定Top=1' if top_fix else '自由拟合Top'])
    w.writerow(['低置信点', 'n<3的剂量数=%d' % int((ns < 3).sum()), '拟合时降权或剔除'])
    w.writerow(['样本量差异', 'max/min=%.2f' % (ns.max() / ns.min() if ns.min() else float('inf')),
                '加权拟合或分层分析'])
print("已保存 step2_group_stats.csv, step2_risk_items.csv")