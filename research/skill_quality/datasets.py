"""Exact/near text groups and source-disjoint sample preparation."""

from __future__ import annotations

import math
import random
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any

from .manifest import digest
from .schemas import SkillSnapshot


def normalized_body(document: str) -> str:
    body = re.sub(r"\A\ufeff?---\s*\n.*?\n---\s*\n", "", document, flags=re.S)
    body = re.sub(r"\A\s*# [^\n]+\n", "", body)
    return " ".join(unicodedata.normalize("NFKC", body).casefold().split())


def shingles(document: str) -> frozenset[str]:
    tokens = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", normalized_body(document))
    if len(tokens) < 5:
        return frozenset(tokens)
    return frozenset(" ".join(tokens[i : i + 5]) for i in range(len(tokens) - 4))


class Groups:
    def __init__(self, ids: list[str]):
        self.parent = {uid: uid for uid in ids}

    def find(self, uid: str) -> str:
        while self.parent[uid] != uid:
            self.parent[uid] = self.parent[self.parent[uid]]
            uid = self.parent[uid]
        return uid

    def union(self, left: str, right: str) -> None:
        a, b = sorted((self.find(left), self.find(right)))
        self.parent[b] = a


def deduplicate(snapshots: list[SkillSnapshot], threshold: float = 0.85) -> dict[str, Any]:
    """Exact prefix-filter Jaccard join, not approximate LSH; semantic duplicates remain unknown."""
    if not 0 < threshold <= 1:
        raise ValueError("Invalid Jaccard threshold")
    uid = [s.skill_uid for s in snapshots]
    groups = Groups(uid)
    exact, norm = defaultdict(list), defaultdict(list)
    for item in snapshots:
        exact[item.document_sha256].append(item.skill_uid)
        norm[digest(normalized_body(item.document))].append(item.skill_uid)
    for cluster in list(exact.values()) + list(norm.values()):
        for other in cluster[1:]:
            groups.union(cluster[0], other)
    sets = [shingles(s.document) for s in snapshots]
    frequency: Counter[str] = Counter(token for value in sets for token in value)
    order = {token: n for n, token in enumerate(sorted(frequency, key=lambda t: (frequency[t], t)))}
    inverted: dict[int, list[int]] = defaultdict(list)
    pairs, checked = [], 0
    for i in sorted(range(len(sets)), key=lambda x: (len(sets[x]), uid[x])):
        current = sets[i]
        if not current:
            continue
        prefix_len = len(current) - math.ceil(threshold * len(current)) + 1
        prefix = sorted(order[t] for t in current)[:prefix_len]
        possible = {
            j for token in prefix for j in inverted[token] if len(sets[j]) + 1e-12 >= threshold * len(current)
        }
        for j in sorted(possible):
            checked += 1
            intersection = len(current & sets[j])
            similarity = intersection / (len(current) + len(sets[j]) - intersection)
            if similarity + 1e-12 >= threshold:
                groups.union(uid[i], uid[j])
                pairs.append(
                    {
                        "left": uid[j],
                        "right": uid[i],
                        "jaccard": similarity,
                        "kind": "near_duplicate_or_version_variant_not_adjudicated",
                    }
                )
        for token in prefix:
            inverted[token].append(i)
    clusters: dict[str, list[str]] = defaultdict(list)
    for key in uid:
        clusters[groups.find(key)].append(key)
    return {
        "threshold": threshold,
        "algorithm": "exact_prefix_join_word_5shingle_jaccard",
        "candidate_pairs_checked": checked,
        "exact_groups": [v for v in exact.values() if len(v) > 1],
        "normalized_groups": [v for v in norm.values() if len(v) > 1],
        "near_pairs": pairs,
        "content_clusters": {k: sorted(v) for k, v in sorted(clusters.items())},
        "semantic_neighbor_review": "not_run; lexical checks cannot rule out semantic leakage",
    }


