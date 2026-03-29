import type {
  DemoCase,
  HealthResponse,
  MissionStepPayload,
  MissionStepResponse,
  MissionPayload,
  RecommendationResponse,
  SimulationStartPayload,
  SimulationStartResponse,
} from "@/lib/types";

const BASE_URL =
  import.meta.env.VITE_API_URL?.trim() ||
  import.meta.env.VITE_API_BASE_URL?.trim() ||
  "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const errorBody = await response.json();
      message = errorBody.detail || errorBody.message || message;
    } catch {
      const fallbackMessage = await response.text();
      if (fallbackMessage) {
        message = fallbackMessage;
      }
    }

    throw new Error(message);
  }

  return (await response.json()) as T;
}

export function recommendMission(payload: MissionPayload): Promise<RecommendationResponse> {
  return request<RecommendationResponse>("/recommend", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function startSimulation(payload: SimulationStartPayload): Promise<SimulationStartResponse> {
  return request<SimulationStartResponse>("/simulation/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function stepMission(payload: MissionStepPayload): Promise<MissionStepResponse> {
  return request<MissionStepResponse>("/mission/step", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchDemoCases(): Promise<DemoCase[]> {
  return request<DemoCase[]>("/demo-cases");
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export { BASE_URL };
