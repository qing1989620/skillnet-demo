# -*- coding: utf-8 -*-
"""
PBMC 10x scRNA-seq 完整可复现流程（单文件精简版）
注意：本脚本使用【模拟数据】演示流程，所有数值均为模拟生成，不代表真实实验结论。
仅依赖 numpy 2.5.3 与 matplotlib 3.11.2。
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

rng = np.random.default_rng(42)

# ============================================================
# 1. 模拟 PBMC 10x 计数矩阵（模拟数据）
# ============================================================
N_CELLS = 1200
N_GENES = 800
N_BATCH = 2          # 两个批次
N_GROUP = 2          # 两组患者

# 细胞元信息
batch = rng.integers(0, N_BATCH, N_CELLS)
group = rng.integers(0, N_GROUP, N_CELLS)   # 0=对照, 1=患者

# 5 个免疫亚群（模拟）：T, B, NK, Mono, DC
TRUE_K = 5
true_label = rng.integers(0, TRUE_K, N_CELLS)

# 每个亚群的特征基因（模拟标记）
marker_genes = {
    'T':    [0, 1, 2, 3],
    'B':    [10, 11, 12, 13],
    'NK':   [20, 21, 22, 23],
    'Mono': [30, 31, 32, 33],
    'DC':   [40, 41, 42, 43],
}
label_names = ['T', 'B', 'NK', 'Mono', 'DC']

# 生成计数：负二项分布 + 亚群特异表达 + 批次效应
base_mu = rng.gamma(shape=1.5, scale=1.0, size=N_GENES)
counts = np.zeros((N_GENES, N_CELLS), dtype=np.float64)
for k in range(TRUE_K):
    idx = np.where(true_label == k)[0]
    mu = np.tile(base_mu, (len(idx), 1)).T
    for g in marker_genes[label_names[k]]:
        mu[g, :] *= 8.0
    counts[:, idx] = rng.poisson(mu)

# 批次效应：批次1部分基因整体上调
batch_effect_genes = rng.choice(N_GENES, 50, replace=False)
counts[np.ix_(batch_effect_genes, np.where(batch == 1)[0])] = (
    counts[np.ix_(batch_effect_genes, np.where(batch == 1)[0])] * 1.8
).astype(np.float64)

# 线粒体基因（模拟：最后 20 个基因）
mito_mask = np.zeros(N_GENES, dtype=bool)
mito_mask[-20:] = True

print("=" * 60)
print("【模拟数据】PBMC scRNA-seq 流程演示")
print(f"原始矩阵: {N_GENES} 基因 x {N_CELLS} 细胞")
print(f"批次: {N_BATCH}, 分组: {N_GROUP}, 真实亚群数: {TRUE_K}")

# ============================================================
# 2. 质控（QC）
# ============================================================
n_umi = counts.sum(axis=0)
n_gene = (counts > 0).sum(axis=0)
mito_pct = counts[mito_mask, :].sum(axis=0) / np.maximum(n_umi, 1) * 100

# 阈值（常规经验值）
MIN_GENE, MIN_UMI, MAX_MITO = 200, 500, 20.0
keep = (n_gene >= MIN_GENE) & (n_umi >= MIN_UMI) & (mito_pct <= MAX_MITO)
n_removed = int((~keep).sum())

print("-" * 60)
print("[QC] 过滤阈值: nGene>=%d, nUMI>=%d, mito%%<=%.1f" % (MIN_GENE, MIN_UMI, MAX_MITO))
print(f"[QC] 去除细胞数: {n_removed} / {N_CELLS} ({n_removed/N_CELLS*100:.1f}%)")
print(f"[QC] 保留细胞数: {int(keep.sum())}")
print(f"[QC] 过滤前 mito%% 中位数: {np.median(mito_pct):.2f}")

counts = counts[:, keep]
batch = batch[keep]
group = group[keep]
true_label = true_label[keep]
n_cells = counts.shape[1]

# 陷阱检查：过滤后是否仍有细胞
assert n_cells > 50, "过滤后细胞数过少，流程终止"
# 陷阱检查：基因全零
gene_keep = counts.sum(axis=1) > 0
print(f"[QC] 全零基因数: {int((~gene_keep).sum())} (已移除)")
counts = counts[gene_keep, :]
mito_mask = mito_mask[gene_keep]
n_genes = counts.shape[0]

# ============================================================
# 3. 归一化 + log 变换 + 高变基因
# ============================================================
lib_size = counts.sum(axis=0)
norm = counts / np.maximum(lib_size, 1) * 1e4
log_norm = np.log1p(norm)

# 高变基因：按标准化后方差排序
gene_mean = log_norm.mean(axis=1)
gene_var = log_norm.var(axis=1)
# 用离散度（方差/均值）避免高表达基因主导
disp = gene_var / np.maximum(gene_mean, 1e-8)
n_hvg = 300
hvg_idx = np.argsort(disp)[::-1][:n_hvg]
print("-" * 60)
print(f"[HVG] 选取高变基因数: {n_hvg} / {n_genes}")

# ============================================================
# 4. PCA + 肘部图 + 轮廓系数确定主成分数
# ============================================================
X = log_norm[hvg_idx, :].T.copy()
X = (X - X.mean(axis=0)) / np.maximum(X.std(axis=0), 1e-8)

# 用 SVD 做 PCA
U, S, Vt = np.linalg.svd(X, full_matrices=False)
explained = (S ** 2) / np.sum(S ** 2)
cum_explained = np.cumsum(explained)

# 肘部：累计解释方差 >= 80% 或拐点
n_pc_elbow = int(np.searchsorted(cum_explained, 0.80) + 1)
n_pc_elbow = max(2, min(n_pc_elbow, 30))

# 轮廓系数（简化：在 PCA 空间用真实标签近似评估，仅用于选 PC 数）
def silhouette_simple(Xp, labels):
    """简化轮廓系数，避免 sklearn 依赖。"""
    uniq = np.unique(labels)
    if len(uniq) < 2:
        return -1.0
    # 采样加速
    n = Xp.shape[0]
    sample = rng.choice(n, size=min(300, n), replace=False)
    Xs, ls = Xp[sample], labels[sample]
    dist = np.sqrt(((Xs[:, None, :] - Xs[None, :, :]) ** 2).sum(-1))
    sils = []
    for i in range(len(sample)):
        same = ls == ls[i]
        same[i] = False
        if same.sum() == 0:
            continue
        a = dist[i, same].mean()
        b = min(dist[i, ls == c].mean() for c in uniq if c != ls[i])
        sils.append((b - a) / max(a, b))
    return float(np.mean(sils)) if sils else -1.0

sil_scores = []
pc_range = range(2, min(21, U.shape[1] + 1))
for k in pc_range:
    sil_scores.append(silhouette_simple(U[:, :k], true_label))
best_pc = list(pc_range)[int(np.argmax(sil_scores))]
n_pc = max(2, min(best_pc, n_pc_elbow))
print("-" * 60)
print(f"[PCA] 肘部法建议 PC 数: {n_pc_elbow}")
print(f"[PCA] 轮廓系数最优 PC 数: {best_pc} (sil={max(sil_scores):.3f})")
print(f"[PCA] 最终采用 PC 数: {n_pc}")

Z = U[:, :n_pc]

# ============================================================
# 5. 批次效应校正（简化：按批次中心化）
# ============================================================
Z_corr = Z.copy()
for b in np.unique(batch):
    m = batch == b
    Z_corr[m] = Z[m] - Z[m].mean(axis=0, keepdims=True)
# 校正后再标准化
Z_corr = (Z_corr - Z_corr.mean(axis=0)) / np.maximum(Z_corr.std(axis=0), 1e-8)

# 陷阱检查：批次校正前后批次间距离
def batch_sep(Zm):
    c = [Zm[batch == b].mean(axis=0) for b in np.unique(batch)]
    return float(np.linalg.norm(c[0] - c[1])) if len(c) > 1 else 0.0
print("-" * 60)
print(f"[Batch] 校正前批次中心距离: {batch_sep(Z):.3f}")
print(f"[Batch] 校正后批次中心距离: {batch_sep(Z_corr):.3f}")

# ============================================================
# 6. Leiden 聚类（简化：KMeans 近似，TODO: 真实 Leiden）
# ============================================================
# TODO: 真实流程应使用 leidenalg / igraph 做图聚类
def kmeans_simple(X, k, n_iter=50):
    idx = rng.choice(len(X), k, replace=False)
    C = X[idx].copy()
    lab = np.zeros(len(X), dtype=int)
    for _ in range(n_iter):
        d = ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1)
        new_lab = d.argmin(axis=1)
        if np.array_equal(new_lab, lab):
            break
        lab = new_lab
        for j in range(k):
            if (lab == j).sum() > 0:
                C[j] = X[lab == j].mean(axis=0)
    return lab

cluster = kmeans_simple(Z_corr, TRUE_K)
print("-" * 60)
print(f"[Cluster] 聚类数: {TRUE_K} (简化 KMeans 近似 Leiden)")
for k in range(TRUE_K):
    print(f"  cluster {k}: {int((cluster==k).sum())} cells")

# ============================================================
# 7. 标记基因鉴定（Wilcoxon 近似：秩和 + 效应量）
# ============================================================
def wilcoxon_approx(x, y):
    """简化 Wilcoxon 秩和检验，返回 z 统计量（近似）。"""
    n1, n2 = len(x), len(y)
    if n1 < 3 or n2 < 3:
        return 0.0
    allv = np.concatenate([x, y])
    ranks = np.argsort(np.argsort(allv)) + 1
    R1 = ranks[:n1].sum()
    mu = n1 * (n1 + n2 + 1) / 2
    sigma = np.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    return (R1 - mu) / max(sigma, 1e-8)

marker_table = []
for k in range(TRUE_K):
    in_c = cluster == k
    out_c = ~in_c
    for g in range(n_genes):
        x = log_norm[g, in_c]
        y = log_norm[g, out_c]
        z = wilcoxon_approx(x, y)
        logfc = x.mean() - y.mean()
        marker_table.append((k, g, z, logfc))

marker_table.sort(key=lambda t: -abs(t[2]))
top_markers = marker_table[:20]
print("-" * 60)
print("[Markers] Top 10 标记基因 (cluster, gene_idx, z, logFC):")
for row in top_markers[:10]:
    print(f"  cluster={row[0]}, gene={row[1]}, z={row[2]:.2f}, logFC={row[3]:.3f}")

# 与已知标记比对（模拟：检查是否命中真实标记基因）
hit = 0
for k, g, z, lf in top_markers:
    if g in marker_genes[label_names[k]]:
        hit += 1
print(f"[Markers] Top20 中命中真实标记基因数: {hit}")

# ============================================================
# 8. 两组患者亚群基因表达差异
# ============================================================
diff_table = []
for k in range(TRUE_K):
    in_c = cluster == k
    g0 = in_c & (group == 0)
    g1 = in_c & (group == 1)
    if g0.sum() < 3 or g1.sum() < 3:
        continue
    for g in range(n_genes):
        x = log_norm[g, g0]
        y = log_norm[g, g1]
        z = wilcoxon_approx(x, y)
        logfc = y.mean() - x.mean()
        diff_table.append((k, g, z, logfc))

diff_table.sort(key=lambda t: -abs(t[2]))
print("-" * 60)
print("[Diff] 组间差异 Top 5 (cluster, gene, z, logFC):")
for row in diff_table[:5]:
    print(f"  cluster={row[0]}, gene={row[1]}, z={row[2]:.2f}, logFC={row[3]:.3f}")

# ============================================================
# 9. 出图
# ============================================================
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# (a) QC 分布
ax = axes[0, 0]
ax.hist(n_umi, bins=40, color='steelblue', alpha=0.7)
ax.axvline(MIN_UMI, color='red', linestyle='--', label=f'阈值={MIN_UMI}')
ax.set_xlabel('nUMI'); ax.set_ylabel('细胞数')
ax.set_title('(a) QC: nUMI 分布（模拟数据）')
ax.legend()

# (b) 肘部图
ax = axes[0, 1]
ax.plot(range(1, len(explained) + 1), cum_explained, 'o-', color='darkorange')
ax.axvline(n_pc, color='red', linestyle='--', label=f'采用 PC={n_pc}')
ax.set_xlabel('主成分数'); ax.set_ylabel('累计解释方差')
ax.set_title('(b) PCA 肘部图（模拟数据）')
ax.legend()

# (c) PCA 散点（按聚类着色）
ax = axes[1, 0]
colors = plt.cm.tab10(np.linspace(0, 1, TRUE_K))
for k in range(TRUE_K):
    m = cluster == k
    ax.scatter(Z_corr[m, 0], Z_corr[m, 1], s=6, color=colors[k], label=f'C{k}')
ax.set_xlabel('PC1'); ax.set_ylabel('PC2')
ax.set_title('(c) 聚类结果 PCA（模拟数据）')
ax.legend(markerscale=2, fontsize=8)

# (d) 组间差异火山图
ax = axes[1, 1]
if diff_table:
    zs = np.array([r[2] for r in diff_table])
    lfs = np.array([r[3] for r in diff_table])
    ax.scatter(lfs, zs, s=5, alpha=0.4, color='gray')
    sig = np.abs(zs) > 2
    ax.scatter(lfs[sig], zs[sig], s=8, color='crimson', label='|z|>2')
    ax.axhline(2, color='blue', linestyle='--', linewidth=0.8)
    ax.axhline(-2, color='blue', linestyle='--', linewidth=0.8)
    ax.set_xlabel('logFC (患者 vs 对照)'); ax.set_ylabel('z 统计量')
    ax.set_title('(d) 组间差异火山图（模拟数据）')
    ax.legend()

plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print("-" * 60)
print("[Output] 图已保存: figure.png")

# ============================================================
# 10. 落盘 CSV
# ============================================================
np.savetxt('qc_metrics.csv',
           np.column_stack([n_umi, n_gene, mito_pct, keep.astype(int)]),
           delimiter=',', header='nUMI,nGene,mito_pct,keep', comments='')

with open('markers.csv', 'w', encoding='utf-8') as f:
    f.write('cluster,gene_idx,z_stat,logFC\n')
    for row in top_markers:
        f.write(f'{row[0]},{row[1]},{row[2]:.4f},{row[3]:.4f}\n')

with open('group_diff.csv', 'w', encoding='utf-8') as f:
    f.write('cluster,gene_idx,z_stat,logFC\n')
    for row in diff_table[:200]:
        f.write(f'{row[0]},{row[1]},{row[2]:.4f},{row[3]:.4f}\n')

with open('cell_meta.csv', 'w', encoding='utf-8') as f:
    f.write('cell_idx,batch,group,cluster,true_label\n')
    for i in range(n_cells):
        f.write(f'{i},{batch[i]},{group[i]},{cluster[i]},{true_label[i]}\n')

print("[Output] CSV 已保存: qc_metrics.csv, markers.csv, group_diff.csv, cell_meta.csv")
print("=" * 60)
print("注意：以上所有结果均基于【模拟数据】，不代表真实实验结论。")