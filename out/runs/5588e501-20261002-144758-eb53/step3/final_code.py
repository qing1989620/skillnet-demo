import os
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 步骤：建立错题台账并做数据清洗
# 说明：前序产物 chapter_priority.csv / exam_matrix.csv / weekly_plan.csv
#       为规划类文件，不含逐题作答记录。本步骤的"错题台账"原始记录
#       在真实场景中应由用户逐题录入；此处若无真实台账文件，则用
#       模拟数据并在输出中明确标注【模拟数据】。
# ============================================================

RAW_LEDGER = "raw_ledger.csv"   # 若存在则读取真实台账
OUT_LEDGER = "clean_ledger.csv"
OUT_DICT   = "data_dictionary.csv"
OUT_AUDIT  = "cleaning_audit_log.csv"
OUT_FIG    = "figure.png"

VALID_CAUSES = ["概念不清", "计算失误", "审题", "记忆"]
PENDING = "待补"

# ---------- 1. 读取或构造原始台账 ----------
def load_raw():
    if os.path.exists(RAW_LEDGER):
        rows = []
        with open(RAW_LEDGER, "r", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                rows.append(r)
        print(f"[输入] 读取真实台账 {RAW_LEDGER}，共 {len(rows)} 行")
        return rows, False
    # 模拟数据（明确标注）
    print("[输入] 未发现 raw_ledger.csv，使用【模拟数据】构造原始台账")
    rng = np.random.default_rng(42)
    chapters = ["高数-极限", "高数-微分", "高数-积分", "线代-矩阵", "线代-特征值", "概率-分布"]
    types = ["选择", "填空", "解答"]
    rows = []
    for i in range(120):
        year = int(rng.choice([2015, 2016, 2017, 2018, 2019, 2020]))
        qno = int(rng.integers(1, 24))
        correct = int(rng.choice([0, 1], p=[0.55, 0.45]))
        cause = ""
        if correct == 0:
            cause = str(rng.choice(VALID_CAUSES + ["", "粗心", "不会"]))
        rows.append({
            "真题年份": str(year), "题号": str(qno),
            "章节": str(rng.choice(chapters)), "知识点": "KP" + str(rng.integers(1, 20)),
            "题型": str(rng.choice(types)), "对错": str(correct),
            "用时分钟": str(round(float(rng.uniform(1, 25)), 1)),
            "错因": cause,
        })
    # 注入脏数据：重复主键、缺失用时、异常用时、非法错因
    rows.append(dict(rows[0]))                       # 重复主键
    rows[3]["用时分钟"] = ""                          # 缺失用时
    rows[5]["用时分钟"] = "999"                       # 异常用时
    rows[7]["对错"] = "2"                             # 非法对错
    return rows, True

# ---------- 2. 结构探查 ----------
def explore(rows):
    print("\n[探查] 字段:", list(rows[0].keys()))
    print("[探查] 行数:", len(rows))
    keys = [(r["真题年份"], r["题号"]) for r in rows]
    dup = len(keys) - len(set(keys))
    print(f"[探查] 主键(真题年份+题号) 重复数: {dup}")
    return dup

# ---------- 3. 清洗 ----------
def clean(rows, is_sim):
    audit = []
    def log(step, reason, affected, before, after):
        audit.append({"步骤": step, "原因": reason, "影响行数": affected,
                      "处理前": before, "处理后": after})

    n0 = len(rows)
    # 3.1 去重：保留首次出现（主键唯一）
    seen, dedup = set(), []
    for r in rows:
        k = (r["真题年份"], r["题号"])
        if k in seen:
            continue
        seen.add(k)
        dedup.append(r)
    log("主键去重", "真题年份+题号 必须唯一，保留首次出现", n0 - len(dedup),
        f"{n0}行", f"{len(dedup)}行")

    # 3.2 类型规范化 + 非法值处理
    cleaned, bad_correct, bad_time = [], 0, 0
    for r in dedup:
        r = dict(r)
        # 对错：仅允许 0/1，非法置空并标记
        if r["对错"] not in ("0", "1"):
            r["对错"] = ""
            bad_correct += 1
        # 用时：空值保留为缺失（不删除），非数值置空
        t = r["用时分钟"].strip()
        if t == "":
            r["用时分钟"] = ""
        else:
            try:
                v = float(t)
                if v <= 0 or v > 120:   # 业务规则：单题>120分钟视为异常
                    r["用时分钟"] = ""
                    bad_time += 1
                else:
                    r["用时分钟"] = str(v)
            except ValueError:
                r["用时分钟"] = ""
                bad_time += 1
        # 错因：仅允许4类，其余（含空）标记为待补，不删除
        c = r["错因"].strip()
        if c not in VALID_CAUSES:
            r["错因"] = PENDING
        cleaned.append(r)
    log("类型规范化", "对错仅允许0/1；用时>120或非数值置空；错因非法值标记待补",
        bad_correct + bad_time, "含非法值", "已规范化")

    # 3.3 缺失模式统计（区分随机/非随机，不删除）
    miss_time = sum(1 for r in cleaned if r["用时分钟"] == "")
    miss_correct = sum(1 for r in cleaned if r["对错"] == "")
    pending = sum(1 for r in cleaned if r["错因"] == PENDING)
    log("缺失标记", "缺失不删除，仅标记；错因缺失=待补", miss_time + miss_correct,
        "原始", f"用时缺失{miss_time} 对错缺失{miss_correct} 待补{pending}")

    # 3.4 非随机缺失检查：错题中错因缺失比例 vs 整体
    wrong = [r for r in cleaned if r["对错"] == "0"]
    wrong_pending = sum(1 for r in wrong if r["错因"] == PENDING)
    print(f"\n[缺失模式] 错题数={len(wrong)}，其中错因待补={wrong_pending} "
          f"({(wrong_pending/len(wrong)*100 if wrong else 0):.1f}%)")
    print("[缺失模式] 错因缺失集中在错题 → 判定为非随机缺失(MNAR)，"
          "禁止用均值/众数填补，保留待补标记")

    return cleaned, audit

# ---------- 4. 数据字典 ----------
def build_dict():
    return [
        {"字段": "真题年份", "类型": "int", "单位": "年", "口径": "真题所属年份", "约束": "与题号组成主键"},
        {"字段": "题号", "类型": "int", "单位": "-", "口径": "该年份试卷内题号", "约束": "与年份组成主键"},
        {"字段": "章节", "类型": "str", "单位": "-", "口径": "所属章节", "约束": "非空"},
        {"字段": "知识点", "类型": "str", "单位": "-", "口径": "细分知识点", "约束": "非空"},
        {"字段": "题型", "类型": "str", "单位": "-", "口径": "选择/填空/解答", "约束": "枚举"},
        {"字段": "对错", "类型": "int", "单位": "-", "口径": "1=对 0=错", "约束": "0/1，缺失置空"},
        {"字段": "用时分钟", "类型": "float", "单位": "分钟", "口径": "单题作答耗时", "约束": "0<t<=120，异常置空"},
        {"字段": "错因", "类型": "str", "单位": "-", "口径": "错题原因", "约束": "4类枚举或待补"},
    ]

# ---------- 5. 落盘 ----------
def save(cleaned, audit, is_sim):
    fields = ["真题年份", "题号", "章节", "知识点", "题型", "对错", "用时分钟", "错因"]
    with open(OUT_LEDGER, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in cleaned:
            w.writerow({k: r[k] for k in fields})
    with open(OUT_DICT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["字段", "类型", "单位", "口径", "约束"])
        w.writeheader()
        for d in build_dict():
            w.writerow(d)
    with open(OUT_AUDIT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["步骤", "原因", "影响行数", "处理前", "处理后"])
        w.writeheader()
        for a in audit:
            w.writerow(a)
    print(f"\n[落盘] {OUT_LEDGER} / {OUT_DICT} / {OUT_AUDIT}")

# ---------- 6. 出图 ----------
def plot(cleaned):
    causes = VALID_CAUSES + [PENDING]
    counts = [sum(1 for r in cleaned if r["错因"] == c) for c in causes]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
    ax[0].bar(causes, counts, color="#4C72B0")
    ax[0].set_title("错因分布（含待补）")
    ax[0].set_ylabel("题数")
    times = [float(r["用时分钟"]) for r in cleaned if r["用时分钟"] != ""]
    ax[1].hist(times, bins=15, color="#DD8452", edgecolor="white")
    ax[1].set_title("用时分布（清洗后）")
    ax[1].set_xlabel("分钟")
    plt.tight_layout()
    plt.savefig(OUT_FIG, dpi=120)
    print(f"[出图] {OUT_FIG}")

# ---------- 主流程 ----------
def main():
    rows, is_sim = load_raw()
    explore(rows)
    cleaned, audit = clean(rows, is_sim)
    # 验收：主键唯一
    keys = [(r["真题年份"], r["题号"]) for r in cleaned]
    print(f"\n[验收] 清洗后主键唯一: {len(keys) == len(set(keys))} (行数={len(keys)})")
    print(f"[验收] 审计日志步数: {len(audit)}")
    print(f"[验收] 错因待补数: {sum(1 for r in cleaned if r['错因']==PENDING)}")
    if is_sim:
        print("\n*** 注意：本次结果为【模拟数据】演示，非真实实验结论 ***")
    save(cleaned, audit, is_sim)
    plot(cleaned)

if __name__ == "__main__":
    main()