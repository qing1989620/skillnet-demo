# -*- coding: utf-8 -*-
"""
mathorcup 大数据竞赛 —— 候选权威文献精读与字段抽取（paper-deep-read 方法卡）
注意：本脚本中所有"文献条目"均为【模拟数据】，用于演示抽取流程与产物结构，
      不代表任何真实赛事规定。真实结论需以官方公告原文为准。
"""
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 1. 候选集（模拟数据）：权威度排序，取前 12 条精读
#    source_type: official(官方明文) / experience(参赛者经验)
# ============================================================
CANDIDATES = [
    {"id": "D01", "title": "MathorCup 大数据竞赛章程（模拟）", "authority": 0.98, "source_type": "official",
     "host": "中国优选法统筹法与经济数学研究会", "edition": "第1届", "year": 2020,
     "target": "全国高校在校生（本科/研究生）", "task_type": "大数据分析",
     "submit": "论文PDF+代码附件", "review": "双盲评审", "award": "一等奖5%/二等奖15%/三等奖30%"},
    {"id": "D02", "title": "第2届赛题说明（模拟）", "authority": 0.95, "source_type": "official",
     "host": "中国优选法统筹法与经济数学研究会", "edition": "第2届", "year": 2021,
     "target": "全国高校在校生", "task_type": "大数据建模",
     "submit": "论文PDF+代码附件", "review": "双盲评审", "award": "一等奖5%/二等奖15%/三等奖30%"},
    {"id": "D03", "title": "第3届获奖公示（模拟）", "authority": 0.93, "source_type": "official",
     "host": "中国优选法统筹法与经济数学研究会", "edition": "第3届", "year": 2022,
     "target": "全国高校在校生", "task_type": "大数据算法",
     "submit": "论文PDF+代码附件", "review": "双盲评审", "award": "一等奖5%/二等奖15%/三等奖30%"},
    {"id": "D04", "title": "第4届赛题说明（模拟）", "authority": 0.92, "source_type": "official",
     "host": "中国优选法统筹法与经济数学研究会", "edition": "第4届", "year": 2023,
     "target": "全国高校在校生", "task_type": "大数据分析",
     "submit": "论文PDF+代码附件", "review": "双盲评审", "award": "一等奖5%/二等奖15%/三等奖30%"},
    {"id": "D05", "title": "第5届官方公告（模拟）", "authority": 0.90, "source_type": "official",
     "host": "中国优选法统筹法与经济数学研究会", "edition": "第5届", "year": 2024,
     "target": "全国高校在校生", "task_type": "大数据建模",
     "submit": "论文PDF+代码附件", "review": "双盲评审", "award": "一等奖5%/二等奖15%/三等奖30%"},
    {"id": "D06", "title": "第5届获奖公示（模拟）", "authority": 0.88, "source_type": "official",
     "host": "中国优选法统筹法与经济数学研究会", "edition": "第5届", "year": 2024,
     "target": "全国高校在校生", "task_type": "大数据算法",
     "submit": "论文PDF+代码附件", "review": "双盲评审", "award": "一等奖5%/二等奖15%/三等奖30%"},
    {"id": "D07", "title": "第6届赛题说明（模拟）", "authority": 0.86, "source_type": "official",
     "host": "中国优选法统筹法与经济数学研究会", "edition": "第6届", "year": 2025,
     "target": "全国高校在校生", "task_type": "大数据分析",
     "submit": "论文PDF+代码附件", "review": "双盲评审", "award": "一等奖5%/二等奖15%/三等奖30%"},
    {"id": "D08", "title": "参赛者经验帖A（模拟）", "authority": 0.55, "source_type": "experience",
     "host": "个人博客", "edition": "第4届", "year": 2023,
     "target": "不限", "task_type": "大数据分析",
     "submit": "论文PDF", "review": "感觉偏重创新性", "award": "获奖率约50%"},
    {"id": "D09", "title": "参赛者经验帖B（模拟）", "authority": 0.50, "source_type": "experience",
     "host": "知乎", "edition": "第5届", "year": 2024,
     "target": "不限", "task_type": "大数据建模",
     "submit": "论文PDF+代码", "review": "评委看重可复现", "award": "一等奖很难"},
    {"id": "D10", "title": "参赛者经验帖C（模拟）", "authority": 0.45, "source_type": "experience",
     "host": "CSDN", "edition": "第3届", "year": 2022,
     "target": "不限", "task_type": "大数据算法",
     "submit": "论文PDF", "review": "双盲", "award": "三等奖较易"},
    {"id": "D11", "title": "参赛者经验帖D（模拟）", "authority": 0.40, "source_type": "experience",
     "host": "微信公众号", "edition": "第2届", "year": 2021,
     "target": "不限", "task_type": "大数据分析",
     "submit": "论文PDF", "review": "未知", "award": "未知"},
    {"id": "D12", "title": "参赛者经验帖E（模拟）", "authority": 0.35, "source_type": "experience",
     "host": "贴吧", "edition": "第1届", "year": 2020,
     "target": "不限", "task_type": "大数据建模",
     "submit": "论文PDF", "review": "未知", "award": "未知"},
]

