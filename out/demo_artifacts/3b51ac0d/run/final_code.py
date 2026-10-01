import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 说明：本脚本使用【模拟数据】进行探索性分析演示。
# 模拟数据不代表任何真实实验结果，仅用于展示分析流程。
# ============================================================

rng = np.random.default_rng(20240607)

# 9 个剂量点（对数等间距），每组 3 次重复
doses = np.array([0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0])
n_rep = 3

# 模拟 4-参数逻辑斯蒂剂量-响应（抑制率 0~100%）
# 真实参数（模拟设定）：bottom=5, top=98, EC50=15, hill=1.2
bottom, top, ec50, hill = 5.0, 98.0, 15.0, 1.2
true_mean = bottom + (top - bottom) / (1.0 + (ec50 / doses) ** hill)

# 加入重复间随机误差（模拟实验噪声）
noise_sd = 3.0
inhibition = true_mean[:, None] + rng.normal(0, noise_sd, size=(len(doses), n_rep))
inhibition = np.clip(inhibition, 0, 100)

# 保存原始数据表为 CSV
header = "dose," + ",".join([f"rep{i+1}" for i in range(n_rep)])
data_matrix = np.column_stack([doses, inhibition])
np.savetxt("dose_response_raw.csv", data_matrix, delimiter=",", header=header, comments="", fmt="%.4f")
print("[数据] 已保存 dose_response_raw.csv （模拟数据）")

# ============================================================
# 1. 基本统计量
# ============================================================
mean_inh = inhibition.mean(axis=1)
sd_inh = inhibition.std(axis=1, ddof=1)
cv_inh = sd_inh / np.maximum(mean_inh, 1e-9) * 100.0

print("\n===== 各剂量点统计（模拟数据）=====")
print(f"{'剂量':>10} {'均值':>10} {'标准差':>10} {'CV(%)':>8}")
for d, m, s, c in zip(doses, mean_inh, sd_inh, cv_inh):
    print(f"{d:>10.2f} {m:>10.3f} {s:>10.3f} {c:>8.2f}")

# ============================================================
# 2. 单调性检查
# ============================================================
diffs = np.diff(mean_inh)
n_increase = int(np.sum(diffs > 0))
n_decrease = int(np.sum(diffs < 0))
monotonic = bool(np.all(diffs >= 0) or np.all(diffs <= 0))
print("\n===== 单调性检查 =====")
print(f"相邻剂量均值差分：{np.round(diffs, 3)}")
print(f"上升段数={n_increase}, 下降段数={n_decrease}")
print(f"整体单调性：{'单调' if monotonic else '非严格单调（存在局部波动）'}")
if not monotonic:
    viol_idx = np.where(diffs < 0)[0]
    for i in viol_idx:
        print(f"  非单调位置：剂量 {doses[i]:.2f} -> {doses[i+1]:.2f}，"
              f"均值 {mean_inh[i]:.3f} -> {mean_inh[i+1]:.3f}")

# ============================================================
# 3. 平台期检查（高剂量端是否趋于饱和）
# ============================================================
tail_n = 3
tail_vals = mean_inh[-tail_n:]
tail_range = float(tail_vals.max() - tail_vals.min())
tail_slope = float(np.polyfit(np.log10(doses[-tail_n:]), tail_vals, 1)[0])
print("\n===== 平台期检查（最高 3 个剂量）=====")
print(f"高剂量端均值：{np.round(tail_vals, 3)}")
print(f"高剂量端极差={tail_range:.3f}，对数剂量斜率={tail_slope:.3f}")
plateau = tail_range < 5.0 and abs(tail_slope) < 5.0
print(f"是否达到平台期：{'是（高剂量端趋于饱和）' if plateau else '否（高剂量端仍在变化）'}")

# 低剂量端（底部平台）
head_vals = mean_inh[:2]
head_range = float(head_vals.max() - head_vals.min())
print(f"低剂量端均值：{np.round(head_vals, 3)}，极差={head_range:.3f}")

# ============================================================
# 4. 重复数是否足够（基于 CV 与标准误）
# ============================================================
print("\n===== 重复数评估 =====")
print(f"每组重复数 n = {n_rep}")
print(f"各剂量点 CV 范围：{cv_inh.min():.2f}% ~ {cv_inh.max():.2f}%")
print(f"平均 CV = {cv_inh.mean():.2f}%")
# 估计达到目标精度所需重复数：n >= (CV / 目标相对误差)^2
target_rel_err = 5.0  # 目标相对标准误 5%
required_n = (cv_inh.mean() / target_rel_err) ** 2
print(f"若目标相对标准误为 {target_rel_err}%，估计所需重复数 ≈ {required_n:.1f}")
print(f"重复数是否充足：{'是' if n_rep >= required_n else '否（建议增加重复）'}")

