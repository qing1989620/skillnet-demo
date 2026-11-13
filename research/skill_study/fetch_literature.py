"""Cache primary paper texts and metadata; download is not a reading claim."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import io
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader


def fetch_one(candidate: dict[str, Any], cache: Path) -> dict[str, Any]:
    folder = cache / candidate["id"]
    folder.mkdir(parents=True, exist_ok=True)
    record = dict(candidate, downloaded_at_utc=datetime.now(UTC).isoformat(), attempts=[])
    with httpx.Client(
        follow_redirects=True,
        timeout=45,
        headers={"User-Agent": "SkillNetResearchLiteratureReview/1.0 (read-only academic paper retrieval)"},
    ) as client:

        def get(url: str, name: str) -> bytes:
            destination = folder / name
            if destination.exists():
                raw = destination.read_bytes()
                record["attempts"].append({"url": url, "cache_hit": True})
                return raw
            response = client.get(url)
            record["attempts"].append({"url": url, "status": response.status_code})
            response.raise_for_status()
            raw = response.content
            if len(raw) > 40_000_000:
                raise ValueError("Paper exceeds size bound")
            destination.write_bytes(raw)
            time.sleep(0.35)
            return raw

        try:
            arxiv = candidate.get("arxiv")
            if arxiv:
                raw = get("https://arxiv.org/abs/" + arxiv, "abstract.html")
                soup = BeautifulSoup(raw, "html.parser")
                title = soup.select_one("h1.title")
                record["observed_title"] = (
                    title.get_text(" ", strip=True).removeprefix("Title:") if title else None
                )
                metadata = {m.get("name"): m.get("content") for m in soup.select("meta[name^=citation_]")}
                record["primary_metadata"] = metadata
                versions = re.findall(re.escape(arxiv) + r"v(\d+)", raw.decode("utf-8"))
                version = max(map(int, versions), default=1)
                pinned = arxiv + "v" + str(version)
                record["pinned_arxiv"] = pinned
                record["primary_url"] = "https://arxiv.org/abs/" + pinned
                record["abstract_page_text"] = soup.get_text(" ", strip=True)[:18_000]
                try:
                    html = get("https://arxiv.org/html/" + pinned, "paper.html")
                    paper = BeautifulSoup(html, "html.parser")
                    article = paper.find("article")
                    if article is None or len(article.get_text()) < 6_000:
                        raise ValueError("Full paper HTML unavailable")
                    for tag in article.select("script,style"):
                        tag.decompose()
                    text = article.get_text("\n", strip=True)
                    record["headings"] = [h.get_text(" ", strip=True) for h in article.select("h1,h2,h3,h4")]
                    record["fulltext_url"] = "https://arxiv.org/html/" + pinned
                    record["format"] = "html"
                except Exception as exc:
                    record["html_fallback_reason"] = type(exc).__name__ + ": " + str(exc)[:180]
                    pdf_url = "https://arxiv.org/pdf/" + pinned
                    pdf = get(pdf_url, "paper.pdf")
                    reader = PdfReader(io.BytesIO(pdf))
                    text = "\n\n".join(
                        f"[PAGE {i}]\n" + (page.extract_text() or "")
                        for i, page in enumerate(reader.pages, 1)
                    )
                    record["pages"] = len(reader.pages)
                    record["fulltext_url"] = pdf_url
                    record["format"] = "pdf_text"
            else:
                pdf_url = candidate["pdf_source"]
                pdf = get(pdf_url, "paper.pdf")
                reader = PdfReader(io.BytesIO(pdf))
                text = "\n\n".join(
                    f"[PAGE {i}]\n" + (p.extract_text() or "") for i, p in enumerate(reader.pages, 1)
                )
                record.update(
                    primary_url=candidate["venue_source"],
                    fulltext_url=pdf_url,
                    format="pdf_text",
                    pages=len(reader.pages),
                )
            if len(text) < 6_000:
                raise ValueError("Too little full text for method review")
            (folder / "fulltext.txt").write_text(text, encoding="utf-8", newline="\n")
            record["fulltext_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
            record["fulltext_characters"] = len(text)
            venue_url = candidate.get("venue_source")
            if venue_url:
                try:
                    raw = get(venue_url, "venue.html")
                    venue_text = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
                    (folder / "venue.txt").write_text(venue_text, encoding="utf-8")
                    record["venue_page_sha256"] = hashlib.sha256(raw).hexdigest()
                    record["venue_page_status"] = "downloaded_needs_manual_verification"
                except Exception as exc:
                    record["venue_page_status"] = "unavailable: " + str(exc)[:160]
            record["status"] = "fulltext_cached_not_yet_reviewed"
        except Exception as exc:
            record["status"] = "retrieval_failed"
            record["error"] = type(exc).__name__ + ": " + str(exc)[:250]
    (folder / "retrieval.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry", type=Path, default=Path(__file__).with_name("literature_candidates.json")
    )
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3, choices=(1, 2, 3))
    args = parser.parse_args()
    candidates = json.loads(args.registry.read_text(encoding="utf-8"))
    args.cache.mkdir(parents=True, exist_ok=True)
    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(fetch_one, row, args.cache) for row in candidates]
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            records.append(row)
            print(
                json.dumps(
                    {
                        "id": row["id"],
                        "status": row["status"],
                        "characters": row.get("fulltext_characters"),
                        "error": row.get("error"),
                    }
                ),
                flush=True,
            )
    (args.cache / "retrieval-index.json").write_text(
        json.dumps(sorted(records, key=lambda r: r["id"]), ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
