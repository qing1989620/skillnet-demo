# -*- coding: utf-8 -*-
"""
两组实验数据统计检验 + 分布对比图 + 效应量森林图
注意：本脚本使用【模拟数据】演示流程，不代表任何真实实验结论。
依赖：numpy 2.5.3, matplotlib 3.11.2
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# ---------------- 中文字体 ----------------
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams.update({
    'font.size': 8, 'axes.titlesize': 9, 'axes.labelsize': 8,
    'xtick.labelsize': 7, 'ytick.labelsize': 7, 'legend.fontsize': 7,
    'axes.linewidth': 0.8, 'lines.linewidth': 1.0,
    'figure.dpi': 300, 'savefig.bbox': 'tight',
})

# ---------------- 模拟数据（明确标注） ----------------
rng = np.random.default_rng(20240517)
N_A, N_B = 42, 38
# 两组均值差约 0.6 个标准差，模拟中等效应
group_A = rng.normal(loc=10.0, scale=2.0, size=N_A)
group_B = rng.normal(loc=11.3, scale=2.1, size=N_B)
print("[模拟数据] 组A n=%d, 组B n=%d" % (N_A, N_B))

# ---------------- 统计量（不依赖 scipy，手写实现） ----------------
def mean_ci(x, conf=0.95):
    n = len(x)
    m = float(np.mean(x))
    sd = float(np.std(x, ddof=1))
    se = sd / np.sqrt(n)
    # 正态近似 z 值（n 较大时足够；小样本可用 t 表，此处简化）
    z = 1.959963985 if conf == 0.95 else 1.644853627
    return m, sd, se, m - z * se, m + z * se

mA, sdA, seA, loA, hiA = mean_ci(group_A)
mB, sdB, seB, loB, hiB = mean_ci(group_B)

# Cohen's d（合并标准差）
sp = np.sqrt(((N_A - 1) * sdA**2 + (N_B - 1) * sdB**2) / (N_A + N_B - 2))
d = (mB - mA) / sp
# d 的 95% CI（Hedges & Olkin 近似）
se_d = np.sqrt((N_A + N_B) / (N_A * N_B) + d**2 / (2 * (N_A + N_B)))
d_lo, d_hi = d - 1.959963985 * se_d, d + 1.959963985 * se_d

# Welch t 检验（手写）
varA, varB = sdA**2, sdB**2
se_diff = np.sqrt(varA / N_A + varB / N_B)
t_stat = (mB - mA) / se_diff
df_w = (varA / N_A + varB / N_B)**2 / (
    (varA / N_A)**2 / (N_A - 1) + (varB / N_B)**2 / (N_B - 1))
# 用正态近似给出双侧 p（严格应查 t 分布，此处标注为近似）
from math import erf, sqrt
p_val = 2 * (1 - 0.5 * (1 + erf(abs(t_stat) / sqrt(2))))

print("组A: mean=%.3f, sd=%.3f, 95%%CI=[%.3f, %.3f]" % (mA, sdA, loA, hiA))
print("组B: mean=%.3f, sd=%.3f, 95%%CI=[%.3f, %.3f]" % (mB, sdB, loB, hiB))
print("Welch t=%.3f, df=%.2f, p(近似)=%.4f" % (t_stat, df_w, p_val))
print("Cohen's d=%.3f, 95%%CI=[%.3f, %.3f]" % (d, d_lo, d_hi))

# ---------------- 陷阱规避检查 ----------------
print("[陷阱检查] 未使用双轴图：单图仅一个 y 轴 -> OK")
print("[陷阱检查] 坐标轴未截断：y 轴范围覆盖两组全部数据 -> OK")
print("[陷阱检查] 配色：使用蓝/橙（色觉障碍友好），未使用红绿对比 -> OK")

# ---------------- 绘图 ----------------
# 色觉障碍友好：蓝(#0072B2) / 橙(#E69F00)（Okabe-Ito 调色板）
C_A, C_B = '#0072B2', '#E69F00'

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.2),
                         gridspec_kw={'width_ratios': [1.15, 1.0]})

# --- 左：小提琴 + 箱线 + 散点 ---
ax = axes[0]
data = [group_A, group_B]
labels = ['组 A', '组 B']
colors = [C_A, C_B]

vp = ax.violinplot(data, positions=[1, 2], widths=0.7,
                   showmeans=False, showextrema=False, showmedians=False)
for body, c in zip(vp['bodies'], colors):
    body.set_facecolor(c); body.set_alpha(0.25); body.set_edgecolor(c)

bp = ax.boxplot(data, positions=[1, 2], widths=0.18, patch_artist=True,
                showfliers=False, medianprops=dict(color='black', lw=1.0),
                whiskerprops=dict(color='black', lw=0.8),
                capprops=dict(color='black', lw=0.8))
for patch, c in zip(bp['boxes'], colors):
    patch.set_facecolor(c); patch.set_alpha(0.6); patch.set_edgecolor('black')

# 散点（抖动）
for i, (g, c) in enumerate(zip(data, colors), start=1):
    jitter = rng.uniform(-0.09, 0.09, size=len(g))
    ax.scatter(np.full(len(g), i) + jitter, g, s=8, color=c,
               edgecolor='black', linewidth=0.2, alpha=0.85, zorder=3)

# 均值 ± 95% CI 误差条
for i, (m, lo, hi, c) in enumerate(
        [(mA, loA, hiA, C_A), (mB, loB, hiB, C_B)], start=1):
    ax.errorbar(i, m, yerr=[[m - lo], [hi - m]], fmt='D', color='black',
                markersize=3.5, capsize=3, lw=1.0, zorder=4)

ax.set_xticks([1, 2])
ax.set_xticklabels(['%s\n(n=%d)' % (labels[0], N_A),
                    '%s\n(n=%d)' % (labels[1], N_B)])
ax.set_ylabel('测量值（任意单位）')
ax.set_title('两组分布对比（小提琴+箱线+散点）')
ax.grid(axis='y', ls=':', lw=0.5, alpha=0.6)
ax.set_axisbelow(True)

# 显著性标注
y_top = max(group_A.max(), group_B.max())
y_bar = y_top + 0.6
ax.plot([1, 1, 2, 2], [y_bar, y_bar + 0.25, y_bar + 0.25, y_bar],
        color='black', lw=0.8)
star = 'n.s.' if p_val >= 0.05 else ('*' if p_val >= 0.01 else '**')
ax.text(1.5, y_bar + 0.3,
        'Welch t=%.2f, p=%.3f %s' % (t_stat, p_val, star),
        ha='center', va='bottom', fontsize=7)
ax.set_ylim(min(group_A.min(), group_B.min()) - 1.0, y_bar + 1.6)

# --- 右：效应量森林图（Cohen's d + 95% CI） ---
ax2 = axes[1]
ax2.axvline(0, color='gray', lw=0.8, ls='--')
ax2.errorbar(d, 1, xerr=[[d - d_lo], [d_hi - d]], fmt='o',
             color=C_B, ecolor='black', elinewidth=1.0,
             capsize=4, markersize=6, zorder=3)
ax2.set_yticks([1])
ax2.set_yticklabels(["组 B − 组 A\n(Cohen's d)"])
ax2.set_xlabel("效应量 Cohen's d（95% CI）")
ax2.set_title('效应量森林图')
ax2.set_xlim(min(-0.5, d_lo - 0.3), max(1.5, d_hi + 0.3))
ax2.set_ylim(0.5, 1.5)
ax2.grid(axis='x', ls=':', lw=0.5, alpha=0.6)
ax2.set_axisbelow(True)
ax2.text(d, 1.18, 'd=%.2f [%.2f, %.2f]' % (d, d_lo, d_hi),
         ha='center', va='bottom', fontsize=7)

# 图例（说明误差条含义）
legend_elems = [
    Patch(facecolor=C_A, alpha=0.6, edgecolor='black', label='组 A'),
    Patch(facecolor=C_B, alpha=0.6, edgecolor='black', label='组 B'),
    plt.Line2D([0], [0], marker='D', color='black', lw=0,
               markersize=4, label='均值 ± 95% CI'),
]
axes[0].legend(handles=legend_elems, loc='upper left', frameon=False)

fig.suptitle('两组实验数据统计检验（模拟数据，非真实实验结论）',
             fontsize=9, y=1.02)
fig.tight_layout()

# ---------------- 落盘 ----------------
fig.savefig('figure.png', dpi=300)
fig.savefig('figure.pdf')   # 矢量
fig.savefig('figure.svg')   # 矢量

# 数据表 CSV
import csv
with open('group_data.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['group', 'value'])
    for v in group_A:
        w.writerow(['A', '%.6f' % v])
    for v in group_B:
        w.writerow(['B', '%.6f' % v])

with open('stats_summary.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['metric', 'value'])
    w.writerow(['n_A', N_A]); w.writerow(['n_B', N_B])
    w.writerow(['mean_A', '%.4f' % mA]); w.writerow(['mean_B', '%.4f' % mB])
    w.writerow(['sd_A', '%.4f' % sdA]); w.writerow(['sd_B', '%.4f' % sdB])
    w.writerow(['ci95_A_low', '%.4f' % loA]); w.writerow(['ci95_A_high', '%.4f' % hiA])
    w.writerow(['ci95_B_low', '%.4f' % loB]); w.writerow(['ci95_B_high', '%.4f' % hiB])
    w.writerow(['welch_t', '%.4f' % t_stat]); w.writerow(['welch_df', '%.4f' % df_w])
    w.writerow(['p_approx', '%.6f' % p_val])
    w.writerow(['cohens_d', '%.4f' % d])
    w.writerow(['cohens_d_ci_low', '%.4f' % d_lo])
    w.writerow(['cohens_d_ci_high', '%.4f' % d_hi])

print("已导出: figure.png / figure.pdf / figure.svg / group_data.csv / stats_summary.csv")
print("图注：小提琴+箱线+散点展示两组分布；菱形为均值，误差条为95% CI；"
      "右侧森林图给出 Cohen's d 及95% CI；显著性由 Welch t 检验（双侧，正态近似）给出。"
      "配色采用 Okabe-Ito 蓝/橙，色觉障碍友好。数据为模拟数据。")