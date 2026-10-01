import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

np.random.seed(42)

# ============================================================
# 数据说明：以下为【模拟数据】，用于演示 EDA 流程，非真实实验结论
# 设计：9 个剂量点，每组 3 次重复 => 27 条观测
# ============================================================
doses = np.array([0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0])
n_rep = 3
reps = np.arange(1, n_rep + 1)

# 4 参数 logistic 生成"真值"抑制率，再叠加实验噪声
top, bottom, ec50, hill = 95.0, 3.0, 25.0, 1.2
true_inh = bottom + (top - bottom) / (1.0 + (ec50 / doses) ** hill)

records = []
for d, t in zip(doses, true_inh):
    noise = np.random.normal(0, 3.0, size=n_rep)
    for r, nz in zip(reps, noise):
        val = float(np.clip(t + nz, 0.0, 100.0))
        records.append((d, r, val))

dose_arr = np.array([x[0] for x in records])
rep_arr = np.array([x[1] for x in records])
inh_arr = np.array([x[2] for x in records])

print("=" * 70)
print("【重要声明】本脚本使用【模拟数据】演示 EDA 流程，非真实实验结论。")
print("=" * 70)
print(f"总观测数: {len(inh_arr)}  |  剂量点数: {len(np.unique(dose_arr))}  |  每组重复数: {n_rep}")

# ============================================================
# 步骤 1：单变量分布与缺失率排行
# ============================================================
print("\n" + "=" * 70)
print("步骤 1：单变量分布与缺失率")
print("=" * 70)

def describe(name, arr):
    arr = np.asarray(arr, dtype=float)
    n_missing = int(np.sum(~np.isfinite(arr)))
    valid = arr[np.isfinite(arr)]
    if valid.size == 0:
        print(f"{name}: 全部缺失")
        return
    q1, q2, q3 = np.percentile(valid, [25, 50, 75])
    print(f"{name:12s} | n={valid.size:3d} 缺失={n_missing} "
          f"| mean={valid.mean():8.3f} std={valid.std(ddof=1):7.3f} "
          f"| min={valid.min():7.3f} Q1={q1:7.3f} med={q2:7.3f} "
          f"Q3={q3:7.3f} max={valid.max():7.3f} "
          f"| skew={float(((valid-valid.mean())**3).mean()/ (valid.std(ddof=0)**3 + 1e-12)):6.3f}")

describe("剂量", dose_arr)
describe("重复编号", rep_arr)
describe("抑制率", inh_arr)

missing_rate = np.mean(~np.isfinite(inh_arr)) * 100
print(f"\n抑制率缺失率: {missing_rate:.2f}%")

# 规避陷阱：只看均值不看分布形态 -> 打印每组分布形态
print("\n[规避陷阱] 每组分布形态（不只看均值）：")
print(f"{'剂量':>8s} {'n':>3s} {'mean':>8s} {'std':>7s} {'min':>7s} {'max':>7s} {'range':>7s}")
for d in doses:
    m = dose_arr == d
    v = inh_arr[m]
    print(f"{d:8.2f} {v.size:3d} {v.mean():8.3f} {v.std(ddof=1):7.3f} "
          f"{v.min():7.3f} {v.max():7.3f} {v.max()-v.min():7.3f}")

# ============================================================
# 步骤 2：分组对比，检查组间基线是否可比
# ============================================================
print("\n" + "=" * 70)
print("步骤 2：分组对比与样本量均衡性")
print("=" * 70)

counts = np.array([np.sum(dose_arr == d) for d in doses])
print(f"各组样本量: {counts.tolist()}")
print(f"样本量是否均衡: {'是' if counts.min() == counts.max() else '否'} "
      f"(min={counts.min()}, max={counts.max()})")

# 规避陷阱：忽略分组间样本量差异
if counts.min() != counts.max():
    print("[规避陷阱] 组间样本量不均衡，后续统计需加权或使用稳健方法。")
else:
    print("[规避陷阱] 组间样本量均衡，可直接比较组均值。")

# 组内变异系数（CV）检查重复性
print("\n组内重复性（CV = std/mean）：")
cv_list = []
for d in doses:
    v = inh_arr[dose_arr == d]
    cv = v.std(ddof=1) / (v.mean() + 1e-12) * 100
    cv_list.append(cv)
    flag = "  <-- CV偏高" if cv > 15 else ""
    print(f"  剂量 {d:8.2f}: CV = {cv:6.2f}%{flag}")
