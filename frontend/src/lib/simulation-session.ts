import type { MissionStepResponse, SimulationStartResponse } from "@/lib/types";

export type SimulationSession = MissionStepResponse | SimulationStartResponse;

interface StoredSimulationSession {
  current: SimulationSession;
  previous: SimulationSession | null;
  initial: SimulationSession;
}

const STORAGE_KEY = "astro-hack:simulation-session";

const hasMissionStateShape = (value: unknown): value is SimulationSession["mission_state"] => {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.mission_id === "string" &&
    candidate.mission_id.trim().length > 0 &&
    typeof candidate.time === "number" &&
    typeof candidate.max_weeks === "number" &&
    candidate.resources !== null &&
    candidate.system_metrics !== null
  );
};

const hasSessionShape = (value: unknown): value is SimulationSession => {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return Boolean(
    hasMissionStateShape(candidate.mission_state) &&
      candidate.selected_system &&
      candidate.ranked_candidates,
  );
};

export const isSimulationSessionTerminal = (value: SimulationSession | null | undefined): boolean =>
  Boolean(
    value &&
      value.mission_state &&
      (value.mission_state.end_reason ||
        value.mission_state.time >= value.mission_state.max_weeks),
  );

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

    const initial = hasSessionShape(parsed.initial) ? parsed.initial : parsed.current;

    return {
      current: parsed.current,
      previous: hasSessionShape(parsed.previous) ? parsed.previous : null,
      initial,
    };
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
};

export const saveSimulationSession = (
  current: SimulationSession,
  previous: SimulationSession | null = null,
  initial?: SimulationSession | null,
): void => {
  if (typeof window === "undefined") {
    return;
  }

  const existing = loadSimulationSession();
  const resolvedInitial =
    (initial && hasSessionShape(initial) && initial) ||
    existing?.initial ||
    current;

  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      current,
      previous,
      initial: resolvedInitial,
    }),
  );
};

export const clearSimulationSession = (): void => {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(STORAGE_KEY);
};

export const loadActiveSimulationSession = (): StoredSimulationSession | null => {
  const stored = loadSimulationSession();
  if (!stored || isSimulationSessionTerminal(stored.current)) {
    return null;
  }
  return stored;
};
