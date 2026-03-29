import type {
  AuthPayload,
  AuthResponse,
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

const SESSION_STORAGE_KEY = "astro-hack-session-id";
const INVALID_INPUT_MESSAGE = "Invalid input";
const SIMULATION_NOT_INITIALIZED_MESSAGE = "Simulation not initialized";
const SIMULATION_ALREADY_ENDED_MESSAGE = "Simulation already ended";
const GENERIC_RETRY_MESSAGE = "Something went wrong, please retry";
const INVALID_CREDENTIALS_MESSAGE = "Invalid credentials";
const LOGIN_REQUIRED_MESSAGE = "Please log in to continue";
const SESSION_EXPIRED_MESSAGE = "Session expired";
const ACCOUNT_EXISTS_MESSAGE = "Account already exists";

type ApiErrorKind = "invalid_input" | "simulation_state" | "rate_limit" | "auth" | "generic";

export class ApiError extends Error {
  status: number;
  path: string;
  kind: ApiErrorKind;

  constructor(message: string, status: number, path: string, kind: ApiErrorKind) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.path = path;
    this.kind = kind;
  }
}

export const isApiError = (error: unknown): error is ApiError => error instanceof ApiError;

export const isSimulationStateError = (error: unknown): error is ApiError =>
  isApiError(error) && error.kind === "simulation_state";

const isSimulationPath = (path: string) => path.startsWith("/simulation") || path.startsWith("/mission");
const isAuthPath = (path: string) => path.startsWith("/auth");

const buildSafeApiError = (path: string, status: number, detail: string | null) => {
  if (status === 429 && detail) {
    return new ApiError(detail, status, path, "rate_limit");
  }
  if (
    isAuthPath(path) &&
    detail &&
    [
      INVALID_CREDENTIALS_MESSAGE,
      LOGIN_REQUIRED_MESSAGE,
      SESSION_EXPIRED_MESSAGE,
      ACCOUNT_EXISTS_MESSAGE,
      INVALID_INPUT_MESSAGE,
    ].includes(detail)
  ) {
    const kind = detail === INVALID_INPUT_MESSAGE ? "invalid_input" : "auth";
    return new ApiError(detail, status, path, kind);
  }
  if (status === 401) {
    return new ApiError(detail || LOGIN_REQUIRED_MESSAGE, status, path, "auth");
  }
  if (status === 400 || status === 422) {
    return new ApiError(INVALID_INPUT_MESSAGE, status, path, "invalid_input");
  }
  if (isSimulationPath(path) && (status === 404 || status === 409)) {
    const message =
      detail === SIMULATION_ALREADY_ENDED_MESSAGE ? SIMULATION_ALREADY_ENDED_MESSAGE : SIMULATION_NOT_INITIALIZED_MESSAGE;
    return new ApiError(message, status, path, "simulation_state");
  }
  return new ApiError(GENERIC_RETRY_MESSAGE, status, path, "generic");
};

function getSessionId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  const existing = window.sessionStorage.getItem(SESSION_STORAGE_KEY)?.trim();
  if (existing) {
    return existing;
  }

  const generated =
    window.crypto?.randomUUID?.() ||
    `astro-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  window.sessionStorage.setItem(SESSION_STORAGE_KEY, generated);
  return generated;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const sessionId = getSessionId();
  let response: Response;

  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(sessionId ? { "X-Session-ID": sessionId } : {}),
        ...(options?.headers || {}),
      },
    });
  } catch {
    throw new ApiError(GENERIC_RETRY_MESSAGE, 0, path, "generic");
  }

  if (!response.ok) {
    let detail: string | null = null;

    try {
      const errorBody = await response.json();
      detail =
        typeof errorBody.detail === "string"
          ? errorBody.detail
          : typeof errorBody.message === "string"
            ? errorBody.message
            : null;
    } catch {
      const fallbackMessage = (await response.text()).trim();
      if (fallbackMessage) {
        detail = fallbackMessage;
      }
    }

    throw buildSafeApiError(path, response.status, detail);
  }

  return (await response.json()) as T;
}

export function recommendMission(payload: MissionPayload): Promise<RecommendationResponse> {
  return request<RecommendationResponse>("/recommend", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function registerUser(payload: AuthPayload): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function loginUser(payload: AuthPayload): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function logoutUser(): Promise<{ success: boolean }> {
  return request<{ success: boolean }>("/auth/logout", {
    method: "POST",
  });
}

export function fetchCurrentUser(): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/me");
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

export {
  ACCOUNT_EXISTS_MESSAGE,
  BASE_URL,
  GENERIC_RETRY_MESSAGE,
  INVALID_CREDENTIALS_MESSAGE,
  INVALID_INPUT_MESSAGE,
  LOGIN_REQUIRED_MESSAGE,
  SESSION_EXPIRED_MESSAGE,
};
