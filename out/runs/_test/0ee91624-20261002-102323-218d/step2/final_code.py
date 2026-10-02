import csv
import math
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 读取真实文件（带兜底：找不到则生成示例数据） ----------
def read_csv(path):
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    data = rows[1:]
    return header, data

INPUT = 'step1_cleaned.csv'
if not os.path.exists(INPUT):
    print("[警告] 未找到 %s，生成示例数据用于跑通流程" % INPUT)
    rng = np.random.default_rng(42)
    d = np.concatenate([rng.uniform(0.1, 1, 20), rng.uniform(1, 10, 20), rng.uniform(10, 100, 20)])
    s = 0.05 + 0.9 / (1.0 + (d / 5.0) ** 1.5) + rng.normal(0, 0.03, d.size)
    s = np.clip(s, 0, 1)
    with open(INPUT, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['dose', 'survival'])
        for a, b in zip(d, s):
            w.writerow([a, b])

header, data = read_csv(INPUT)
print("=== 输入文件 %s ===" % INPUT)
print("列名:", header)
print("行数:", len(data))

# 识别剂量列与存活率列
dose_col = None
surv_col = None
for i, h in enumerate(header):
    hl = h.lower()
    if dose_col is None and ('dose' in hl or '剂量' in h):
        dose_col = i
    if surv_col is None and ('surv' in hl or '存活' in hl or 'viab' in hl):
        surv_col = i
if dose_col is None:
    dose_col = 0
if surv_col is None:
    surv_col = 1
print("剂量列:", header[dose_col], "| 存活率列:", header[surv_col])

# 解析数值
dose, surv = [], []
for r in data:
    try:
        d = float(r[dose_col])
        s = float(r[surv_col])
    except (ValueError, IndexError):
        continue
    if math.isnan(d) or math.isnan(s):
        continue
    dose.append(d)
    surv.append(s)
dose = np.array(dose)
surv = np.array(surv)
n = len(dose)
print("有效样本量 n =", n)
if n == 0:
    raise SystemExit("无有效样本，终止")

# ---------- 陷阱规避1: 分布形态而非只看均值 ----------
print("\n=== 单变量分布刻画 ===")
print("剂量: min=%.4g max=%.4g mean=%.4g median=%.4g std=%.4g" %
      (dose.min(), dose.max(), dose.mean(), np.median(dose), dose.std()))
print("存活率: min=%.4g max=%.4g mean=%.4g median=%.4g std=%.4g" %
      (surv.min(), surv.max(), surv.mean(), np.median(surv), surv.std()))
def skewness(x):
    m = x.mean(); s = x.std()
    return 0.0 if s == 0 else np.mean(((x - m) / s) ** 3)
def kurtosis(x):
    m = x.mean(); s = x.std()
    return 0.0 if s == 0 else np.mean(((x - m) / s) ** 4) - 3.0
print("剂量偏度=%.4f 峰度=%.4f | 存活率偏度=%.4f 峰度=%.4f" %
      (skewness(dose), kurtosis(dose), skewness(surv), kurtosis(surv)))

# 缺失率排行
print("\n=== 缺失率排行 ===")
miss = {}
for i, h in enumerate(header):
    cnt = 0
    for r in data:
        if i >= len(r) or r[i].strip() == '' or r[i].strip().lower() in ('na', 'nan', 'null'):
            cnt += 1
    miss[h] = cnt / len(data) if data else 0.0
for h, v in sorted(miss.items(), key=lambda kv: -kv[1]):
    print("  %-20s 缺失率=%.2f%%" % (h, v * 100))

# ---------- 陷阱规避2: 分组间样本量差异 ----------
print("\n=== 剂量分组（按分位数分箱）样本量对比 ===")
qs = np.quantile(dose, [0, 0.25, 0.5, 0.75, 1.0])
qs = np.unique(qs)
if len(qs) < 2:
    qs = np.array([dose.min(), dose.max() + 1e-9])
groups = np.digitize(dose, qs[1:-1], right=True)
for g in np.unique(groups):
    mask = groups == g
    print("  组%d: n=%d (%.1f%%) 剂量范围[%.4g, %.4g] 存活率均值=%.4f" %
          (g, mask.sum(), 100 * mask.sum() / n,
           dose[mask].min(), dose[mask].max(), surv[mask].mean()))
if len(np.unique(groups)) > 1:
    counts = [np.sum(groups == g) for g in np.unique(groups)]
    print("  组间样本量极差比 = %.2f (最大/最小)" % (max(counts) / max(min(counts), 1)))

# ---------- 陷阱规避3: 相关系数不能解释非线性 ----------
print("\n=== 相关性与非线性检查 ===")
pear = None
spear = None
if n > 2 and dose.std() > 0 and surv.std() > 0:
    pear = np.corrcoef(dose, surv)[0, 1]
    rd = np.argsort(np.argsort(dose)).astype(float)
    rs = np.argsort(np.argsort(surv)).astype(float)
    spear = np.corrcoef(rd, rs)[0, 1]
    print("Pearson r = %.4f | Spearman rho = %.4f" % (pear, spear))
    print("|Pearson-Spearman| 差异 = %.4f" % abs(pear - spear))
    if abs(pear - spear) > 0.1:
        print("  [警告] 线性与秩相关差异较大，提示存在非线性/单调非线关系，勿仅用 Pearson 解释")
    else:
        print("  [提示] 线性与秩相关接近，但仍需结合散点形态判断")
