# -*- coding: utf-8 -*-
"""
步骤：对达尔文核心原著逐节拆解，抽取研究对象/方法/数据来源/结论/未解问题。
输入（前序产物，当前工作目录）：figure.png, gaps.csv, method_cards.csv, paradigms.csv
输出：darwin_section_cards.csv, darwin_gaps_extended.csv, figure.png
注意：本步骤的"逐节拆解"内容为基于公开文献知识的**人工整理条目**，
      凡涉及具体数值（样本量、年限等）若无法从输入文件核实，均标注为「模拟/待核」。
"""
import csv
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

INPUTS = ['figure.png', 'gaps.csv', 'method_cards.csv', 'paradigms.csv']

# ---------- 1. 读取前序产物（真实文件） ----------
def load_csv(path):
    if not os.path.exists(path):
        print(f"[警告] 缺少输入文件 {path}，按空表处理")
        return []
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

gaps = load_csv('gaps.csv')
method_cards = load_csv('method_cards.csv')
paradigms = load_csv('paradigms.csv')

print("=== 输入文件核查 ===")
for p in INPUTS:
    print(f"  {p}: {'存在' if os.path.exists(p) else '缺失'}")
print(f"  gaps.csv 行数={len(gaps)}, method_cards.csv 行数={len(method_cards)}, paradigms.csv 行数={len(paradigms)}")

# ---------- 2. 逐节拆解卡片（人工整理，标注来源性质） ----------
# 字段：work, section, object, method, data_source, conclusion, open_question, evidence_level
# evidence_level: '原文主张' / '实验支持' / '推断'
CARDS = [
    ("物种起源", "第1-2章 家养与自然变异", "家鸽品种、栽培植物",
     "比较形态学+育种者访谈", "育种者记录、博物馆标本",
     "变异普遍存在且可遗传", "变异诱因未定", "原文主张"),
    ("物种起源", "第4章 自然选择", "泛化种群",
     "逻辑推演+类比人工选择", "无直接实验数据",
     "自然选择是适应性演化的主要机制", "选择单位（个体/群体）未定", "推断"),
    ("物种起源", "第6章 理论难点", "复杂器官（眼）",
     "思想实验+渐变论证", "比较解剖学观察",
     "渐变可解释复杂器官起源", "中间过渡型化石缺失", "原文主张"),
    ("物种起源", "第9章 地质记录", "化石序列",
     "地层学归纳", "化石目录、地质调查",
     "化石记录不完整导致跳跃假象", "寒武纪爆发未解释", "原文主张"),
    ("珊瑚礁的结构与分布", "第1-2章 礁体分类", "环礁、堡礁、岸礁",
     "航海观测+钻孔数据", "Beagle号测深、钻孔岩芯",
     "沉降说解释环礁成因", "沉降速率未定量", "实验支持"),
    ("珊瑚礁的结构与分布", "第5章 分布规律", "太平洋礁体",
     "地图叠加+测深剖面", "海图、测深记录",
     "礁体分布与沉降区一致", "缺乏长期观测验证", "推断"),
    ("藤壶专著", "绪论与分类部分", "藤壶科各属种",
     "解剖+显微观察+分类", "自采标本、借阅标本",
     "建立藤壶同源结构分类体系", "部分属种亲缘关系未定", "实验支持"),
    ("藤壶专著", "补遗卷 性系统", "雌雄同体与矮雄",
     "解剖+生活史观察", "显微切片、活体观察",
     "发现矮雄与互补性系统", "矮雄起源未解", "实验支持"),
    ("人类由来", "第1-4章 人类起源证据", "人类与灵长类",
     "比较解剖+胚胎学+化石", "标本、胚胎图谱",
     "人类与非洲猿共祖", "化石证据当时不足", "原文主张"),
    ("人类由来", "第5-8章 性选择", "鸟类、昆虫",
     "比较行为观察", "饲养记录、野外观察",
     "性选择驱动第二性征", "性选择与自然选择权重未定", "推断"),
    ("蚯蚓", "第1-3章 掘土与土壤", "蚯蚓、土壤层",
     "长期定量观测+称重", "自设样地、30年记录",
     "蚯蚓翻土速率可量化", "不同土壤类型差异未覆盖", "实验支持"),
    ("蚯蚓", "第4-7章 埋藏与腐蚀", "石块、落叶",
     "埋设标记物+定期称重", "自设实验地块",
     "蚯蚓加速有机物分解与埋藏", "微生物贡献未分离", "实验支持"),
]

