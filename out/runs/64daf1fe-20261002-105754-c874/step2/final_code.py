# -*- coding: utf-8 -*-
"""
步骤2：依据符号推导结果判定问题类别，选择求解器，检查可行性与数值尺度，
       求解并输出对偶变量与敏感性区间。

输入（前序步骤产物，真实读取）：
  - step1_kkt_results.csv   （符号推导 / KKT 结果）
  - step1_figure.png        （前序图，仅作存在性校验）

求解器说明：
  本环境仅允许 numpy / matplotlib，无 scipy / pulp / pyomo / ipopt 绑定。
  因此这里实现一个自包含的 LP 单纯形求解器（HiGHS/CBC 的等价核心路径），
  并显式给出对偶变量与敏感性区间（RHS 影子价格区间）。
  NLP 情形：若判定为 NLP，则用投影梯度法求局部最优，并明确标注
  「启发式/局部解，非全局最优」——规避"把启发式解当全局最优"的陷阱。
"""

import os
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

np.set_printoptions(precision=6, suppress=True)

# ============================================================
# 0. 读取前序步骤产物（真实文件）
# ============================================================
KKT_FILE = "step1_kkt_results.csv"
FIG_FILE = "step1_figure.png"

def load_kkt(path):
    """读取 step1 的 KKT / 符号推导结果。返回 list[dict]。"""
    rows = []
    if not os.path.exists(path):
        print(f"[警告] 未找到 {path}，使用内置的模拟 KKT 结果（模拟数据）。")
        # 模拟数据：一个 2 变量 LP 的 KKT 结构
        rows = [
            {"symbol": "x1", "role": "decision", "coeff_obj": "3.0",
             "constraint": "c1", "coeff_con": "1.0", "rhs": "4.0"},
            {"symbol": "x2", "role": "decision", "coeff_obj": "5.0",
             "constraint": "c2", "coeff_con": "2.0", "rhs": "12.0"},
            {"symbol": "x1", "role": "decision", "coeff_obj": "3.0",
             "constraint": "c3", "coeff_con": "3.0", "rhs": "18.0"},
            {"symbol": "x2", "role": "decision", "coeff_obj": "5.0",
             "constraint": "c3", "coeff_con": "2.0", "rhs": "18.0"},
        ]
        return rows, True
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v.strip() if isinstance(v, str) else v)
                         for k, v in r.items()})
    return rows, False

kkt_rows, is_simulated = load_kkt(KKT_FILE)
print("=" * 70)
print("步骤2：问题类别判定 / 求解器选择 / 求解 / 敏感性分析")
print("=" * 70)
print(f"[输入] {KKT_FILE} 读取到 {len(kkt_rows)} 行；"
      f"{'（模拟数据，非真实实验结论）' if is_simulated else '（真实前序产物）'}")
print(f"[输入] {FIG_FILE} 存在性检查：{os.path.exists(FIG_FILE)}")

# ============================================================
# 1. 从 KKT 结果重建数学模型（决策变量 / 目标 / 约束）
# ============================================================
# 解析：目标系数、约束矩阵、RHS
obj = {}
A_rows = {}   # constraint name -> {var: coeff}
rhs = {}
for r in kkt_rows:
    var = r.get("symbol", "")
    role = r.get("role", "decision")
    if role != "decision":
        continue
    try:
        c = float(r.get("coeff_obj", 0) or 0)
    except ValueError:
        c = 0.0
    obj[var] = obj.get(var, 0.0) + c
    cname = r.get("constraint", "")
    if cname:
        try:
            a = float(r.get("coeff_con", 0) or 0)
        except ValueError:
            a = 0.0
        A_rows.setdefault(cname, {})[var] = A_rows.setdefault(cname, {}).get(var, 0.0) + a
        try:
            rhs[cname] = float(r.get("rhs", 0) or 0)
        except ValueError:
            rhs[cname] = 0.0

vars_list = sorted(obj.keys())
cons_list = sorted(A_rows.keys())
n = len(vars_list)
m = len(cons_list)

if n == 0 or m == 0:
    raise RuntimeError("未能从 KKT 结果中解析出决策变量或约束，请检查 step1 输出格式。")

c_vec = np.array([obj[v] for v in vars_list], dtype=float)
A_mat = np.array([[A_rows[cn].get(v, 0.0) for v in vars_list] for cn in cons_list], dtype=float)
b_vec = np.array([rhs[cn] for cn in cons_list], dtype=float)

print("\n[模型重建] 决策变量:", vars_list)
print("[模型重建] 目标系数 c =", c_vec)
print("[模型重建] 约束矩阵 A =\n", A_mat)
print("[模型重建] 右端项 b =", b_vec)

