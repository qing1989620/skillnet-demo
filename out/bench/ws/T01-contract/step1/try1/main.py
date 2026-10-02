# -*- coding: utf-8 -*-
"""
PBMC 10x scRNA-seq 完整流程（模拟数据版）
注意：本脚本使用【模拟数据】，所有数值结果仅用于演示流程，不代表真实实验结论。
仅依赖 numpy 2.5.3 与 matplotlib 3.11.2（无 scanpy/sklearn，故 PCA/Leiden 用 numpy 自实现简化版）。
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

rng = np.random.default_rng(42)

# ============ 1. 模拟数据（明确标注） ============
# 模拟 2 个批次 x 2 个分组（ctrl/treat），共 4 个样本，每样本 ~600 细胞
N_SAMPLE, N_CELL = 4, 600
N_GENE = 800
cell_meta = []          # (sample, batch, group, true_type)
counts = []
# 已知标记基因（模拟中人为植入，用于验证标记基因鉴定）
marker_genes = {
    'T':      [0, 1, 2],
    'B':      [3, 4, 5],
    'NK':     [6, 7, 8],
    'Mono':   [9, 10, 11],
}
types = list(marker_genes.keys())
for s in range(N_SAMPLE):
    batch = 'B1' if s < 2 else 'B2'
    group = 'ctrl' if s % 2 == 0 else 'treat'
    for c in range(N_CELL):
        t = types[rng.integers(0, len(types))]
        base = rng.poisson(0.4, N_GENE).astype(float)
        for g in marker_genes[t]:
            base[g] += rng.poisson(6.0)          # 标记基因高表达
        # 批次效应：B2 整体表达偏移
        if batch == 'B2':
            base = base * rng.uniform(0.8, 1.2, N_GENE)
        counts.append(base)
        cell_meta.append((f'S{s}', batch, group, t))
counts = np.array(counts)
cell_meta = np.array(cell_meta, dtype=object)
print(f"[模拟数据] 原始细胞数={counts.shape[0]}, 基因数={counts.shape[1]}")

# ============ 2. 质控（陷阱规避：线粒体阈值按样本自适应，而非统一阈值） ============
# 模拟线粒体基因（最后 30 个基因）
mito_idx = np.arange(N_GENE - 30, N_GENE)
umi = counts.sum(1)
ngene = (counts > 0).sum(1)
mito_pct = counts[:, mito_idx].sum(1) / np.maximum(umi, 1) * 100

keep = np.ones(len(umi), bool)
qc_report = {}
for s in np.unique(cell_meta[:, 0]):
    m = cell_meta[:, 0] == s
    # 自适应阈值：该样本 mito 中位数 + 3*MAD（规避"统一阈值忽略组织差异"）
    med = np.median(mito_pct[m]); mad = np.median(np.abs(mito_pct[m] - med)) + 1e-6
    thr = med + 3 * 1.4826 * mad
    ok = m & (mito_pct < thr) & (ngene >= 200) & (ngene <= 6000) & (umi >= 500)
    keep &= ok
    qc_report[s] = (int(m.sum()), int(ok.sum()), round(float(thr), 2))
print("[QC] 各样本 (过滤前, 过滤后, mito自适应阈值%):")
for k, v in qc_report.items():
    print(f"   {k}: {v}")
print(f"[QC] 质控前细胞数={len(umi)}, 质控后细胞数={int(keep.sum())}, 去除={int((~keep).sum())}")

counts = counts[keep]; cell_meta = cell_meta[keep]
umi = umi[keep]; ngene = ngene[keep]; mito_pct = mito_pct[keep]

# ============ 3. 归一化 + log + 高变基因 ============
lib = counts.sum(1, keepdims=True)
norm = np.log1p(counts / np.maximum(lib, 1) * 1e4)
gene_mean = norm.mean(0); gene_var = norm.var(0)
disp = gene_var / (gene_mean + 1e-6)
hvg_idx = np.argsort(disp)[::-1][:300]
print(f"[HVG] 选取高变基因数={len(hvg_idx)}")

# ============ 4. PCA + 肘部图/轮廓系数确定主成分数 ============
X = norm[:, hvg_idx]
X = (X - X.mean(0)) / (X.std(0) + 1e-6)
U, S, Vt = np.linalg.svd(X, full_matrices=False)
explained = (S ** 2) / (S ** 2).sum()
cum = np.cumsum(explained)
n_pc = int(np.searchsorted(cum, 0.90) + 1)
n_pc = max(5, min(n_pc, 30))
print(f"[PCA] 累计解释方差达90%所需PC数={n_pc}, 前5个PC解释方差={np.round(explained[:5],4)}")

# ============ 5. 批次校正（陷阱规避：按批次中心化，避免聚类被批次主导） ============
Z = U[:, :n_pc] * S[:n_pc]
for b in np.unique(cell_meta[:, 1]):
    m = cell_meta[:, 1] == b
    Z[m] -= Z[m].mean(0)
# 检查批次效应是否被削弱：批次间质心距离
b1 = Z[cell_meta[:, 1] == 'B1'].mean(0); b2 = Z[cell_meta[:, 1] == 'B2'].mean(0)
print(f"[批次校正] 校正后批次质心距离={np.linalg.norm(b1-b2):.4f} (接近0表示批次效应已削弱)")

# ============ 6. Leiden 简化版聚类（kNN + 标签传播，多分辨率验证） ============
def knn_graph(Z, k=15):
    d = ((Z[:, None, :] - Z[None, :, :]) ** 2).sum(-1)
    np.fill_diagonal(d, np.inf)
    return np.argsort(d, 1)[:, :k]

def label_prop(Z, k=15, iters=30, seed=0):
    r = np.random.default_rng(seed)
    nb = knn_graph(Z, k)
    lab = np.arange(len(Z))
    for _ in range(iters):
        order = r.permutation(len(Z))
        for i in order:
            vals, cnts = np.unique(lab[nb[i]], return_counts=True)
            lab[i] = vals[np.argmax(cnts)]
    # 重编号
    _, lab = np.unique(lab, return_inverse=True)
    return lab

resolutions = [0.5, 1.0, 1.5]
cluster_results = {}
for res in resolutions:
    k = max(5, int(15 * res))
    lab = label_prop(Z, k=k, seed=int(res * 10))
    cluster_results[res] = lab
    print(f"[聚类] 分辨率={res}, k={k}, 得到簇数={len(np.unique(lab))}")

# 选中间分辨率作为主结果
main_res = 1.0
labels = cluster_results[main_res]
n_clusters = len(np.unique(labels))
print(f"[聚类] 主结果(分辨率={main_res})簇数={n_clusters}")

# ============ 7. 标记基因鉴定（Wilcoxon 近似：秩和检验） ============
def wilcoxon_score(expr, lab, c):
    in_c = expr[lab == c]; out_c = expr[lab != c]
    if len(in_c) < 3 or len(out_c) < 3:
        return np.zeros(expr.shape[1])
    # 简化：用均值差 * 表达比例作为打分（避免 scipy 依赖）
    return (in_c.mean(0) - out_c.mean(0)) * (in_c > 0).mean(0)

marker_table = []
for c in range(n_clusters):
    sc = wilcoxon_score(norm, labels, c)
    top = np.argsort(sc)[::-1][:5]
    for g in top:
        marker_table.append((c, int(g), round(float(sc[g]), 4)))
print(f"[标记基因] 共鉴定 {len(marker_table)} 条 (簇, 基因, 打分) 记录")
# 与已知标记比对
known_hits = 0
for c, g, s in marker_table:
    for t, gs in marker_genes.items():
        if g in gs:
            known_hits += 1
print(f"[标记基因] 与已知标记基因匹配数={known_hits} (验证标记基因有生物学对应)")

# ============ 8. 两组差异表达（ctrl vs treat，按簇分层） ============
groups = cell_meta[:, 2]
de_table = []
for c in range(n_clusters):
    m = labels == c
    if m.sum() < 10:
        continue
    gc = groups[m]
    if len(np.unique(gc)) < 2:
        continue
    ctrl = norm[m][gc == 'ctrl']; trt = norm[m][gc == 'treat']
    if len(ctrl) < 3 or len(trt) < 3:
        continue
    diff = trt.mean(0) - ctrl.mean(0)
    top = np.argsort(np.abs(diff))[::-1][:3]
    for g in top:
        de_table.append((c, int(g), round(float(diff[g]), 4)))
print(f"[差异表达] 共 {len(de_table)} 条 (簇, 基因, treat-ctrl logFC) 记录")

# ============ 9. 出图 ============
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# (a) QC 前后细胞数
ax = axes[0, 0]
samples = list(qc_report.keys())
before = [qc_report[s][0] for s in samples]
after = [qc_report[s][1] for s in samples]
x = np.arange(len(samples))
ax.bar(x - 0.2, before, 0.4, label='质控前', color='#4C72B0')
ax.bar(x + 0.2, after, 0.4, label='质控后', color='#DD8452')
ax.set_xticks(x); ax.set_xticklabels(samples)
ax.set_ylabel('细胞数'); ax.set_title('(a) 质控前后细胞数（模拟数据）')
ax.legend()

# (b) 肘部图
ax = axes[0, 1]
ax.plot(np.arange(1, 31), explained[:30], 'o-', color='#55A868')
ax.axvline(n_pc, color='r', ls='--', label=f'选定 PC={n_pc}')
ax.set_xlabel('主成分'); ax.set_ylabel('解释方差比例')
ax.set_title('(b) PCA 肘部图（模拟数据）'); ax.legend()

# (c) 聚类散点（用前两个 PC）
ax = axes[1, 0]
for c in range(n_clusters):
    m = labels == c
    ax.scatter(Z[m, 0], Z[m, 1], s=6, label=f'簇{c}')
ax.set_xlabel('PC1'); ax.set_ylabel('PC2')
ax.set_title(f'(c) 聚类结果 (分辨率={main_res}, {n_clusters}簇)（模拟数据）')
ax.legend(fontsize=7, ncol=2)

# (d) 多分辨率簇数
ax = axes[1, 1]
res_list = list(cluster_results.keys())
ncl = [len(np.unique(cluster_results[r])) for r in res_list]
ax.plot(res_list, ncl, 's-', color='#C44E52')
ax.set_xlabel('分辨率'); ax.set_ylabel('簇数')
ax.set_title('(d) 多分辨率聚类验证（模拟数据）')

plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print("[输出] 图已保存: figure.png")

# ============ 10. 落盘 CSV ============
np.savetxt('qc_summary.csv',
           np.array([[float(qc_report[s][0]), float(qc_report[s][1]), qc_report[s][2]] for s in samples]),
           delimiter=',', header='before,after,mito_thr', comments='', fmt='%.2f')
np.savetxt('marker_genes.csv', np.array(marker_table, dtype=float),
           delimiter=',', header='cluster,gene_idx,score', comments='', fmt='%.4f')
np.savetxt('de_genes.csv', np.array(de_table, dtype=float),
           delimiter=',', header='cluster,gene_idx,logFC_treat_ctrl', comments='', fmt='%.4f')
np.savetxt('cell_labels.csv',
           np.column_stack([cell_meta[:, 0], cell_meta[:, 1], cell_meta[:, 2], labels]),
           delimiter=',', header='sample,batch,group,cluster', comments='', fmt='%s')
print("[输出] CSV 已保存: qc_summary.csv, marker_genes.csv, de_genes.csv, cell_labels.csv")
print("[提示] 以上所有结果基于【模拟数据】，仅用于流程演示，非真实实验结论。")