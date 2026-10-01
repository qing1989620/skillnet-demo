"""
边界与随机测试脚本：覆盖空结构、单元素、重复元素、极端规模、非法输入。
运行后输出通过/失败报告，并保存为 test_report.txt。
本脚本依赖 core_data_structures.py 中的实现。
"""

import random
import sys
from core_data_structures import (
    DynamicArray, SinglyLinkedList, Stack, Queue, HashTable, BinarySearchTree, MinHeap
)


def run_test(name, func):
    try:
        func()
        return name, "PASS", ""
    except Exception as e:
        return name, "FAIL", str(e)


def test_dynamic_array():
    arr = DynamicArray()
    assert len(arr) == 0
    try:
        arr[0]
        raise AssertionError("空数组索引应报错")
    except IndexError:
        pass
    arr.append(1)
    assert arr[0] == 1
    arr.append(2)
    arr.append(3)
    assert arr.find(2) == 1
    assert arr.remove_at(1) == 2
    assert arr.traverse() == [1, 3]
    for i in range(1000):
        arr.append(i)
    assert len(arr) == 1002


def test_linked_list():
    ll = SinglyLinkedList()
    assert ll.traverse() == []
    assert ll.remove(1) is False
    ll.push_back(1)
    assert ll.traverse() == [1]
    ll.push_front(0)
    ll.push_back(2)
    assert ll.traverse() == [0, 1, 2]
    assert ll.find(1) == 1
    assert ll.remove(1) is True
    assert ll.traverse() == [0, 2]
    for i in range(1000):
        ll.push_back(i)
    assert len(ll) == 1002


def test_stack():
    st = Stack()
    assert st.is_empty()
    try:
        st.pop()
        raise AssertionError("空栈pop应报错")
    except IndexError:
        pass
    st.push(1)
    st.push(2)
    assert st.pop() == 2
    assert st.peek() == 1
    for i in range(1000):
        st.push(i)
    assert st.pop() == 999


def test_queue():
    q = Queue()
    assert q.is_empty()
    try:
        q.dequeue()
        raise AssertionError("空队列dequeue应报错")
    except IndexError:
        pass
    q.enqueue(1)
    q.enqueue(2)
    assert q.dequeue() == 1
    assert q.peek() == 2
    for i in range(1000):
        q.enqueue(i)
    assert q.dequeue() == 2


def test_hash_table():
    ht = HashTable()
    try:
        ht.get("missing")
        raise AssertionError("缺失键应报错")
    except KeyError:
        pass
    ht.put("a", 1)
    ht.put("a", 2)
    assert ht.get("a") == 2
    assert ht.delete("a") is True
    assert ht.delete("a") is False
    for i in range(1000):
        ht.put(i, i * 2)
    assert ht.get(500) == 1000


def test_bst():
    bst = BinarySearchTree()
    assert bst.inorder() == []
    assert bst.search(1) is False
    for k in [5, 3, 8, 1, 4, 7, 9]:
        bst.insert(k)
    assert bst.inorder() == [1, 3, 4, 5, 7, 8, 9]
    assert bst.search(4) is True
    bst.delete(5)
    assert bst.inorder() == [1, 3, 4, 7, 8, 9]
    for i in range(1000):
        bst.insert(i)
    assert bst.search(500) is True


def test_min_heap():
    heap = MinHeap()
    try:
        heap.pop()
        raise AssertionError("空堆pop应报错")
    except IndexError:
        pass
    for v in [5, 2, 8, 1]:
        heap.push(v)
    assert heap.pop() == 1
    assert heap.peek() == 2
    for i in range(1000):
        heap.push(random.randint(0, 10000))
    assert heap.peek() <= 10000


def main():
    tests = [
        ("DynamicArray 边界与随机", test_dynamic_array),
        ("SinglyLinkedList 边界与随机", test_linked_list),
        ("Stack 边界与随机", test_stack),
        ("Queue 边界与随机", test_queue),
        ("HashTable 边界与随机", test_hash_table),
        ("BinarySearchTree 边界与随机", test_bst),
        ("MinHeap 边界与随机", test_min_heap),
    ]
    results = [run_test(name, func) for name, func in tests]
    with open("test_report.txt", "w", encoding="utf-8") as f:
        for name, status, msg in results:
            line = f"{name}: {status} {msg}"
            print(line)
            f.write(line + "\n")
    if any(status == "FAIL" for _, status, _ in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
