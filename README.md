# Adaptive Closed-Loop Space Agriculture AI

Hackathon MVP that combines a FastAPI mission-planning engine with a React mission-control dashboard. The backend handles crop ranking, system selection, resource planning, risk analysis, and simulated adaptation. The frontend turns those results into a live demo UI.

## Project Layout

```text
C:\Users\VICTUS\ASTRO
|- app
|- data
|- tests
|- frontend
|- requirements.txt
`- README.md
```

## Backend Setup

```powershell
cd C:\Users\VICTUS\ASTRO
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run The Demo

Start the backend:

```powershell
cd C:\Users\VICTUS\ASTRO
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend in a second terminal:

```powershell
cd C:\Users\VICTUS\ASTRO\frontend
npm install
npm run dev
```

Open:

- `http://localhost:5173`
- `http://localhost:8000/docs`

Optional frontend API override:

```powershell
$env:VITE_API_BASE_URL="http://localhost:8000"
npm run dev
```

## API Endpoints

- `GET /health`
- `GET /demo-cases`
- `POST /recommend`
- `POST /simulate`

## Sample Requests

Recommend:

```powershell
curl.exe -X POST http://localhost:8000/recommend `
  -H "Content-Type: application/json" `
  -d "{\"environment\":\"mars\",\"duration\":\"long\",\"constraints\":{\"water\":\"low\",\"energy\":\"medium\",\"area\":\"medium\"},\"goal\":\"balanced\"}"
```

Simulate:

```powershell
curl.exe -X POST http://localhost:8000/simulate `
  -H "Content-Type: application/json" `
  -d "{\"mission_profile\":{\"environment\":\"mars\",\"duration\":\"long\",\"constraints\":{\"water\":\"low\",\"energy\":\"medium\",\"area\":\"medium\"},\"goal\":\"balanced\"},\"change_event\":\"water_drop\"}"
```

## Demo Flow

1. Start the backend on port `8000`.
2. Start the frontend on port `5173`.
3. In the dashboard, select the mission profile and click `Generate Plan`.
4. Trigger `Water`, `Energy`, or `Yield` crisis simulation to show the adaptive re-ranking.

## Tests

Backend tests:

```powershell
cd C:\Users\VICTUS\ASTRO
pytest
```

Frontend build check:

```powershell
cd C:\Users\VICTUS\ASTRO\frontend
npm run build
```

## Notes

- No external AI APIs are used.
- Data is JSON-backed for hackathon speed.
- The frontend consumes the real backend responses; no mock runtime data is used in the integrated demo flow.