def check_disjoint(rows: list[dict[str, Any]]) -> None:
    seen: dict[tuple[str, str], str] = {}
    for row in rows:
        for key in (
            "skill_uid",
            "document_sha256",
            "repo_family_id",
            "content_cluster_id",
            "task_family_id",
            "verifier_lineage_id",
        ):
            if not row.get(key):
                continue
            identity = (key, str(row[key]))
            if identity in seen and seen[identity] != row["partition"]:
                raise ValueError("Split leakage: " + key)
            seen[identity] = row["partition"]


def prepare_splits(
    snapshots: list[SkillSnapshot], dedup: dict[str, Any], *, seed: int = 20261104, target: int = 200
) -> dict[str, Any]:
    by_uid = {s.skill_uid: s for s in snapshots}
    groups = Groups(list(by_uid))
    repos: dict[str, list[str]] = defaultdict(list)
    content_id = {}
    for cluster_id, members in dedup["content_clusters"].items():
        for member in members:
            content_id[member] = cluster_id
            groups.union(members[0], member)
    for item in snapshots:
        repos[item.repo_family_id].append(item.skill_uid)
    for members in repos.values():
        for member in members[1:]:
            groups.union(members[0], member)
    components: dict[str, list[str]] = defaultdict(list)
    for uid in sorted(by_uid):
        components[groups.find(uid)].append(uid)
    blocks = sorted(components.values(), key=lambda members: digest([seed, members]))
    # Subset sum chooses whole source/content components. Never split a large
    # connected component just to meet the nominal sample size.
    reachable: dict[int, tuple[int, ...]] = {0: ()}
    for i, block in enumerate(blocks):
        for size, indices in list(reachable.items()):
            reachable.setdefault(size + len(block), indices + (i,))
    options = [size for size in reachable if size >= target and len(by_uid) - size >= target]
    if options:
        test_size = min(options)
    else:
        options = [size for size in reachable if 0 < size < len(by_uid)]
        test_size = min(options, key=lambda n: (abs(n - target), n)) if options else 0
    test_blocks = set(reachable[test_size])
    rows = []
    for i, block in enumerate(blocks):
        for uid in block:
            snap = by_uid[uid]
            rows.append(
                {
                    "skill_uid": uid,
                    "document_sha256": snap.document_sha256,
                    "repo_family_id": snap.repo_family_id,
                    "content_cluster_id": content_id[uid],
                    "partition": "D2" if i in test_blocks else "D1",
                }
            )
    check_disjoint(rows)
    rng = random.Random(seed)
    samples = {}
    for partition in ("D1", "D2"):
        buckets: dict[tuple[str, bool], list[str]] = defaultdict(list)
        for row in rows:
            if row["partition"] == partition:
                snap = by_uid[row["skill_uid"]]
                buckets[(snap.domain, any(r.path.startswith("scripts/") for r in snap.resources))].append(
                    snap.skill_uid
                )
        keys = sorted(buckets)
        rng.shuffle(keys)
        for values in buckets.values():
            rng.shuffle(values)
        selected: list[str] = []
        while len(selected) < target and any(buckets.values()):
            for key in keys:
                if buckets[key] and len(selected) < target:
                    selected.append(buckets[key].pop())
        samples[partition] = selected
    return {
        "seed": seed,
        "target_per_split": target,
        "assignments": rows,
        "sample_ids": samples,
        "component_sizes": sorted((len(v) for v in blocks), reverse=True),
        "status": "prepared_unlabelled"
        if all(len(v) == target for v in samples.values())
        else "insufficient_independent_source_groups",
        "training_20_ids": samples["D1"][:20],
        "human_labels": "not_collected",
        "seal_status": "no_test_labels_exist; membership_hash_only_no_OS_access_control",
        "stratification": "domain_and_script_presence_round_robin; source_components_take_priority",
        "unmet_strata": ["human_risk", "independent_origin_of_forks", "embedding_neighbors_not_reviewed"],
    }
