import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 读取真实输入文件 ----------
def load_csv(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8-sig') as f:
        lines = [l.rstrip('\n') for l in f if l.strip() != '']
    if len(lines) < 2:
        return None
    header = [h.strip() for h in lines[0].split(',')]
    rows = []
    for l in lines[1:]:
        parts = l.split(',')
        if len(parts) != len(header):
            continue
        rows.append(parts)
    return header, rows

def to_float(x):
    try:
        return float(x)
    except Exception:
        return np.nan

clean = load_csv('clean_dose_response.csv')
raw = load_csv('raw_dose_response.csv')
ddict = load_csv('data_dictionary.csv')
audit = load_csv('audit_log.csv')

print("=== 输入文件状态 ===")
for name, obj in [('clean_dose_response.csv', clean), ('raw_dose_response.csv', raw),
                  ('data_dictionary.csv', ddict), ('audit_log.csv', audit)]:
    print(f"{name}: {'已读取, 行数=%d' % (len(obj[1]) if obj else 0) if obj else '缺失'}")

if clean is None:
    raise SystemExit("缺少 clean_dose_response.csv，无法继续。")

header, rows = clean
print("clean 列名:", header)

# ---------- 识别列 ----------
def find_col(cands):
    for c in cands:
        for h in header:
            if c.lower() == h.lower():
                return h
    for c in cands:
        for h in header:
            if c.lower() in h.lower():
                return h
    return None

dose_col = find_col(['dose', '剂量', 'concentration', 'conc'])
resp_col = find_col(['response', 'survival', '存活', 'viability', 'inhibition', '抑制'])
print("识别列 -> dose:", dose_col, "| response:", resp_col)
if dose_col is None or resp_col is None:
    raise SystemExit("无法识别剂量/响应列。")

dose = np.array([to_float(r[header.index(dose_col)]) for r in rows])
resp = np.array([to_float(r[header.index(resp_col)]) for r in rows])

# ---------- 缺失率排行（单变量分布与缺失率） ----------
print("\n=== 1. 缺失率排行 ===")
miss = []
for i, h in enumerate(header):
    vals = [r[i] for r in rows]
    n_miss = sum(1 for v in vals if v.strip() == '' or v.strip().lower() in ('na', 'nan', 'null'))
    miss.append((h, n_miss / len(rows)))
for h, m in sorted(miss, key=lambda x: -x[1]):
    print(f"  {h}: 缺失率={m:.3f}")

# ---------- 分组统计 ----------
print("\n=== 2. 按剂量分组统计 (mean/SD/n) ===")
valid = ~(np.isnan(dose) | np.isnan(resp))
dose_v, resp_v = dose[valid], resp[valid]
uniq = np.unique(dose_v)
groups = {}
for d in uniq:
    v = resp_v[dose_v == d]
    groups[d] = v
    print(f"  dose={d:g}: n={len(v)}, mean={np.mean(v):.4f}, SD={np.std(v, ddof=1) if len(v)>1 else float('nan'):.4f}")

# 平台期覆盖判断
means = {d: np.mean(v) for d, v in groups.items()}
dmin, dmax = min(means), max(means)
low_ok = means[dmin] <= 5.0
high_ok = means[dmax] >= 95.0
print(f"\n平台期覆盖: 最低剂量({dmin:g})均值={means[dmin]:.2f} <=5%? {low_ok} | "
      f"最高剂量({dmax:g})均值={means[dmax]:.2f} >=95%? {high_ok}")

# 低置信点 (n<3) 与组间样本量差异
low_conf = [d for d, v in groups.items() if len(v) < 3]
ns = [len(v) for v in groups.values()]
print(f"低置信剂量点(n<3): {low_conf if low_conf else '无'}")
print(f"组间样本量: min={min(ns)}, max={max(ns)}, 极差={max(ns)-min(ns)} "
      f"-> {'存在样本量不均衡风险' if max(ns)-min(ns) >= 3 else '样本量较均衡'}")

# ---------- 相关矩阵 ----------
print("\n=== 3. 相关矩阵与共线性标注 ===")
num_cols = []
num_data = []
for i, h in enumerate(header):
    vals = np.array([to_float(r[i]) for r in rows])
    if np.sum(~np.isnan(vals)) >= 3:
        num_cols.append(h)
        num_data.append(vals)
if len(num_cols) >= 2:
    M = np.vstack(num_data)
    corr = np.zeros((len(num_cols), len(num_cols)))
    for a in range(len(num_cols)):
        for b in range(len(num_cols)):
            xa, xb = M[a], M[b]
            m = ~(np.isnan(xa) | np.isnan(xb))
            if m.sum() >= 3 and np.std(xa[m]) > 0 and np.std(xb[m]) > 0:
                corr[a, b] = np.corrcoef(xa[m], xb[m])[0, 1]
            else:
                corr[a, b] = np.nan
    print("  相关矩阵 (行/列顺序):", num_cols)
    for a in range(len(num_cols)):
        print("   ", " ".join(f"{corr[a,b]:+.2f}" if not np.isnan(corr[a,b]) else " nan " for b in range(len(num_cols))))
    print("  |r|>0.8 共线性特征对:")
    found = False
    for a in range(len(num_cols)):
        for b in range(a+1, len(num_cols)):
            if not np.isnan(corr[a, b]) and abs(corr[a, b]) > 0.8:
                print(f"    {num_cols[a]} <-> {num_cols[b]}: r={corr[a,b]:+.3f}")
                found = True
    if not found:
        print("    无")
    print("  注意: 相关系数仅反映线性关系，剂量-响应常为非线性，勿据此推断因果。")
else:
    print("  数值列不足，跳过相关矩阵。")

# ---------- 目标变量分布 / 类别不平衡 ----------
print("\n=== 4. 目标变量分布 ===")
print(f"  response: min={np.nanmin(resp_v):.3f}, max={np.nanmax(resp_v):.3f}, "
      f"mean={np.nanmean(resp_v):.3f}, median={np.nanmedian(resp_v):.3f}, "
      f"skew={float(np.mean(((resp_v-np.mean(resp_v))/np.std(resp_v))**3)):.3f}")
print("  提示: 仅看均值会掩盖分布形态，需结合直方图/箱线图判断。")

# ---------- 候选特征与风险项 ----------
print("\n=== 5. 候选特征清单与风险项 ===")
print("  候选特征: dose (自变量), response (因变量)")
risks = []
if low_conf:
    risks.append(f"低置信剂量点 n<3: {low_conf} -> 建议合并或补测")
if max(ns) - min(ns) >= 3:
    risks.append("组间样本量差异大 -> 建议加权或分层分析")
if not (low_ok and high_ok):
    risks.append("平台期未完全覆盖 -> 建议扩展剂量范围")
if found:
    risks.append("存在 |r|>0.8 共线性对 -> 建模时需剔除或正则化")
if not risks:
    risks.append("未发现显著风险项")
for r in risks:
    print("  -", r)

# ---------- 绘图 ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
ax = axes[0]
ax.scatter(dose_v, resp_v, s=25, alpha=0.6, color='steelblue', label='样本点')
ax.errorbar(list(means.keys()), list(means.values()),
            yerr=[np.std(v, ddof=1) if len(v) > 1 else 0 for v in groups.values()],
            fmt='o-', color='crimson', capsize=4, label='分组均值±SD')
for d in low_conf:
    ax.axvline(d, color='orange', ls='--', alpha=0.6)
ax.set_xlabel('剂量'); ax.set_ylabel('响应/存活率')
ax.set_title('剂量-响应散点与分组均值'); ax.legend(); ax.grid(alpha=0.3)

ax2 = axes[1]
data_box = [groups[d] for d in uniq]
ax2.boxplot(data_box, labels=[f"{d:g}" for d in uniq])
ax2.set_xlabel('剂量'); ax2.set_ylabel('响应分布')
ax2.set_title('各剂量组分布(箱线图)'); ax2.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print("\n已保存 figure.png")

# ---------- 落盘 ----------
with open('group_stats.csv', 'w', encoding='utf-8-sig') as f:
    f.write("dose,n,mean,sd\n")
    for d in uniq:
        v = groups[d]
        sd = np.std(v, ddof=1) if len(v) > 1 else float('nan')
        f.write(f"{d},{len(v)},{np.mean(v):.6f},{sd:.6f}\n")
print("已保存 group_stats.csv")