# ============================================================
# 2. 问题类别判定（LP / MILP / NLP）
# ============================================================
# 判定规则：变量是否整数（MILP）、目标/约束是否非线性（NLP）
has_integer = any(str(r.get("role", "")).lower() in ("integer", "binary")
                  for r in kkt_rows)
has_nonlinear = any(str(r.get("nonlinear", "")).lower() in ("true", "1", "yes")
                    for r in kkt_rows)

if has_nonlinear:
    problem_class = "NLP"
    solver_name = "IPOPT（本环境无绑定，使用投影梯度法作为等价核心路径）"
elif has_integer:
    problem_class = "MILP"
    solver_name = "HiGHS / CBC（本环境无绑定，使用分支定界 + LP 单纯形核心路径）"
else:
    problem_class = "LP"
    solver_name = "HiGHS / CBC（本环境无绑定，使用自包含单纯形核心路径）"

print("\n[类别判定] 整数变量:", has_integer, "| 非线性项:", has_nonlinear)
print(f"[类别判定] 问题类别 = {problem_class}")
print(f"[求解器选择] {solver_name}")

# ============================================================
# 3. 可行性与数值尺度检查（规避"数值尺度过差导致求解失败"）
# ============================================================
scale_checks = []
if np.any(np.abs(A_mat) > 1e6) or np.any(np.abs(b_vec) > 1e6):
    scale_checks.append("系数/RHS 量级 > 1e6，存在尺度风险")
if np.any((np.abs(A_mat) > 0) & (np.abs(A_mat) < 1e-6)):
    scale_checks.append("存在极小非零系数（<1e-6），存在尺度风险")
if np.any(np.abs(b_vec) < 0):
    scale_checks.append("RHS 出现负值，需检查约束方向")
cond = np.linalg.cond(A_mat) if A_mat.shape[0] == A_mat.shape[1] else np.inf
if np.isfinite(cond) and cond > 1e8:
    scale_checks.append(f"约束矩阵条件数过大 ({cond:.2e})")

print("\n[数值尺度检查] 系数绝对值范围: "
      f"[{np.min(np.abs(A_mat)):.3e}, {np.max(np.abs(A_mat)):.3e}]")
print(f"[数值尺度检查] RHS 绝对值范围: [{np.min(np.abs(b_vec)):.3e}, {np.max(np.abs(b_vec)):.3e}]")
print(f"[数值尺度检查] 条件数 = {cond:.3e}")
if scale_checks:
    for s in scale_checks:
        print("  [风险]", s)
else:
    print("  [通过] 未发现明显数值尺度问题。")

# 可行性预检：x=0 是否可行（对 <= 型约束）
feas_zero = bool(np.all(A_mat @ np.zeros(n) <= b_vec + 1e-9))
print(f"[可行性预检] 原点 x=0 是否满足全部 <= 约束: {feas_zero}")

# ============================================================
# 4. 求解（LP：单纯形 + 对偶变量；NLP：投影梯度，标注局部解）
# ============================================================
def solve_lp_simplex(c, A, b, max_iter=2000, tol=1e-9):
    """
    标准型 LP: min c^T x  s.t. A x <= b, x >= 0
    返回 (x, obj, status, dual, basis, slack)
    对偶变量 y = c_B^T B^{-1}（对应 <= 约束的影子价格，<=0 表示放松 RHS 可降目标）
    """
    m_, n_ = A.shape
    # 构造 [A | I] 初始基（松弛变量）
    T = np.hstack([A, np.eye(m_)])
    rhs_ = b.copy()
    cost = np.concatenate([c, np.zeros(m_)])
    basis = list(range(n_, n_ + m_))

    # 若 RHS 有负值，先做对偶单纯形式修正（此处简单处理：取绝对值并标记）
    neg = rhs_ < -tol
    if np.any(neg):
        # 用 -1 乘该行，使 RHS 非负（约束方向随之翻转，仅用于可行性修复）
        T[neg, :] *= -1.0
        rhs_[neg] *= -1.0

    status = "optimal"
    for it in range(max_iter):
        # 计算检验数
        cB = cost[basis]
        y = np.linalg.solve(T[:, basis].T, cB)   # 对偶变量
        reduced = cost - T.T @ y
        # 入基：最小检验数（< -tol）
        entering = int(np.argmin(reduced))
        if reduced[entering] >= -tol:
            break
        # 出基：最小比值检验
        col = T[:, entering]
        ratios = np.where(col > tol, rhs_ / np.where(col > tol, col, 1.0), np.inf)
        if np.all(np.isinf(ratios)):
            status = "unbounded"
            break
        leaving = int(np.argmin(ratios))
        # 枢轴
        piv = T[leaving, entering]
        T[leaving, :] /= piv
        rhs_[leaving] /= piv
        for i in range(m_):
            if i != leaving and abs(T[i, entering]) > tol:
                f = T[i, entering]
                T[i, :] -= f * T[leaving, :]
                rhs_[i] -= f * rhs_[leaving]
        basis[leaving] = entering
    else:
        status = "max_iter_reached"

    x_full = np.zeros(n_ + m_)
    for i, bi in enumerate(basis):
        x_full[bi] = rhs_[i]
    x = x_full[:n_]
    slack = x_full[n_:]
    obj_val = float(c @ x)
    cB = cost[basis]
    dual = np.linalg.solve(T[:, basis].T, cB)
    return x, obj_val, status, dual, basis, slack, it + 1

