"""Neutral, typed metadata projection. Execution keys never reach a selector."""

from __future__ import annotations

import hashlib
import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import kernels
from .contracts import CAPS, TEXT


def full_registry() -> list[dict]:
    nodes = []
    for key, function in kernels.OPS.items():
        cap = CAPS[key[0]]
        dependencies: list[Callable[..., Any]] = [kernels.metric_values] if cap == "metrics" else []
        if cap == "bundle":
            dependencies = [
                kernels.OPS[k]
                for k in {"b0": ["d0", "x0", "m0"], "b1": ["m0", "x0", "d0"], "b2": ["d1", "x0", "m0"]}[key]
            ]
        context = TEXT[cap] + "\n" + "\n".join(inspect.getsource(f) for f in [*dependencies, function])
        identifier = "s-" + hashlib.sha256(("opaque-node-seed-20261111:" + key).encode()).hexdigest()[:10]
        nodes.append(
            {
                "id": identifier,
                "capability": cap,
                "text": TEXT[cap],
                "source_sha256": hashlib.sha256(
                    Path(kernels.__file__).read_bytes() + context.encode()
                ).hexdigest(),
                "context_bytes": len(context.encode("utf-8")),
                "implementation_key": key,
                "context": context,
            }
        )
    return sorted(nodes, key=lambda n: n["id"])


def public_nodes(nodes: list[dict]) -> list[dict]:
    allowed = ["id", "capability", "text", "source_sha256", "context_bytes"]
    return [{k: n[k] for k in allowed} for n in nodes]
