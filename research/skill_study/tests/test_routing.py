from __future__ import annotations

import copy

import numpy as np
import pytest

from research.skill_study.routing_pilot import POLICIES, dpp_kernel, score, select, vectors


def candidates() -> list[dict]:
    return [
        {"name": f"skill-{i}", "capability": text, "outputs": [], "use_when": []}
        for i, text in enumerate(
            [
                "clean csv missing values",
                "clean csv missing values",
                "plot monthly revenue",
                "calculate confidence intervals",
                "extract pdf tables",
                "check dataset schema",
            ]
        )
    ]


def test_dpp_is_psd_and_retains_top_one_relevance() -> None:
    rows = candidates()
    query, skills = vectors("clean csv and plot revenue", rows)
    quality = 1 / np.sqrt(np.arange(1, len(rows) + 1))
    for residual in (0.0, 0.5, 1.0):
        kernel = dpp_kernel(query, skills, quality, residual)
        assert np.linalg.eigvalsh(kernel).min() > -1e-9
        assert np.isfinite(kernel).all()
    for policy in POLICIES:
        assert select("clean csv", rows, policy, k=1) == ["skill-0"]


def test_duplicate_relevance_can_be_replaced_by_complementary_candidate() -> None:
    # This owned counterexample checks that the selectors are not all aliases of top-k.
    rows = candidates()
    selected = select("clean csv and plot monthly revenue", rows, "DPP_raw", k=2)
    assert selected[0] == "skill-0"
    assert "skill-1" not in selected


@pytest.mark.parametrize("policy", POLICIES)
def test_selection_is_deterministic_bounded_and_does_not_mutate(policy: str) -> None:
    rows = candidates()
    before = copy.deepcopy(rows)
    result = select("clean csv and plot monthly revenue", rows, policy, k=3)
    assert result == select("clean csv and plot monthly revenue", rows, policy, k=3)
    assert len(result) == 3 and len(set(result)) == 3
    assert rows == before


def test_reference_metrics_are_not_retrieval_top_one_only() -> None:
    recall, full = score(["a", "b"], ["a", "b", "c"])
    assert recall == 2 / 3 and not full
    assert score(["a", "b", "c"], ["a", "b", "c"]) == (1.0, True)


def test_empty_pool_and_duplicate_ids_are_explicit() -> None:
    for policy in POLICIES:
        assert select("q", [], policy) == []
    with pytest.raises(ValueError, match="Duplicate"):
        select("q", candidates()[:1] * 2, "DPP_raw")
