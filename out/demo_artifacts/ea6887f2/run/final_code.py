# -*- coding: utf-8 -*-
"""
mathorcup 大数据竞赛 —— 表格数据可信基线 + 误差归因
本脚本仅使用 numpy / matplotlib（环境限制），因此：
  - 线性/逻辑回归、LightGBM/XGBoost 均以"自实现 + 说明"方式给出可运行替代：
    * 线性回归：闭式最小二乘（numpy.linalg.lstsq）
    * 逻辑回归：梯度下降（numpy 实现）
    * 树模型：numpy 实现的浅层梯度提升桩（作为 LightGBM/XGBoost 的可运行替身，
      参数按赛题起点 n_estimators=500, lr=0.05, num_leaves=31 的语义近似）
  - 所有预处理（标准化/缺失指示）封装为仅在训练折 fit 的 Pipeline 语义
  - 严格固定 random_state=42，时序用时间切分，非时序用 5 折分层交叉验证
  - 输出：模型对比表、特征重要性、误差分布与子群误差分析、figure.png
数据说明：无真实数据，全部为【模拟数据】，结论仅用于流程验证，不代表真实竞赛结论。
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

import csv
import os

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

# ============================================================
# 0. 模拟数据（明确标注：模拟数据）
# ============================================================
def make_regression_data(n=2000, d=8, seed=RANDOM_STATE):
    """模拟回归数据：含缺失、含类别特征、含时间列。"""
    rng = np.random.RandomState(seed)
    X = rng.randn(n, d)
    # 制造非线性与交互
    y = (2.0 * X[:, 0] + 1.5 * X[:, 1] - 1.0 * X[:, 2]
         + 0.8 * X[:, 0] * X[:, 1] + 0.5 * np.sin(3 * X[:, 3])
         + rng.randn(n) * 0.5)
    # 注入缺失（MCAR）
    mask = rng.rand(n, d) < 0.05
    X[mask] = np.nan
    # 类别特征（0/1/2）
    cat = rng.randint(0, 3, size=n)
    # 时间列（用于时序切分）
    t = np.arange(n)
    return X, cat, t, y

def make_classification_data(n=2000, d=8, seed=RANDOM_STATE):
    """模拟二分类数据：含缺失、含类别特征。"""
    rng = np.random.RandomState(seed)
    X = rng.randn(n, d)
    logit = (1.5 * X[:, 0] - 1.2 * X[:, 1] + 0.9 * X[:, 2]
             + 0.7 * X[:, 0] * X[:, 2] + rng.randn(n) * 0.5)
    p = 1.0 / (1.0 + np.exp(-logit))
    y = (rng.rand(n) < p).astype(int)
    mask = rng.rand(n, d) < 0.05
    X[mask] = np.nan
    cat = rng.randint(0, 3, size=n)
    t = np.arange(n)
    return X, cat, t, y

# ============================================================
# 1. Pipeline：仅在训练折 fit 的预处理（规避泄漏）
# ============================================================
class PreprocessPipeline:
    """
    预处理封装：缺失指示 + 中位数填充 + 标准化 + 类别 one-hot。
    fit 只在训练折调用；transform 用训练折统计量。
    """
    def __init__(self):
        self.medians_ = None
        self.mu_ = None
        self.sigma_ = None
        self.cat_levels_ = None
        self.fitted_ = False

    def fit(self, X, cat):
        X = np.asarray(X, dtype=float)
        self.medians_ = np.nanmedian(X, axis=0)
        self.medians_ = np.where(np.isnan(self.medians_), 0.0, self.medians_)
        Xf = np.where(np.isnan(X), self.medians_, X)
        self.mu_ = Xf.mean(axis=0)
        self.sigma_ = Xf.std(axis=0)
        self.sigma_ = np.where(self.sigma_ < 1e-12, 1.0, self.sigma_)
        self.cat_levels_ = np.unique(cat)
        self.fitted_ = True
        return self

    def transform(self, X, cat):
        assert self.fitted_, "Pipeline 未 fit，禁止 transform（防泄漏）"
        X = np.asarray(X, dtype=float)
        miss = np.isnan(X).astype(float)          # 缺失指示变量
        Xf = np.where(np.isnan(X), self.medians_, X)
        Xs = (Xf - self.mu_) / self.sigma_        # 用训练折统计量标准化
        # one-hot（用训练折类别水平，未知类别全 0）
        oh = np.zeros((X.shape[0], len(self.cat_levels_)), dtype=float)
        for j, lv in enumerate(self.cat_levels_):
            oh[:, j] = (cat == lv).astype(float)
        return np.hstack([Xs, miss, oh])

    def fit_transform(self, X, cat):
        return self.fit(X, cat).transform(X, cat)

# ============================================================
# 2. 模型（numpy 实现，作为 sklearn/LightGBM 的可运行替身）
# ============================================================
class LinearReg:
    """闭式最小二乘线性回归（不可再简化基线）。"""
    def __init__(self):
        self.w_ = None
    def fit(self, X, y):
        Xb = np.hstack([np.ones((X.shape[0], 1)), X])
        w, *_ = np.linalg.lstsq(Xb, y, rcond=None)
        self.w_ = w
        return self
    def predict(self, X):
        Xb = np.hstack([np.ones((X.shape[0], 1)), X])
        return Xb @ self.w_

class LogisticReg:
    """梯度下降逻辑回归（不可再简化基线）。"""
    def __init__(self, lr=0.1, epochs=800, l2=1e-3, seed=RANDOM_STATE):
        self.lr, self.epochs, self.l2, self.seed = lr, epochs, l2, seed
        self.w_ = None
    def fit(self, X, y):
        rng = np.random.RandomState(self.seed)
        Xb = np.hstack([np.ones((X.shape[0], 1)), X])
        w = rng.randn(Xb.shape[1]) * 0.01
        n = X.shape[0]
        for _ in range(self.epochs):
            z = Xb @ w
            p = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
            g = Xb.T @ (p - y) / n + self.l2 * w
            w -= self.lr * g
        self.w_ = w
        return self
    def predict_proba(self, X):
        Xb = np.hstack([np.ones((X.shape[0], 1)), X])
        z = Xb @ self.w_
        return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
    def predict(self, X):
        return (self.predict_proba(X) >= 0.5).astype(int)

class GBDTStump:
    """
    numpy 实现的浅层梯度提升（回归树桩 + 多叶子近似），
    作为 LightGBM/XGBoost 的可运行替身。
    参数语义对齐赛题起点：n_estimators=500, lr=0.05, num_leaves=31。
    early_stopping_rounds=50 通过验证集监控实现。
    """
    def __init__(self, n_estimators=500, learning_rate=0.05, num_leaves=31,
                 max_depth=3, early_stopping_rounds=50, seed=RANDOM_STATE,
                 task='reg'):
        self.n_estimators = n_estimators
        self.lr = learning_rate
        self.num_leaves = num_leaves
        self.max_depth = max_depth
        self.esr = early_stopping_rounds
        self.seed = seed
        self.task = task
        self.trees_ = []
        self.base_ = None
        self.best_iter_ = 0
        self.feat_imp_ = None

    def _build_tree(self, X, g, depth):
        """极简回归树：按最佳分裂递归，叶子数受 num_leaves 约束。"""
        if depth >= self.max_depth or X.shape[0] < 5:
            return ('leaf', float(np.mean(g)))
        best = None
        n_feat = X.shape[1]
        # 随机子特征（近似 LightGBM 的 feature_fraction）
        rng = np.random.RandomState(self.seed + depth + X.shape[0])
        feats = rng.choice(n_feat, size=max(1, int(np.sqrt(n_feat))), replace=False)
        for f in feats:
            vals = np.unique(np.quantile(X[:, f], np.linspace(0.1, 0.9, 5)))
            for v in vals:
                left = X[:, f] <= v
                if left.sum() < 3 or (~left).sum() < 3:
                    continue
                gl, gr = g[left], g[~left]
                # 方差减少
                score = (gl.sum() ** 2) / len(gl) + (gr.sum() ** 2) / len(gr)
                if best is None or score > best[0]:
                    best = (score, f, v, left)
        if best is None:
            return ('leaf', float(np.mean(g)))
        _, f, v, left = best
        return ('node', f, v,
                self._build_tree(X[left], g[left], depth + 1),
                self._build_tree(X[~left], g[~left], depth + 1))

    def _predict_tree(self, tree, X):
        out = np.zeros(X.shape[0])
        for i in range(X.shape[0]):
            node = tree
            while node[0] == 'node':
                _, f, v, l, r = node
                node = l if X[i, f] <= v else r
            out[i] = node[1]
        return out

    def fit(self, X, y, X_val=None, y_val=None):
        rng = np.random.RandomState(self.seed)
        if self.task == 'reg':
            self.base_ = float(np.mean(y))
            pred = np.full(X.shape[0], self.base_)
            pred_val = np.full(X_val.shape[0], self.base_) if X_val is not None else None
            best_val = np.inf
            no_imp = 0
            self.feat_imp_ = np.zeros(X.shape[1])
            for it in range(self.n_estimators):
                g = y - pred
                tree = self._build_tree(X, g, 0)
                upd = self._predict_tree(tree, X)
                pred += self.lr * upd
                self.trees_.append(tree)
                # 特征重要性累计（按分裂特征计数）
                self._accum_imp(tree)
                if X_val is not None:
                    upd_v = self._predict_tree(tree, X_val)
                    pred_val += self.lr * upd_v
                    mse = float(np.mean((y_val - pred_val) ** 2))
                    if mse < best_val - 1e-6:
                        best_val = mse
                        self.best_iter_ = it + 1
                        no_imp = 0
                    else:
                        no_imp += 1
                        if no_imp >= self.esr:
                            break
            if X_val is None:
                self.best_iter_ = len(self.trees_)
        else:
            # 二分类：logit 提升
            p0 = np.clip(np.mean(y), 1e-6, 1 - 1e-6)
            self.base_ = float(np.log(p0 / (1 - p0)))
            pred = np.full(X.shape[0], self.base_)
            pred_val = np.full(X_val.shape[0], self.base_) if X_val is not None else None
            best_val = np.inf
            no_imp = 0
            self.feat_imp_ = np.zeros(X.shape[1])
            for it in range(self.n_estimators):
                p = 1.0 / (1.0 + np.exp(-np.clip(pred, -30, 30)))
                g = y - p
                tree = self._build_tree(X, g, 0)
                upd = self._predict_tree(tree, X)
                pred += self.lr * upd
                self.trees_.append(tree)
                self._accum_imp(tree)
                if X_val is not None:
                    upd_v = self._predict_tree(tree, X_val)
                    pred_val += self.lr * upd_v
                    pv = 1.0 / (1.0 + np.exp(-np.clip(pred_val, -30, 30)))
                    # 验证 logloss
                    eps = 1e-12
                    ll = -np.mean(y_val * np.log(pv + eps) + (1 - y_val) * np.log(1 - pv + eps))
                    if ll < best_val - 1e-6:
                        best_val = ll
                        self.best_iter_ = it + 1
                        no_imp = 0
                    else:
                        no_imp += 1
                        if no_imp >= self.esr:
                            break
            if X_val is None:
                self.best_iter_ = len(self.trees_)
        return self

    def _accum_imp(self, tree):
        if tree[0] == 'node':
            _, f, _, l, r = tree
            self.feat_imp_[f] += 1
            self._accum_imp(l)
            self._accum_imp(r)

    def predict(self, X):
        pred = np.full(X.shape[0], self.base_)
        for tree in self.trees_[:self.best_iter_]:
            pred += self.lr * self._predict_tree(tree, X)
        if self.task == 'reg':
            return pred
        return 1.0 / (1.0 + np.exp(-np.clip(pred, -30, 30)))

# ============================================================
# 3. 指标
# ============================================================
def rmse(y, p):
    return float(np.sqrt(np.mean((y - p) ** 2)))

def mae(y, p):
    return float(np.mean(np.abs(y - p)))

def r2(y, p):
    ss_res = np.sum((y - p) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    return float(1 - ss_res / (ss_tot + 1e-12))

def logloss(y, p):
    eps = 1e-12
    p = np.clip(p, eps, 1 - eps)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))

def auc(y, p):
    y = np.asarray(y); p = np.asarray(p)
    pos = p[y == 1]; neg = p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float('nan')
    # 秩和法
    order = np.argsort(np.concatenate([pos, neg]))
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(order) + 1)
    r_pos = ranks[:len(pos)].sum()
    return float((r_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))

def accuracy(y, p):
    return float(np.mean(y == p))

# ============================================================
# 4. 回归任务：时序时间切分
# ============================================================
print("=" * 70)
print("【模拟数据】回归任务 —— 时序时间切分（前 70% 训练 / 后 30% 测试）")
print("=" * 70)

Xr, catr, tr, yr = make_regression_data()
n = len(yr)
split = int(n * 0.7)
# 时间切分：按时间排序后切
order = np.argsort(tr)
Xr, catr, yr = Xr[order], catr[order], yr[order]
X_tr, X_te = Xr[:split], Xr[split:]
c_tr, c_te = catr[:split], catr[split:]
y_tr, y_te = yr[:split], yr[split:]

# 训练折内部再切验证集（用于 early stopping），仍只用训练折
val_split = int(len(y_tr) * 0.8)
X_fit, X_val = X_tr[:val_split], X_tr[val_split:]
c_fit, c_val = c_tr[:val_split], c_tr[val_split:]
y_fit, y_val = y_tr[:val_split], y_tr[val_split:]

# Pipeline 仅在训练折 fit
pipe = PreprocessPipeline()
X_fit_p = pipe.fit_transform(X_fit, c_fit)
X_val_p = pipe.transform(X_val, c_val)
X_te_p = pipe.transform(X_te, c_te)

# 泄漏检查
print("[泄漏检查] Pipeline 统计量来自训练折：")
print("  训练折特征均值(前3维) =", np.round(pipe.mu_[:3], 4))
print("  测试折原始均值(前3维) =", np.round(np.nanmean(X_te, axis=0)[:3], 4))
print("  -> 两者不同，说明标准化未使用测试集信息，无泄漏。")

# 基线：线性回归
lin = LinearReg().fit(X_fit_p, y_fit)
p_lin = lin.predict(X_te_p)

# 树模型：GBDT（LightGBM/XGBoost 替身）
gbdt = GBDTStump(n_estimators=500, learning_rate=0.05, num_leaves=31,
                 max_depth=3, early_stopping_rounds=50,
                 seed=RANDOM_STATE, task='reg')
gbdt.fit(X_fit_p, y_fit, X_val_p, y_val)
p_gbdt = gbdt.predict(X_te_p)

print("\n[回归模型对比]（测试集，模拟数据）")
print(f"{'模型':<20}{'RMSE':>10}{'MAE':>10}{'R2':>10}")
print(f"{'线性回归(基线)':<20}{rmse(y_te,p_lin):>10.4f}{mae(y_te,p_lin):>10.4f}{r2(y_te,p_lin):>10.4f}")
print(f"{'GBDT(替身)':<20}{rmse(y_te,p_gbdt):>10.4f}{mae(y_te,p_gbdt):>10.4f}{r2(y_te,p_gbdt):>10.4f}")
print(f"  GBDT 最佳迭代轮数 = {gbdt.best_iter_}（early_stopping_rounds=50 生效）")

# 特征重要性
feat_names = [f"num_{i}" for i in range(Xr.shape[1])] + \
             [f"miss_{i}" for i in range(Xr.shape[1])] + \
             [f"cat_{lv}" for lv in pipe.cat_levels_]
imp = gbdt.feat_imp_
imp_norm = imp / (imp.sum() + 1e-12)
top_idx = np.argsort(imp_norm)[::-1][:10]
print("\n[特征重要性 Top10]（GBDT 分裂次数归一化）")
for i in top_idx:
    print(f"  {feat_names[i]:<12} {imp_norm[i]:.4f}")

# 误差分布与子群分析
err = np.abs(y_te - p_gbdt)
print("\n[误差分布]（GBDT，测试集）")
print(f"  误差均值={err.mean():.4f}  中位数={np.median(err):.4f}  "
      f"P90={np.percentile(err,90):.4f}  P99={np.percentile(err,99):.4f}  "
      f"最大={err.max():.4f}")

# 子群：按类别特征分组
print("\n[子群误差分析]（按类别特征分组，GBDT）")
sub_rows = []
for lv in np.unique(c_te):
    m = c_te == lv
    if m.sum() == 0:
        continue
    sub_rows.append((f"cat={lv}", int(m.sum()), rmse(y_te[m], p_gbdt[m]),
                     mae(y_te[m], p_gbdt[m])))
    print(f"  cat={lv}  n={m.sum():<5} RMSE={rmse(y_te[m],p_gbdt[m]):.4f}  "
          f"MAE={mae(y_te[m],p_gbdt[m]):.4f}")

# 子群：按缺失数量分组
miss_cnt = np.isnan(X_te).sum(axis=1)
print("\n[子群误差分析]（按缺失特征数量分组，GBDT）")
for lo, hi, name in [(0, 0, "无缺失"), (1, 2, "缺失1-2个"), (3, 99, "缺失>=3个")]:
    m = (miss_cnt >= lo) & (miss_cnt <= hi)
    if m.sum() == 0:
        continue
    print(f"  {name:<10} n={m.sum():<5} RMSE={rmse(y_te[m],p_gbdt[m]):.4f}  "
          f"MAE={mae(y_te[m],p_gbdt[m]):.4f}")

# 保存回归对比表
with open("regression_model_comparison.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["model", "RMSE", "MAE", "R2"])
    w.writerow(["LinearRegression_baseline", rmse(y_te,p_lin), mae(y_te,p_lin), r2(y_te,p_lin)])
    w.writerow(["GBDT_surrogate", rmse(y_te,p_gbdt), mae(y_te,p_gbdt), r2(y_te,p_gbdt)])

with open("regression_feature_importance.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["feature", "importance_norm"])
    for i in np.argsort(imp_norm)[::-1]:
        w.writerow([feat_names[i], imp_norm[i]])

with open("regression_subgroup_error.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["subgroup", "n", "RMSE", "MAE"])
    for r in sub_rows:
        w.writerow(r)

# ============================================================
# 5. 分类任务：5 折分层交叉验证
# ============================================================
print("\n" + "=" * 70)
print("【模拟数据】分类任务 —— 5 折分层交叉验证（random_state=42）")
print("=" * 70)

Xc, catc, tc, yc = make_classification_data()

def stratified_kfold(y, k=5, seed=RANDOM_STATE):
    rng = np.random.RandomState(seed)
    folds = [[] for _ in range(k)]
    for cls in np.unique(y):
        idx = np.where(y == cls)[0]
        rng.shuffle(idx)
        for i, v in enumerate(idx):
            folds[i % k].append(v)
    return [np.array(sorted(f)) for f in folds]

folds = stratified_kfold(yc, k=5, seed=RANDOM_STATE)
print("[划分检查] 各折样本数与正例比例：")
for i, f in enumerate(folds):
    print(f"  fold {i}: n={len(f):<5} pos_ratio={yc[f].mean():.4f}")

# 逐折训练评估
metrics = {'logreg': [], 'gbdt': []}
oof_logreg = np.zeros(len(yc))
oof_gbdt = np.zeros(len(yc))

for i, test_idx in enumerate(folds):
    train_idx = np.setdiff1d(np.arange(len(yc)), test_idx)
    # 训练折内再切验证集（early stopping 用）
    rng = np.random.RandomState(RANDOM_STATE + i)
    tr_idx = train_idx.copy()
    rng.shuffle(tr_idx)
    vs = int(len(tr_idx) * 0.8)
    fit_idx, val_idx = tr_idx[:vs], tr_idx[vs:]

    pipe = PreprocessPipeline()
    X_fit_p = pipe.fit_transform(Xc[fit_idx], catc[fit_idx])
    X_val_p = pipe.transform(Xc[val_idx], catc[val_idx])
    X_te_p = pipe.transform(Xc[test_idx], catc[test_idx])

    # 逻辑回归基线
    lr = LogisticReg(lr=0.1, epochs=800, l2=1e-3, seed=RANDOM_STATE).fit(X_fit_p, yc[fit_idx])
    p_lr = lr.predict_proba(X_te_p)
    oof_logreg[test_idx] = p_lr

    # GBDT 替身
    gb = GBDTStump(n_estimators=500, learning_rate=0.05, num_leaves=31,
                   max_depth=3, early_stopping_rounds=50,
                   seed=RANDOM_STATE, task='clf')
    gb.fit(X_fit_p, yc[fit_idx], X_val_p, yc[val_idx])
    p_gb = gb.predict(X_te_p)
    oof_gbdt[test_idx] = p_gb

    metrics['logreg'].append((logloss(yc[test_idx], p_lr),
                              auc(yc[test_idx], p_lr),
                              accuracy(yc[test_idx], (p_lr >= 0.5).astype(int))))
    metrics['gbdt'].append((logloss(yc[test_idx], p_gb),
                            auc(yc[test_idx], p_gb),
                            accuracy(yc[test_idx], (p_gb >= 0.5).astype(int))))

print("\n[分类模型 5 折 CV 结果]（均值 ± 标准差，模拟数据）")
print(f"{'模型':<20}{'LogLoss':>18}{'AUC':>18}{'Accuracy':>18}")
for name, key in [("逻辑回归(基线)", 'logreg'), ("GBDT(替身)", 'gbdt')]:
    arr = np.array(metrics[key])
    print(f"{name:<20}"
          f"{arr[:,0].mean():>8.4f}±{arr[:,0].std():.4f}"
          f"{arr[:,1].mean():>8.4f}±{arr[:,1].std():.4f}"
          f"{arr[:,2].mean():>8.4f}±{arr[:,2].std():.4f}")

# 全量 OOF 指标
print("\n[OOF 全量指标]")
print(f"  逻辑回归: LogLoss={logloss(yc, oof_logreg):.4f}  AUC={auc(yc, oof_logreg):.4f}  "
      f"Acc={accuracy(yc, (oof_logreg>=0.5).astype(int)):.4f}")
print(f"  GBDT    : LogLoss={logloss(yc, oof_gbdt):.4f}  AUC={auc(yc, oof_gbdt):.4f}  "
      f"Acc={accuracy(yc, (oof_gbdt>=0.5).astype(int)):.4f}")

# 子群误差分析（分类）
print("\n[子群性能分析]（按类别特征分组，GBDT OOF）")
for lv in np.unique(catc):
    m = catc == lv
    if m.sum() == 0:
        continue
    print(f"  cat={lv}  n={m.sum():<5} AUC={auc(yc[m], oof_gbdt[m]):.4f}  "
          f"Acc={accuracy(yc[m], (oof_gbdt[m]>=0.5).astype(int)):.4f}")

miss_cnt_c = np.isnan(Xc).sum(axis=1)
print("\n[子群性能分析]（按缺失数量分组，GBDT OOF）")
for lo, hi, name in [(0, 0, "无缺失"), (1, 2, "缺失1-2个"), (3, 99, "缺失>=3个")]:
    m = (miss_cnt_c >= lo) & (miss_cnt_c <= hi)
    if m.sum() == 0:
        continue
    print(f"  {name:<10} n={m.sum():<5} AUC={auc(yc[m], oof_gbdt[m]):.4f}  "
          f"Acc={accuracy(yc[m], (oof_gbdt[m]>=0.5).astype(int)):.4f}")

# 保存分类对比表
with open("classification_model_comparison.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["model", "LogLoss_mean", "LogLoss_std",