print(f"平均 CV = {np.mean(cv_list):.2f}%  (经验阈值: CV>15% 提示重复性不足)")

# ============================================================
# 步骤 3：相关矩阵与共线性标注
# ============================================================
print("\n" + "=" * 70)
print("步骤 3：相关矩阵与共线性检查")
print("=" * 70)

log_dose = np.log10(dose_arr)
X = np.column_stack([dose_arr, log_dose, rep_arr, inh_arr])
names = ["剂量", "log10剂量", "重复编号", "抑制率"]
corr = np.corrcoef(X.T)

print("Pearson 相关矩阵：")
print("        " + "".join(f"{n:>12s}" for n in names))
for i, n in enumerate(names):
    print(f"{n:>8s}" + "".join(f"{corr[i, j]:12.4f}" for j in range(len(names))))

print("\n共线性检查（|r| > 0.9 的特征对）：")
collinear_pairs = []
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        if abs(corr[i, j]) > 0.9:
            collinear_pairs.append((names[i], names[j], corr[i, j]))
            print(f"  {names[i]} <-> {names[j]}: r = {corr[i, j]:.4f}  <-- 高度共线")
if not collinear_pairs:
    print("  未发现 |r|>0.9 的特征对。")

# 规避陷阱：用相关系数解释非线性关系
print("\n[规避陷阱] 剂量-抑制率关系为非线性（S 型），"
      "Pearson r 仅作参考，不能作为线性关系证据。")
print(f"  Pearson r(剂量, 抑制率) = {corr[0, 3]:.4f}")
print(f"  Pearson r(log10剂量, 抑制率) = {corr[1, 3]:.4f}")
print("  建议：使用 4 参数 logistic 或 Spearman 秩相关刻画单调性。")

# Spearman 秩相关（单调性检查）
def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])

rho = spearman(dose_arr, inh_arr)
print(f"  Spearman rho(剂量, 抑制率) = {rho:.4f}  (接近 1 表示强单调递增)")

# ============================================================
# 步骤 4：目标变量分布与单调性/平台期检查
# ============================================================
print("\n" + "=" * 70)
print("步骤 4：目标变量分布、单调性与平台期")
print("=" * 70)

print(f"抑制率范围: [{inh_arr.min():.3f}, {inh_arr.max():.3f}]")
print(f"抑制率均值: {inh_arr.mean():.3f}  中位数: {np.median(inh_arr):.3f}")
print(f"抑制率偏度: {float(((inh_arr-inh_arr.mean())**3).mean()/(inh_arr.std(ddof=0)**3+1e-12)):.3f}")

# 单调性检查（基于组均值）
group_means = np.array([inh_arr[dose_arr == d].mean() for d in doses])
diffs = np.diff(group_means)
mono_inc = np.all(diffs >= 0)
n_violations = int(np.sum(diffs < 0))
print(f"\n组均值序列: {np.round(group_means, 2).tolist()}")
print(f"单调递增: {'是' if mono_inc else '否'}  (违反次数: {n_violations})")

# 平台期检查：相邻剂量组均值变化 < 2% 视为平台
plateau_thresh = 2.0
plateaus = []
for i in range(len(doses) - 1):
    delta = abs(group_means[i + 1] - group_means[i])
    if delta < plateau_thresh:
        plateaus.append((doses[i], doses[i + 1], delta))
print(f"\n平台期检查（相邻组均值变化 < {plateau_thresh}%）：")
if plateaus:
    for d1, d2, dl in plateaus:
        print(f"  剂量 {d1} -> {d2}: Δ = {dl:.3f}  <-- 疑似平台")
else:
    print("  未检测到明显平台期。")

# 重复数是否足够
print(f"\n重复数检查：每组 {n_rep} 次重复")
if n_rep < 3:
    print("  [风险] 重复数 < 3，无法可靠估计组内变异。")
else:
    print(f"  每组 {n_rep} 次重复，满足最低要求（>=3）。")

# ============================================================
# 步骤 5：候选特征清单与风险项
# ============================================================
print("\n" + "=" * 70)
print("步骤 5：候选特征清单与风险项")
print("=" * 70)

print("候选特征：")
print("  - log10(剂量)：推荐作为建模主特征（线性化 S 型曲线）")
print("  - 剂量：保留用于可视化与生物学解释")
print("  - 重复编号：仅作分组标识，不作为预测特征")

risks = []
if np.mean(cv_list) > 15:
    risks.append(("组内重复性不足", f"平均 CV={np.mean(cv_list):.2f}% > 15%",
                  "增加重复数或排查实验操作误差"))
