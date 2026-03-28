# Terra Vision Frontend

React + Vite dashboard for the Adaptive Closed-Loop Space Agriculture AI hackathon MVP.

This frontend is the Terra Vision mission-control UI. It visualizes real recommendations from the FastAPI backend and supports runtime crisis simulation.

## Stack

- React
- Vite
- TypeScript
- Tailwind CSS
- shadcn/ui and Radix UI components
- Framer Motion
- Recharts
- Sonner

## Run

```bash
npm install
npm run dev
```

The backend should be running at:

- `http://localhost:8000`

If needed, set:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Main User Flows

1. Select mission parameters.
2. Generate a recommendation from the backend.
3. Display the top 3 crops with scores, strengths, tradeoffs, and metric breakdowns.
4. Show system, resource, and risk panels.
5. Simulate crisis updates for water, energy, or yield.

## Notes

- The dashboard uses real API calls now.
- Mock runtime flow has been removed.
- If the backend is unreachable, the UI shows an error state instead of fake data.
