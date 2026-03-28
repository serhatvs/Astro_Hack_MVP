# Adaptive Closed-Loop Space Agriculture AI

Hackathon-ready FastAPI backend for mission-aware crop planning in closed-loop space agriculture scenarios. The MVP acts as an intelligent planning and adaptation engine, not a hardware controller.

## Why This Matters

Long-duration space missions need food production systems that balance calories, water, energy, operational complexity, and resilience. This project demonstrates how a lightweight AI planning engine can help mission teams compare crop portfolios and growing methods under different mission constraints.

## Concept Summary

The backend combines:

- rule-based filtering for interpretability
- dynamic weighted scoring for mission-aware optimization
- deterministic explanations for transparent recommendations

The current MVP focuses on mission planning and also includes a scaffolded, functional runtime adaptation endpoint for simulated mission changes.

## Architecture

```text
apps/space_agri_ai/
├── app/
│   ├── main.py
│   ├── routes/
│   ├── core/
│   ├── models/
│   ├── services/
│   └── utils/
├── data/
│   ├── crops.json
│   └── systems.json
├── tests/
├── requirements.txt
├── README.md
└── .gitignore
```

### Main Layers

- `app/routes`: thin FastAPI endpoints
- `app/services`: orchestration, explanation, resource planning, provider abstraction
- `app/core`: normalization, weights, scoring, rule filters, risk analysis
- `app/models`: Pydantic request/response/data models
- `data`: JSON datasets designed to be replaceable by a SQL-backed provider later

## Recommendation Logic

### Inputs

- environment: `mars`, `moon`, `iss`
- duration: `short`, `medium`, `long`
- constraints: `water`, `energy`, `area` each using `low`, `medium`, `high`
- goal: `balanced`, `calorie_max`, `water_efficiency`, `low_maintenance`

### Scoring

1. The engine ranks growing systems first.
2. It then filters crops by system compatibility.
3. Compatible crops are scored with normalized multi-objective weighting.
4. Small rule-based bonuses and penalties improve interpretability.
5. The API returns the top 3 crops, a resource plan, risk summary, and explanation.

## Setup

### Requirements

- Python 3.11+

### Install

```bash
cd apps/space_agri_ai
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
cd apps/space_agri_ai
uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
```

Open the docs at:

- `http://localhost:8010/docs`
- `http://localhost:8010/redoc`

## API Endpoints

### `GET /health`

Simple health check for demos and tests.

### `POST /recommend`

Main mission-planning endpoint.

Example request:

```json
{
  "environment": "mars",
  "duration": "long",
  "constraints": {
    "water": "low",
    "energy": "medium",
    "area": "medium"
  },
  "goal": "balanced"
}
```

Example response:

```json
{
  "mission_profile": {
    "environment": "mars",
    "duration": "long",
    "constraints": {
      "water": "low",
      "energy": "medium",
      "area": "medium"
    },
    "goal": "balanced"
  },
  "top_crops": [
    {
      "name": "spirulina",
      "score": 1.0,
      "reason": "Strong water efficiency supports tight water budgets.",
      "selected_system": "aeroponic"
    },
    {
      "name": "lettuce",
      "score": 0.69,
      "reason": "Strong water efficiency supports tight water budgets.",
      "selected_system": "aeroponic"
    },
    {
      "name": "spinach",
      "score": 0.59,
      "reason": "Lower operational risk improves continuous food production reliability.",
      "selected_system": "aeroponic"
    }
  ],
  "recommended_system": "aeroponic",
  "resource_plan": {
    "water_level": "optimized-low",
    "energy_level": "moderate",
    "area_usage": "compact"
  },
  "risk_analysis": {
    "level": "moderate",
    "factors": [
      "water scarcity paired with system complexity"
    ]
  },
  "explanation": "For a long-duration Mars mission shaped by water scarcity, the engine selected aeroponic as the primary growing method and ranked spirulina first."
}
```

### `POST /simulate`

Lightweight runtime adaptation scaffold for mission updates.

Supported change events:

- `water_drop`
- `energy_drop`
- `yield_drop`

Example request:

```json
{
  "mission_profile": {
    "environment": "mars",
    "duration": "long",
    "constraints": {
      "water": "medium",
      "energy": "medium",
      "area": "medium"
    },
    "goal": "balanced"
  },
  "change_event": "water_drop"
}
```

Behavior:

- `water_drop`: reduces water availability one step and reruns recommendations
- `energy_drop`: reduces energy availability one step and reruns recommendations
- `yield_drop`: applies a temporary penalty to an affected crop or biases reranking toward faster, lower-risk crops

## Testing

Run the local test suite:

```bash
cd apps/space_agri_ai
pytest
```

Covered cases:

- health endpoint works
- recommend endpoint returns top 3
- simulation endpoint adapts mission input
- scoring stays normalized and ranked

## Future Improvements

- add a SQL-backed provider implementing the same `DataProvider` interface
- add persistent mission state and runtime event history
- add more crops, nutrient profiles, and crew-diet objectives
- add scenario presets and Monte Carlo style sensitivity testing
- add frontend dashboards and mission comparison views

