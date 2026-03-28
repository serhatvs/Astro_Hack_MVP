# Adaptive Closed-Loop Space Agriculture AI

Integrated hackathon MVP for mission-aware space agriculture planning.

- The FastAPI backend is the decision engine.
- The React + Vite frontend in `frontend/` is the Terra Vision dashboard UI.

## Overview

The backend evaluates mission environment, duration, resource constraints, and optimization goals to recommend:

- top 3 crop candidates
- a primary growing system
- a resource posture
- mission agriculture risk
- a deterministic explanation

The frontend consumes those APIs and presents the results in a mission-control dashboard with crisis simulation.

## Architecture

Backend APIs:

- `GET /health`
- `GET /demo-cases`
- `POST /recommend`
- `POST /simulate`

Frontend:

- reads mission input from the dashboard
- calls the backend APIs
- renders recommendations, reasoning, resources, risk, and adaptation updates

## Project Structure

```text
.
├── app/
├── data/
├── tests/
├── frontend/
├── requirements.txt
└── README.md
```

## Setup

Backend:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Frontend expects the backend at `http://localhost:8000`.

## Demo Flow

1. Open the frontend dashboard.
2. Load a demo scenario or set mission inputs manually.
3. Generate a recommendation.
4. Simulate a crisis.
5. Observe crop ranking, system, risk, and explanation updates.

## API Summary

- `GET /health` checks service availability.
- `GET /demo-cases` returns preset mission scenarios.
- `POST /recommend` returns the mission recommendation package.
- `POST /simulate` returns the adapted recommendation after a crisis event.

## Example Requests

Recommend:

```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "environment": "mars",
    "duration": "long",
    "constraints": {
      "water": "low",
      "energy": "medium",
      "area": "medium"
    },
    "goal": "balanced"
  }'
```

Simulate:

```bash
curl -X POST http://localhost:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{
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
    "change_event": "water_drop"
  }'
```

## Validation

Backend tests:

```bash
pytest
```

Frontend build:

```bash
cd frontend
npm run build
```
