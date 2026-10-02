import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 纯成分特征预测无机化合物形成能 + 未见元素外推评估
# 注意：本脚本使用【模拟数据】，仅用于演示方法流程，
#       不代表任何真实实验或 DFT 结论。
# ============================================================

rng = np.random.default_rng(42)

# ---------- 1. 构造模拟元素周期表属性 ----------
# 模拟 40 个"元素"，每个元素有 4 个成分描述符
N_ELEM = 40
elem_props = rng.normal(size=(N_ELEM, 4))  # 模拟：电负性/半径/价电子/族 等
elem_props[:, 0] = np.abs(elem_props[:, 0]) + 0.5   # 电负性 > 0
elem_props[:, 1] = np.abs(elem_props[:, 1]) + 0.5   # 半径 > 0

# ---------- 2. 构造模拟化合物（二元/三元） ----------
def make_compound(n_atoms):
    idx = rng.choice(N_ELEM, size=n_atoms, replace=False)
    frac = rng.dirichlet(np.ones(n_atoms))
    return idx, frac

def featurize(idx, frac):
    """成分特征：加权均值、加权方差、元素数、最大电负性差"""
    P = elem_props[idx]                      # (n,4)
    mean = (frac[:, None] * P).sum(0)        # 加权均值
    var = (frac[:, None] * (P - mean) ** 2).sum(0)  # 加权方差
    n = len(idx)
    en = P[:, 0]
    dEN = en.max() - en.min()
    return np.concatenate([mean, var, [n, dEN]])

N_SAMPLES = 1200
X, y, comps = [], [], []
for _ in range(N_SAMPLES):
    n = rng.choice([2, 3], p=[0.7, 0.3])
    idx, frac = make_compound(n)
    f = featurize(idx, frac)
    # 模拟形成能：线性 + 非线性 + 噪声（单位 eV/atom）
    e = (-0.8 * f[0] + 0.5 * f[4] - 0.3 * f[8]
         + 0.2 * f[9] ** 2 - 0.15 * f[10] + rng.normal(0, 0.05))
    X.append(f); y.append(e); comps.append(idx)
X = np.array(X); y = np.array(y)

# ---------- 3. 划分：按元素外推（leave-elements-out） ----------
# 关键陷阱：随机划分会高估外推能力 -> 必须按元素划分
held_out = set(rng.choice(N_ELEM, size=8, replace=False))
test_mask = np.array([any(i in held_out for i in c) for c in comps])
train_mask = ~test_mask
print(f"[数据] 总样本 {N_SAMPLES}，训练 {train_mask.sum()}，"
      f"外推测试 {test_mask.sum()}（含未见元素 {sorted(held_out)}）")

# ---------- 4. 简单岭回归（闭式解，避免第三方依赖） ----------
def ridge_fit(Xtr, ytr, lam=1e-2):
    Xb = np.hstack([Xtr, np.ones((len(Xtr), 1))])
    A = Xb.T @ Xb + lam * np.eye(Xb.shape[1])
    w = np.linalg.solve(A, Xb.T @ ytr)
    return w

def ridge_pred(w, Xte):
    Xb = np.hstack([Xte, np.ones((len(Xte), 1))])
    return Xb @ w

w = ridge_fit(X[train_mask], y[train_mask])
pred_tr = ridge_pred(w, X[train_mask])
pred_te = ridge_pred(w, X[test_mask])

def metrics(yt, yp):
    mae = np.mean(np.abs(yt - yp))
    rmse = np.sqrt(np.mean((yt - yp) ** 2))
    r2 = 1 - np.sum((yt - yp) ** 2) / np.sum((yt - yt.mean()) ** 2)
    return mae, rmse, r2

mae_tr, rmse_tr, r2_tr = metrics(y[train_mask], pred_tr)
mae_te, rmse_te, r2_te = metrics(y[test_mask], pred_te)
print(f"[训练集] MAE={mae_tr:.4f}  RMSE={rmse_tr:.4f}  R2={r2_tr:.4f}")
print(f"[外推集] MAE={mae_te:.4f}  RMSE={rmse_te:.4f}  R2={r2_te:.4f}")

# ---------- 5. 陷阱检查：随机划分 vs 元素外推 ----------
rand_idx = rng.permutation(N_SAMPLES)
n_tr = int(0.8 * N_SAMPLES)
tr_r, te_r = rand_idx[:n_tr], rand_idx[n_tr:]
w_r = ridge_fit(X[tr_r], y[tr_r])
mae_r, _, r2_r = metrics(y[te_r], ridge_pred(w_r, X[te_r]))
print(f"[陷阱检查] 随机划分 MAE={mae_r:.4f} R2={r2_r:.4f} "
      f"vs 元素外推 MAE={mae_te:.4f} R2={r2_te:.4f}")
print("  -> 随机划分明显乐观，说明必须用元素外推评估泛化。")

# ---------- 6. 候选材料推荐（模拟） ----------
# 生成一批新化合物，预测形成能，挑最负的作为候选
cand = []
for _ in range(3000):
    n = rng.choice([2, 3], p=[0.7, 0.3])
    idx, frac = make_compound(n)
    f = featurize(idx, frac)
    e = ridge_pred(w, f[None, :])[0]
    cand.append((e, idx, frac))
cand.sort(key=lambda t: t[0])
print("\n[候选材料 Top-5]（模拟预测，需实验/DFT 验证）")
for e, idx, frac in cand[:5]:
    formula = "".join(f"E{i}{frac[k]:.2f}" for k, i in enumerate(idx))
    print(f"  {formula}  预测形成能={e:.4f} eV/atom")

# ---------- 7. 出图 ----------
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
axes[0].scatter(y[test_mask], pred_te, s=12, alpha=0.6, color='tab:red')
lim = [y.min(), y.max()]
axes[0].plot(lim, lim, 'k--', lw=1)
axes[0].set_xlabel('真实形成能 (eV/atom)')
axes[0].set_ylabel('预测形成能 (eV/atom)')
axes[0].set_title(f'元素外推集 (R²={r2_te:.3f})')

axes[1].hist(y, bins=40, alpha=0.6, label='全部', color='tab:blue')
axes[1].hist(y[test_mask], bins=40, alpha=0.7, label='外推集', color='tab:red')
axes[1].set_xlabel('形成能 (eV/atom)')
axes[1].set_ylabel('样本数')
axes[1].set_title('形成能分布（模拟数据）')
axes[1].legend()
plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print("\n[输出] 图已保存 figure.png")

# ---------- 8. 落盘 ----------
np.savetxt('predictions_extrapolation.csv',
           np.column_stack([y[test_mask], pred_te]),
           delimiter=',', header='true_formation_energy,pred_formation_energy',
           comments='')
with open('candidates.csv', 'w') as fh:
    fh.write('formula,pred_formation_energy_eV_per_atom\n')
    for e, idx, frac in cand[:20]:
        formula = "".join(f"E{i}{frac[k]:.2f}" for k, i in enumerate(idx))
        fh.write(f'{formula},{e:.6f}\n')
print("[输出] predictions_extrapolation.csv, candidates.csv 已保存")
print("\n[声明] 以上全部为模拟数据，仅演示方法流程，非真实材料结论。")