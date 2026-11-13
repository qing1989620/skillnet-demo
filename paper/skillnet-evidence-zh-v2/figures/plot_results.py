"""Actual API outcomes on constructed tasks; no simulated performance values.

Style: gallery oa-tech-pone-0258309-f05 (dot intervals),
oa-tech-pone-0255450-f02 (discrete matrix), grouped-stacked-rounded-bars (spacing).
Only layout/color ideas are borrowed; all plotted values come from this study.
"""

import json
from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image, ImageDraw

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import ListedColormap

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "results"
d = json.loads((DATA / "analysis.json").read_text(encoding="utf-8"))
font_path = Path("C:/Windows/Fonts/msyh.ttc")
if font_path.exists():
    font_manager.fontManager.addfont(str(font_path))
    chinese = font_manager.FontProperties(fname=font_path).get_name()
else:
    chinese = "Noto Sans CJK SC"
    font_manager.findfont(chinese, fallback_to_default=False)
plt.rcParams.update(
    {
        "font.family": chinese,
        "font.size": 9,
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
names = {
    "no_skill": "A0 无 Skill",
    "original": "A1 原始包",
    "evidence_contract": "A2 原包＋契约",
    "unrelated": "A3 无关上下文",
    "contract_only": "A4 仅契约",
}
colors = ["#747c88", "#27408b", "#2686a3", "#b4becb", "#4b9b87"]


def save(fig, name):
    fig.savefig(HERE / (name + ".png"), dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(HERE / (name + ".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


# Primary: the zero line remains visible; color does not encode significance.
fig, ax = plt.subplots(figsize=(7.0, 2.8), layout="constrained")
for i, row in enumerate(d["paired_effects"]):
    mean = 100 * row["mean_paired_difference"]
    low, high = np.array(row["conditional_percentile_interval_95"]) * 100
    ax.errorbar(
        mean, i, xerr=[[mean - low], [high - mean]], fmt="o", color="#27408b", capsize=3, markersize=5, lw=1.4
    )
    ax.text(17.2, i, f"{mean:+.2f}", va="center", ha="right", fontsize=8.5)
ax.axvline(0, color="#8d949c", lw=0.8, zorder=0)
ax.set_yticks(
    range(5),
    [
        names[r["selected"]].split(" ", 1)[0] + " − " + names[r["base"]].split(" ", 1)[0]
        for r in d["paired_effects"]
    ],
)
ax.invert_yaxis()
ax.set_xlim(-18, 18)
ax.set_xlabel("完整产物成功率差（百分点）")
ax.set_title("构造任务的实际 API 结果；12 条件簇的条件重采样区间", loc="left", fontsize=10)
ax.text(17.2, -0.65, "点估计", ha="right", fontsize=8)
save(fig, "paired_effects")

# Alternate direction 1: grouped bars, with explicit 0-100 scale.
fig, ax = plt.subplots(figsize=(7.0, 3.4), layout="constrained")
x = np.arange(5)
width = 0.34
for offset, size, face in [(-width / 2, 8, "#27408b"), (width / 2, 48, "#87ceeb")]:
    values = [
        next(r["passed"] / r["n"] * 100 for r in d["by_row_count"] if r["arm"] == a and r["rows"] == size)
        for a in d["arms"]
    ]
    ax.bar(
        x + offset,
        values,
        width,
        label=f"{size} 行（每臂24次）",
        color=face,
        edgecolor="white",
        linewidth=0.4,
    )
    for i, value in enumerate(values):
        ax.text(x[i] + offset, value + 1.0, f"{value:.1f}", ha="center", fontsize=8)
ax.set_xticks(x, [names[a] for a in d["arms"]], rotation=10)
ax.set_ylim(0, 100)
ax.set_ylabel("完整产物成功率（%）")
ax.legend(frameon=False, loc="upper right", fontsize=8)
ax.set_title("构造 CSV 任务的实际模型输出", loc="left", fontsize=10)
save(fig, "artifact_rates")

# Alternate direction 2: exact binary outcomes. No aggregate is colored as a binary class.
rows = [json.loads(line) for line in (DATA / "trial-outcomes.jsonl").read_text(encoding="utf-8").splitlines()]
normal = [r for r in rows if r["stratum"] == "artifact"]
conditions = list(dict.fromkeys(r["condition"] for r in normal))
units = []
for condition in conditions:
    keys = sorted({(r["task_id"], r["repeat"]) for r in normal if r["condition"] == condition})
    units.extend(keys)
matrix = np.array(
    [
        [
            int(
                next(
                    r["task_success"]
                    for r in normal
                    if (r["task_id"], r["repeat"]) == key and r["arm"] == arm
                )
            )
            for arm in d["arms"]
        ]
        for key in units
    ]
)
fig, ax = plt.subplots(figsize=(6.0, 4.6), layout="constrained")
ax.imshow(
    matrix,
    aspect="auto",
    interpolation="nearest",
    cmap=ListedColormap(["#e9edf1", "#1c73b3"]),
    vmin=0,
    vmax=1,
)
ax.set_xticks(range(5), [names[a] for a in d["arms"]], rotation=12)
ax.set_yticks(
    np.arange(12) * 4 + 1.5, [f"{i + 1:02} {condition}" for i, condition in enumerate(conditions)], fontsize=8
)
for line in np.arange(4, 48, 4) - 0.5:
    ax.axhline(line, color="white", lw=1)
ax.set_title("48 个配对输入－重复单元：蓝=合格，灰=失败", loc="left", fontsize=10)
ax.set_ylabel("构造条件（每条件4个单元）")
save(fig, "artifact_matrix")

images = []
for name, _label in [
    ("paired_effects", "首选：配对效应与不确定性"),
    ("artifact_rates", "备选：规模分层柱状图"),
    ("artifact_matrix", "备选：逐次结果矩阵"),
]:
    im = Image.open(HERE / (name + ".png")).convert("RGB")
    im.thumbnail((1050, 650))
    canvas = Image.new("RGB", (1100, 710), "white")
    canvas.paste(im, ((1100 - im.width) // 2, 45))
    # English identifiers avoid relying on a separate Pillow font path.
    ImageDraw.Draw(canvas).text((20, 15), name, fill="black")
    images.append(canvas)
sheet = Image.new("RGB", (1100, 2130), "#dddddd")
for i, im in enumerate(images):
    sheet.paste(im, (0, i * 710))
sheet.save(HERE / "style-comparison.png")
(HERE / "style-provenance.json").write_text(
    json.dumps(
        {
            "primary_reference": "oa-tech-pone-0258309-f05",
            "alternate_references": ["oa-tech-pone-0255450-f02", "grouped-stacked-rounded-bars"],
            "borrowed_parts": [
                "dot-interval layout",
                "blue/gray palette",
                "white space and thin zero baseline",
            ],
            "data": "recorded API responses on constructed inputs",
            "interval": "conditional cluster bootstrap, not SEM or population CI",
            "gallery_not_modified": True,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print("Created three data-faithful chart directions (PNG and vector PDF).")