# ============================================================
# 5. 共线性 / 风险清单
# ============================================================
print("\n===== 共线性与风险清单 =====")
log_doses = np.log10(doses)
# 剂量点间距均匀性
gaps = np.diff(log_doses)
print(f"对数剂量间距：{np.round(gaps, 3)}")
print(f"间距变异系数 CV = {gaps.std(ddof=1)/gaps.mean()*100:.2f}%")
if gaps.std(ddof=1) / gaps.mean() < 0.05:
    print("  -> 剂量点近似对数等间距，设计良好")
else:
    print("  -> 剂量点间距不均匀，可能影响曲线拟合稳定性")

# 高剂量端是否出现抑制率下降（毒性/钩状效应风险）
if np.any(diffs[-3:] < -2.0):
    print("  [风险] 高剂量端抑制率下降，可能存在毒性或钩状效应")
else:
    print("  [检查] 高剂量端未见明显抑制率下降")

# 低剂量端是否已有明显响应（基线风险）
if mean_inh[0] > 20:
    print("  [风险] 最低剂量已产生较强响应，可能缺少基线平台")
else:
    print("  [检查] 最低剂量响应较低，基线平台合理")

# 数据范围检查
print(f"  [检查] 抑制率范围：{inhibition.min():.2f}% ~ {inhibition.max():.2f}%")
if inhibition.min() < 0 or inhibition.max() > 100:
    print("  [风险] 存在超出 0~100% 的抑制率，需检查数据有效性")
else:
    print("  [检查] 抑制率均在 0~100% 合理范围内")

# ============================================================
# 6. 绘图
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

# 子图1：剂量-响应散点 + 均值曲线
ax = axes[0]
for j in range(n_rep):
    ax.scatter(doses, inhibition[:, j], alpha=0.5, s=25,
               label=f"重复 {j+1}" if j == 0 else None, color="steelblue")
ax.plot(doses, mean_inh, "o-", color="crimson", lw=2, ms=6, label="均值")
ax.errorbar(doses, mean_inh, yerr=sd_inh, fmt="none", ecolor="crimson",
            capsize=4, alpha=0.7)
ax.set_xscale("log")
ax.set_xlabel("剂量 (对数刻度)")
ax.set_ylabel("抑制率 (%)")
ax.set_title("剂量-响应关系（模拟数据）")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

# 子图2：各剂量点分布（箱线图）
ax = axes[1]
ax.boxplot([inhibition[i, :] for i in range(len(doses))],
           tick_labels=[f"{d:g}" for d in doses])
ax.set_xlabel("剂量")
ax.set_ylabel("抑制率 (%)")
ax.set_title("各剂量点重复分布（模拟数据）")
ax.grid(alpha=0.3, axis="y")

# 子图3：CV 随剂量变化
ax = axes[2]
ax.bar(range(len(doses)), cv_inh, color="seagreen", alpha=0.7)
ax.axhline(cv_inh.mean(), color="crimson", ls="--",
           label=f"平均 CV={cv_inh.mean():.2f}%")
ax.set_xticks(range(len(doses)))
ax.set_xticklabels([f"{d:g}" for d in doses], rotation=45)
ax.set_xlabel("剂量")
ax.set_ylabel("变异系数 CV (%)")
ax.set_title("重复间变异（模拟数据）")
ax.legend(fontsize=8)
ax.grid(alpha=0.3, axis="y")

plt.tight_layout()
plt.savefig("figure.png", dpi=150)
print("\n[绘图] 已保存 figure.png")

# ============================================================
# 7. 汇总
# ============================================================
print("\n===== 探索性分析汇总（模拟数据）=====")
print(f"剂量点数：{len(doses)}，每组重复数：{n_rep}")
print(f"整体单调性：{'单调' if monotonic else '非严格单调'}")
print(f"高剂量平台期：{'达到' if plateau else '未达到'}")
print(f"平均 CV：{cv_inh.mean():.2f}%，重复数是否充足：{'是' if n_rep >= required_n else '否'}")
print("注意：以上结论基于模拟数据，不代表真实实验结论。")