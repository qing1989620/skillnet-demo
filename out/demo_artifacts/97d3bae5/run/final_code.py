# -*- coding: utf-8 -*-
"""
表格数据预测建模：不可再简化基线 vs 梯度提升树
注意：本脚本使用【模拟数据】演示流程，所有数值均为模拟结果，非真实实验结论。
环境限制：仅使用 numpy 2.5.3 与 matplotlib 3.11.2（无 sklearn）。
因此手写：分层K折、逻辑回归(梯度下降)、简易梯度提升树(回归树桩)。
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SEED = 42
rng = np.random.default_rng(SEED)

# ---------------- 1. 模拟数据（明确标注：模拟数据） ----------------
def make_data(n=1200, d=6, seed=SEED):
    r = np.random.default_rng(seed)
    X = r.normal(size=(n, d))
    # 非线性 + 交互项，制造 GBDT 相对 LR 的优势
    logit = 1.2 * X[:, 0] - 0.8 * X[:, 1] + 1.5 * X[:, 2] * X[:, 3] + 0.9 * (X[:, 4] ** 2 - 1)
    p = 1 / (1 + np.exp(-logit))
    y = (r.random(n) < p).astype(int)
    # 人为注入缺失（模拟真实表格缺失）
    mask = r.random(X.shape) < 0.05
    X = X.copy()
    X[mask] = np.nan
    # 子群标签（用于误差归因）
    group = np.where(X[:, 0] > 0, "A_高X0", "B_低X0")
    return X, y, group

X, y, group = make_data()
n, d = X.shape
print("=" * 60)
print("【模拟数据】样本数=%d, 特征数=%d, 正类比例=%.3f" % (n, d, y.mean()))
print("=" * 60)

# ---------------- 2. 预处理（仅训练折 fit，避免泄漏） ----------------
def fit_preprocess(Xtr):
    med = np.nanmedian(Xtr, axis=0)
    med = np.where(np.isnan(med), 0.0, med)
    mu = np.nanmean(Xtr, axis=0)
    sd = np.nanstd(Xtr, axis=0)
    sd = np.where(sd < 1e-8, 1.0, sd)
    return med, mu, sd

def transform(X, med, mu, sd):
    miss = np.isnan(X).astype(float)          # 缺失指示变量
    Xf = np.where(np.isnan(X), med, X)
    Xs = (Xf - mu) / sd                        # 标准化（用训练折统计量）
    return np.hstack([Xs, miss])

# ---------------- 3. 分层 5 折（固定随机种子） ----------------
def stratified_kfold(y, k=5, seed=SEED):
    r = np.random.default_rng(seed)
    idx = np.arange(len(y))
    folds = [[] for _ in range(k)]
    for c in np.unique(y):
        ci = idx[y == c]
        r.shuffle(ci)
        for i, v in enumerate(ci):
            folds[i % k].append(v)
    return [np.array(sorted(f)) for f in folds]

folds = stratified_kfold(y, 5, SEED)
print("分层5折划分完成，各折正类比例：", [round(y[f].mean(), 3) for f in folds])

# ---------------- 4. 模型 ----------------
def sigmoid(z):
    return 1 / (1 + np.exp(-np.clip(z, -30, 30)))

def fit_logreg(X, y, lr=0.1, epochs=400, l2=1e-3):
    n, d = X.shape
    w = np.zeros(d); b = 0.0
    for _ in range(epochs):
        p = sigmoid(X @ w + b)
        g = p - y
        w -= lr * (X.T @ g / n + l2 * w)
        b -= lr * g.mean()
    return w, b

def predict_logreg(X, w, b):
    return sigmoid(X @ w + b)

# 简易梯度提升树（回归树桩，二分类用 logit 残差）
def fit_stump(X, g):
    best = None
    for j in range(X.shape[1]):
        vals = np.unique(np.quantile(X[:, j], np.linspace(0.1, 0.9, 9)))
        for t in vals:
            left = X[:, j] <= t
            if left.sum() < 5 or (~left).sum() < 5:
                continue
            gl, gr = g[left].mean(), g[~left].mean()
            sse = ((g[left] - gl) ** 2).sum() + ((g[~left] - gr) ** 2).sum()
            if best is None or sse < best[0]:
                best = (sse, j, t, gl, gr)
    return best

def fit_gbdt(X, y, n_trees=60, lr=0.2):
    p0 = np.clip(y.mean(), 1e-6, 1 - 1e-6)
    F = np.full(len(y), np.log(p0 / (1 - p0)))
    trees = []
    for _ in range(n_trees):
        p = sigmoid(F)
        g = y - p
        st = fit_stump(X, g)
        if st is None:
            break
        _, j, t, gl, gr = st
        F += lr * np.where(X[:, j] <= t, gl, gr)
        trees.append((j, t, gl, gr))
    return p0, trees, lr

def predict_gbdt(X, p0, trees, lr):
    F = np.full(X.shape[0], np.log(p0 / (1 - p0)))
    for j, t, gl, gr in trees:
        F += lr * np.where(X[:, j] <= t, gl, gr)
    return sigmoid(F)

# ---------------- 5. 交叉验证（Pipeline 仅训练折 fit） ----------------
def cv_eval(model_name):
    oof = np.zeros(n)
    for f in folds:
        tr = np.setdiff1d(np.arange(n), f)
        med, mu, sd = fit_preprocess(X[tr])          # 仅训练折 fit
        Xtr, Xte = transform(X[tr], med, mu, sd), transform(X[f], med, mu, sd)
        if model_name == "LogReg":
            w, b = fit_logreg(Xtr, y[tr])
            oof[f] = predict_logreg(Xte, w, b)
        else:
            p0, trees, lr = fit_gbdt(Xtr, y[tr])
            oof[f] = predict_gbdt(Xte, p0, trees, lr)
    return oof

def metrics(y, p, thr=0.5):
    yh = (p >= thr).astype(int)
    acc = (yh == y).mean()
    tp = ((yh == 1) & (y == 1)).sum(); fp = ((yh == 1) & (y == 0)).sum()
    fn = ((yh == 0) & (y == 1)).sum()
    prec = tp / (tp + fp + 1e-9); rec = tp / (tp + fn + 1e-9)
    f1 = 2 * prec * rec / (prec + rec + 1e-9)
    return acc, prec, rec, f1

oof_lr = cv_eval("LogReg")
oof_gb = cv_eval("GBDT")
res = {}
for name, p in [("LogReg", oof_lr), ("GBDT", oof_gb)]:
    res[name] = metrics(y, p)
    print("【%s】Acc=%.4f Prec=%.4f Rec=%.4f F1=%.4f" % ((name,) + res[name]))

# ---------------- 6. 误差分布分析（子群） ----------------
print("-" * 60)
print("误差分布分析（GBDT，按子群）：")
err_rows = []
for g in np.unique(group):
    m = group == g
    acc, prec, rec, f1 = metrics(y[m], oof_gb[m])
    err_rows.append((g, m.sum(), acc, f1))
    print("  子群 %s: n=%d Acc=%.4f F1=%.4f" % (g, m.sum(), acc, f1))
gap = abs(err_rows[0][2] - err_rows[1][2])
print("  子群 Acc 差距 = %.4f （>0.05 需警惕子群性能不均）" % gap)

# 误差 vs 缺失数
miss_cnt = np.isnan(X).sum(axis=1)
err = ((oof_gb >= 0.5).astype(int) != y).astype(int)
print("  缺失数=0 样本错误率=%.4f, 缺失数>0 样本错误率=%.4f" % (
    err[miss_cnt == 0].mean(), err[miss_cnt > 0].mean() if (miss_cnt > 0).any() else float('nan')))

# ---------------- 7. 陷阱规避检查 ----------------
print("-" * 60)
print("陷阱规避检查：")
print("  [OK] 标准化统计量仅在训练折 fit（见 cv_eval 中 fit_preprocess(X[tr])）")
print("  [OK] 测试集未参与任何调参，仅用于最终评估")
print("  [OK] 已报告子群性能差距，非单一指标")

# ---------------- 8. 出图 ----------------
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
names = ["LogReg", "GBDT"]
f1s = [res[n][3] for n in names]
axes[0].bar(names, f1s, color=["#7f8c8d", "#2980b9"])
axes[0].set_title("模型 F1 对比（模拟数据）"); axes[0].set_ylim(0, 1)
for i, v in enumerate(f1s):
    axes[0].text(i, v + 0.02, "%.3f" % v, ha="center")
axes[1].hist(oof_gb[y == 1], bins=25, alpha=0.6, label="正类", color="#27ae60")
axes[1].hist(oof_gb[y == 0], bins=25, alpha=0.6, label="负类", color="#c0392b")
axes[1].axvline(0.5, ls="--", c="k"); axes[1].set_title("GBDT 预测概率分布（模拟数据）")
axes[1].legend()
plt.tight_layout()
plt.savefig("figure.png", dpi=120)

# ---------------- 9. 落盘 ----------------
with open("model_comparison.csv", "w", encoding="utf-8") as f:
    f.write("model,acc,prec,rec,f1\n")
    for nm in names:
        f.write("%s,%.4f,%.4f,%.4f,%.4f\n" % ((nm,) + res[nm]))
with open("error_by_group.csv", "w", encoding="utf-8") as f:
    f.write("group,n,acc,f1\n")
    for r in err_rows:
        f.write("%s,%d,%.4f,%.4f\n" % r)
print("已保存: figure.png, model_comparison.csv, error_by_group.csv")