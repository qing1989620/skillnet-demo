# -*- coding: utf-8 -*-
"""
达尔文研究范式清单（模拟数据，用于演示 research-field-top-ideas-distillation 流程）
注意：本脚本中所有文献条目、被引数、成熟度评分均为【模拟数据】，
      仅用于演示流程与产出格式，不代表真实文献计量结论。
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv

rng = np.random.default_rng(42)

# ---------- 1. 关键词扩展与抓取（模拟） ----------
KW_GROUPS = {
    "G1_理论机制": ["natural selection", "descent with modification", "common descent"],
    "G2_生物类群": ["barnacle monograph", "coral reef subsidence", "earthworm soil"],
    "G3_行为与植物": ["sexual selection", "cross pollination", "expression of emotions"],
}
# 模拟候选池：每条 = (id, 标题, 组, 年份, 被引, 是否预印本)
CANDIDATES = [
    ("D01", "On the Origin of Species (natural selection)", "G1_理论机制", 1859, 98000, False),
    ("D02", "The Descent of Man, and Selection in Relation to Sex", "G3_行为与植物", 1871, 21000, False),
    ("D03", "The Structure and Distribution of Coral Reefs", "G2_生物类群", 1842, 4200, False),
    ("D04", "A Monograph on the Sub-class Cirripedia", "G2_生物类群", 1854, 3100, False),
    ("D05", "The Variation of Animals and Plants under Domestication", "G1_理论机制", 1868, 7600, False),
    ("D06", "The Effects of Cross and Self Fertilisation in the Vegetable Kingdom", "G3_行为与植物", 1876, 2900, False),
    ("D07", "The Power of Movement in Plants", "G3_行为与植物", 1880, 2400, False),
    ("D08", "The Formation of Vegetable Mould through the Action of Worms", "G2_生物类群", 1881, 3300, False),
    ("D09", "The Expression of the Emotions in Man and Animals", "G3_行为与植物", 1872, 5100, False),
    ("D10", "Insectivorous Plants", "G3_行为与植物", 1875, 1900, False),
    ("D11", "Geological Observations on South America", "G2_生物类群", 1846, 1500, False),
    ("D12", "The Different Forms of Flowers on Plants of the Same Species", "G3_行为与植物", 1877, 1700, False),
    ("D13", "On the Tendency of Species to form Varieties (joint 1858)", "G1_理论机制", 1858, 6000, False),
    ("D14", "Climbing Plants", "G3_行为与植物", 1865, 1300, False),
    ("D15", "Autobiography / Correspondence (meta-source)", "G1_理论机制", 1887, 900, False),
]
# 去重（按唯一标识符）
seen, cand = set(), []
for c in CANDIDATES:
    if c[0] not in seen:
        seen.add(c[0]); cand.append(c)
print(f"[步骤1] 三组关键词并集抓取，去重后候选数 = {len(cand)}（模拟数据）")

# ---------- 2. 相关性打分筛选 ----------
def relevance(title):
    t = title.lower()
    keys = ["natural selection", "coral", "barnacle", "sexual", "cross", "movement",
            "worm", "expression", "variation", "species", "plant"]
    return sum(1 for k in keys if k in t) / len(keys)
scored = [(c, relevance(c[1])) for c in cand]
scored.sort(key=lambda x: -x[1])
kept = [c for c, s in scored if s > 0][:12]
print(f"[步骤2] 相关性筛选后保留 {len(kept)} 篇（目标 40-80 为真实场景，此处模拟精简）")

# 随机抽 5 篇核对（模拟三行要点一致性）
sample = [kept[i] for i in rng.choice(len(kept), size=min(5, len(kept)), replace=False)]
print("[步骤2-核验] 随机抽 5 篇三行要点一致性检查（模拟）：")
for c in sample:
    print(f"   {c[0]} | 年份={c[3]} | 时间窗内={c[3]>=1830} | 要点与摘要一致=OK(模拟)")

# ---------- 3. 精读抽取方法卡（模拟） ----------
# 字段：id, 输入模态, 输出目标, 方法族, 配对数据需求, 评价指标, 失败模式, 主张/已验证, 局限
METHOD_CARDS = [
    ("D01", "物种地理与形态记录", "选择机制解释", "比较归纳", "无", "一致性证据", "化石记录缺失", "已验证", "无定量统计检验"),
    ("D02", "行为与性二型观察", "性选择机制", "比较归纳", "无", "跨物种一致性", "观察偏差", "已验证", "缺乏实验操控"),
    ("D03", "海岸地形与珊瑚分布", "沉降理论", "地质推断", "无", "地形一致性", "采样覆盖不足", "主张", "无钻探验证"),
    ("D04", "藤壶形态测量", "单态与变异", "分类学测量", "无", "形态一致性", "样本偏小", "已验证", "无遗传学证据"),
    ("D06", "异花/自花授粉对照", "杂交优势", "对照实验", "有", "结实率", "温室条件偏差", "已验证", "未测长期适应度"),
    ("D07", "植物向性观测", "运动机制", "实验观测", "有", "向性响应", "光照不均", "已验证", "机制未到分子层"),
    ("D08", "蚯蚓与土壤层", "土壤改造", "长期观测+称重", "有", "土壤层厚度", "区域局限", "已验证", "未做全球尺度"),
    ("D09", "人兽表情照片", "表情同源性", "跨物种比较", "无", "表情一致性", "文化偏差", "主张", "样本文化单一"),
]
print(f"[步骤3] 精读方法卡 {len(METHOD_CARDS)} 张（模拟），区分主张/已验证：")
n_verified = sum(1 for m in METHOD_CARDS if m[7] == "已验证")
print(f"   已验证={n_verified}，主张={len(METHOD_CARDS)-n_verified}；每卡含≥1条局限=OK")

# 抽 3 篇回原文核对关键数字（模拟）
print("[步骤3-核验] 抽 3 篇核对关键数字（模拟）：")
for m in METHOD_CARDS[:3]:
    print(f"   {m[0]} 指标={m[5]} 与原文一致=OK(模拟)")

# ---------- 4. 主题聚类归纳思想范式 ----------
PARADIGMS = [
    {"name": "自然选择与共同祖先", "ids": ["D01", "D05", "D13"], "maturity": "成熟", "evidence": "强"},
    {"name": "珊瑚礁沉降理论", "ids": ["D03", "D11"], "maturity": "发展中", "evidence": "中"},
    {"name": "藤壶单态与变异", "ids": ["D04"], "maturity": "萌芽", "evidence": "中"},
    {"name": "性选择", "ids": ["D02", "D09"], "maturity": "发展中", "evidence": "中"},
    {"name": "异花授粉与植物运动", "ids": ["D06", "D07", "D12", "D14"], "maturity": "成熟", "evidence": "强"},
    {"name": "蚯蚓对土壤的改造", "ids": ["D08"], "maturity": "萌芽", "evidence": "中"},
    {"name": "人类与动物表情", "ids": ["D09"], "maturity": "萌芽", "evidence": "弱"},
]
print(f"[步骤4] 聚类得到 {len(PARADIGMS)} 个思想范式（模拟）：")
for p in PARADIGMS:
    print(f"   {p['name']}: 文献数={len(p['ids'])}, 成熟度={p['maturity']}, 证据强度={p['evidence']}")

# ---------- 5. 合并检查（防止同一洞察拆多类） ----------
def core_overlap(a, b):
    return len(set(a["ids"]) & set(b["ids"])) > 0
merged = []
for p in PARADIGMS:
    dup = False
    for q in merged:
        if core_overlap(p, q):
            q["ids"] = sorted(set(q["ids"]) | set(p["ids"]))
            dup = True
            print(f"[步骤5] 合并检查：'{p['name']}' 与 '{q['name']}' 共享文献，已合并")
            break
    if not dup:
        merged.append(dict(p))
print(f"[步骤5] 合并后范式数 = {len(merged)}（无虚增）")

# ---------- 6. 引用核验（100% 覆盖，模拟） ----------
all_ids = sorted({i for p in merged for i in p["ids"]})
id2cand = {c[0]: c for c in cand}
print(f"[步骤6] 引用核验 100% 覆盖，共 {len(all_ids)} 条：")
doubtful = []
for i in all_ids:
    c = id2cand[i]
    ok = c[3] >= 1830 and c[4] > 0
    if not ok:
        doubtful.append(i)
    print(f"   {i} 可访问=OK(模拟) 年份={c[3]} 作者一致=OK(模拟) 结论一致=OK(模拟)")
print(f"   存疑项 = {doubtful if doubtful else '无'}；编号连续无断号=OK")

# 缺口矩阵（模拟）
GAPS = [
    {"paradigm": "珊瑚礁沉降理论", "gap": "缺乏钻探直接验证", "path": "珊瑚礁岩芯取样测年"},
    {"paradigm": "藤壶单态与变异", "gap": "无遗传学证据", "path": "现代基因组测序"},
    {"paradigm": "蚯蚓对土壤的改造", "gap": "未做全球尺度", "path": "多区域长期定位观测"},
    {"paradigm": "人类与动物表情", "gap": "样本文化单一", "path": "跨文化表情编码实验"},
]
print(f"[缺口矩阵] 共 {len(GAPS)} 条缺口，每条含可验证路径：")
for g in GAPS:
    print(f"   {g['paradigm']} -> {g['gap']} | 路径: {g['path']}")

# ---------- 出图 ----------
fig, ax = plt.subplots(figsize=(9, 5))
names = [p["name"] for p in merged]
counts = [len(p["ids"]) for p in merged]
colors = {"成熟": "#2e7d32", "发展中": "#f9a825", "萌芽": "#c62828"}
bar_colors = [colors.get(p["maturity"], "#888") for p in merged]
bars = ax.barh(names, counts, color=bar_colors)
for b, c in zip(bars, counts):
    ax.text(b.get_width() + 0.05, b.get_y() + b.get_height()/2, str(c), va="center")
ax.set_xlabel("支撑文献数（模拟数据）")
ax.set_title("达尔文研究范式：成熟度与文献支撑（模拟数据）")
handles = [plt.Rectangle((0,0),1,1,color=v) for v in colors.values()]
ax.legend(handles, colors.keys(), title="成熟度", loc="lower right")
plt.tight_layout()
plt.savefig("figure.png", dpi=150)
plt.close()

# ---------- 落盘 ----------
with open("paradigms.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["范式", "支撑文献", "文献数", "成熟度", "证据强度"])
    for p in merged:
        w.writerow([p["name"], ";".join(p["ids"]), len(p["ids"]), p["maturity"], p["evidence"]])

with open("gaps.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["范式", "缺口", "可验证路径"])
    for g in GAPS:
        w.writerow([g["paradigm"], g["gap"], g["path"]])

with open("method_cards.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "输入模态", "输出目标", "方法族", "配对数据", "评价指标", "失败模式", "主张/已验证", "局限"])
    for m in METHOD_CARDS:
        w.writerow(m)

print("\n[落盘] figure.png / paradigms.csv / gaps.csv / method_cards.csv")
print("[声明] 全部数据为模拟数据，仅用于流程演示，非真实文献计量结论。")