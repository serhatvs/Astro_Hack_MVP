# Adaptive Closed-Loop Space Agriculture AI

Hackathon-ready FastAPI MVP for mission-aware crop planning in closed-loop space agriculture and life-support scenarios. The service recommends crops, growing systems, resource posture, and mission risk, then shows how recommendations adapt when mission conditions change.

## Project Structure

```text
C:\Users\VICTUS\ASTRO
├── app
├── data
├── tests
├── requirements.txt
└── README.md
```

## Install

```powershell
cd C:\Users\VICTUS\ASTRO
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

```powershell
cd C:\Users\VICTUS\ASTRO
uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
```

Open:

- `http://127.0.0.1:8010/docs`
- `http://127.0.0.1:8010/redoc`

## Endpoints

- `GET /health`
- `GET /demo-cases`
- `POST /recommend`
- `POST /simulate`

## Demo Flow

1. Load a preset mission from `GET /demo-cases`
2. Send the mission to `POST /recommend`
3. Trigger a mission change with `POST /simulate`
4. Show how top crops, system choice, and risk change

## Sample Curl Requests

### Load Demo Cases

```powershell
curl.exe http://127.0.0.1:8010/demo-cases
```

### Recommend

```powershell
curl.exe -X POST http://127.0.0.1:8010/recommend `
  -H "Content-Type: application/json" `
  -d "{\"environment\":\"mars\",\"duration\":\"long\",\"constraints\":{\"water\":\"low\",\"energy\":\"medium\",\"area\":\"medium\"},\"goal\":\"water_efficiency\"}"
```

### Simulate Adaptation

```powershell
curl.exe -X POST http://127.0.0.1:8010/simulate `
  -H "Content-Type: application/json" `
  -d "{\"mission_profile\":{\"environment\":\"mars\",\"duration\":\"long\",\"constraints\":{\"water\":\"medium\",\"energy\":\"medium\",\"area\":\"medium\"},\"goal\":\"balanced\"},\"change_event\":\"water_drop\"}"
```

## What The MVP Shows

- mission-aware crop ranking with top 3 recommendations
- system selection with deterministic reasoning
- UI-friendly strengths, tradeoffs, and metric breakdowns
- resource posture summary for water, energy, area, maintenance, and calorie output
- lightweight adaptation logic for `water_drop`, `energy_drop`, and `yield_drop`

## Demo Presets

- `Mars Water Crisis`
- `ISS Low Maintenance Mission`
- `Moon Long Duration Calorie Mission`

## Testing

```powershell
cd C:\Users\VICTUS\ASTRO
pytest
```

## Notes

- No external AI APIs are used
- Data is JSON-backed for hackathon speed
- The closed-loop/life-support framing is lightweight and deterministic, not a full simulator
