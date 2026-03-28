import type { RecommendationResponse, MissionPayload, SimulationPayload, SimulationResponse } from "@/lib/types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
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

export function simulateMission(payload: SimulationPayload): Promise<SimulationResponse> {
  return request<SimulationResponse>("/simulate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export { API_BASE_URL };
