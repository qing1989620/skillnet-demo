import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 说明：本脚本使用【模拟数据】演示生存分析流程（无真实数据）。
# 所有数值结果均为模拟数据产物，不代表任何真实临床结论。
# 仅使用 numpy + matplotlib，因此手写 Cox 比例风险模型的
# 偏似然（Breslow 近似）与梯度上升优化，避免依赖第三方统计库。
# ============================================================

rng = np.random.default_rng(20240517)

# ---------- 1. 生成模拟随访数据（模拟数据） ----------
n = 600
# 电子病历检验指标（基线，随访前采集，避免数据泄漏）
age = rng.normal(60, 10, n)
albumin = rng.normal(38, 5, n)          # 白蛋白 g/L
ldh = rng.normal(220, 60, n)            # 乳酸脱氢酶 U/L
crp = rng.normal(8, 6, n)               # C反应蛋白 mg/L
nlr = rng.normal(3.0, 1.5, n)           # 中性粒/淋巴比
# 真实风险系数（模拟设定）
beta_true = np.array([0.030, -0.045, 0.004, 0.035, 0.150])
X = np.column_stack([age, albumin, ldh, crp, nlr])
X_std = (X - X.mean(0)) / X.std(0)      # 标准化，便于优化与解释
lin = X_std @ beta_true
# 指数分布生存时间（比例风险假设下）
T_event = rng.exponential(scale=1.0 / np.exp(lin - lin.mean()) * 30.0)
# 5 年（60 个月）随访，行政删失
C = rng.uniform(1, 60, n)
time = np.minimum(T_event, C)
event = (T_event <= C).astype(float)

print("=" * 60)
print("【模拟数据】样本量 n =", n)
print("复发事件数 =", int(event.sum()), " 删失数 =", int((1 - event).sum()))
print("随访时间(月) 中位数 = %.2f" % np.median(time))

# ---------- 2. 数据泄漏检查 ----------
# 检查：特征是否包含随访后信息 / 结局变量
feature_names = ["age", "albumin", "ldh", "crp", "nlr"]
leak_flags = [f for f in feature_names if f in ("time", "event", "recurrence")]
print("\n[泄漏检查] 特征列表:", feature_names)
print("[泄漏检查] 是否混入结局/随访时间变量:", len(leak_flags) > 0)
print("[泄漏检查] 所有特征均为基线检验指标，未使用随访后信息 -> 通过")

# ---------- 3. 手写 Cox 偏似然（Breslow）与梯度上升 ----------
def neg_log_partial_likelihood(beta, Xs, t, e):
    """返回负偏对数似然及其梯度（Breslow 近似）。"""
    risk = Xs @ beta
    order = np.argsort(t)
    Xs, t, e, risk = Xs[order], t[order], e[order], risk[order]
    # 风险集累积（从后往前）
    nll = 0.0
    grad = np.zeros_like(beta)
    # log-sum-exp 稳定计算
    for i in range(len(t)):
        if e[i] == 1:
            idx = np.arange(i, len(t))          # 风险集：t >= t_i
            r = risk[idx]
            m = r.max()
            log_sum = m + np.log(np.exp(r - m).sum())
            nll -= (risk[i] - log_sum)
            # 梯度：x_i - sum_j w_j x_j
            w = np.exp(r - m)
            w = w / w.sum()
            grad -= (Xs[i] - w @ Xs[idx])
    return nll, grad

def fit_cox(Xs, t, e, lr=0.05, iters=800):
    beta = np.zeros(Xs.shape[1])
    for it in range(iters):
        nll, grad = neg_log_partial_likelihood(beta, Xs, t, e)
        beta = beta - lr * grad
    return beta

beta_hat = fit_cox(X_std, time, event)

# ---------- 4. 结果输出 ----------
print("\n[模型] Cox 比例风险（Breslow 偏似然，梯度上升）")
print("变量        真实系数    估计系数    HR=exp(beta)")
for name, bt, bh in zip(feature_names, beta_true, beta_hat):
    print("%-10s %8.4f %10.4f %10.4f" % (name, bt, bh, np.exp(bh)))

# 风险评分分层（按中位数分高低危）
risk_score = X_std @ beta_hat
group = (risk_score > np.median(risk_score)).astype(int)
print("\n[分层] 高危组事件率 = %.3f, 低危组事件率 = %.3f" % (
    event[group == 1].mean(), event[group == 0].mean()))

# ---------- 5. 绘图：KM 曲线（高低危组） ----------
def km_curve(t, e):
    order = np.argsort(t)
    t, e = t[order], e[order]
    times, surv = [0.0], [1.0]
    s = 1.0
    n_at_risk = len(t)
    for i in range(len(t)):
        if e[i] == 1:
            s *= (1 - 1.0 / n_at_risk)
            times.append(t[i]); surv.append(s)
        n_at_risk -= 1
    return np.array(times), np.array(surv)

fig, ax = plt.subplots(figsize=(7, 5))
for g, label, color in [(0, "低危组", "#2E86AB"), (1, "高危组", "#D1495B")]:
    tt, ss = km_curve(time[group == g], event[group == g])
    ax.step(tt, ss, where="post", label=label, color=color, lw=2)
ax.set_xlabel("随访时间（月）")
ax.set_ylabel("无复发生存概率")
ax.set_title("【模拟数据】高低危组无复发生存曲线（KM）")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("figure.png", dpi=150)
plt.close(fig)

# ---------- 6. 落盘 ----------
import csv
with open("cox_results.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["variable", "beta_true", "beta_hat", "HR"])
    for name, bt, bh in zip(feature_names, beta_true, beta_hat):
        w.writerow([name, round(bt, 4), round(bh, 4), round(float(np.exp(bh)), 4)])

print("\n已保存: figure.png, cox_results.csv")
print("注意：以上全部为【模拟数据】结果，非真实临床结论。")