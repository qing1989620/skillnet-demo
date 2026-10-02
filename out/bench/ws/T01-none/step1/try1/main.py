# -*- coding: utf-8 -*-
"""
PBMC 10x scRNA-seq 完整可复现流程（简化核心路径）
注意：本脚本使用【模拟数据】演示流程，所有数值均为模拟，不代表真实实验结论。
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

rng = np.random.default_rng(42)

# ============================================================
# 1. 模拟 10x 数据：counts 矩阵 (细胞 x 基因)
# ============================================================
N_CELLS = 1200
N_GENES = 300
GROUP = np.array(['Ctrl'] * (N_CELLS // 2) + ['Case'] * (N_CELLS // 2))
rng.shuffle(GROUP)

# 定义 5 个免疫亚群标记基因
MARKERS = {
    'T_cell':      ['CD3D', 'CD3E', 'IL7R'],
    'B_cell':      ['CD79A', 'MS4A1', 'CD19'],
    'NK_cell':     ['NKG7', 'GNLY', 'KLRD1'],
    'Monocyte':    ['LYZ', 'CD14', 'FCGR3A'],
    'Dendritic':   ['FCER1A', 'CST3', 'CLEC10A'],
}
gene_names = []
for gs in MARKERS.values():
    gene_names.extend(gs)
gene_names += [f'GENE{i}' for i in range(N_GENES - len(gene_names))]
gene_names = np.array(gene_names)

# 每个细胞随机分配一个真实亚群（模拟 ground truth）
true_labels = rng.choice(list(MARKERS.keys()), size=N_CELLS)

# 生成 counts：负二项分布，标记基因在对应亚群高表达
counts = rng.negative_binomial(2, 0.5, size=(N_CELLS, N_GENES)).astype(float)
gene_idx = {g: i for i, g in enumerate(gene_names)}
for i, lab in enumerate(true_labels):
    for g in MARKERS[lab]:
        counts[i, gene_idx[g]] += rng.negative_binomial(8, 0.4)

# 模拟两组间差异表达：Case 组 T_cell 的 CD3D 上调
case_mask = GROUP == 'Case'
t_mask = true_labels == 'T_cell'
counts[case_mask & t_mask, gene_idx['CD3D']] *= 1.8

print("=" * 60)
print("【模拟数据】PBMC scRNA-seq 流程演示")
print(f"细胞数: {N_CELLS}, 基因数: {N_GENES}")
print(f"分组: Ctrl={np.sum(GROUP=='Ctrl')}, Case={np.sum(GROUP=='Case')}")

# ============================================================
# 2. 质控 QC
# ============================================================
total_counts = counts.sum(axis=1)
n_genes_detected = (counts > 0).sum(axis=1)
mito_genes = np.array([g.startswith('MT-') for g in gene_names])
# 模拟数据无 MT- 基因，人为构造 5% 线粒体比例用于演示
mito_pct = rng.uniform(0, 20, size=N_CELLS)

qc_pass = (total_counts >= 500) & (n_genes_detected >= 100) & (mito_pct < 15)
print("\n[QC] 过滤前细胞数:", N_CELLS)
print(f"[QC] 通过过滤细胞数: {qc_pass.sum()} ({qc_pass.mean()*100:.1f}%)")
print(f"[QC] 中位总 counts: {np.median(total_counts):.0f}")
print(f"[QC] 中位检测基因数: {np.median(n_genes_detected):.0f}")
print(f"[QC] 中位线粒体比例: {np.median(mito_pct):.1f}%")

counts_qc = counts[qc_pass]
labels_qc = true_labels[qc_pass]
group_qc = GROUP[qc_pass]

# 已知陷阱检查：全零基因 / 全零细胞
zero_genes = (counts_qc.sum(axis=0) == 0).sum()
zero_cells = (counts_qc.sum(axis=1) == 0).sum()
print(f"[陷阱检查] 全零基因数: {zero_genes}, 全零细胞数: {zero_cells}")

# ============================================================
# 3. 归一化 + log1p
# ============================================================
lib_size = counts_qc.sum(axis=1, keepdims=True)
lib_size[lib_size == 0] = 1
norm = counts_qc / lib_size * 1e4
log_norm = np.log1p(norm)

# ============================================================
# 4. 简易聚类（基于标记基因打分的亚群识别）
#    真实流程应使用 PCA + 邻居图 + Leiden；此处用标记基因打分近似
# ============================================================
marker_scores = np.zeros((log_norm.shape[0], len(MARKERS)))
for j, (cell_type, gs) in enumerate(MARKERS.items()):
    idxs = [gene_idx[g] for g in gs]
    marker_scores[:, j] = log_norm[:, idxs].mean(axis=1)

pred_labels = np.array(list(MARKERS.keys()))[marker_scores.argmax(axis=1)]
accuracy = (pred_labels == labels_qc).mean()
print(f"\n[聚类] 基于标记基因打分的亚群识别准确率: {accuracy*100:.1f}%")
for ct in MARKERS:
    n = np.sum(pred_labels == ct)
    print(f"  {ct}: {n} 细胞 ({n/len(pred_labels)*100:.1f}%)")

# ============================================================
# 5. 两组间差异表达（T_cell 亚群内 CD3D）
# ============================================================
t_cells = pred_labels == 'T_cell'
cd3d_idx = gene_idx['CD3D']
ctrl_expr = log_norm[t_cells & (group_qc == 'Ctrl'), cd3d_idx]
case_expr = log_norm[t_cells & (group_qc == 'Case'), cd3d_idx]

mean_ctrl = ctrl_expr.mean()
mean_case = case_expr.mean()
log2fc = mean_case - mean_ctrl
# 简易 t 统计量（不依赖 scipy）
pooled_std = np.sqrt(ctrl_expr.var(ddof=1)/len(ctrl_expr) + case_expr.var(ddof=1)/len(case_expr))
t_stat = (mean_case - mean_ctrl) / (pooled_std + 1e-9)

print(f"\n[差异表达] T_cell 亚群 CD3D")
print(f"  Ctrl 均值: {mean_ctrl:.3f} (n={len(ctrl_expr)})")
print(f"  Case 均值: {mean_case:.3f} (n={len(case_expr)})")
print(f"  log2FC: {log2fc:.3f}, t 统计量: {t_stat:.2f}")

# ============================================================
# 6. 出图
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

# 图1: QC 分布
axes[0].hist(total_counts, bins=40, color='steelblue', alpha=0.8)
axes[0].axvline(500, color='red', linestyle='--', label='阈值 500')
axes[0].set_xlabel('总 counts'); axes[0].set_ylabel('细胞数')
axes[0].set_title('QC: 总 counts 分布'); axes[0].legend()

# 图2: 亚群比例
cts = list(MARKERS.keys())
props = [np.sum(pred_labels == c) / len(pred_labels) * 100 for c in cts]
axes[1].bar(cts, props, color='mediumseagreen')
axes[1].set_ylabel('比例 (%)'); axes[1].set_title('识别到的免疫细胞亚群比例')
axes[1].tick_params(axis='x', rotation=30)

# 图3: 两组 CD3D 表达对比
axes[2].boxplot([ctrl_expr, case_expr], labels=['Ctrl', 'Case'],
                patch_artist=True,
                boxprops=dict(facecolor='lightcoral'))
axes[2].set_ylabel('log1p 归一化表达'); axes[2].set_title('T_cell 亚群 CD3D 表达对比')
axes[2].text(0.5, 0.95, f'log2FC={log2fc:.2f}', transform=axes[2].transAxes,
             ha='center', va='top', fontsize=10)

plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print("\n[输出] 图已保存: figure.png")

# ============================================================
# 7. 落盘 CSV
# ============================================================
import csv
with open('qc_summary.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['metric', 'value'])
    w.writerow(['total_cells', N_CELLS])
    w.writerow(['cells_passed_qc', int(qc_pass.sum())])
    w.writerow(['median_total_counts', float(np.median(total_counts))])
    w.writerow(['median_genes', float(np.median(n_genes_detected))])
    w.writerow(['median_mito_pct', float(np.median(mito_pct))])

with open('celltype_proportions.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['cell_type', 'n_cells', 'proportion_pct'])
    for c in cts:
        n = int(np.sum(pred_labels == c))
        w.writerow([c, n, round(n / len(pred_labels) * 100, 2)])

with open('deg_Tcell_CD3D.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['group', 'mean_log1p_expr', 'n_cells'])
    w.writerow(['Ctrl', round(float(mean_ctrl), 4), len(ctrl_expr)])
    w.writerow(['Case', round(float(mean_case), 4), len(case_expr)])
    w.writerow(['log2FC', round(float(log2fc), 4), ''])
    w.writerow(['t_stat', round(float(t_stat), 4), ''])

print("[输出] CSV 已保存: qc_summary.csv, celltype_proportions.csv, deg_Tcell_CD3D.csv")
print("\n注意：以上所有结果均基于【模拟数据】，仅用于流程演示。")