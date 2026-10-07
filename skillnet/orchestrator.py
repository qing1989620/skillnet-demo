"""技能编排：把选中的技能组织成依赖保持的执行工作流。

对标 SkillNet-Gym 的 Skill Orchestration Completeness：
预测的依赖边越接近 gold workflow，编排完整度越高。
"""
from __future__ import annotations

from typing import Any

from .catalog import SkillLibrary
from .llm import chat_json


class Orchestrator:
    def __init__(self, lib: SkillLibrary) -> None:
        self.lib = lib

    # ------------------------------------------------------------------
    def build_from_relations(self, names: list[str]) -> dict[str, Any]:
        """只用技能库里已有的类型化关系推导工作流（零额外 LLM 成本）。"""
        pool = {n for n in names if self.lib.get(n)}
        edges: set[tuple[str, str]] = set()
        # 只遍历技能自身声明的出边（relations 列表）。
        # 注意不能用无向邻居查询：那会把「A 依赖 B」在遍历 A 时记成 B→A，
        # 再在遍历 B 时反向记成 A→B，凭空制造出环。
        for n in pool:
            s = self.lib.get(n)
            if not s:
                continue
            for rel, tgt in s.relations:
                if rel not in ("depend_on", "compose_with"):
                    continue
                if tgt not in pool or tgt == n:
                    continue
                # depend_on: n 依赖 tgt -> tgt 先执行
                edges.add((tgt, n) if rel == "depend_on" else (n, tgt))

        # 三人以上的环是可能出现的（A 依赖 B、B 组合 C、C 又依赖 A），
        # 而 `_toposort` 遇到环不会报错，只会把环上节点**静默追加到序列末尾** ——
        # 于是给出一个违反依赖关系的执行顺序却毫无提示。
        # 这里显式打断环，并把被丢弃的边回报出去，让调用方看得见。
        kept = self._break_cycles(pool, edges)
        dropped = sorted(edges - kept)

        order = self._toposort(pool, kept)
        return {
            "skills": order,
            "workflow": [list(e) for e in sorted(kept)],
            "source": "relations",
            "cycles_broken": [list(e) for e in dropped],
        }

    def build_with_llm(self, query: str, names: list[str]) -> dict[str, Any]:
        """在关系推导的基础上，让 LLM 补全/修正编排（对齐 Fabric 的 Explorer）。"""
        base = self.build_from_relations(names)
        cards = []
        for n in base["skills"]:
            s = self.lib.get(n)
            if s:
                cards.append(
                    {"skill": n, "capability": s.capability,
                     "inputs": s.inputs, "outputs": s.outputs}
                )
        prompt = (
            "你是科研工作流编排器。给定任务与已选中的技能，请给出它们的执行顺序与依赖边。\n"
            "依赖边 [A, B] 表示 A 必须在 B 之前执行（A 的输出被 B 使用）。\n\n"
            f"【任务】\n{query}\n\n"
            f"【技能】\n{cards}\n\n"
            f"【基于技能关系的初始编排】\n{base['workflow']}\n\n"
            '严格输出 JSON：{"workflow": [["A","B"], ...], "reason": "一句话说明关键依赖"}'
        )
        out = chat_json(
            [{"role": "user", "content": prompt}],
            role="orchestrator",
            temperature=0.0,
            max_tokens=700,
            default={},
        )
        if not isinstance(out, dict):
            out = {}
        result = self.merge_workflow(names, out.get("workflow"))
        result["reason"] = out.get("reason", "") if isinstance(out.get("reason", ""), str) else ""
        return result

    def merge_workflow(self, names: list[str], proposed: Any) -> dict[str, Any]:
        """Validate model edges while preserving the established dependency DAG.

        Model output is untrusted even when it parses as JSON. Invalid members
        must not crash a request, introduce unknown nodes, or displace a known
        prerequisite to accommodate a new model edge.
        """
        base = self.build_from_relations(names)
        valid = set(base["skills"])
        malformed = 0
        edges: set[tuple[str, str]] = set()
        if not isinstance(proposed, list):
            malformed = 1
        else:
            for edge in proposed:
                if (not isinstance(edge, (list, tuple)) or len(edge) != 2
                        or not all(isinstance(n, str) for n in edge)
                        or edge[0] not in valid or edge[1] not in valid
                        or edge[0] == edge[1]):
                    malformed += 1
                    continue
                edges.add(tuple(edge))

        kept = {tuple(e) for e in base["workflow"]}
        adj: dict[str, set[str]] = {n: set() for n in valid}
        for a, b in kept:
            adj[a].add(b)

        rejected: list[list[str]] = []
        for a, b in sorted(edges - kept):
            pending, seen = [b], set()
            while pending:
                node = pending.pop()
                if node in seen:
                    continue
                seen.add(node)
                pending.extend(adj[node] - seen)
            if a in seen:
                rejected.append([a, b])
                continue
            kept.add((a, b))
            adj[a].add(b)

        reasons = []
        if malformed:
            reasons.append(f"ignored {malformed} invalid model workflow item(s)")
        if rejected:
            reasons.append(f"rejected {len(rejected)} model edge(s) conflicting with dependencies")
        if base["cycles_broken"]:
            reasons.append("existing relation cycles were broken")
        return {
            "skills": self._toposort(valid, kept),
            "workflow": [list(e) for e in sorted(kept)],
            "source": "relations+llm" if isinstance(proposed, list) else "relations",
            "cycles_broken": base["cycles_broken"] + rejected,
            "invalid_edges": malformed,
            "degraded": bool(reasons),
            "degraded_reason": "; ".join(reasons),
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _toposort(nodes: set[str], edges: set[tuple[str, str]]) -> list[str]:
        indeg = {n: 0 for n in nodes}
        adj: dict[str, list[str]] = {n: [] for n in nodes}
        for a, b in edges:
            if a in nodes and b in nodes:
                adj[a].append(b)
                indeg[b] += 1
        ready = sorted([n for n, d in indeg.items() if d == 0])
        out: list[str] = []
        while ready:
            n = ready.pop(0)
            out.append(n)
            for m in sorted(adj[n]):
                indeg[m] -= 1
                if indeg[m] == 0:
                    ready.append(m)
            ready.sort()
        for n in sorted(nodes):
            if n not in out:
                out.append(n)
        return out

    @staticmethod
    def _break_cycles(nodes: set[str], edges: set[tuple[str, str]]) -> set[tuple[str, str]]:
        """贪心删边保证无环：按拓扑探索，回边直接丢弃。"""
        keep: set[tuple[str, str]] = set()
        adj: dict[str, list[str]] = {n: [] for n in nodes}
        for a, b in sorted(edges):
            adj.setdefault(a, []).append(b)

        state: dict[str, int] = {n: 0 for n in nodes}  # 0 未访问 1 在栈 2 完成

        def dfs(u: str, path: list[tuple[str, str]]) -> None:
            state[u] = 1
            for v in adj.get(u, []):
                if state.get(v, 0) == 1:
                    continue  # 回边，丢弃
                keep.add((u, v))
                if state.get(v, 0) == 0:
                    dfs(v, path + [(u, v)])
            state[u] = 2

        for n in sorted(nodes):
            if state[n] == 0:
                dfs(n, [])
        return keep

    # ------------------------------------------------------------------
    @staticmethod
    def completeness(predicted: list[list[str]], gold: list[list[str]]) -> float:
        """编排完整度：gold 依赖边被恢复的比例。"""
        g = {tuple(e) for e in gold}
        if not g:
            return 0.0
        p = {tuple(e) for e in predicted}
        return len(g & p) / len(g)
