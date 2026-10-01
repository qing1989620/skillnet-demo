"""
时间-规模实测曲线与拟合：对动态数组追加、链表查找、哈希表插入、BST插入、堆插入进行计时。
输出 CSV 文件 benchmark_results.csv，并绘制拟合曲线图。
注意：运行时间受机器影响，结果仅为示意，需真实数据验证。
"""

import time
import random
import csv
import matplotlib.pyplot as plt
from core_data_structures import DynamicArray, SinglyLinkedList, HashTable, BinarySearchTree, MinHeap

plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def time_it(func, *args):
    start = time.perf_counter()
    func(*args)
    end = time.perf_counter()
    return end - start


def benchmark():
    sizes = [100, 500, 1000, 2000, 5000]
    results = []
    for n in sizes:
        data = [random.randint(0, 10 * n) for _ in range(n)]

        arr = DynamicArray()
        t_arr = time_it(lambda: [arr.append(x) for x in data])

        ll = SinglyLinkedList()
        for x in data:
            ll.push_back(x)
        t_ll = time_it(lambda: [ll.find(x) for x in data[:100]])

        ht = HashTable()
        t_ht = time_it(lambda: [ht.put(i, i) for i in range(n)])

        bst = BinarySearchTree()
        t_bst = time_it(lambda: [bst.insert(x) for x in data])

        heap = MinHeap()
        t_heap = time_it(lambda: [heap.push(x) for x in data])

        results.append((n, t_arr, t_ll, t_ht, t_bst, t_heap))
        print(f"n={n}: arr={t_arr:.6f}, ll_find100={t_ll:.6f}, ht={t_ht:.6f}, bst={t_bst:.6f}, heap={t_heap:.6f}")

    with open("benchmark_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["n", "dynamic_array_append_s", "linked_list_find100_s", "hash_table_put_s", "bst_insert_s", "min_heap_push_s"])
        writer.writerows(results)

    # 绘制曲线
    ns = [r[0] for r in results]
    plt.figure(figsize=(8, 5))
    plt.plot(ns, [r[1] for r in results], marker="o", label="DynamicArray append")
    plt.plot(ns, [r[2] for r in results], marker="s", label="LinkedList find(100)")
    plt.plot(ns, [r[3] for r in results], marker="^", label="HashTable put")
    plt.plot(ns, [r[4] for r in results], marker="d", label="BST insert")
    plt.plot(ns, [r[5] for r in results], marker="x", label="MinHeap push")
    plt.xlabel("规模 n")
    plt.ylabel("耗时 (秒)")
    plt.title("时间-规模实测曲线（示意值，需真实数据验证）")
