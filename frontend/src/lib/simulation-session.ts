import type { MissionStepResponse, SimulationStartResponse } from "@/lib/types";

export type SimulationSession = MissionStepResponse | SimulationStartResponse;

interface StoredSimulationSession {
  current: SimulationSession;
  previous: SimulationSession | null;
}

const STORAGE_KEY = "astro-hack:simulation-session";

const hasSessionShape = (value: unknown): value is SimulationSession => {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return Boolean(candidate.mission_state && candidate.selected_system && candidate.ranked_candidates);
};

export const loadSimulationSession = (): StoredSimulationSession | null => {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw) as Partial<StoredSimulationSession>;
    if (!hasSessionShape(parsed.current)) {
      window.localStorage.removeItem(STORAGE_KEY);
      return null;
    }

    return {
      current: parsed.current,
      previous: hasSessionShape(parsed.previous) ? parsed.previous : null,
    };
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
};

export const saveSimulationSession = (
  current: SimulationSession,
  previous: SimulationSession | null = null,
): void => {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      current,
      previous,
    }),
  );
};

export const clearSimulationSession = (): void => {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(STORAGE_KEY);
};
