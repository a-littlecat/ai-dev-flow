"""Small deterministic helpers for the frozen 30-sample benchmark protocol."""

from __future__ import annotations

import math
from collections.abc import Iterable


def nearest_rank(samples: Iterable[float], percentile: float) -> float:
    values = sorted(float(item) for item in samples)
    if not values:
        raise ValueError("at least one sample is required")
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be in (0, 1]")
    return values[math.ceil(percentile * len(values)) - 1]


def benchmark_summary(samples_ms: Iterable[float]) -> dict[str, object]:
    values = tuple(float(item) for item in samples_ms)
    if len(values) != 30:
        raise ValueError("the dashboard benchmark protocol requires 30 samples")
    return {
        "samples_ms": list(values),
        "p50_ms": nearest_rank(values, 0.50),
        "p95_ms": nearest_rank(values, 0.95),
    }
