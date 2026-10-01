# -*- coding: utf-8 -*-
"""
MathorCup 大数据竞赛 - EDA 步骤
单变量分布 / 缺失率 / 分组基线 / 相关矩阵 / 目标不平衡 / 候选特征与风险项

注意：本脚本在无真实数据时使用【模拟数据】，所有输出均标注为模拟数据结论，
      不代表任何真实实验结论。
仅使用 numpy 2.5.3 与 matplotlib 3.11.2（不引入 pandas / scipy / sklearn）。
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

np.random.seed(42)

# ============================================================
# 0. 构造【模拟数据】（明确标注）
# ============================================================
N = 1200
print("=" * 70)
print("【重要声明】以下全部数据为模拟数据，结论仅用于演示 EDA 流程，")
print("           不代表任何真实实验结论。")
print("=" * 70)

# 分组变量：region（3 组，样本量不均，其中一组 <30 用于触发描述性报告规则）
region = np.random.choice(['A区', 'B区', 'C区'], size=N, p=[0.55, 0.42, 0.03])

# 连续特征
age = np.random.normal(38, 12, N).clip(18, 80)
income = np.random.normal(9000, 3000, N).clip(1000, 30000)
# 与 income 高度共线（用于触发共线性标记）
income_dup = income * 1.02 + np.random.normal(0, 150, N)
# 与 age 中等相关
work_years = age * 0.6 + np.random.normal(0, 6, N)
# 非线性关系特征（用于演示"相关系数不能解释非线性"陷阱）
x_nonlin = np.random.uniform(-3, 3, N)
y_nonlin = x_nonlin ** 2 + np.random.normal(0, 0.5, N)
# 序数特征
edu_level = np.random.choice([1, 2, 3, 4], size=N, p=[0.2, 0.4, 0.3, 0.1])
# 类别特征
channel = np.random.choice(['线上', '线下', '代理'], size=N, p=[0.5, 0.3, 0.2])

# 目标变量：二分类，少数类占比约 6%（触发不平衡规则）
logit = -3.0 + 0.02 * (income / 1000) + 0.03 * age
p_pos = 1 / (1 + np.exp(-logit))
target = (np.random.uniform(0, 1, N) < p_pos).astype(int)

# 注入缺失（不同列不同缺失率）
def inject_missing(arr, rate):
    arr = arr.astype(float).copy()
    idx = np.random.choice(N, int(N * rate), replace=False)
    arr[idx] = np.nan
    return arr

age = inject_missing(age, 0.02)
income = inject_missing(income, 0.08)
income_dup = inject_missing(income_dup, 0.08)
work_years = inject_missing(work_years, 0.15)
x_nonlin = inject_missing(x_nonlin, 0.01)
y_nonlin = inject_missing(y_nonlin, 0.01)
edu_level = inject_missing(edu_level, 0.05)

# 组装为 dict（避免依赖 pandas）
data = {
    'age': age,
    'income': income,
    'income_dup': income_dup,
    'work_years': work_years,
    'x_nonlin': x_nonlin,
    'y_nonlin': y_nonlin,
    'edu_level': edu_level,
}
cat_data = {
    'region': region,
    'channel': channel,
}
target = target.astype(float)

feature_names = list(data.keys())
cat_names = list(cat_data.keys())

# ============================================================
# 工具函数
# ============================================================
def nan_mask(a):
    return ~np.isnan(a)

def pearson(x, y):
    m = nan_mask(x) & nan_mask(y)
    if m.sum() < 3:
        return np.nan
    xv, yv = x[m], y[m]
    if np.std(xv) == 0 or np.std(yv) == 0:
        return np.nan
    return float(np.corrcoef(xv, yv)[0, 1])

def spearman(x, y):
    m = nan_mask(x) & nan_mask(y)
    if m.sum() < 3:
        return np.nan
    xv, yv = x[m], y[m]
    rx = np.argsort(np.argsort(xv)).astype(float)
    ry = np.argsort(np.argsort(yv)).astype(float)
    if np.std(rx) == 0 or np.std(ry) == 0:
        return np.nan
    return float(np.corrcoef(rx, ry)[0, 1])

def cramers_v(c1, c2):
    """类别-类别关联强度"""
    cats1 = np.unique(c1)
    cats2 = np.unique(c2)
    table = np.zeros((len(cats1), len(cats2)))
    for i, a in enumerate(cats1):
        for j, b in enumerate(cats2):
            table[i, j] = np.sum((c1 == a) & (c2 == b))
    n = table.sum()
    if n == 0:
        return np.nan
    row_sum = table.sum(axis=1, keepdims=True)
    col_sum = table.sum(axis=0, keepdims=True)
    expected = row_sum @ col_sum / n
    with np.errstate(divide='ignore', invalid='ignore'):
        chi2 = np.nansum((table - expected) ** 2 / np.where(expected == 0, np.nan, expected))
    if n == 0:
        return np.nan
    k = min(table.shape) - 1
    if k <= 0:
        return np.nan
    return float(np.sqrt(chi2 / (n * k)))

def vif_for_feature(X, j):
    """用其余列线性回归第 j 列，返回 VIF（含截距）"""
    cols = [c for c in range(X.shape[1]) if c != j]
    Xo = X[:, cols]
    y = X[:, j]
    m = ~np.isnan(y) & ~np.isnan(Xo).any(axis=1)
    if m.sum() < Xo.shape[1] + 2:
        return np.nan
    Xo_m = Xo[m]
    y_m = y[m]
    Xd = np.column_stack([np.ones(Xo_m.shape[0]), Xo_m])
    try:
        beta, *_ = np.linalg.lstsq(Xd, y_m, rcond=None)
    except np.linalg.LinAlgError:
        return np.nan
    y_hat = Xd @ beta
    ss_res = np.sum((y_m - y_hat) ** 2)
    ss_tot = np.sum((y_m - y_m.mean()) ** 2)
    if ss_tot == 0:
        return np.nan
    r2 = 1 - ss_res / ss_tot
    if r2 >= 1:
        return np.inf
    return float(1 / (1 - r2))

# ============================================================
# 1. 单变量分布与缺失率排行
# ============================================================
print("\n" + "=" * 70)
print("【步骤1】单变量分布与缺失率排行（模拟数据）")
print("=" * 70)

missing_rows = []
for name in feature_names:
    a = data[name]
    miss = np.mean(np.isnan(a))
    valid = a[~np.isnan(a)]
    missing_rows.append((name, miss, len(valid),
                         np.mean(valid), np.std(valid),
                         np.percentile(valid, 25), np.median(valid),
                         np.percentile(valid, 75),
                         float(np.min(valid)), float(np.max(valid))))
missing_rows.sort(key=lambda r: -r[1])

print(f"{'特征':<12}{'缺失率':>8}{'有效N':>8}{'均值':>10}{'标准差':>10}{'P25':>10}{'中位数':>10}{'P75':>10}{'偏度':>10}")
for r in missing_rows:
    name, miss, n, mu, sd, p25, med, p75, mn, mx = r
    a = data[name]
    v = a[~np.isnan(a)]
    if len(v) > 2 and np.std(v) > 0:
        skew = float(np.mean(((v - v.mean()) / v.std()) ** 3))
    else:
        skew = np.nan
    print(f"{name:<12}{miss:>8.2%}{n:>8d}{mu:>10.2f}{sd:>10.2f}{p25:>10.2f}{med:>10.2f}{p75:>10.2f}{skew:>10.2f}")

print("\n[陷阱规避] 分布形态检查（均值 vs 中位数 vs 偏度）：")
for r in missing_rows:
    name, miss, n, mu, sd, p25, med, p75, mn, mx = r
    a = data[name]
    v = a[~np.isnan(a)]
    skew = float(np.mean(((v - v.mean()) / v.std()) ** 3)) if np.std(v) > 0 else np.nan
    flag = "偏态明显" if abs(skew) > 1 else "近似对称"
    gap = abs(mu - med) / (sd + 1e-9)
    print(f"  {name:<12} 偏度={skew:>6.2f}  |均值-中位数|/std={gap:.3f}  -> {flag}")

# ============================================================
# 2. 分组对比（按 region）
# ============================================================
print("\n" + "=" * 70)
print("【步骤2】按 region 分组基线对比（模拟数据）")
print("=" * 70)

groups = np.unique(region)
group_sizes = {g: int(np.sum(region == g)) for g in groups}
print("分组样本量：", group_sizes)
small_groups = [g for g, s in group_sizes.items() if s < 30]
print(f"[陷阱规避] 样本量<30 的分组（仅描述性报告，不做推断）：{small_groups}")

group_table = []
for name in feature_names:
    a = data[name]
    row = {'feature': name}
    for g in groups:
        m = (region == g) & ~np.isnan(a)
        v = a[m]
        row[f'{g}_n'] = int(m.sum())
        row[f'{g}_mean'] = float(np.mean(v)) if len(v) > 0 else np.nan
        row[f'{g}_median'] = float(np.median(v)) if len(v) > 0 else np.nan
        row[f'{g}_std'] = float(np.std(v)) if len(v) > 0 else np.nan
    group_table.append(row)

print(f"\n{'特征':<12}{'组':<6}{'N':>6}{'均值':>12}{'中位数':>12}{'标准差':>12}")
for row in group_table:
    for g in groups:
        print(f"{row['feature']:<12}{g:<6}{row[f'{g}_n']:>6d}"
              f"{row[f'{g}_mean']:>12.2f}{row[f'{g}_median']:>12.2f}{row[f'{g}_std']:>12.2f}")

# 组间差异（仅对样本量>=30 的组做描述性差异，不做统计推断）
print("\n[组间基线可比性] 仅对样本量>=30 的组做描述性差异（不做推断）：")
valid_groups = [g for g in groups if group_sizes[g] >= 30]
for name in feature_names:
    a = data[name]
    means = []
    for g in valid_groups:
        m = (region == g) & ~np.isnan(a)
        if m.sum() > 0:
            means.append(np.mean(a[m]))
    if len(means) >= 2:
        spread = max(means) - min(means)
        overall = np.nanmean(a)
        rel = spread / (abs(overall) + 1e-9)
        print(f"  {name:<12} 组间均值极差={spread:>10.2f}  相对差异={rel:>7.2%}  "
              f"{'差异较大' if rel > 0.2 else '差异较小'}")

# ============================================================
# 3. 相关矩阵与共线性标注
# ============================================================
print("\n" + "=" * 70)
print("【步骤3】相关矩阵与共线性标注（模拟数据）")
print("=" * 70)

# 连续-连续：Pearson 与 Spearman 同时计算
n_feat = len(feature_names)
pear_mat = np.full((n_feat, n_feat), np.nan)
spear_mat = np.full((n_feat, n_feat), np.nan)
for i in range(n_feat):
    for j in range(n_feat):
        if i == j:
            pear_mat[i, j] = 1.0
            spear_mat[i, j] = 1.0
        else:
            pear_mat[i, j] = pearson(data[feature_names[i]], data[feature_names[j]])
            spear_mat[i, j] = spearman(data[feature_names[i]], data[feature_names[j]])

print("\nPearson 相关矩阵：")
print("            " + "".join(f"{n:>12}" for n in feature_names))
for i, n in enumerate(feature_names):
    print(f"{n:<12}" + "".join(f"{pear_mat[i, j]:>12.3f}" for j in range(n_feat)))

print("\nSpearman 相关矩阵（用于非正态/序数）：")
print("            " + "".join(f"{n:>12}" for n in feature_names))
for i, n in enumerate(feature_names):
    print(f"{n:<12}" + "".join(f"{spear_mat[i, j]:>12.3f}" for j in range(n_feat)))

# 高共线性对（|Pearson r| > 0.85）
COLLINEAR_THRESHOLD = 0.85
collinear_pairs = []
for i in range(n_feat):
    for j in range(i + 1, n_feat):
        r = pear_mat[i, j]
        if not np.isnan(r) and abs(r) > COLLINEAR_THRESHOLD:
            collinear_pairs.append((feature_names[i], feature_names[j], r))

print(f"\n[共线性标记] |Pearson r| > {COLLINEAR_THRESHOLD} 的特征对：")
if collinear_pairs:
    for a, b, r in collinear_pairs:
        print(f"  {a} <-> {b}  r = {r:.4f}  -> 候选剔除")
else:
    print("  无")

# VIF 计算
print("\n[VIF 计算] 对连续特征做 VIF（含截距）：")
X_vif = np.column_stack([data[n] for n in feature_names])
vif_results = []
for j, n in enumerate(feature_names):
    v = vif_for_feature(X_vif, j)
    vif_results.append((n, v))
    flag = "VIF>10 候选剔除" if (not np.isnan(v) and v > 10) else "正常"
    print(f"  {n:<12} VIF = {v:>10.3f}  -> {flag}")

# 类别-类别 Cramér's V
print("\n[类别-类别] Cramér's V：")
for i in range(len(cat_names)):
    for j in range(i + 1, len(cat_names)):
        v = cramers_v(cat_data[cat_names[i]], cat_data[cat_names[j]])
        print(f"  {cat_names[i]} <-> {cat_names[j]}  V = {v:.4f}")

# 非线性陷阱检查
print("\n[陷阱规避] 相关系数不能解释非线性关系：")
r_lin = pearson(data['x_nonlin'], data['y_nonlin'])
print(f"  x_nonlin 与 y_nonlin 的 Pearson r = {r_lin:.4f}（接近0）")
print(f"  但 y_nonlin = x_nonlin^2 + 噪声，存在强非线性关系。")
print(f"  -> 结论：低相关不等于无关系，需结合散点图/分箱均值判断。")

# ============================================================
# 4. 目标变量分布与类别不平衡
# ============================================================
print("\n" + "=" * 70)
print("【步骤4】目标变量分布与类别不平衡（模拟数据）")
print("=" * 70)

pos = int(np.sum(target == 1))
neg = int(np.sum(target == 0))
minority_ratio = min(pos, neg) / (pos + neg)
print(f"目标变量：正类={pos}，负类={neg}，正类占比={pos/(pos+neg):.2%}")
print(f"少数类占比 = {minority_ratio:.2%}")
IMBALANCE_THRESHOLD = 0.10
if minority_ratio < IMBALANCE_THRESHOLD:
    print(f"[不平衡判定] 少数类占比 < {IMBALANCE_THRESHOLD:.0%} -> 启用分层划分 + 类别权重")
    imbalance_flag = True
else:
    print(f"[不平衡判定] 少数类占比 >= {IMBALANCE_THRESHOLD:.0%} -> 无需特殊处理")
    imbalance_flag = False

# ============================================================
# 5. 输出候选特征清单与风险项
# ============================================================
print("\n" + "=" * 70)
print("【步骤5】候选特征清单与风险项（模拟数据）")
print("=" * 70)

# 候选特征：缺失率<30%，且不在高共线性对中（保留信息量更大的一个）
drop_due_collinear = set()
for a, b, r in collinear_pairs:
    # 保留缺失率更低的
    miss_a = np.mean(np.isnan(data[a]))
    miss_b = np.mean(np.isnan(data[b]))
    drop = b if miss_a <= miss_b else a
    drop_due_collinear.add(drop)

candidate_features = []
risk_items = []

for name in feature_names:
    miss = np.mean(np.isnan(data[name]))
    if miss >= 0.30:
        risk_items.append(f"- **{name}**：缺失率 {miss:.2%} >= 30%，建议剔除或谨慎插补。")
        continue
    if name in drop_due_collinear:
        risk_items.append(f"- **{name}**：与高共线特征对中的另一特征高度相关（|r|>{COLLINEAR_THRESHOLD}），建议剔除。")
        continue
    candidate_features.append(name)

# 高 VIF 风险
for n, v in vif_results:
    if not np.isnan(v) and v > 10:
        risk_items.append(f"- **{n}**：VIF={v:.2f} > 10，存在多重共线性风险，建议剔除或做正则化。")

# 偏态风险
for r in missing_rows:
    name, miss, n, mu, sd, p25, med, p75, mn, mx = r
    a = data[name]
    v = a[~np.isnan(a)]
    if np.std(v) > 0:
        skew = float(np.mean(((v - v.mean()) / v.std()) ** 3))
        if abs(skew) > 1:
            risk_items.append(f"- **{name}**：偏度={skew:.2f}，分布明显偏态，建议做变换（log/Box-Cox）或分箱。")

# 分组样本量风险
for g, s in group_sizes.items():
    if s < 30:
        risk_items.append(f"- **region={g}**：样本量={s} < 30，仅做描述性报告，不做统计推断。")

# 不平衡风险
if imbalance_flag:
    risk_items.append(f"- **目标变量**：少数类占比={minority_ratio:.2%} < 10%，建议分层划分 + 类别权重（class_weight='balanced'）。")

# 非线性风险
risk_items.append(f"- **x_nonlin / y_nonlin**：Pearson r={r_lin:.4f} 接近 0，但存在强非线性关系，"
                  f"建议加入多项式/分箱特征，勿仅凭相关系数判断重要性。")

print("\n候选特征清单：")
for f in candidate_features:
    print(f"  - {f}")

print("\n风险项：")
for r in risk_items:
    print(r)

# ============================================================
# 6. 落盘：candidate_features.csv 与 risk_items.md
# ============================================================
with open('candidate_features.csv', 'w', encoding='utf-8') as f:
    f.write("feature,missing_rate,mean,std,skew,status\n")
    for name in feature_names:
        a = data[name]
        v = a[~np.isnan(a)]
        miss = np.mean(np.isnan(a))
        mu = np.mean(v) if len(v) > 0 else np.nan
        sd = np.std(v) if len(v) > 0 else np.nan
        skew = float(np.mean(((v - v.mean()) / v.std()) ** 3)) if len(v) > 2 and np.std(v) > 0 else np.nan
        status = "candidate" if name in candidate_features else "dropped"
        f.write(f"{name},{miss:.4f},{mu:.4f},{sd:.4f},{skew:.4f},{status}\n")

with open('risk_items.md', 'w', encoding='utf-8') as f:
    f.write("# 风险项清单（模拟数据）\n\n")
    f.write("> 注意：本文件基于模拟数据生成，仅用于演示 EDA 流程，不代表真实实验结论。\n\n")
    f.write("## 风险项\n\n")
    for r in risk_items:
        f.write(r + "\n")
    f.write("\n## 候选特征\n\n")
    for c in candidate_features:
        f.write(f"- {c}\n")

print("\n已保存：candidate_features.csv, risk_items.md")

# ============================================================
# 7. 出图：分布图组 + 相关热力图 + 分组对比
# ============================================================
fig, axes = plt.subplots(3, 3, figsize=(18, 14))
fig.suptitle('EDA 报告（模拟数据）', fontsize=16)

# 7.1 单变量分布（前 6 个连续特征）
for idx, name in enumerate(feature_names[:6]):
    ax = axes[idx // 3, idx % 3]
    v = data[name][~np.isnan(data[name])]
    ax.hist(v, bins=30, color='steelblue', edgecolor='white', alpha=0.8)
    ax.set_title(f'{name} 分布 (缺失率={np.mean(np.isnan(data[name])):.1%})')
    ax.set_xlabel(name)
    ax.set_ylabel('频数')

# 7.2 相关热力图
ax = axes[2, 0]
im = ax.imshow(pear_mat, cmap='RdBu_r', vmin=-1, vmax=1)
ax.set_xticks(range(n_feat))
ax.set_yticks(range(n_feat))
ax.set_xticklabels(feature_names, rotation=45, ha='right', fontsize=8)
ax.set_yticklabels(feature_names, fontsize=8)
ax.set_title('Pearson 相关热力图')
for i in range(n_feat):
    for j in range(n_feat):
        if not np.isnan(pear_mat[i, j]):
            ax.text(j, i, f'{pear_mat[i, j]:.2f}', ha='center', va='center', fontsize=6)
plt.colorbar(im, ax=ax, fraction=0.046)

# 7.3 分组对比（income 按 region）
ax = axes[2, 1]
for g in groups:
    m = (region == g) & ~np.isnan(data['income'])
    v = data['income'][m]
    if len(v) > 0:
        ax.hist(v, bins=25, alpha=0.5, label=f'{g} (n={len(v)})')
ax.set_title('income 按 region 分组分布')
ax.set_xlabel('income')
ax.set_ylabel('频数')
ax.legend(fontsize=8)

# 7.4 目标变量分布
ax = axes[2, 2]
ax.bar(['负类(0)', '正类(1)'], [neg, pos], color=['#4C72B0', '#C44E52'])
ax.set_title(f'目标变量分布 (少数类占比={minority_ratio:.2%})')
ax.set_ylabel('样本数')
for i, v in enumerate([neg, pos]):
    ax.text(i, v + 5, str(v), ha='center')

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig('figure.png', dpi=120, bbox_inches='tight')
plt.close()

print("已保存：figure.png")
print("\n" + "=" * 70)
print("EDA 完成（模拟数据）")
print("=" * 70)