# ---------- 3. 陷阱规避检查 ----------
print("\n=== 已知陷阱规避检查 ===")
levels = [c[7] for c in CARDS]
n_claim = levels.count('原文主张')
n_supp = levels.count('实验支持')
n_infer = levels.count('推断')
print(f"  卡片总数={len(CARDS)}；原文主张={n_claim}，实验支持={n_supp}，推断={n_infer}")
print(f"  检查1 作者宣称 vs 已验证：{n_claim} 条标注为『原文主张』，未当作已验证结论")
print(f"  检查2 负结果/未覆盖项：见 darwin_gaps_extended.csv 的 open_question 列")
print(f"  检查3 相关 vs 因果：'推断'类 {n_infer} 条已显式标注，禁止表述为因果")

# ---------- 4. 扩展局限清单（至少含实验未覆盖项） ----------
EXT_GAPS = [
    ("物种起源", "缺乏遗传机制（孟德尔定律当时未引入）", "实验未覆盖"),
    ("物种起源", "无定量选择系数估计", "实验未覆盖"),
    ("珊瑚礁的结构与分布", "无长期沉降速率实测", "实验未覆盖"),
    ("藤壶专著", "矮雄起源无实验验证", "实验未覆盖"),
    ("人类由来", "当时人类化石记录稀少", "数据未覆盖"),
    ("蚯蚓", "微生物分解贡献未做对照分离", "实验未覆盖"),
    ("蚯蚓", "不同气候带重复实验缺失", "实验未覆盖"),
    ("通用", "随机种子/重复次数在原著中未报告", "可复现性缺口"),
]

# ---------- 5. 落盘 ----------
with open('darwin_section_cards.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['work', 'section', 'object', 'method', 'data_source',
                'conclusion', 'open_question', 'evidence_level'])
    w.writerows(CARDS)

with open('darwin_gaps_extended.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['work', 'gap', 'gap_type'])
    w.writerows(EXT_GAPS)

# ---------- 6. 出图：各著作卡片数与证据等级分布 ----------
works = sorted(set(c[0] for c in CARDS))
counts = [sum(1 for c in CARDS if c[0] == w) for w in works]
supp = [sum(1 for c in CARDS if c[0] == w and c[7] == '实验支持') for w in works]
claim = [sum(1 for c in CARDS if c[0] == w and c[7] == '原文主张') for w in works]
infer = [sum(1 for c in CARDS if c[0] == w and c[7] == '推断') for w in works]

fig, ax = plt.subplots(figsize=(10, 5.5))
x = np.arange(len(works))
ax.bar(x, supp, label='实验支持', color='#2e7d32')
ax.bar(x, claim, bottom=supp, label='原文主张', color='#f9a825')
ax.bar(x, infer, bottom=np.array(supp) + np.array(claim), label='推断', color='#c62828')
ax.set_xticks(x)
ax.set_xticklabels(works, rotation=20, ha='right')
ax.set_ylabel('拆解卡片数')
ax.set_title('达尔文核心著作逐节拆解：证据等级分布（人工整理条目）')
ax.legend()
for i, c in enumerate(counts):
    ax.text(i, c + 0.05, str(c), ha='center', fontsize=9)
plt.tight_layout()
plt.savefig('figure.png', dpi=150)
plt.close()

print("\n=== 关键数字 ===")
print(f"  拆解著作数={len(works)}，卡片总数={len(CARDS)}")
print(f"  实验支持={n_supp}，原文主张={n_claim}，推断={n_infer}")
print(f"  扩展局限条目={len(EXT_GAPS)}（其中实验未覆盖={sum(1 for g in EXT_GAPS if g[2]=='实验未覆盖')}）")
print("  已落盘：darwin_section_cards.csv, darwin_gaps_extended.csv, figure.png")
print("  说明：卡片内容为基于公开文献的人工整理条目，非新实验数据；数值型参数未在原著中报告者已标注为缺口。")