# ============================================================
# 2. 精读：按权威度排序取前 12 条，区分官方明文 vs 经验描述
# ============================================================
cands = sorted(CANDIDATES, key=lambda x: -x["authority"])[:12]
official = [c for c in cands if c["source_type"] == "official"]
experience = [c for c in cands if c["source_type"] == "experience"]

print("=" * 60)
print("【精读候选集】共 %d 条（模拟数据）" % len(cands))
print("  官方明文条目: %d 条" % len(official))
print("  参赛者经验条目: %d 条" % len(experience))
print("  权威度区间: %.2f ~ %.2f" % (cands[-1]["authority"], cands[0]["authority"]))

# 字段一致性检查（官方明文内部）
def field_consistency(records, field):
    vals = [r[field] for r in records]
    uniq = sorted(set(vals))
    return uniq, len(uniq)

print("\n【官方明文内部字段一致性检查】")
for f in ["host", "target", "submit", "review", "award"]:
    uniq, n = field_consistency(official, f)
    flag = "一致" if n == 1 else "存在 %d 种表述" % n
    print("  %-8s -> %s | %s" % (f, flag, uniq))

# 届次时间线
years = sorted(set(c["year"] for c in official))
print("\n【届次时间线（官方明文）】年份: %s" % years)
print("  跨度: %d 年, 届次数: %d" % (max(years) - min(years) + 1, len(years)))

# 赛题类型分布
from collections import Counter
tt = Counter(c["task_type"] for c in official)
print("\n【赛题类型分布（官方明文）】")
for k, v in tt.items():
    print("  %s: %d 条 (%.1f%%)" % (k, v, 100.0 * v / len(official)))

# ============================================================
# 3. 陷阱规避检查
# ============================================================
print("\n【已知陷阱规避检查】")
# 陷阱1：把宣称当已验证结论
claim_only = [c["id"] for c in experience if c["review"] in ("未知", "感觉偏重创新性", "评委看重可复现")]
print("  [陷阱1] 经验帖中'评审'字段无官方依据的条目: %s" % claim_only)
print("          -> 结论：这些表述仅作参考，不纳入官方字段。")

# 陷阱2：忽略负结果/未覆盖项
covered = set()
for c in official:
    covered.add(c["task_type"])
all_types = {"大数据分析", "大数据建模", "大数据算法"}
uncovered = all_types - covered
print("  [陷阱2] 官方明文未覆盖的赛题类型: %s" % (sorted(uncovered) if uncovered else "无"))

# 陷阱3：混淆相关性与因果性
print("  [陷阱3] 权威度与'官方明文'为设计上的相关，非因果；")
print("          本脚本按 source_type 显式分层，避免将经验帖结论外推为官方规定。")

# ============================================================
# 4. 方法卡（可复现要素）
# ============================================================
print("\n【方法卡】")
print("  适用条件: 候选集含官方公告/赛题说明/获奖公示，且可标注权威度与来源类型")
print("  输入: 候选条目列表(含 authority, source_type, 各字段)")
print("  步骤: 排序取TopN -> 按source_type分层 -> 字段一致性检查 -> 时间线/分布统计")
print("  代价: O(N log N) 排序 + O(N) 遍历")
print("  失败模式: 权威度标注主观；经验帖字段缺失导致统计偏差")
print("  复现要素: 候选集、权威度阈值、TopN、字段名列表")

# ============================================================
# 5. 局限清单
# ============================================================
print("\n【局限清单】")
print("  1. 本脚本全部条目为模拟数据，未接入真实官方公告。")
print("  2. 权威度评分为人工设定，未做多标注者一致性检验。")
print("  3. 未覆盖：报名费用、赛程具体日期、评审细则权重等字段。")
print("  4. 未做跨届字段变更的因果分析，仅做描述性统计。")

# ============================================================
# 6. 出图：届次时间线 + 赛题类型分布
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

ax1 = axes[0]
ax1.plot(years, [1] * len(years), 'o-', color='#2c7fb8', markersize=10)
for y in years:
    ax1.annotate(str(y), (y, 1), textcoords="offset points", xytext=(0, 12), ha='center')
ax1.set_ylim(0.5, 1.5)
ax1.set_yticks([])
ax1.set_title("官方明文届次时间线（模拟数据）")
ax1.set_xlabel("年份")

ax2 = axes[1]
labels = list(tt.keys())
vals = [tt[k] for k in labels]
ax2.bar(labels, vals, color=['#2c7fb8', '#7fcdbb', '#edf8b1'])
ax2.set_title("官方明文赛题类型分布（模拟数据）")
ax2.set_ylabel("条目数")
for i, v in enumerate(vals):
    ax2.text(i, v + 0.05, str(v), ha='center')

plt.tight_layout()
plt.savefig("figure.png", dpi=150)
plt.close()

# ============================================================
# 7. 落盘 CSV
# ============================================================
with open("mathorcup_deepread.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "title", "authority", "source_type", "host", "edition",
                "year", "target", "task_type", "submit", "review", "award"])
    for c in cands:
        w.writerow([c["id"], c["title"], c["authority"], c["source_type"], c["host"],
                    c["edition"], c["year"], c["target"], c["task_type"],
                    c["submit"], c["review"], c["award"]])

print("\n已保存: figure.png, mathorcup_deepread.csv")
print("（注：以上所有条目均为模拟数据，非真实赛事结论）")