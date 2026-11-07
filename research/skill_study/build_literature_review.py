"""Build a metadata-only, annotated review; never publish cached full papers."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup

VENUE_UPDATES = {
    "P04": ("COLM 2026", "https://colm.eventhosts.cc/Conferences/2026/AcceptedPapers"),
    "P10": ("USENIX Security 2026", "https://www.usenix.org/conference/usenixsecurity26/presentation/liu-yi"),
    "P12": ("ICLR 2023", "https://openreview.net/forum?id=WE_vluYUL-X"),
    "P19": (
        "ICLR 2024",
        "https://proceedings.iclr.cc/paper_files/paper/2024/hash/f1cf02ce09757f57c3b93c0db83181e0-Abstract-Conference.html",
    ),
    "P25": (
        "NeurIPS 2023 Datasets and Benchmarks",
        "https://proceedings.neurips.cc/paper_files/paper/2023/hash/91f18a1287b398d378ef22505bf41832-Abstract-Datasets_and_Benchmarks.html",
    ),
    "P27": (
        "ICLR 2025",
        "https://proceedings.iclr.cc/paper_files/paper/2025/hash/9e720fce64f91114c49cfd640d821da3-Abstract-Conference.html",
    ),
    "P30": ("Findings of ACL 2024", "https://aclanthology.org/2024.findings-acl.624/"),
    "P31": (
        "ICLR 2024",
        "https://proceedings.iclr.cc/paper_files/paper/2024/hash/7274ed909a312d4d869cc328ad1c5f04-Abstract-Conference.html",
    ),
    "P34": ("Findings of NAACL 2025", "https://aclanthology.org/2025.findings-naacl.65/"),
    "P35": (
        "ICLR 2025",
        "https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b126cc38b8638e07bef37e7b2bb72bf-Abstract-Conference.html",
    ),
    "P37": ("Journal of the ACM 2021", "https://dl.acm.org/doi/10.1145/3478535"),
    "P38": ("Foundations and Trends in Machine Learning 2012", "https://doi.org/10.1561/2200000044"),
    "P39": ("EMNLP 2023", "https://aclanthology.org/2023.emnlp-main.398/"),
    "P40": ("EMNLP 2023", "https://aclanthology.org/2023.emnlp-main.741/"),
    "P41": ("ACL 2023", "https://aclanthology.org/2023.acl-long.910/"),
    "P42": ("WWW 2010", "https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/p661.pdf"),
    "P44": ("COLM 2026", "https://colm.eventhosts.cc/Conferences/2026/AcceptedPapers"),
}


def build(cache: Path, destination: Path) -> None:
    base = Path(__file__).parent
    candidates = json.loads((base / "literature_candidates.json").read_text(encoding="utf-8"))
    notes = {r["id"]: r for r in json.loads((base / "reading_notes.json").read_text(encoding="utf-8"))}
    records = []
    for candidate in candidates:
        identity = candidate["id"]
        folder = cache / identity
        retrieval = json.loads((folder / "retrieval.json").read_text(encoding="utf-8"))
        windows = json.loads((folder / "review-windows.json").read_text(encoding="utf-8"))
        if retrieval["status"] == "retrieval_failed" or not windows["windows"]:
            raise ValueError("Paper not available for method review: " + identity)
        text = (folder / "fulltext.txt").read_text(encoding="utf-8")
        if hashlib.sha256(text.encode()).hexdigest() != retrieval["fulltext_sha256"]:
            raise ValueError("Cached paper changed")
        authors = []
        if (folder / "abstract.html").exists():
            soup = BeautifulSoup((folder / "abstract.html").read_bytes(), "html.parser")
            authors = [m["content"] for m in soup.select('meta[name="citation_author"]')]
        venue, venue_url = VENUE_UPDATES.get(identity, (candidate["venue"], candidate.get("venue_source")))
        if "to verify" in venue:
            raise ValueError("Unresolved candidate venue")
        title = retrieval.get("observed_title", candidate["title"])
        title = title.strip() if title else candidate["title"]
        records.append(
            {
                "id": identity,
                "title": title,
                "candidate_title": candidate["title"],
                "authors": authors,
                "track": candidate["track"],
                "venue": venue,
                "publication_status": "preprint_formal_venue_not_verified"
                if venue == "arXiv preprint"
                else "formal_publication_record",
                "venue_source": venue_url,
                "publication_note": "Venue is distinct from the cached reading version; no claim that the preprint equals the final publisher version.",
                "reading_source": retrieval["fulltext_url"],
                "primary_url": retrieval["primary_url"],
                "pinned_arxiv": retrieval.get("pinned_arxiv"),
                "cached_fulltext_sha256": retrieval["fulltext_sha256"],
                "review_level": "targeted_method_and_experiment_or_limitation_excerpt_review_by_current_agent",
                "read_sections": [{k: v for k, v in w.items() if k != "window"} for w in windows["windows"]],
                "review_is_not_independent_human_validation": True,
                **{k: notes[identity][k] for k in ("strength", "limit", "use")},
            }
        )
        if identity in ("P04", "P44"):
            records[-1]["formal_venue_independently_verified"] = True
            records[-1]["venue_verification"] = "official COLM 2026 accepted-paper list, checked 2026-11-06"
            records[-1]["cached_venue_page_sha256"] = hashlib.sha256(
                (folder / "colm-accepted-2026.html").read_bytes()
            ).hexdigest()
    if len({r.get("pinned_arxiv") or r["primary_url"] for r in records}) != len(records):
        raise ValueError("Duplicate paper identity")
    index = {
        "date": "2026-11-06",
        "review_kind": "purposeful_method_scoping_review_not_systematic_meta_analysis",
        "papers": len(records),
        "direct_modern_skill_papers": 12,
        "formal_publication_records": sum(
            r["publication_status"] == "formal_publication_record" for r in records
        ),
        "preprints_without_verified_formal_venue": sum(r["venue"] == "arXiv preprint" for r in records),
        "inclusion": "reusable skills, tool/agent execution, judges/evidence, calibrated risk, set selection or workflow optimization",
        "exclusions": "blogs, duplicated versions, keyword-only motor-skill papers, and unverified titles",
        "limitations": [
            "purposive selection, not exhaustive literature coverage",
            "current Agent review, not independent expert consensus",
            "targeted sections, not a claim of line-by-line reading of every paper",
            "arXiv and formal versions may differ",
        ],
        "records": records,
    }
    destination.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    lines = [
        "# 44 篇论文的方法学习与迁移表",
        "",
        "核验日期：2026-11-06。",
        "",
        f"这是围绕两个研究问题的定向方法综述。P01–P10、P43–P44 直接讨论现代 Agent Skill，其余提供程序技能、工具执行、评价、校准与优化方法。{index['preprints_without_verified_formal_venue']} 篇目前仅按预印本列入，其余列明正式发表记录；它们并非 44 篇‘Skill 顶刊’。",
        "",
        "已取得每篇正文并定向阅读方法、实验或局限片段，不声称逐字通读全部正文。阅读版本与正式出版版本分开记录。每条优势是论文方法概括，局限及迁移建议包含本研究的判断，不是作者对本项目的背书。原始全文仅缓存本地，不在仓库转载。",
        "",
        "| 编号 / 论文与阅读版本 | 发表记录 | 可借鉴之处 | 迁移限制 | 在本课题中的用途 |",
        "|---|---|---|---|---|---|",
    ]
    for row in records:
        version = row["pinned_arxiv"] or "正式 PDF"
        publication = f"[{row['venue']}]({row['venue_source']})" if row["venue_source"] else row["venue"]
        lines.append(
            f"| {row['id']} [{row['title']}]({row['primary_url']})；{version} | {publication} | {row['strength']} | {row['limit']} | {row['use']} |"
        )
    lines += [
        "",
        "正文指纹、作者、原始候选标题、阅读章节和版本差异记录见 `literature_review.json`。",
        "",
        "候选表中需核验的年份/会议信息已更正：ToolSandbox 为 Findings of NAACL 2025，RCPS 为 Journal of the ACM 2021。SkillRouter v5 的标题也与初版不同，按同一 arXiv ID 去重。",
        "",
        "SkillRouter 与 SkillLearnBench 的 COLM 2026 录用信息已在会议官方名单独立核实；初期未核实版本曾将它们保守列为预印本，现已更新。阅读正文仍固定为账本中的 arXiv 版本。",
    ]
    destination.with_name("LITERATURE_REVIEW.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("literature_review.json"))
    args = parser.parse_args()
    build(args.cache, args.output)
