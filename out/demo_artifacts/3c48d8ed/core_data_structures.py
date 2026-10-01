"""
核心数据结构实现：动态数组、单向链表、栈、队列、哈希表（链地址法）、二叉搜索树、最小堆。
每个结构均提供插入、删除、查找、遍历等典型操作，并附时间复杂度注释。
本代码可直接运行，用于后续可视化、测试与复杂度实测。
"""

import random
from collections import deque


class DynamicArray:
    """动态数组：支持索引访问、尾部插入/删除、按值查找。
    时间复杂度：索引 O(1)，尾部插入均摊 O(1)，按值查找 O(n)，删除 O(n)。
    空间复杂度：O(n)。
    """

    def __init__(self, capacity=4):
        self._data = [None] * capacity
        self._size = 0
        self._capacity = capacity

    def __len__(self):
        return self._size

    def __getitem__(self, index):
        if index < 0 or index >= self._size:
            raise IndexError("index out of range")
        return self._data[index]

    def append(self, value):
        if self._size == self._capacity:
            self._resize(self._capacity * 2)
        self._data[self._size] = value
        self._size += 1

    def _resize(self, new_capacity):
        new_data = [None] * new_capacity
        for i in range(self._size):
            new_data[i] = self._data[i]
        self._data = new_data
        self._capacity = new_capacity

    def find(self, value):
        for i in range(self._size):
            if self._data[i] == value:
                return i
        return -1

    def remove_at(self, index):
        if index < 0 or index >= self._size:
            raise IndexError("index out of range")
        removed = self._data[index]
        for i in range(index, self._size - 1):
            self._data[i] = self._data[i + 1]
        self._data[self._size - 1] = None
        self._size -= 1
        return removed

    def traverse(self):
        return [self._data[i] for i in range(self._size)]


class SinglyLinkedList:
    """单向链表：头插、尾插、按值删除、查找、遍历。
    时间复杂度：头插 O(1)，尾插 O(n)（无尾指针），查找 O(n)，删除 O(n)。
    空间复杂度：O(n)。
    """

    class Node:
        __slots__ = ("value", "next")

        def __init__(self, value, next=None):
            self.value = value
            self.next = next

    def __init__(self):
        self.head = None
        self._size = 0

    def __len__(self):
        return self._size

    def push_front(self, value):
        self.head = self.Node(value, self.head)
        self._size += 1

    def push_back(self, value):
        node = self.Node(value)
        if self.head is None:
            self.head = node
        else:
            cur = self.head
            while cur.next:
                cur = cur.next
            cur.next = node
        self._size += 1

    def find(self, value):
        cur = self.head
        idx = 0
        while cur:
            if cur.value == value:
                return idx
            cur = cur.next
            idx += 1
        return -1

    def remove(self, value):
        dummy = self.Node(None, self.head)
        prev, cur = dummy, self.head
        while cur:
            if cur.value == value:
                prev.next = cur.next
                self._size -= 1
                self.head = dummy.next
                return True
            prev, cur = cur, cur.next
        self.head = dummy.next
        return False

    def traverse(self):
        result = []
        cur = self.head
        while cur:
            result.append(cur.value)
            cur = cur.next
        return result


class Stack:
    """栈（基于 Python list）：push/pop/peek。
    时间复杂度：push/pop/peek 均摊 O(1)。空间复杂度：O(n)。
    """

    def __init__(self):
        self._items = []

    def push(self, value):
        self._items.append(value)

    def pop(self):
        if not self._items:
            raise IndexError("pop from empty stack")
        return self._items.pop()

    def peek(self):
        if not self._items:
            raise IndexError("peek from empty stack")
        return self._items[-1]

    def is_empty(self):
        return len(self._items) == 0


class Queue:
    """队列（基于 collections.deque）：enqueue/dequeue/peek。
    时间复杂度：enqueue/dequeue/peek 均摊 O(1)。空间复杂度：O(n)。
    """

    def __init__(self):
        self._items = deque()

    def enqueue(self, value):
        self._items.append(value)

    def dequeue(self):
        if not self._items:
            raise IndexError("dequeue from empty queue")
        return self._items.popleft()

    def peek(self):
        if not self._items:
            raise IndexError("peek from empty queue")
        return self._items[0]

    def is_empty(self):
        return len(self._items) == 0


class HashTable:
    """哈希表（链地址法）：put/get/delete。
    时间复杂度：平均 O(1)，最坏 O(n)（大量冲突）。空间复杂度：O(n)。
    """

    def __init__(self, capacity=8):
        self._capacity = capacity
        self._buckets = [[] for _ in range(capacity)]
        self._size = 0

    def _hash(self, key):
        return hash(key) % self._capacity

    def put(self, key, value):
        bucket = self._buckets[self._hash(key)]
        for i, (k, v) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)
                return
        bucket.append((key, value))
        self._size += 1

    def get(self, key):
        bucket = self._buckets[self._hash(key)]
        for k, v in bucket:
            if k == key:
                return v
        raise KeyError(key)

    def delete(self, key):
        bucket = self._buckets[self._hash(key)]
        for i, (k, v) in enumerate(bucket):
            if k == key:
                del bucket[i]
                self._size -= 1
                return True
        return False


