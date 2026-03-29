from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.data_provider import JSONDataProvider


client = TestClient(app)


def test_recommend_returns_top_three_sorted_with_ui_fields(monkeypatch) -> None:
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    payload = {
        "environment": "mars",
        "duration": "long",
        "constraints": {
            "water": "low",
            "energy": "medium",
            "area": "medium",
        },
        "goal": "balanced",
    }

    response = client.post("/recommend", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["mission_profile"] == payload
    assert data["recommended_system"] in {"hydroponic", "aeroponic", "hybrid"}
    assert data["system_reason"]
    assert data["system_reasoning"]
    assert data["why_this_system"]
    assert data["tradeoff_summary"]
    assert data["mission_status"] in {"NOMINAL", "WATCH", "CRITICAL"}
    assert data["executive_summary"]
    assert data["operational_note"]
    assert data["ui_enhanced"]["crop_note"]
    assert data["ui_enhanced"]["algae_note"]
    assert data["ui_enhanced"]["microbial_note"]
    assert data["ranked_candidates"]["crop"]
    assert data["ranked_candidates"]["algae"]
    assert data["ranked_candidates"]["microbial"]
    assert data["ranked_candidates"]["crop"][0]["rank"] == 1
    assert len(data["top_crops"]) == 5
    assert data["top_crops"][0]["score"] >= data["top_crops"][1]["score"] >= data["top_crops"][2]["score"]
    assert data["top_crops"][2]["score"] >= data["top_crops"][3]["score"] >= data["top_crops"][4]["score"]
    assert all(item["reason"] for item in data["top_crops"])
    assert all(len(item["strengths"]) == 2 for item in data["top_crops"])
    assert all(len(item["tradeoffs"]) == 1 for item in data["top_crops"])
    assert all("metric_breakdown" in item for item in data["top_crops"])
    assert all("compatibility_score" in item for item in data["top_crops"])
    assert "water_score" in data["resource_plan"]
    assert "score" in data["risk_analysis"]
    assert data["explanation"]


def test_simulate_returns_ranking_diff_and_risk_delta(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    payload = {
        "mission_profile": {
            "environment": "mars",
            "duration": "long",
            "constraints": {
                "water": "medium",
                "energy": "medium",
                "area": "medium",
            },
            "goal": "balanced",
        },
        "change_event": "water_drop",
    }

    response = client.post("/simulate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["updated_mission_profile"]["constraints"]["water"] == "high"
    assert data["changed_fields"][0] == "constraints.water"
    assert isinstance(data["ranking_diff"], dict)
    assert data["risk_delta"] in {"increased", "decreased", "unchanged"}
    assert isinstance(data["risk_score_delta"], float)
    assert data["previous_mission_status"] in {"NOMINAL", "WATCH", "CRITICAL"}
    assert data["new_mission_status"] in {"NOMINAL", "WATCH", "CRITICAL"}
    assert data["previous_top_crop"]
    assert data["new_top_crop"]
    assert len(data["updated_recommendation"]["top_crops"]) == 5
    assert data["updated_recommendation"]["executive_summary"]
    assert data["updated_recommendation"]["ui_enhanced"]["adaptation_summary"]
    assert data["updated_recommendation"]["ranked_candidates"]["algae"]
    assert data["adaptation_summary"]
    assert "water" in data["adaptation_summary"].lower()
    assert "risk" in data["adaptation_summary"].lower()
    assert data["reason"] == data["adaptation_summary"]
    assert data["adaptation_reason"] == data["adaptation_summary"]
    assert not data["updated_recommendation"]["llm_analysis"]["reasoning_summary"].endswith(" -gemini")


def test_simulate_yield_drop_with_affected_crop_returns_clear_diff(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    mission = {
        "environment": "moon",
        "duration": "long",
        "constraints": {
            "water": "medium",
            "energy": "medium",
            "area": "medium",
        },
        "goal": "balanced",
    }
    baseline = client.post("/recommend", json=mission)
    assert baseline.status_code == 200
    top_crop = baseline.json()["top_crops"][0]["name"]

    payload = {
        "mission_profile": {
            **mission,
        },
        "change_event": "yield_drop",
        "affected_crop": top_crop,
    }

    response = client.post("/simulate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "top_crops" in data["changed_fields"]
    assert top_crop in data["ranking_diff"]
    assert top_crop.title() in data["adaptation_summary"]
    assert data["previous_top_crop"] == top_crop
    assert data["new_top_crop"] != top_crop
    assert data["updated_recommendation"]["top_crops"]
    assert data["updated_recommendation"]["mission_status"] in {"NOMINAL", "WATCH", "CRITICAL"}


def test_openapi_and_requirements_have_no_external_ai_runtime_dependency(monkeypatch) -> None:
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = client.post(
        "/recommend",
        json={
            "environment": "iss",
            "duration": "medium",
            "constraints": {
                "water": "medium",
                "energy": "medium",
                "area": "medium",
            },
            "goal": "balanced",
        },
    )

    assert response.status_code == 200
    assert "/optimize_agriculture" not in app.openapi()["paths"]

    requirements_text = (Path(__file__).resolve().parents[1] / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "openai" not in requirements_text
    assert "anthropic" not in requirements_text


def test_recommend_returns_stateful_multidomain_payload(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = client.post(
        "/recommend",
        json={
            "environment": "mars",
            "duration": "long",
            "constraints": {
                "water": "medium",
                "energy": "medium",
                "area": "medium",
            },
            "goal": "balanced",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mission_state"]["mission_id"]
    assert data["mission_state"]["active_system"]["crops"][0]["type"] == "crop"
    assert data["mission_state"]["active_system"]["algae"][0]["type"] == "algae"
    assert data["mission_state"]["active_system"]["microbial"][0]["type"] == "microbial"
    assert data["selected_system"]["crop"]["support_system"] == data["recommended_system"]
    assert data["ranked_candidates"]["crop"][0]["type"] == "crop"
    assert data["ranked_candidates"]["algae"][0]["type"] == "algae"
    assert data["ranked_candidates"]["microbial"][0]["type"] == "microbial"
    assert "crop" in data["scores"]["domain"]
    assert "interaction" in data["scores"]
    assert data["explanations"]["executive_summary"] == data["executive_summary"]
    assert data["llm_analysis"]["reasoning_summary"]
    assert isinstance(data["llm_analysis"]["weaknesses"], list)
    assert "second_pass" in data["llm_analysis"]
    assert data["ui_enhanced"]["executive_summary"]
    assert "crop_note" in data["ui_enhanced"]


def test_initial_risk_is_fairly_calibrated_by_constraints_and_duration(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    low_response = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "moon",
                "duration": "short",
                "constraints": {
                    "water": "low",
                    "energy": "low",
                    "area": "low",
                },
                "goal": "balanced",
            },
            "selected_crop": "Lactuca sativa (Marul)",
            "selected_algae": "Chlorella vulgaris",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )
    assert low_response.status_code == 200
    low_data = low_response.json()

    medium_response = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "mars",
                "duration": "medium",
                "constraints": {
                    "water": "medium",
                    "energy": "medium",
                    "area": "medium",
                },
                "goal": "balanced",
            },
            "selected_crop": "Lactuca sativa (Marul)",
            "selected_algae": "Chlorella vulgaris",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )
    assert medium_response.status_code == 200
    medium_data = medium_response.json()

    high_response = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "mars",
                "duration": "long",
                "constraints": {
                    "water": "high",
                    "energy": "high",
                    "area": "high",
                },
                    "goal": "balanced",
                },
            "selected_crop": "Triticum aestivum (Cuce Bugday)",
            "selected_algae": "Dunaliella salina",
            "selected_microbial": "Methylobacterium extorquens",
        },
    )
    assert high_response.status_code == 200
    high_data = high_response.json()

    low_risk = low_data["mission_state"]["system_metrics"]["risk_level"] / 100
    medium_risk = medium_data["mission_state"]["system_metrics"]["risk_level"] / 100
    high_risk = high_data["mission_state"]["system_metrics"]["risk_level"] / 100

    assert 0.10 <= low_risk <= 0.25
    assert 0.25 <= medium_risk <= 0.45
    assert 0.44 <= high_risk <= 0.65
    assert low_risk < medium_risk < high_risk


def test_simulation_duration_maps_to_weekly_horizon(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    for duration, expected_weeks in {
        "short": 12,
        "medium": 24,
        "long": 48,
    }.items():
        response = client.post(
            "/simulation/start",
            json={
                "mission_profile": {
                    "environment": "moon",
                    "duration": duration,
                    "constraints": {
                        "water": "medium",
                        "energy": "medium",
                        "area": "medium",
                    },
                    "goal": "balanced",
                },
                "selected_crop": "Lactuca sativa (Marul)",
                "selected_algae": "Chlorella vulgaris",
                "selected_microbial": "Saccharomyces boulardii",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mission_state"]["max_weeks"] == expected_weeks


def test_simulation_start_initializes_water_recovery_profile(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "moon",
                "duration": "medium",
                "constraints": {
                    "water": "medium",
                    "energy": "medium",
                    "area": "medium",
                },
                "goal": "balanced",
            },
            "selected_crop": "Lactuca sativa (Marul)",
            "selected_algae": "Chlorella vulgaris",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )

    assert response.status_code == 200
    state = response.json()["mission_state"]
    assert state["water_recovery_queue"] == []
    assert state["water_recovery_cycle_weeks"] >= 4
    assert 0.45 <= state["water_recovery_rate"] <= 0.72
    assert state["last_recovered_water"] == 0


def test_water_recovery_returns_after_cycle_delay(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    bootstrap = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "moon",
                "duration": "medium",
                "constraints": {
                    "water": "medium",
                    "energy": "medium",
                    "area": "medium",
                },
                "goal": "balanced",
            },
            "selected_crop": "Lactuca sativa (Marul)",
            "selected_algae": "Chlorella vulgaris",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )
    assert bootstrap.status_code == 200
    bootstrap_data = bootstrap.json()
    mission_id = bootstrap_data["mission_state"]["mission_id"]

    cycle_weeks = bootstrap_data["mission_state"]["water_recovery_cycle_weeks"]
    latest = None
    for _ in range(cycle_weeks + 1):
        response = client.post(
            "/mission/step",
            json={
                "mission_id": mission_id,
                "time_step": 1,
            },
        )
        assert response.status_code == 200
        latest = response.json()

    assert latest is not None
    assert latest["mission_state"]["last_consumed_water"] > 0
    assert latest["mission_state"]["last_recovered_water"] > 0
    assert latest["adaptation_summary"].lower().count("water recovery") >= 1


def test_photosynthesis_drives_weekly_energy_production(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    provider = JSONDataProvider()
    crop = next(item for item in provider.get_crops() if item.name == "Lactuca sativa (Marul)")
    algae = next(item for item in provider.get_algae_systems() if item.name == "Chlorella vulgaris")
    microbial = next(item for item in provider.get_microbial_systems() if item.name == "Saccharomyces boulardii")
    assert crop.has_photosynthesis is True
    assert algae.has_photosynthesis is True
    assert microbial.has_photosynthesis is False

    bootstrap = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "moon",
                "duration": "medium",
                "constraints": {
                    "water": "medium",
                    "energy": "medium",
                    "area": "medium",
                },
                "goal": "balanced",
            },
            "selected_crop": crop.name,
            "selected_algae": algae.name,
            "selected_microbial": microbial.name,
        },
    )
    assert bootstrap.status_code == 200
    bootstrap_data = bootstrap.json()
    initial_energy = bootstrap_data["mission_state"]["resources"]["energy"]

    response = client.post(
        "/mission/step",
        json={
            "mission_id": bootstrap_data["mission_state"]["mission_id"],
            "time_step": 1,
        },
    )
    assert response.status_code == 200
    data = response.json()
    state = data["mission_state"]

    assert state["last_consumed_energy"] > 0
    assert state["last_solar_energy"] > 0
    assert state["last_photosynthesis_energy"] > 0

    expected_energy = round(
        max(
            0,
            min(
                100,
                initial_energy
                - state["last_consumed_energy"]
                + state["last_solar_energy"]
                + state["last_photosynthesis_energy"],
            ),
        ),
        2,
    )
    assert state["resources"]["energy"] == expected_energy


def test_stronger_stack_recovers_water_more_efficiently_than_weaker_stack(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    strong = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "moon",
                "duration": "medium",
                "constraints": {
                    "water": "low",
                    "energy": "low",
                    "area": "low",
                },
                "goal": "balanced",
            },
            "selected_crop": "Lactuca sativa (Marul)",
            "selected_algae": "Chlorella vulgaris",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )
    weak = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "moon",
                "duration": "medium",
                "constraints": {
                    "water": "low",
                    "energy": "low",
                    "area": "low",
                },
                "goal": "balanced",
            },
            "selected_crop": "Lactuca sativa (Marul)",
            "selected_algae": "Dunaliella salina",
            "selected_microbial": "Methylobacterium extorquens",
        },
    )

    assert strong.status_code == 200
    assert weak.status_code == 200
    assert strong.json()["mission_state"]["water_recovery_rate"] > weak.json()["mission_state"]["water_recovery_rate"]