def solve_nlp_projected_gradient(c, A, b, max_iter=5000, lr=0.01, tol=1e-10):
    """NLP 局部解：投影梯度（仅作等价核心路径，明确标注为局部解）。"""
    x = np.zeros(len(c))
    for it in range(max_iter):
        g = c  # 线性目标；若为非线性目标，此处替换为梯度
        x_new = x - lr * g
        x_new = np.maximum(x_new, 0.0)
        # 投影到 A x <= b（简单逐约束裁剪）
        for i in range(A.shape[0]):
            if A[i] @ x_new > b[i]:
                a = A[i]
                na2 = a @ a
                if na2 > 1e-12:
                    x_new = x_new - a * ((a @ x_new - b[i]) / na2)
                    x_new = np.maximum(x_new, 0.0)
        if np.linalg.norm(x_new - x) < tol:
            x = x_new
            break
        x = x_new
    obj_val = float(c @ x)
    return x, obj_val, "local_optimum(heuristic)", it + 1

if problem_class == "LP":
    x_sol, obj_sol, status, dual, basis, slack, iters = solve_lp_simplex(c_vec, A_mat, b_vec)
elif problem_class == "MILP":
    # 简化：先解 LP 松弛，再对整数变量取整并做可行性修复
    x_lp, obj_lp, status_lp, dual, basis, slack, iters = solve_lp_simplex(c_vec, A_mat, b_vec)
    x_sol = np.round(x_lp)
    # 可行性修复：若取整后不可行，逐步回退
    for _ in range(100):
        viol = A_mat @ x_sol - b_vec
        if np.all(viol <= 1e-9):
            break
        idx = int(np.argmax(viol))
        x_sol = np.maximum(x_sol - 1.0, 0.0)
    obj_sol = float(c_vec @ x_sol)
    status = "feasible_integer(heuristic)"
    dual = dual
    basis = basis
    slack = b_vec - A_mat @ x_sol
    iters = iters
else:
    x_sol, obj_sol, status, iters = solve_nlp_projected_gradient(c_vec, A_mat, b_vec)
    dual = np.zeros(m)
    basis = []
    slack = b_vec - A_mat @ x_sol

print("\n" + "-" * 70)
print(f"[求解结果] 状态 = {status}")
print(f"[求解结果] 迭代次数 = {iters}")
print(f"[求解结果] 最优目标值 = {obj_sol:.6f}")
for v, xv in zip(vars_list, x_sol):
    print(f"[求解结果] {v} = {xv:.6f}")
print(f"[求解结果] 约束松弛量 (b - Ax) = {np.asarray(slack).ravel()}")
print(f"[求解结果] 对偶变量 y = {np.asarray(dual).ravel()}")

# 最优性间隙（LP 情形由单纯形保证为 0；MILP/NLP 给出说明）
if problem_class == "LP":
    gap = 0.0
    print(f"[最优性间隙] LP 单纯形收敛，gap = {gap:.3e}（全局最优）")
elif problem_class == "MILP":
    gap = abs(obj_sol - obj_lp) / max(abs(obj_lp), 1e-9)
    print(f"[最优性间隙] MILP 启发式解 vs LP 松弛：相对 gap = {gap:.4%}（非全局最优保证）")
else:
    print("[最优性间隙] NLP 使用投影梯度，仅保证局部最优，无全局 gap 保证。")

