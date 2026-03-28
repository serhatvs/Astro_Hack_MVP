"""Normalization helpers for stable weighted scoring."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any


MetricRanges = dict[str, tuple[float, float]]


def min_max_normalize(
    value: float,
    minimum: float,
    maximum: float,
    fallback: float = 0.5,
) -> float:
    """Normalize a value into the 0..1 range with a stable fallback."""

    if maximum == minimum:
        return fallback
    return (value - minimum) / (maximum - minimum)


def build_metric_ranges(records: Sequence[Any], metrics: Iterable[str]) -> MetricRanges:
    """Build min/max ranges for a set of numeric object attributes."""

    ranges: MetricRanges = {}
    for metric in metrics:
        values = [float(getattr(record, metric)) for record in records]
        ranges[metric] = (min(values), max(values))
    return ranges


def normalize_record(record: Any, ranges: Mapping[str, tuple[float, float]]) -> dict[str, float]:
    """Normalize all requested metrics for a record."""

    return {
        metric: min_max_normalize(float(getattr(record, metric)), minimum, maximum)
        for metric, (minimum, maximum) in ranges.items()
    }


def normalize_scores(scores: Sequence[float], fallback: float = 0.5) -> list[float]:
    """Normalize a score vector into the 0..1 range."""

    if not scores:
        return []
    minimum = min(scores)
    maximum = max(scores)
    return [min_max_normalize(score, minimum, maximum, fallback=fallback) for score in scores]

