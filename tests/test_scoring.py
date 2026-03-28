from app.core.scoring import score_crops, score_systems
from app.models.mission import (
    ConstraintLevel,
    Duration,
    Environment,
    Goal,
    MissionConstraints,
    MissionProfile,
)
from app.services.data_provider import JSONDataProvider
from app.services.recommender import RecommendationEngine


def test_scoring_produces_valid_normalized_ranking() -> None:
    provider = JSONDataProvider()
    crops = provider.get_crops()
    systems = provider.get_systems()
    mission = MissionProfile(
        environment=Environment.MARS,
        duration=Duration.LONG,
        constraints=MissionConstraints(
            water=ConstraintLevel.LOW,
            energy=ConstraintLevel.MEDIUM,
            area=ConstraintLevel.MEDIUM,
        ),
        goal=Goal.WATER_EFFICIENCY,
    )

    ranked_systems = score_systems(systems, mission)
    ranked_crops = score_crops(crops, mission, ranked_systems[0].system)

    assert ranked_systems
    assert ranked_crops
    assert all(0.0 <= item.score <= 1.0 for item in ranked_crops)
    assert ranked_crops == sorted(ranked_crops, key=lambda item: item.score, reverse=True)

    ranked_names = [item.crop.name for item in ranked_crops]
    assert ranked_names.index("spirulina") < ranked_names.index("potato")


def test_environment_influence_changes_recommendation_behavior() -> None:
    engine = RecommendationEngine(provider=JSONDataProvider())
    mars = engine.recommend(
        MissionProfile(
            environment=Environment.MARS,
            duration=Duration.MEDIUM,
            constraints=MissionConstraints(
                water=ConstraintLevel.MEDIUM,
                energy=ConstraintLevel.MEDIUM,
                area=ConstraintLevel.MEDIUM,
            ),
            goal=Goal.BALANCED,
        )
    )
    iss = engine.recommend(
        MissionProfile(
            environment=Environment.ISS,
            duration=Duration.MEDIUM,
            constraints=MissionConstraints(
                water=ConstraintLevel.MEDIUM,
                energy=ConstraintLevel.MEDIUM,
                area=ConstraintLevel.MEDIUM,
            ),
            goal=Goal.BALANCED,
        )
    )

    assert mars.recommended_system != iss.recommended_system
    assert mars.top_crops[0].name != iss.top_crops[0].name
