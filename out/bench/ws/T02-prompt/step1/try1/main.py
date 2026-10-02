# -*- coding: utf-8 -*-
"""
纯成分特征预测无机化合物形成能 + 留一元素(LOO)外推评估
注意：本脚本使用【模拟数据】(synthetic data)，因为环境中没有真实材料数据库。
      所有数值结果仅用于演示流程，不代表真实材料结论。
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

rng = np.random.default_rng(42)

# ----------------------------------------------------------------------
# 1. 模拟元素属性表（模拟数据）
# ----------------------------------------------------------------------
ELEMENTS = [f"E{i}" for i in range(20)]
# 每个元素: 电负性 chi, 原子半径 r, 价电子数 ve, 族 group
chi = rng.uniform(0.7, 3.5, len(ELEMENTS))
rad = rng.uniform(0.9, 2.6, len(ELEMENTS))
ve  = rng.integers(1, 8, len(ELEMENTS)).astype(float)
grp = rng.integers(1, 17, len(ELEMENTS)).astype(float)
ELEM = {e: dict(chi=chi[i], rad=rad[i], ve=ve[i], grp=grp[i])
        for i, e in enumerate(ELEMENTS)}

# ----------------------------------------------------------------------
# 2. 生成模拟化合物样本（二元/三元），标签为"形成能"
# ----------------------------------------------------------------------
def make_sample():
    n = rng.integers(2, 4)                      # 2 或 3 元
    els = rng.choice(ELEMENTS, size=n, replace=False)
    frac = rng.dirichlet(np.ones(n))
    return list(els), frac

def true_energy(els, frac):
    """模拟的"真实"形成能生成过程（含噪声）"""
    chi_m = sum(f * ELEM[e]['chi'] for e, f in zip(els, frac))
    rad_m = sum(f * ELEM[e]['rad'] for e, f in zip(els, frac))
    ve_m  = sum(f * ELEM[e]['ve']  for e, f in zip(els, frac))
    # 电负性差越大越稳定(负)，半径越大越不稳定(正)
    chi_spread = max(ELEM[e]['chi'] for e in els) - min(ELEM[e]['chi'] for e in els)
    e = -1.6 * chi_spread + 0.9 * rad_m - 0.15 * ve_m + 0.4 * chi_m
    e += rng.normal(0, 0.08)
    return e

N = 1200
samples = []
for _ in range(N):
    els, frac = make_sample()
    samples.append((els, frac, true_energy(els, frac)))

# ----------------------------------------------------------------------
# 3. 纯成分特征构造（不依赖晶体结构）
# ----------------------------------------------------------------------
def featurize(els, frac):
    chi_v = np.array([ELEM[e]['chi'] for e in els])
    rad_v = np.array([ELEM[e]['rad'] for e in els])
    ve_v  = np.array([ELEM[e]['ve']  for e in els])
    grp_v = np.array([ELEM[e]['grp'] for e in els])
    f = np.asarray(frac)
    feats = [
        np.sum(f * chi_v), np.sum(f * rad_v), np.sum(f * ve_v), np.sum(f * grp_v),
        np.sum(f * chi_v**2), np.sum(f * rad_v**2),
        chi_v.max() - chi_v.min(), rad_v.max() - rad_v.min(),
        np.std(chi_v), np.std(rad_v),
        len(els),
        np.sum(f**2),                       # 混合熵代理
        -np.sum(f * np.log(f + 1e-12)),     # 构型熵
    ]
    return np.array(feats, dtype=float)

X = np.array([featurize(e, f) for e, f, _ in samples])
y = np.array([t for _, _, t in samples])
elem_sets = [set(e) for e, _, _ in samples]

print("=" * 60)
print("【模拟数据】样本数 =", len(y))
print("特征维度 =", X.shape[1])
print("形成能统计: mean=%.3f  std=%.3f  min=%.3f  max=%.3f"
      % (y.mean(), y.std(), y.min(), y.max()))

# ----------------------------------------------------------------------
# 4. 轻量模型实现（只用 numpy）：岭回归 + 随机森林风格 bagging 树桩
# ----------------------------------------------------------------------
def ridge_fit(Xtr, ytr, lam=1.0):
    Xb = np.hstack([Xtr, np.ones((len(Xtr), 1))])
    A = Xb.T @ Xb + lam * np.eye(Xb.shape[1])
    w = np.linalg.solve(A, Xb.T @ ytr)
    return w

def ridge_pred(w, Xte):
    Xb = np.hstack([Xte, np.ones((len(Xte), 1))])
    return Xb @ w

def stump_fit(Xtr, ytr, n_trees=60, depth=3, seed=0):
    """极简回归树集合（bagging），用于近似随机森林"""
    r = np.random.default_rng(seed)
    trees = []
    n, d = Xtr.shape
    for _ in range(n_trees):
        idx = r.integers(0, n, n)
        Xb, yb = Xtr[idx], ytr[idx]
        tree = build_tree(Xb, yb, depth, r)
        trees.append(tree)
    return trees

def build_tree(X, y, depth, r):
    if depth == 0 or len(y) < 5 or np.std(y) < 1e-6:
        return ('leaf', float(y.mean()))
    d = X.shape[1]
    feat = r.integers(0, d)
    vals = np.unique(X[:, feat])
    if len(vals) < 2:
        return ('leaf', float(y.mean()))
    thr = r.choice(vals)
    left = X[:, feat] <= thr
    if left.sum() == 0 or (~left).sum() == 0:
        return ('leaf', float(y.mean()))
    return ('node', feat, thr,
            build_tree(X[left], y[left], depth - 1, r),
            build_tree(X[~left], y[~left], depth - 1, r))

def tree_pred(tree, x):
    if tree[0] == 'leaf':
        return tree[1]
    _, feat, thr, L, R = tree
    return tree_pred(L, x) if x[feat] <= thr else tree_pred(R, x)

def forest_pred(trees, Xte):
    return np.mean([[tree_pred(t, x) for t in trees] for x in Xte], axis=1)

# ----------------------------------------------------------------------
# 5. 随机划分评估
# ----------------------------------------------------------------------
def rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))

def mae(a, b):
    return float(np.mean(np.abs(a - b)))

perm = rng.permutation(len(y))
n_tr = int(0.8 * len(y))
tr, te = perm[:n_tr], perm[n_tr:]

w = ridge_fit(X[tr], y[tr], lam=1.0)
p_ridge = ridge_pred(w, X[te])
trees = stump_fit(X[tr], y[tr], n_trees=40, depth=3, seed=1)
p_rf = forest_pred(trees, X[te])

print("-" * 60)
print("【随机划分】测试集 n=%d" % len(te))
print("  岭回归   RMSE=%.4f  MAE=%.4f" % (rmse(p_ridge, y[te]), mae(p_ridge, y[te])))
print("  随机森林 RMSE=%.4f  MAE=%.4f" % (rmse(p_rf, y[te]), mae(p_rf, y[te])))

# ----------------------------------------------------------------------
# 6. 留一元素 (LOO) 外推评估
# ----------------------------------------------------------------------
loo_rmse_ridge, loo_rmse_rf = [], []
loo_mae_ridge, loo_mae_rf = [], []
held_out_elems = ELEMENTS[:6]   # 只对前 6 个元素做 LOO，控制耗时

for e in held_out_elems:
    mask_te = np.array([e in s for s in elem_sets])
    mask_tr = ~mask_te
    if mask_te.sum() < 5 or mask_tr.sum() < 20:
        continue
    w2 = ridge_fit(X[mask_tr], y[mask_tr], lam=1.0)
    p2 = ridge_pred(w2, X[mask_te])
    t2 = stump_fit(X[mask_tr], y[mask_tr], n_trees=25, depth=3, seed=2)
    p2f = forest_pred(t2, X[mask_te])
    loo_rmse_ridge.append(rmse(p2, y[mask_te]))
    loo_mae_ridge.append(mae(p2, y[mask_te]))
    loo_rmse_rf.append(rmse(p2f, y[mask_te]))
    loo_mae_rf.append(mae(p2f, y[mask_te]))
    print("  LOO 元素 %-4s  n_test=%3d  岭RMSE=%.4f  森林RMSE=%.4f"
          % (e, mask_te.sum(), loo_rmse_ridge[-1], loo_rmse_rf[-1]))

print("-" * 60)
print("【LOO 外推汇总】")
print("  岭回归  平均RMSE=%.4f  平均MAE=%.4f"
      % (np.mean(loo_rmse_ridge), np.mean(loo_mae_ridge)))
print("  随机森林 平均RMSE=%.4f  平均MAE=%.4f"
      % (np.mean(loo_rmse_rf), np.mean(loo_mae_rf)))
print("  → 外推误差显著高于随机划分，说明模型对未见元素泛化能力有限（模拟数据结论）")

# ----------------------------------------------------------------------
# 7. 已知陷阱检查
# ----------------------------------------------------------------------
print("-" * 60)
print("【陷阱检查】")
# 陷阱1: 特征尺度差异导致岭回归不稳定
print("  特征量纲范围: min=%.3f max=%.3f  → 需标准化" % (X.min(), X.max()))
Xs = (X - X.mean(0)) / (X.std(0) + 1e-9)
w_s = ridge_fit(Xs[tr], y[tr], lam=1.0)
p_s = ridge_pred(w_s, Xs[te])
print("  标准化后岭回归 RMSE=%.4f (原 %.4f)" % (rmse(p_s, y[te]), rmse(p_ridge, y[te])))
# 陷阱2: 元素分布不均衡
cnt = np.array([sum(e in s for s in elem_sets) for e in ELEMENTS])
print("  元素出现次数 min=%d max=%d → 稀有元素外推更不可靠" % (cnt.min(), cnt.max()))
# 陷阱3: 误差分布而非仅均值
res = p_rf - y[te]
print("  随机划分残差分位数 5%%=%.3f 50%%=%.3f 95%%=%.3f"
      % tuple(np.percentile(res, [5, 50, 95])))

# ----------------------------------------------------------------------
# 8. 候选材料推荐（模拟数据，仅演示流程）
# ----------------------------------------------------------------------
# 用全量数据训练，在候选池中挑预测形成能最负的
w_all = ridge_fit(Xs, y, lam=1.0)
cand = []
for _ in range(3000):
    els, frac = make_sample()
    cand.append((els, frac))
Xc = np.array([featurize(e, f) for e, f in cand])
Xc_s = (Xc - X.mean(0)) / (X.std(0) + 1e-9)
pc = ridge_pred(w_all, Xc_s)
order = np.argsort(pc)[:10]
print("-" * 60)
print("【候选材料 Top-10】(模拟数据，仅供流程演示，非真实结论)")
for i in order:
    els, frac = cand[i]
    formula = "".join("%s%.2f" % (e, f) for e, f in zip(els, frac))
    print("  %-28s 预测形成能=%.3f eV/atom" % (formula, pc[i]))

# ----------------------------------------------------------------------
# 9. 出图
# ----------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

axes[0].scatter(y[te], p_rf, s=8, alpha=0.5, color='steelblue')
lim = [min(y[te].min(), p_rf.min()), max(y[te].max(), p_rf.max())]
axes[0].plot(lim, lim, 'r--', lw=1)
axes[0].set_xlabel("真实形成能 (eV/atom)")
axes[0].set_ylabel("预测形成能 (eV/atom)")
axes[0].set_title("随机划分：预测 vs 真实\n(模拟数据)")

axes[1].hist(res, bins=30, color='salmon', edgecolor='k', alpha=0.8)
axes[1].axvline(0, color='k', ls='--')
axes[1].set_xlabel("残差 (eV/atom)")
axes[1].set_ylabel("频数")
axes[1].set_title("误差分布 (随机划分)\n(模拟数据)")

xpos = np.arange(len(loo_rmse_ridge))
axes[2].bar(xpos - 0.2, loo_rmse_ridge, 0.4, label='岭回归', color='steelblue')
axes[2].bar(xpos + 0.2, loo_rmse_rf, 0.4, label='随机森林', color='salmon')
axes[2].set_xticks(xpos)
axes[2].set_xticklabels([e for e in held_out_elems[:len(xpos)]])
axes[2].set_xlabel("留出元素")
axes[2].set_ylabel("RMSE (eV/atom)")
axes[2].set_title("留一元素外推误差\n(模拟数据)")
axes[2].legend()

plt.tight_layout()
plt.savefig("figure.png", dpi=150)
print("-" * 60)
print("已保存图: figure.png")

# ----------------------------------------------------------------------
# 10. 落盘
# ----------------------------------------------------------------------
import csv
with open("loo_results.csv", "w", newline="", encoding="utf-8") as fh:
    wcsv = csv.writer(fh)
    wcsv.writerow(["held_out_element", "n_test", "ridge_rmse", "rf_rmse"])
    for i, e in enumerate(held_out_elems[:len(loo_rmse_ridge)]):
        wcsv.writerow([e, "", "%.4f" % loo_rmse_ridge[i], "%.4f" % loo_rmse_rf[i]])

with open("candidates.csv", "w", newline="", encoding="utf-8") as fh:
    wcsv = csv.writer(fh)
    wcsv.writerow(["formula", "predicted_formation_energy_eV_per_atom"])
    for i in order:
        els, frac = cand[i]
        formula = "".join("%s%.2f" % (e, f) for e, f in zip(els, frac))
        wcsv.writerow([formula, "%.4f" % pc[i]])

print("已保存: loo_results.csv, candidates.csv")
print("=" * 60)
print("注意：以上全部为【模拟数据】结果，不代表真实材料实验结论。")