if n_violations > 0:
    risks.append(("单调性违反", f"{n_violations} 处组均值下降",
                  "检查异常点，考虑稳健回归或剔除离群值"))
if collinear_pairs:
    risks.append(("特征共线性", f"{len(collinear_pairs)} 对 |r|>0.9",
                  "建模时仅保留 log10(剂量)，避免剂量与 log 剂量同时入模"))
if not plateaus:
    risks.append(("未观测到平台期", "最高剂量可能未达饱和",
                  "建议补充更高剂量点以确认上平台"))
if n_rep < 3:
    risks.append(("重复数不足", f"n_rep={n_rep}", "增加重复至 >=3"))

print("\n风险清单：")
if risks:
    for i, (name, detail, action) in enumerate(risks, 1):
        print(f"  {i}. [{name}] {detail}")
        print(f"     处理建议: {action}")
else:
    print("  未发现显著风险项。")

# ============================================================
# 落盘：数据表 CSV
# ============================================================
import csv
with open("dose_response_data.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["dose", "log10_dose", "replicate", "inhibition_rate"])
    for d, r, v in zip(dose_arr, rep_arr, inh_arr):
        w.writerow([d, round(float(np.log10(d)), 6), int(r), round(float(v), 6)])
print("\n已保存数据表: dose_response_data.csv")

# 汇总表
with open("dose_response_summary.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["dose", "n", "mean", "std", "cv_pct", "min", "max"])
    for d in doses:
        v = inh_arr[dose_arr == d]
        w.writerow([d, v.size, round(float(v.mean()), 4), round(float(v.std(ddof=1)), 4),
                    round(float(v.std(ddof=1) / (v.mean() + 1e-12) * 100), 4),
                    round(float(v.min()), 4), round(float(v.max()), 4)])
print("已保存汇总表: dose_response_summary.csv")

# ============================================================
# 绘图：1 张图，含 4 个子图
# ============================================================
fig, axes = plt.subplots(2, 2, figsize=(13, 10))

# (a) 剂量-响应散点 + 组均值
ax = axes[0, 0]
ax.scatter(dose_arr, inh_arr, s=45, alpha=0.65, color="#4C72B0", label="个体观测（模拟）")
ax.plot(doses, group_means, "-o", color="#C44E52", lw=2, ms=7, label="组均值")
ax.set_xscale("log")
ax.set_xlabel("剂量 (log 刻度)")
ax.set_ylabel("抑制率 (%)")
ax.set_title("(a) 剂量-响应关系（模拟数据）")
ax.legend()
ax.grid(alpha=0.3)

# (b) 各组箱线图
ax = axes[0, 1]
data_by_dose = [inh_arr[dose_arr == d] for d in doses]
bp = ax.boxplot(data_by_dose, tick_labels=[f"{d:g}" for d in doses], patch_artist=True)
for patch in bp['boxes']:
    patch.set_facecolor("#8FBCDB")
    patch.set_alpha(0.7)
ax.set_xlabel("剂量")
ax.set_ylabel("抑制率 (%)")
ax.set_title("(b) 各组分布（箱线图）")
ax.grid(alpha=0.3, axis="y")

# (c) 组内 CV 柱状图
ax = axes[1, 0]
colors = ["#C44E52" if c > 15 else "#55A868" for c in cv_list]
ax.bar([f"{d:g}" for d in doses], cv_list, color=colors, alpha=0.8)
ax.axhline(15, color="red", ls="--", lw=1.5, label="CV=15% 阈值")
ax.set_xlabel("剂量")
ax.set_ylabel("组内 CV (%)")
ax.set_title("(c) 组内重复性（CV）")
ax.legend()
ax.grid(alpha=0.3, axis="y")

# (d) 相关矩阵热图
ax = axes[1, 1]
im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_xticks(range(len(names)))
ax.set_yticks(range(len(names)))
ax.set_xticklabels(names, rotation=30, ha="right")
ax.set_yticklabels(names)
for i in range(len(names)):
    for j in range(len(names)):
        ax.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center",
                color="white" if abs(corr[i, j]) > 0.6 else "black", fontsize=9)
ax.set_title("(d) 相关矩阵（|r|>0.9 为共线）")
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

plt.tight_layout()
plt.savefig("figure.png", dpi=150, bbox_inches="tight")
print("已保存图像: figure.png")

print("\n" + "=" * 70)
print("EDA 完成。所有结果基于【模拟数据】，仅用于流程演示。")
print("=" * 70)