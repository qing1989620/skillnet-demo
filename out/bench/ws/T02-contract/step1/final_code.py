# -*- coding: utf-8 -*-
"""
纯成分特征预测无机化合物形成能 + 留一元素(LOO)外推评估
注意：本脚本使用【模拟数据】(synthetic data)，所有数值均为演示用途，
      不代表任何真实实验或DFT结论。
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

rng = np.random.default_rng(42)

# ----------------------------------------------------------------------
# 1. 构造模拟数据（模拟数据！）
#    元素池：用原子序数 Z 代表元素身份，每个元素有电负性、半径、族等属性
# ----------------------------------------------------------------------
N_ELEM = 30
Z = np.arange(1, N_ELEM + 1)
# 模拟元素属性（模拟数据）
elem_chi = 0.7 + 2.5 * (Z / N_ELEM) + rng.normal(0, 0.15, N_ELEM)      # 电负性
elem_rad = 0.8 + 1.6 * (Z / N_ELEM) + rng.normal(0, 0.10, N_ELEM)      # 原子半径
elem_group = (Z % 18) + 1                                              # 族号

# 生成化合物：随机 2~3 元，化学计量比 1~4
N_SAMPLE = 1200
comp_idx, comp_frac, labels = [], [], []
for _ in range(N_SAMPLE):
    k = rng.integers(2, 4)
    idx = rng.choice(N_ELEM, size=k, replace=False)
    frac = rng.integers(1, 5, size=k).astype(float)
    frac /= frac.sum()
    # 模拟形成能：由成分加权属性 + 非线性项 + 噪声决定（模拟数据）
    chi_mix = np.sum(frac * elem_chi[idx])
    rad_mix = np.sum(frac * elem_rad[idx])
    chi_var = np.var(elem_chi[idx])
    e_form = (-1.2 * chi_var - 0.8 * abs(chi_mix - 1.8)
              + 0.5 * rad_mix + 0.3 * np.sin(3 * chi_mix)
              + rng.normal(0, 0.12))
    comp_idx.append(idx)
    comp_frac.append(frac)
    labels.append(e_form)
labels = np.array(labels)

# ----------------------------------------------------------------------
# 2. 纯成分描述符（不依赖晶体结构）
#    统一能量参考态：这里形成能已按每原子归一（模拟数据中已保证）
# ----------------------------------------------------------------------
def featurize(idx, frac):
    chi = elem_chi[idx]; rad = elem_rad[idx]; grp = elem_group[idx]
    feats = [
        np.sum(frac * chi), np.sum(frac * rad), np.sum(frac * grp),
        np.var(chi), np.var(rad),
        np.max(chi) - np.min(chi), np.max(rad) - np.min(rad),
        np.sum(frac * chi * rad),
        len(idx),
        np.sum(frac * np.log(frac + 1e-12)),   # 混合熵
    ]
    return np.array(feats)

X = np.array([featurize(i, f) for i, f in zip(comp_idx, comp_frac)])
y = labels.copy()

# 能量参考态统一检查（模拟数据）
print("[检查] 能量参考态：形成能已按每原子归一，均值=%.4f eV/atom，标准差=%.4f"
      % (y.mean(), y.std()))

# ----------------------------------------------------------------------
# 3. 模型：用 numpy 实现 随机森林风格(袋装决策树) 与 核回归
#    说明：环境仅允许 numpy/matplotlib，故用 numpy 手写简化模型
# ----------------------------------------------------------------------
class SimpleTree:
    """极简回归树（深度受限，用于袋装）"""
    def __init__(self, depth=4, min_leaf=8):
        self.depth, self.min_leaf = depth, min_leaf
    def fit(self, X, y):
        self.tree = self._build(X, y, 0)
        return self
    def _build(self, X, y, d):
        if d >= self.depth or len(y) < 2 * self.min_leaf:
            return ('leaf', y.mean())
        best = None
        for f in range(X.shape[1]):
            vals = np.unique(X[:, f])
            if len(vals) < 2:
                continue
            thr = np.median(vals)
            m = X[:, f] <= thr
            if m.sum() < self.min_leaf or (~m).sum() < self.min_leaf:
                continue
            sse = ((y[m] - y[m].mean())**2).sum() + ((y[~m] - y[~m].mean())**2).sum()
            if best is None or sse < best[0]:
                best = (sse, f, thr, m)
        if best is None:
            return ('leaf', y.mean())
        _, f, thr, m = best
        return ('node', f, thr,
                self._build(X[m], y[m], d + 1),
                self._build(X[~m], y[~m], d + 1))
    def predict(self, X):
        return np.array([self._pred(x, self.tree) for x in X])
    def _pred(self, x, node):
        if node[0] == 'leaf':
            return node[1]
        _, f, thr, L, R = node
        return self._pred(x, L) if x[f] <= thr else self._pred(x, R)

class BaggedForest:
    """袋装回归树（随机森林简化版）"""
    def __init__(self, n_trees=25, depth=5, seed=0):
        self.n_trees, self.depth, self.seed = n_trees, depth, seed
    def fit(self, X, y):
        r = np.random.default_rng(self.seed)
        self.trees = []
        n = len(y)
        for _ in range(self.n_trees):
            idx = r.integers(0, n, n)
            t = SimpleTree(depth=self.depth).fit(X[idx], y[idx])
            self.trees.append(t)
        return self
    def predict(self, X):
        return np.mean([t.predict(X) for t in self.trees], axis=0)

class KernelRidge:
    """核岭回归（RBF核）"""
    def __init__(self, gamma=0.5, lam=1e-2):
        self.gamma, self.lam = gamma, lam
    def fit(self, X, y):
        self.Xtr = X
        d2 = ((X[:, None, :] - X[None, :, :])**2).sum(-1)
        K = np.exp(-self.gamma * d2)
        self.alpha = np.linalg.solve(K + self.lam * np.eye(len(y)), y)
        return self
    def predict(self, X):
        d2 = ((X[:, None, :] - self.Xtr[None, :, :])**2).sum(-1)
        K = np.exp(-self.gamma * d2)
        return K @ self.alpha

def metrics(y_true, y_pred):
    err = y_pred - y_true
    return dict(MAE=np.mean(np.abs(err)),
                RMSE=np.sqrt(np.mean(err**2)),
                R2=1 - np.sum(err**2) / np.sum((y_true - y_true.mean())**2))

# ----------------------------------------------------------------------
# 4. 随机划分评估（规避：同时报告随机与LOO，避免只报随机）
# ----------------------------------------------------------------------
def random_split_eval(X, y, seed=1):
    r = np.random.default_rng(seed)
    perm = r.permutation(len(y))
    ntr = int(0.8 * len(y))
    tr, te = perm[:ntr], perm[ntr:]
    res = {}
    for name, model in [("随机森林(袋装)", BaggedForest(seed=seed)),
                        ("核回归(RBF)", KernelRidge())]:
        model.fit(X[tr], y[tr])
        res[name] = metrics(y[te], model.predict(X[te]))
    return res, te

# ----------------------------------------------------------------------
# 5. 留一元素(LOO)外推评估：按元素身份划分，测试集含训练未见元素
# ----------------------------------------------------------------------
def loo_eval(X, y, comp_idx, seed=1):
    # 每个样本的"主元素"= 占比最大的元素
    main_elem = np.array([idx[np.argmax(f)] for idx, f in zip(comp_idx, comp_frac)])
    uniq = np.unique(main_elem)
    # 取 5 个元素作为留出元素（模拟外推边界）
    hold = uniq[::max(1, len(uniq)//5)][:5]
    te = np.where(np.isin(main_elem, hold))[0]
    tr = np.where(~np.isin(main_elem, hold))[0]
    res = {}
    for name, model in [("随机森林(袋装)", BaggedForest(seed=seed)),
                        ("核回归(RBF)", KernelRidge())]:
        model.fit(X[tr], y[tr])
        res[name] = metrics(y[te], model.predict(X[te]))
    return res, te, hold

# ----------------------------------------------------------------------
# 6. 执行评估
# ----------------------------------------------------------------------
print("\n===== 随机划分评估（模拟数据）=====")
res_rand, te_rand = random_split_eval(X, y)
for k, v in res_rand.items():
    print("  %-14s MAE=%.4f RMSE=%.4f R2=%.4f" % (k, v['MAE'], v['RMSE'], v['R2']))

print("\n===== 留一元素(LOO)外推评估（模拟数据）=====")
res_loo, te_loo, hold = loo_eval(X, y, comp_idx)
print("  留出元素(原子序数):", hold.tolist())
for k, v in res_loo.items():
    print("  %-14s MAE=%.4f RMSE=%.4f R2=%.4f" % (k, v['MAE'], v['RMSE'], v['R2']))

# 陷阱检查：随机 vs LOO 性能差距（外推边界）
gap = res_loo["随机森林(袋装)"]['MAE'] - res_rand["随机森林(袋装)"]['MAE']
print("\n[检查] 随机→LOO 的 MAE 恶化 = %.4f eV/atom（越大说明外推越难）" % gap)

# 陷阱检查：标签分布偏移
print("[检查] 训练/LOO测试 标签均值: %.4f vs %.4f（差异=%.4f）"
      % (y[np.setdiff1d(np.arange(len(y)), te_loo)].mean(),
         y[te_loo].mean(),
         y[te_loo].mean() - y[np.setdiff1d(np.arange(len(y)), te_loo)].mean()))

# ----------------------------------------------------------------------
# 7. 误差分布（不只报平均误差）
# ----------------------------------------------------------------------
model = BaggedForest(seed=1).fit(X[np.setdiff1d(np.arange(len(y)), te_loo)],
                                 y[np.setdiff1d(np.arange(len(y)), te_loo)])
err_loo = model.predict(X[te_loo]) - y[te_loo]
qs = np.percentile(np.abs(err_loo), [50, 75, 90, 95])
print("\n[误差分布] LOO 绝对误差分位数 |e|: P50=%.4f P75=%.4f P90=%.4f P95=%.4f"
      % tuple(qs))

# ----------------------------------------------------------------------
# 8. 候选材料推荐（模拟数据，仅演示流程）
# ----------------------------------------------------------------------
# 用全数据训练，在候选池中挑预测形成能最低的
full = BaggedForest(seed=7).fit(X, y)
cand_idx, cand_frac = [], []
for _ in range(300):
    k = rng.integers(2, 4)
    idx = rng.choice(N_ELEM, size=k, replace=False)
    frac = rng.integers(1, 5, size=k).astype(float); frac /= frac.sum()
    cand_idx.append(idx); cand_frac.append(frac)
Xc = np.array([featurize(i, f) for i, f in zip(cand_idx, cand_frac)])
pred_c = full.predict(Xc)
order = np.argsort(pred_c)[:5]
print("\n[候选材料] 预测形成能最低的 5 个（模拟数据，仅供流程演示）:")
for r, o in enumerate(order):
    print("  #%d 元素Z=%s 比例=%s 预测Ef=%.4f eV/atom"
          % (r + 1, cand_idx[o].tolist(), np.round(cand_frac[o], 2).tolist(), pred_c[o]))

# ----------------------------------------------------------------------
# 9. 出图
# ----------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
axes[0].hist(err_loo, bins=25, color='steelblue', edgecolor='k', alpha=0.8)
axes[0].axvline(0, color='r', ls='--')
axes[0].set_title('LOO 外推误差分布（模拟数据）')
axes[0].set_xlabel('预测误差 (eV/atom)'); axes[0].set_ylabel('频数')

names = list(res_rand.keys())
xpos = np.arange(len(names))
axes[1].bar(xpos - 0.2, [res_rand[n]['MAE'] for n in names], 0.4,
            label='随机划分', color='seagreen')
axes[1].bar(xpos + 0.2, [res_loo[n]['MAE'] for n in names], 0.4,
            label='留一元素(LOO)', color='indianred')
axes[1].set_xticks(xpos); axes[1].set_xticklabels(names)
axes[1].set_ylabel('MAE (eV/atom)')
axes[1].set_title('随机 vs 外推性能对比（模拟数据）')
axes[1].legend()
plt.tight_layout()
plt.savefig('figure.png', dpi=150)

# ----------------------------------------------------------------------
# 10. 落盘
# ----------------------------------------------------------------------
np.savetxt('loo_errors.csv', np.column_stack([y[te_loo], model.predict(X[te_loo])]),
           delimiter=',', header='y_true,y_pred', comments='')
with open('metrics.csv', 'w', encoding='utf-8') as f:
    f.write('split,model,MAE,RMSE,R2\n')
    for n, v in res_rand.items():
        f.write('random,%s,%.6f,%.6f,%.6f\n' % (n, v['MAE'], v['RMSE'], v['R2']))
    for n, v in res_loo.items():
        f.write('LOO,%s,%.6f,%.6f,%.6f\n' % (n, v['MAE'], v['RMSE'], v['R2']))
print("\n[落盘] figure.png / metrics.csv / loo_errors.csv 已生成")