class BinarySearchTree:
    """二叉搜索树：insert/search/delete/inorder。
    时间复杂度：平均 O(log n)，最坏 O(n)（退化为链表）。空间复杂度：O(n)。
    """

    class Node:
        __slots__ = ("key", "left", "right")

        def __init__(self, key):
            self.key = key
            self.left = None
            self.right = None

    def __init__(self):
        self.root = None

    def insert(self, key):
        if self.root is None:
            self.root = self.Node(key)
            return
        cur = self.root
        while True:
            if key < cur.key:
                if cur.left is None:
                    cur.left = self.Node(key)
                    return
                cur = cur.left
            elif key > cur.key:
                if cur.right is None:
                    cur.right = self.Node(key)
                    return
                cur = cur.right
            else:
                return  # 重复键不插入

    def search(self, key):
        cur = self.root
        while cur:
            if key == cur.key:
                return True
            cur = cur.left if key < cur.key else cur.right
        return False

    def delete(self, key):
        self.root = self._delete(self.root, key)

    def _delete(self, node, key):
        if node is None:
            return None
        if key < node.key:
            node.left = self._delete(node.left, key)
        elif key > node.key:
            node.right = self._delete(node.right, key)
        else:
            if node.left is None:
                return node.right
            if node.right is None:
                return node.left
            succ = node.right
            while succ.left:
                succ = succ.left
            node.key = succ.key
            node.right = self._delete(node.right, succ.key)
        return node

    def inorder(self):
        result = []
        self._inorder(self.root, result)
        return result

    def _inorder(self, node, result):
        if node:
            self._inorder(node.left, result)
            result.append(node.key)
            self._inorder(node.right, result)


class MinHeap:
    """最小堆：push/pop/peek。
    时间复杂度：push/pop O(log n)，peek O(1)。空间复杂度：O(n)。
    """

    def __init__(self):
        self._data = []

    def push(self, value):
        self._data.append(value)
        self._sift_up(len(self._data) - 1)

    def _sift_up(self, i):
        while i > 0:
            parent = (i - 1) // 2
            if self._data[parent] <= self._data[i]:
                break
            self._data[parent], self._data[i] = self._data[i], self._data[parent]
            i = parent

    def pop(self):
        if not self._data:
            raise IndexError("pop from empty heap")
        root = self._data[0]
        last = self._data.pop()
        if self._data:
            self._data[0] = last
            self._sift_down(0)
        return root

    def _sift_down(self, i):
        n = len(self._data)
        while True:
            left, right = 2 * i + 1, 2 * i + 2
            smallest = i
            if left < n and self._data[left] < self._data[smallest]:
                smallest = left
            if right < n and self._data[right] < self._data[smallest]:
                smallest = right
            if smallest == i:
                break
            self._data[i], self._data[smallest] = self._data[smallest], self._data[i]
            i = smallest

    def peek(self):
        if not self._data:
            raise IndexError("peek from empty heap")
        return self._data[0]


if __name__ == "__main__":
    # 示例调用
    arr = DynamicArray()
    for x in [10, 20, 30]:
        arr.append(x)
    print("DynamicArray:", arr.traverse(), "find 20 ->", arr.find(20))

    ll = SinglyLinkedList()
    ll.push_back(1)
    ll.push_front(0)
    ll.push_back(2)
    print("LinkedList:", ll.traverse(), "remove 1 ->", ll.remove(1), ll.traverse())

    st = Stack()
    st.push(1)
    st.push(2)
    print("Stack pop:", st.pop(), "peek:", st.peek())

    q = Queue()
    q.enqueue("a")
    q.enqueue("b")
    print("Queue dequeue:", q.dequeue(), "peek:", q.peek())

    ht = HashTable()
    ht.put("k1", 100)
    ht.put("k2", 200)
    print("HashTable get k1:", ht.get("k1"), "delete k2:", ht.delete("k2"))

    bst = BinarySearchTree()
    for k in [5, 3, 8, 1, 4, 7, 9]:
        bst.insert(k)
    print("BST inorder:", bst.inorder(), "search 4:", bst.search(4))
    bst.delete(5)
    print("BST after delete 5:", bst.inorder())

    heap = MinHeap()
    for v in [5, 2, 8, 1]:
        heap.push(v)
    print("Heap pop:", heap.pop(), "peek:", heap.peek())
