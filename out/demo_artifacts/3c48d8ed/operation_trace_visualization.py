"""
关键操作可视化轨迹：生成数组插入、链表删除、BST查找、堆调整的步骤图。
使用 matplotlib 绘制，输出 PNG 文件，便于确认逻辑与实现一致。
本脚本不依赖外部数据，直接运行即可生成示意图。
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches

plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def draw_array_trace():
    """动态数组尾部插入 30 的轨迹：扩容前 -> 扩容后 -> 写入。"""
    fig, axes = plt.subplots(1, 3, figsize=(12, 3))
    steps = [
        {"title": "步骤1: 容量满 [10,20,None,None]", "data": [10, 20, None, None], "highlight": None},
        {"title": "步骤2: 扩容为8 [10,20,None,None,None,None,None,None]", "data": [10, 20, None, None, None, None, None, None], "highlight": None},
        {"title": "步骤3: 写入30 [10,20,30,None,...]", "data": [10, 20, 30, None, None, None, None, None], "highlight": 2},
    ]
    for ax, step in zip(axes, steps):
        ax.set_title(step["title"], fontsize=9)
        ax.set_xlim(-0.5, len(step["data"]) - 0.5)
        ax.set_ylim(-0.5, 1.5)
        ax.axis("off")
        for i, val in enumerate(step["data"]):
            color = "#ffd966" if step["highlight"] == i else "#d9e1f2"
            rect = patches.Rectangle((i - 0.4, 0.2), 0.8, 0.8, linewidth=1, edgecolor="black", facecolor=color)
            ax.add_patch(rect)
            ax.text(i, 0.6, str(val) if val is not None else "_", ha="center", va="center", fontsize=10)
    plt.tight_layout()
    plt.savefig("trace_array_insert.png", dpi=150)
    plt.close()


def draw_linked_list_trace():
    """单向链表删除值 20 的轨迹：定位前驱 -> 修改指针。"""
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    nodes = [("head", 1), ("10", 3), ("20", 5), ("30", 7)]
    for label, x in nodes:
        circle = patches.Circle((x, 1.5), 0.5, edgecolor="black", facecolor="#d9e1f2")
        ax.add_patch(circle)
        ax.text(x, 1.5, label, ha="center", va="center", fontsize=10)
    for i in range(len(nodes) - 1):
        ax.annotate("", xy=(nodes[i + 1][1] - 0.5, 1.5), xytext=(nodes[i][1] + 0.5, 1.5),
                    arrowprops=dict(arrowstyle="->", color="black"))
    ax.annotate("删除20：前驱10指向30", xy=(7, 1.5), xytext=(5, 2.5),
                arrowprops=dict(arrowstyle="->", color="red"), color="red", fontsize=10)
    ax.set_title("单向链表删除操作轨迹（示意）", fontsize=11)
    plt.tight_layout()
    plt.savefig("trace_linked_list_delete.png", dpi=150)
    plt.close()


def draw_bst_search_trace():
    """BST 查找 4 的路径：5 -> 3 -> 4。"""
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    positions = {5: (5, 8), 3: (3, 5), 8: (7, 5), 1: (1, 2), 4: (4, 2), 7: (6, 2), 9: (8, 2)}
    edges = [(5, 3), (5, 8), (3, 1), (3, 4), (8, 7), (8, 9)]
    for a, b in edges:
        ax.plot([positions[a][0], positions[b][0]], [positions[a][1], positions[b][1]], "k-")
    path = [5, 3, 4]
    for key, (x, y) in positions.items():
        color = "#ffd966" if key in path else "#d9e1f2"
        circle = patches.Circle((x, y), 0.5, edgecolor="black", facecolor=color)
        ax.add_patch(circle)
        ax.text(x, y, str(key), ha="center", va="center", fontsize=10)
    ax.set_title("BST 查找 4 的路径：5 -> 3 -> 4（示意）", fontsize=11)
    plt.tight_layout()
    plt.savefig("trace_bst_search.png", dpi=150)
    plt.close()


def draw_heap_trace():
    """最小堆插入 1 的上浮轨迹：1 与父节点交换至根。"""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    steps = [
        {"title": "插入1前: [2,5,8]", "data": [2, 5, 8], "highlight": None},
        {"title": "插入1后上浮: [1,5,2,8]", "data": [1, 5, 2, 8], "highlight": 0},
    ]
    for ax, step in zip(axes, steps):
        ax.set_title(step["title"], fontsize=10)
        ax.set_xlim(-0.5, len(step["data"]) - 0.5)
        ax.set_ylim(-0.5, 1.5)
        ax.axis("off")
        for i, val in enumerate(step["data"]):
            color = "#ffd966" if step["highlight"] == i else "#d9e1f2"
            rect = patches.Rectangle((i - 0.4, 0.2), 0.8, 0.8, linewidth=1, edgecolor="black", facecolor=color)
            ax.add_patch(rect)
            ax.text(i, 0.6, str(val), ha="center", va="center", fontsize=10)
    plt.tight_layout()
    plt.savefig("trace_heap_insert.png", dpi=150)
    plt.close()


if __name__ == "__main__":
    draw_array_trace()
    draw_linked_list_trace()
    draw_bst_search_trace()
    draw_heap_trace()
    print("已生成轨迹图：trace_array_insert.png, trace_linked_list_delete.png, trace_bst_search.png, trace_heap_insert.png")
