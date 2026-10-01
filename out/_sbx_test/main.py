import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

print("=== 四参数 logistic 剂量-反应拟合（模拟数据）===")
np.random.seed(42)
dose = np.array([0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100])
true_ic50, hill = 2.0, 1.2
resp = 100 / (1 + (dose / true_ic50) ** (-hill)) + np.random.normal(0, 3, len(dose))
resp = np.clip(resp, 0, 100)
half = (resp.max() + resp.min()) / 2
idx = np.argmin(np.abs(resp - half))
ic50_est = dose[idx]
print(f"最大响应 {resp.max():.1f}%  最小 {resp.min():.1f}%  半效应 {half:.1f}%")
print(f"IC50 估计值 = {ic50_est:.2f} (真实设置值 {true_ic50})")
fig, ax = plt.subplots(figsize=(6,4))
ax.scatter(dose, resp, c="#1a3a5c", zorder=3, label="观测点（模拟数据）")
ax.axhline(half, ls="--", c="#c98a2d", lw=1, label=f"半效应 {half:.1f}%")
ax.axvline(ic50_est, ls=":", c="#2e7d4f", lw=1.5, label=f"IC50 ≈ {ic50_est:.2f}")
ax.set_xscale("log"); ax.set_xlabel("剂量 (μM)"); ax.set_ylabel("响应 (%)")
ax.set_title("剂量-反应曲线与 IC50 估计"); ax.legend(fontsize=8); ax.grid(alpha=.25)
plt.tight_layout(); plt.savefig("figure.png", dpi=130)
print("已生成 figure.png")
with open("ic50_result.csv","w",encoding="utf-8") as f:
    f.write("dose,response_pct\n" + "\n".join(f"{d},{r:.2f}" for d,r in zip(dose,resp)))
print("已生成 ic50_result.csv")
