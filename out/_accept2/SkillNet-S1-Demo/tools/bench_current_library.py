# -*- coding: utf-8 -*-
"""当前库基准（Round 4 / Track C）。

与测试分开：测试保证代码正确，benchmark 测产品效果。
每次运行自动快照库元数据入 manifest（指令 22：库变了数字不混乱）。

Experiment A — Retrieval：bm25 / hybrid / fabric(graph) 三档，
指标 = gold Recall@K + gold coverage + 延迟；fabric 额外测「补回 vs 噪声」：
  +relevant  = fabric 有而 bm25 没有的技能中，在 gold 里的
  +noise     = fabric 有而 bm25 没有的技能中，不在 gold 里的
（fabric 以 rerank=False 运行：纯测图扩展本身的价值，零 LLM 成本，口径见 manifest）
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillnet.catalog import SkillLibrary, build_seed_skills  # noqa: E402
from skillnet.retriever import Retriever  # noqa: E402
from skillnet import config  # noqa: E402


def _sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT),
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return "unknown"


def snapshot_manifest(lib: SkillLibrary, tasks_files: list[pathlib.Path]) -> dict:
    stats = lib.stats() if hasattr(lib, "stats") else {}
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git_commit": _git_commit(),
        "skill_count": len(lib),
        "edge_count": sum(len(s.relations) for s in lib),
        "evolved_count": sum(1 for s in lib if s.source != "seed"),
        "domain_count": len({s.domain for s in lib}),
        "library_hash": _sha(config.LIBRARY_FILE) if pathlib.Path(config.LIBRARY_FILE).exists() else None,
        "dataset_hash": {f.name: _sha(f) for f in tasks_files},
        "model": config.MODEL,
        "fabric_rerank": False,
        "note": "fabric 档 rerank=False：纯图扩展消融口径，不含 LLM 重排收益",
    }


def recall_at_k(selected: list[str], gold: list[str], k: int) -> float:
    if not gold:
        return float("nan")
    return len({*selected[:k]} & {*gold}) / len(gold)


def main() -> None:
    # 当前 live 库 = 种子 + 演化 + 学习统计（与 server 启动一致）。
    # 不能用 build_seed_skills()：那会退回 75/90 的种子库，冒充当前基准（指令 21/22）。
    lib = SkillLibrary.load()
    tasks_files = [ROOT / "tasks" / "benchmark.json", ROOT / "tasks" / "heldout.json"]
    manifest = snapshot_manifest(lib, tasks_files)

    retr = Retriever(lib).build()
    K = 5
    rows = []
    for split, fname in (("dev", "benchmark.json"), ("heldout", "heldout.json")):
        data = json.loads((ROOT / "tasks" / fname).read_text(encoding="utf-8"))["tasks"]
        for t in data:
            gold = [g for g in (t.get("gold") or []) if lib.get(g)]
            if not gold:
                continue
            row: dict = {"split": split, "id": t["id"], "gold_n": len(gold)}
            per = {}
            for m in ("bm25", "hybrid", "fabric"):
                t0 = time.perf_counter()
                res = retr.search(t["query"], k=K, mode=m,
                                  rerank=(False if m == "fabric" else True))
                ms = (time.perf_counter() - t0) * 1000
                sel = [c.name if hasattr(c, "name") else c for c in (res.selected or [])][:K]
                per[m] = {"recall": round(recall_at_k(sel, gold, K), 4),
                          "latency_ms": round(ms, 1), "selected": sel}
            # fabric 相对 bm25 的补回 / 噪声
            b25, fab = set(per["bm25"]["selected"]), set(per["fabric"]["selected"])
            added = fab - b25
            per["fabric_gain"] = {"added_n": len(added),
                                  "added_relevant": len(added & set(gold)),
                                  "added_noise": len(added - set(gold))}
            row.update(per)
            rows.append(row)

    def agg(split):
        rs = [r for r in rows if r["split"] == split]
        return {m: round(sum(r[m]["recall"] for r in rs) / len(rs), 4)
                for m in ("bm25", "hybrid", "fabric")} | {"n": len(rs)}

    out = {"manifest": manifest,
           "summary": {"dev": agg("dev"), "heldout": agg("heldout")},
           "rows": rows}
    dest = ROOT / "out" / "bench"
    dest.mkdir(parents=True, exist_ok=True)
    fp = dest / f"retrieval_{time.strftime('%Y%m%d_%H%M%S')}.json"
    fp.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("已写出", fp)
    print(json.dumps(out["summary"], ensure_ascii=False, indent=1))
    print("manifest:", json.dumps({k: v for k, v in manifest.items() if k != "dataset_hash"},
                                  ensure_ascii=False))


if __name__ == "__main__":
    main()