def test_strong_low_constraint_system_survives_past_week_20_on_medium_and_long_horizons(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    for duration in ("medium", "long"):
        bootstrap = client.post(
            "/simulation/start",
            json={
                "mission_profile": {
                    "environment": "moon",
                    "duration": duration,
                    "constraints": {
                        "water": "low",
                        "energy": "low",
                        "area": "low",
                    },
                    "goal": "balanced",
                },
                "selected_crop": "Lactuca sativa (Marul)",
                "selected_algae": "Chlorella vulgaris",
                "selected_microbial": "Saccharomyces boulardii",
            },
        )

        assert bootstrap.status_code == 200
        mission_id = bootstrap.json()["mission_state"]["mission_id"]

        latest = None
        for _ in range(20):
            response = client.post(
                "/mission/step",
                json={
                    "mission_id": mission_id,
                    "time_step": 1,
                },
            )
            assert response.status_code == 200
            latest = response.json()

        assert latest is not None
        assert latest["mission_state"]["time"] == 20
        assert latest["mission_state"]["end_reason"] is None
        assert latest["mission_state"]["resources"]["energy"] > 0
        assert latest["mission_state"]["system_metrics"]["risk_level"] < 85


def test_simulation_start_bootstraps_selected_stack(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    baseline = client.post(
        "/recommend",
        json={
            "environment": "mars",
            "duration": "long",
            "constraints": {
                "water": "medium",
                "energy": "medium",
                "area": "medium",
            },
            "goal": "balanced",
        },
    )
    assert baseline.status_code == 200
    baseline_data = baseline.json()

    response = client.post(
        "/simulation/start",
        json={
            "mission_profile": baseline_data["mission_profile"],
            "selected_crop": baseline_data["selected_system"]["crop"]["name"],
            "selected_algae": baseline_data["selected_system"]["algae"]["name"],
            "selected_microbial": baseline_data["selected_system"]["microbial"]["name"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mission_state"]["mission_id"]
    assert data["selected_system"]["crop"]["name"] == baseline_data["selected_system"]["crop"]["name"]
    assert data["selected_system"]["algae"]["name"] == baseline_data["selected_system"]["algae"]["name"]
    assert data["selected_system"]["microbial"]["name"] == baseline_data["selected_system"]["microbial"]["name"]
    assert data["ranked_candidates"]["crop"]
    assert data["scores"]["integrated"] >= 0
    assert data["mission_status"] in {"NOMINAL", "WATCH", "CRITICAL"}
    assert data["operational_note"]
    assert data["ui_enhanced"]["executive_summary"]
    assert data["mission_state"]["max_weeks"] == 48
    assert data["mission_state"]["initial_risk_level"] == data["mission_state"]["system_metrics"]["risk_level"]
    assert not data["llm_analysis"]["reasoning_summary"].endswith(" -gemini")


def test_simulation_start_rejects_invalid_selected_names(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "mars",
                "duration": "long",
                "constraints": {
                    "water": "medium",
                    "energy": "medium",
                    "area": "medium",
                },
                "goal": "balanced",
            },
            "selected_crop": "not-a-real-crop",
            "selected_algae": "Chlorella vulgaris",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid input"


def test_mission_step_updates_stored_state(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    baseline = client.post(
        "/recommend",
        json={
            "environment": "moon",
            "duration": "medium",
            "constraints": {
                "water": "medium",
                "energy": "medium",
                "area": "medium",
            },
            "goal": "balanced",
        },
    )
    assert baseline.status_code == 200
    mission_state = baseline.json()["mission_state"]

    response = client.post(
        "/mission/step",
        json={
            "mission_id": mission_state["mission_id"],
            "time_step": 3,
            "events": {
                "water_drop": 18,
                "yield_variation": -20,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mission_state"]["mission_id"] == mission_state["mission_id"]
    assert data["mission_state"]["max_weeks"] == mission_state["max_weeks"]
    assert data["mission_state"]["time"] == mission_state["time"] + 3
    assert data["mission_state"]["resources"]["water"] < mission_state["resources"]["water"]
    assert data["mission_state"]["resources"]["energy"] < mission_state["resources"]["energy"]
    assert len(data["mission_state"]["history"]) >= 2
    assert data["adaptation_summary"]
    assert data["adaptation_summary"].startswith("Week 3:")
    assert "water drop" in data["adaptation_summary"].lower()
    assert "risk" in data["adaptation_summary"].lower()
    assert data["ui_enhanced"]["adaptation_summary"]
    assert data["ranked_candidates"]["crop"]
    assert isinstance(data["system_changes"], list)
    assert isinstance(data["risk_delta"], float)
    assert not data["llm_analysis"]["reasoning_summary"].endswith(" -gemini")


def test_mission_step_metrics_evolve_gradually_and_remain_clamped(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    bootstrap = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "moon",
                "duration": "medium",
                "constraints": {
                    "water": "medium",
                    "energy": "medium",
                    "area": "medium",
                },
                "goal": "balanced",
            },
            "selected_crop": "Lactuca sativa (Marul)",
            "selected_algae": "Chlorella vulgaris",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )
    assert bootstrap.status_code == 200
    bootstrap_data = bootstrap.json()
    mission_id = bootstrap_data["mission_state"]["mission_id"]
    initial_metrics = bootstrap_data["mission_state"]["system_metrics"]

    step_one = client.post(
        "/mission/step",
        json={
            "mission_id": mission_id,
            "time_step": 1,
        },
    )
    assert step_one.status_code == 200
    step_one_metrics = step_one.json()["mission_state"]["system_metrics"]

    step_two = client.post(
        "/mission/step",
        json={
            "mission_id": mission_id,
            "time_step": 1,
        },
    )
    assert step_two.status_code == 200
    step_two_metrics = step_two.json()["mission_state"]["system_metrics"]

    tracked_metrics = (
        "oxygen_level",
        "co2_balance",
        "food_supply",
        "nutrient_cycle_efficiency",
    )
    for metric_name in tracked_metrics:
        assert 0 <= step_one_metrics[metric_name] <= 100
        assert 0 <= step_two_metrics[metric_name] <= 100
        assert abs(step_one_metrics[metric_name] - initial_metrics[metric_name]) < 20
        assert abs(step_two_metrics[metric_name] - step_one_metrics[metric_name]) < 20

    assert step_one_metrics["oxygen_level"] != step_one_metrics["risk_level"]
    assert step_one_metrics["food_supply"] != step_one_metrics["risk_level"]
    assert len({round(step_two_metrics[name], 2) for name in tracked_metrics}) > 1


def test_mission_step_metrics_respond_to_stress_without_becoming_risk_copies(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    bootstrap = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "mars",
                "duration": "medium",
                "constraints": {
                    "water": "medium",
                    "energy": "medium",
                    "area": "medium",
                },
                "goal": "balanced",
            },
            "selected_crop": "Solanum lycopersicum (Dwarf Domates)",
            "selected_algae": "Chlorella vulgaris",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )
    assert bootstrap.status_code == 200
    bootstrap_data = bootstrap.json()
    mission_id = bootstrap_data["mission_state"]["mission_id"]
    initial_metrics = bootstrap_data["mission_state"]["system_metrics"]

    stressed = client.post(
        "/mission/step",
        json={
            "mission_id": mission_id,
            "time_step": 1,
            "events": {
                "water_drop": 14,
                "contamination": 10,
            },
        },
    )
    assert stressed.status_code == 200
    stressed_metrics = stressed.json()["mission_state"]["system_metrics"]

    assert stressed_metrics["risk_level"] != initial_metrics["risk_level"]
    assert stressed_metrics["oxygen_level"] < initial_metrics["oxygen_level"]
    assert stressed_metrics["nutrient_cycle_efficiency"] < initial_metrics["nutrient_cycle_efficiency"]
    assert stressed_metrics["co2_balance"] != stressed_metrics["risk_level"]
    assert stressed_metrics["food_supply"] != stressed_metrics["risk_level"]


def test_mission_step_works_after_simulation_start(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    bootstrap = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "moon",
                "duration": "medium",
                "constraints": {
                    "water": "medium",
                    "energy": "medium",
                    "area": "medium",
                },
                "goal": "balanced",
            },
            "selected_crop": "Lactuca sativa (Marul)",
            "selected_algae": "Arthrospira platensis (Spirulina)",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )
    assert bootstrap.status_code == 200
    mission_id = bootstrap.json()["mission_state"]["mission_id"]

    response = client.post(
        "/mission/step",
        json={
            "mission_id": mission_id,
            "time_step": 2,
            "events": {
                "water_drop": 10,
                "contamination": 15,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mission_state"]["mission_id"] == mission_id
    assert data["mission_state"]["time"] == 2
    assert data["adaptation_summary"].startswith("Week 2:")
    assert data["mission_status"] in {"NOMINAL", "WATCH", "CRITICAL"}
    assert data["operational_note"]
    assert data["adaptation_summary"]
    assert data["mission_state"]["max_weeks"] == 24


def test_mission_step_applies_weekly_baseline_drain_without_explicit_events(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    bootstrap = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "moon",
                "duration": "medium",
                "constraints": {
                    "water": "medium",
                    "energy": "medium",
                    "area": "medium",
                },
                "goal": "balanced",
            },
            "selected_crop": "Lactuca sativa (Marul)",
            "selected_algae": "Chlorella vulgaris",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )
    assert bootstrap.status_code == 200
    bootstrap_data = bootstrap.json()

    response = client.post(
        "/mission/step",
        json={
            "mission_id": bootstrap_data["mission_state"]["mission_id"],
            "time_step": 1,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mission_state"]["time"] == 1
    assert data["mission_state"]["resources"]["water"] < bootstrap_data["mission_state"]["resources"]["water"]
    assert data["mission_state"]["resources"]["energy"] < bootstrap_data["mission_state"]["resources"]["energy"]
    assert data["adaptation_summary"].startswith("Week 1:")


def test_mission_step_risk_accumulates_across_weeks(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    bootstrap = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "mars",
                "duration": "medium",
                "constraints": {
                    "water": "medium",
                    "energy": "medium",
                    "area": "medium",
                },
                "goal": "balanced",
            },
            "selected_crop": "Lactuca sativa (Marul)",
            "selected_algae": "Chlorella vulgaris",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )
    assert bootstrap.status_code == 200
    bootstrap_data = bootstrap.json()
    mission_id = bootstrap_data["mission_state"]["mission_id"]
    initial_risk = bootstrap_data["mission_state"]["system_metrics"]["risk_level"]

    stressed = client.post(
        "/mission/step",
        json={
            "mission_id": mission_id,
            "time_step": 1,
            "events": {
                "water_drop": 15,
                "contamination": 20,
            },
        },
    )
    assert stressed.status_code == 200
    stressed_data = stressed.json()

    recovered = client.post(
        "/mission/step",
        json={
            "mission_id": mission_id,
            "time_step": 1,
        },
    )
    assert recovered.status_code == 200
    recovered_data = recovered.json()

    assert stressed_data["mission_state"]["system_metrics"]["risk_level"] > initial_risk
    assert recovered_data["mission_state"]["system_metrics"]["risk_level"] >= 0
    assert recovered_data["mission_state"]["system_metrics"]["risk_level"] <= 100
    assert recovered_data["mission_state"]["system_metrics"]["risk_level"] != initial_risk


def test_recommendation_data_balance_varies_top_crop_by_mission_profile(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    missions = {
        "mars_balanced": {
            "environment": "mars",
            "duration": "long",
            "constraints": {
                "water": "medium",
                "energy": "medium",
                "area": "medium",
            },
            "goal": "balanced",
        },
        "iss_low_maintenance": {
            "environment": "iss",
            "duration": "short",
            "constraints": {
                "water": "low",
                "energy": "low",
                "area": "low",
            },
            "goal": "low_maintenance",
        },
        "mars_calorie": {
            "environment": "mars",
            "duration": "medium",
            "constraints": {
                "water": "low",
                "energy": "medium",
                "area": "medium",
            },
            "goal": "calorie_max",
        },
    }

    outputs = {
        label: client.post("/recommend", json=payload).json()["top_crops"][0]["name"]
        for label, payload in missions.items()
    }

    assert outputs["mars_balanced"] == "Solanum lycopersicum (Dwarf Domates)"
    assert outputs["iss_low_maintenance"] == "Lactuca sativa (Marul)"
    assert outputs["mars_calorie"] == "Triticum aestivum (Cuce Bugday)"
    assert len(set(outputs.values())) == 3