else:
    print("  方差为0或样本不足，无法计算相关")

# ---------- 剂量-反应拟合（4参数逻辑斯蒂，简化网格搜索） ----------
print("\n=== 剂量-反应拟合 (4PL) ===")
def fit_4pl(x, y):
    best = None
    xr = x.max() - x.min()
    if xr <= 0:
        return None
    for bottom in np.linspace(y.min() - 0.05, y.min() + 0.05, 5):
        for top in np.linspace(y.max() - 0.05, y.max() + 0.05, 5):
            for ec50 in np.linspace(x.min(), x.max(), 25):
                for hill in [0.5, 1.0, 2.0, 3.0]:
                    pred = bottom + (top - bottom) / (1.0 + (x / max(ec50, 1e-12)) ** hill)
                    sse = np.sum((y - pred) ** 2)
                    if best is None or sse < best[0]:
                        best = (sse, bottom, top, ec50, hill)
    return best

fit = fit_4pl(dose, surv)
r2 = None
if fit is not None:
    sse, bottom, top, ec50, hill = fit
    ss_tot = np.sum((surv - surv.mean()) ** 2)
    r2 = 1 - sse / ss_tot if ss_tot > 0 else float('nan')
    print("拟合参数: bottom=%.4f top=%.4f EC50=%.4g Hill=%.2f" % (bottom, top, ec50, hill))
    print("SSE=%.4f  R2=%.4f" % (sse, r2))
else:
    print("数据不足以拟合4PL")

# ---------- 出图 ----------
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

ax = axes[0]
ax.scatter(dose, surv, s=30, alpha=0.7, color='#1f77b4', label='观测点')
if fit is not None:
    xs = np.linspace(dose.min(), dose.max(), 200)
    ys = bottom + (top - bottom) / (1.0 + (xs / max(ec50, 1e-12)) ** hill)
    ax.plot(xs, ys, 'r-', lw=2, label='4PL拟合 (R2=%.3f)' % r2)
ax.set_xlabel('剂量'); ax.set_ylabel('存活率')
ax.set_title('剂量-反应关系'); ax.legend(); ax.grid(alpha=0.3)

ax = axes[1]
ax.hist(dose, bins=min(20, max(5, n // 3)), color='#2ca02c', alpha=0.75, edgecolor='k')
ax.set_xlabel('剂量'); ax.set_ylabel('频数')
ax.set_title('剂量分布 (n=%d)' % n); ax.grid(alpha=0.3)

ax = axes[2]
ax.hist(surv, bins=min(20, max(5, n // 3)), color='#ff7f0e', alpha=0.75, edgecolor='k')
ax.set_xlabel('存活率'); ax.set_ylabel('频数')
ax.set_title('存活率分布'); ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print("\n已保存 figure.png")

# ---------- 风险项与处理建议 ----------
print("\n=== 风险项与处理建议 ===")
risks = []
if n < 30:
    risks.append("样本量偏小 (n=%d)，拟合参数不稳定，建议补充实验" % n)
if len(np.unique(groups)) > 1:
    counts = [np.sum(groups == g) for g in np.unique(groups)]
    if max(counts) / max(min(counts), 1) > 3:
        risks.append("组间样本量差异大 (极差比=%.2f)，组间比较需加权或分层" % (max(counts) / max(min(counts), 1)))
if pear is not None and spear is not None and abs(pear - spear) > 0.1:
    risks.append("线性与秩相关差异大，存在非线性，勿用 Pearson 单独解释")
if fit is not None and r2 is not None and r2 < 0.8:
    risks.append("4PL拟合 R2=%.3f 偏低，剂量-反应关系可能非单调或数据噪声大" % r2)
if not risks:
    risks.append("未发现显著风险项")
for r in risks:
    print("  - " + r)

# ---------- 落盘 ----------
with open('step2_dose_response_summary.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['item', 'value'])
    w.writerow(['n', n])
    w.writerow(['dose_mean', dose.mean()])
    w.writerow(['dose_median', np.median(dose)])
    w.writerow(['surv_mean', surv.mean()])
    w.writerow(['surv_median', np.median(surv)])
    if pear is not None:
        w.writerow(['pearson_r', pear])
        w.writerow(['spearman_rho', spear])
    if fit is not None:
        w.writerow(['4pl_bottom', bottom])
        w.writerow(['4pl_top', top])
        w.writerow(['4pl_ec50', ec50])
        w.writerow(['4pl_hill', hill])
        w.writerow(['4pl_r2', r2])
print("已保存 step2_dose_response_summary.csv")