"""Shared internal dataclasses for multi-domain biological scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DomainEvaluation:
    """Evaluation result for a single domain candidate."""

    candidate: Any
    domain_type: str
    domain_score: float
    mission_fit_score: float
    risk_score: float
    combined_score: float
    metrics: dict[str, float]
    notes: list[str] = field(default_factory=list)
    support_system: str | None = None


@dataclass(slots=True)
class InteractionEvaluation:
    """Cross-domain interaction result."""

    synergy_score: float
    conflict_score: float
    complexity_penalty: float
    resource_overlap: float
    loop_closure_bonus: float
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DomainRankingSet:
    """Ordered candidates for each biological domain."""

    crop: list[DomainEvaluation]
    algae: list[DomainEvaluation]
    microbial: list[DomainEvaluation]


@dataclass(slots=True)
class IntegratedResult:
    """Fully integrated recommendation candidate."""

    crop: DomainEvaluation
    algae: DomainEvaluation
    microbial: DomainEvaluation
    interaction: InteractionEvaluation
    grow_system_name: str
    integrated_score: float


@dataclass(slots=True)
class IntegratedSelection:
    """Integrated candidate plus the ranking context needed by the API."""

    result: IntegratedResult
    ranked_candidates: DomainRankingSet
    grow_system: Any
