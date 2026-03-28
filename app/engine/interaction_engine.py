"""Cross-domain interaction scoring for integrated biological loops."""

from __future__ import annotations

from app.engine.types import DomainEvaluation, InteractionEvaluation
from app.models.mission import Environment, MissionProfile
from app.models.system import GrowingSystem


class InteractionEngine:
    """Evaluate synergy, conflicts, and complexity across selected domains."""

    def evaluate(
        self,
        crop: DomainEvaluation,
        algae: DomainEvaluation,
        microbial: DomainEvaluation,
        grow_system: GrowingSystem,
        mission: MissionProfile,
    ) -> InteractionEvaluation:
        crop_candidate = crop.candidate
        algae_candidate = algae.candidate
        microbial_candidate = microbial.candidate

        crop_algae_synergy = (
            (crop_candidate.closed_loop_score)
            + (algae_candidate.oxygen_contribution / 100)
            + (algae_candidate.co2_utilization / 100)
        ) / 3
        crop_microbial_synergy = (
            (crop_candidate.waste_recycling_synergy / 100)
            + (microbial_candidate.nutrient_conversion_capability / 100)
            + (microbial_candidate.loop_closure_contribution / 100)
        ) / 3
        algae_microbial_synergy = (
            (algae_candidate.water_system_compatibility / 100)
            + (microbial_candidate.waste_recycling_efficiency / 100)
            + (microbial_candidate.loop_closure_contribution / 100)
        ) / 3
        synergy = (crop_algae_synergy + crop_microbial_synergy + algae_microbial_synergy) / 3

        conflict = (
            (crop_candidate.risk / 100)
            + (algae_candidate.energy_light_dependency / 100)
            + (microbial_candidate.contamination_risk / 100)
        ) / 3
        complexity = (
            (grow_system.complexity / 100)
            + (algae_candidate.maintenance_complexity / 100)
            + (microbial_candidate.maintenance_burden / 100)
        ) / 3
        overlap = (
            (crop_candidate.water_need / 100)
            + (algae_candidate.energy_light_dependency / 100)
            + (microbial_candidate.reactor_dependency / 100)
        ) / 3
        loop_bonus = (
            crop_candidate.closed_loop_score
            + (algae_candidate.co2_utilization / 100)
            + (microbial_candidate.loop_closure_contribution / 100)
            + (grow_system.water_efficiency / 100)
        ) / 4

        notes: list[str] = []
        if algae_candidate.oxygen_contribution >= 80:
            notes.append("algae adds an oxygen buffer to the food loop")
        if microbial_candidate.nutrient_conversion_capability >= 85:
            notes.append("microbial conversion strengthens nutrient recovery for crops")
        if complexity >= 0.58:
            notes.append("combined loop increases operational complexity")
        if microbial_candidate.contamination_risk >= 40:
            notes.append("contamination propagation remains a watch item")

        if mission.environment is Environment.MARS:
            synergy += 0.04
            loop_bonus += 0.06
            notes.append("Mars weighting rewards robust loop closure")
        elif mission.environment is Environment.MOON:
            loop_bonus += 0.08
            overlap += 0.03
            notes.append("Moon weighting emphasizes water-coupled closure")
        elif mission.environment is Environment.ISS:
            complexity += 0.06
            conflict += 0.03
            notes.append("ISS weighting penalizes crew-facing maintenance complexity")

        return InteractionEvaluation(
            synergy_score=round(min(synergy, 1.0), 3),
            conflict_score=round(min(conflict, 1.0), 3),
            complexity_penalty=round(min(complexity, 1.0), 3),
            resource_overlap=round(min(overlap, 1.0), 3),
            loop_closure_bonus=round(min(loop_bonus, 1.0), 3),
            notes=notes[:5],
        )