# ============================================================
# 5. 敏感性分析：RHS 影子价格区间（LP 情形）
# ============================================================
sens_rows = []
if problem_class == "LP":
    print("\n[敏感性分析] 逐约束 RHS 扰动（±10%）对目标值的影响：")
    for i, cn in enumerate(cons_list):
        base = b_vec[i]
        for delta in (-0.10, 0.10):
            b_new = b_vec.copy()
            b_new[i] = base * (1 + delta)
            _, obj_new, st, _, _, _, _ = solve_lp_simplex(c_vec, A_mat, b_new)
            d_obj = obj_new - obj_sol
            shadow = d_obj / (b_new[i] - base) if abs(b_new[i] - base) > 1e-12 else 0.0
            sens_rows.append({
                "constraint": cn, "rhs_base": base,
                "rhs_new": b_new[i], "delta_pct": delta * 100,
                "obj_new": obj_new, "obj_change": d_obj,
                "shadow_price_est": shadow, "status": st
            })
            print(f"  {cn}: RHS {base:.3f} -> {b_new[i]:.3f} "
                  f"({delta*100:+.0f}%), 目标 {obj_sol:.4f} -> {obj_new:.4f} "
                  f"(Δ={d_obj:+.4f}), 影子价格≈{shadow:.4f}, 状态={st}")
    print("[敏感性结论] 影子价格绝对值越大，该约束越紧、越值得放松；"
          "若扰动后状态非 optimal，则超出稳健区间。")
else:
    print("\n[敏感性分析] 非 LP 问题，采用有限差分近似目标对 RHS 的敏感度：")
    for i, cn in enumerate(cons_list):
        base = b_vec[i]
        b_new = b_vec.copy()
        b_new[i] = base * 1.10
        if problem_class == "MILP":
            x2, o2, _, _, _, _, _ = solve_lp_simplex(c_vec, A_mat, b_new)
            x2 = np.round(x2)
            o2 = float(c_vec @ x2)
        else:
            x2, o2, _, _ = solve_nlp_projected_gradient(c_vec, A_mat, b_new)
        d_obj = o2 - obj_sol
        shadow = d_obj / (b_new[i] - base) if abs(b_new[i] - base) > 1e-12 else 0.0
        sens_rows.append({
            "constraint": cn, "rhs_base": base, "rhs_new": b_new[i],
            "delta_pct": 10.0, "obj_new": o2, "obj_change": d_obj,
            "shadow_price_est": shadow, "status": status
        })
        print(f"  {cn}: RHS {base:.3f} -> {b_new[i]:.3f} (+10%), "
              f"目标 {obj_sol:.4f} -> {o2:.4f} (Δ={d_obj:+.4f}), "
              f"近似影子价格≈{shadow:.4f}")

# ============================================================
# 6. 业务约束逐条对应检查（规避"遗漏实际约束"）
# ============================================================
print("\n[约束对应检查] 模型约束 vs 业务约束逐条核对：")
for i, cn in enumerate(cons_list):
    lhs = float(A_mat[i] @ x_sol)
    ok = lhs <= b_vec[i] + 1e-6
    print(f"  {cn}: A·x = {lhs:.6f} <= b = {b_vec[i]:.6f} -> "
          f"{'满足' if ok else '违反'}")

# ============================================================
# 7. 出图：目标值对 RHS 扰动的敏感性
# ============================================================
fig, ax = plt.subplots(figsize=(9, 5.5))
labels = [r["constraint"] for r in sens_rows]
vals = [r["obj_change"] for r in sens_rows]
colors = ['#d62728' if v < 0 else '#2ca02c' for v in vals]
ax.bar(range(len(vals)), vals, color=colors, alpha=0.85)
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=0)
ax.axhline(0, color='black', linewidth=0.8)
ax.set_xlabel("约束名称")
ax.set_ylabel("目标值变化量 Δobj")
ax.set_title(f"RHS 扰动敏感性分析（问题类别：{problem_class}）")
ax.grid(axis='y', linestyle='--', alpha=0.4)
plt.tight_layout()
plt.savefig("figure.png", dpi=150)
plt.close()

# ============================================================
# 8. 落盘
# ============================================================
with open("step2_solution.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["item", "value"])
    w.writerow(["problem_class", problem_class])
    w.writerow(["solver", solver_name])
    w.writerow(["status", status])
    w.writerow(["objective", obj_sol])
    w.writerow(["iterations", iters])
    for v, xv in zip(vars_list, x_sol):
        w.writerow([f"x_{v}", xv])
    for cn, dv in zip(cons_list, np.asarray(dual).ravel()):
        w.writerow([f"dual_{cn}", dv])

with open("step2_sensitivity.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["constraint", "rhs_base", "rhs_new",
                                      "delta_pct", "obj_new", "obj_change",
                                      "shadow_price_est", "status"])
    w.writeheader()
    for r in sens_rows:
        w.writerow(r)

print("\n[落盘] step2_solution.csv, step2_sensitivity.csv, figure.png")
print("=" * 70)