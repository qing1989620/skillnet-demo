"""Prepare reproducible method/evaluation reading windows from cached papers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

TARGETS = {
    "P43": [r"^3\.3", r"^4\.", r"^5\.8"],
    "P44": [r"^3\.2", r"^L\.3", r"^N\.2"],
    "P01": [r"^3\.4", r"^4\.1"],
    "P02": [r"^3 SkillsBench", r"^6\.1"],
    "P03": [r"^2\.1", r"^2\.3"],
    "P04": [r"^3", r"^4\.1"],
    "P05": [r"^3\.2", r"^3\.3", r"^3\.4"],
    "P06": [r"^3\.2", r"^4"],
    "P07": [r"^3\.2", r"^3\.3"],
    "P08": [r"^3\.1", r"^3\.2"],
    "P09": [r"^3\.3", r"^4 Evaluation"],
    "P10": [r"^3 Methodology", r"^3\.1"],
    "P11": [r"^2\.2", r"^2\.3"],
    "P15": [r"^2\.3", r"^A\.5"],
    "P17": [r"^3\.1", r"^4 LATM"],
    "P26": [r"^3\.1", r"^3\.2"],
    "P23": [r"^3 GEPA", r"^3\.1"],
    "P36": [r"^1\.1", r"^2\.1"],
    "P37": [r"^2 Upper", r"^2\.2"],
    "P38": [r"^2\.2 L", r"^3\.1 Quality"],
}


def prepare(folder: Path) -> dict:
    retrieval = json.loads((folder / "retrieval.json").read_text(encoding="utf-8"))
    if retrieval["status"] == "retrieval_failed":
        return {"id": folder.name, "status": "unavailable"}
    windows = []
    if retrieval["format"] == "html":
        soup = BeautifulSoup((folder / "paper.html").read_bytes(), "html.parser")
        headings = soup.select("article h2,article h3,article h4")
        targets = TARGETS.get(
            folder.name,
            [r"method|framework|approach|model|construction|system|design|benchmark|evaluation|experiment"],
        )
        used = set()
        for pattern in targets:
            for heading in headings:
                title = heading.get_text(" ", strip=True)
                if not re.search(pattern, title, re.I) or title in used:
                    continue
                section = heading.find_parent("section")
                if section is None:
                    continue
                text = section.get_text("\n", strip=True)
                windows.append(
                    {
                        "section": title,
                        "characters_in_section": len(text),
                        "window": text[:6500],
                        "section_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    }
                )
                used.add(title)
                break
        if len(windows) < 2:
            for heading in headings:
                title = heading.get_text(" ", strip=True)
                if title in used or re.search(
                    r"references|introduction|related work|acknowledg|appendix", title, re.I
                ):
                    continue
                section = heading.find_parent("section")
                if section is not None:
                    text = section.get_text("\n", strip=True)
                    windows.append(
                        {
                            "section": title,
                            "characters_in_section": len(text),
                            "window": text[:6500],
                            "section_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        }
                    )
                    used.add(title)
                if len(windows) >= 2:
                    break
    else:
        text = (folder / "fulltext.txt").read_text(encoding="utf-8")
        for label, pattern in [
            (
                "method",
                r"(?im)^\s*(?:2|3|4)[. ]+[^\n]{0,90}(?:method|framework|approach|model|design|algorithm)[^\n]*",
            ),
            ("evaluation", r"(?im)^\s*(?:3|4|5)[. ]+[^\n]{0,90}(?:experiment|evaluation|result)[^\n]*"),
        ]:
            match = re.search(pattern, text)
            start = match.start() if match else (3500 if label == "method" else 10000)
            window = text[start : start + 6500]
            windows.append(
                {
                    "section": match.group().strip() if match else label + "_fallback_offset",
                    "start_character": start,
                    "window": window,
                    "window_sha256": hashlib.sha256(window.encode()).hexdigest(),
                }
            )
    record = {
        "id": folder.name,
        "fulltext_url": retrieval["fulltext_url"],
        "fulltext_sha256": retrieval["fulltext_sha256"],
        "reading_claim": "prepared_only_not_a_review_until_agent_reads_selected_windows",
        "windows": windows,
    }
    (folder / "review-windows.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"id": folder.name, "sections": [w["section"] for w in windows]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    args = parser.parse_args()
    for folder in sorted(args.cache.glob("P*")):
        print(json.dumps(prepare(folder), ensure_ascii=False))


if __name__ == "__main__":
    main()
