import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import { clearSimulationSession, saveSimulationSession } from "@/lib/simulation-session";
import Simulation from "@/pages/Simulation";
import type { SimulationStartResponse } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  generateSimulationInsight: vi.fn(),
  stepMission: vi.fn(),
}));

const session: SimulationStartResponse = {
  mission_profile: {
    environment: "moon",
    duration: "medium",
    constraints: {
      water: "medium",
      energy: "medium",
      area: "medium",
    },
    goal: "balanced",
  },
  mission_state: {
    mission_id: "sim-1",
    environment: "moon",
    duration: "medium",
    goal: "balanced",
    constraints: {
      water: "medium",
      energy: "medium",
      area: "medium",
    },
    time: 0,
    max_weeks: 24,
    initial_risk_level: 24,
    end_reason: null,
    resources: {
      water: 62,
      energy: 62,
      area: 62,
    },
    water_recovery_queue: [],
    last_consumed_water: 0,
    last_recovered_water: 0,
    water_recovery_cycle_weeks: 6,
    water_recovery_rate: 0.58,
    last_consumed_energy: 0,
    last_solar_energy: 0,
    last_photosynthesis_energy: 0,
    active_system: {
      crops: [],
      algae: [],
      microbial: [],
    },
    system_metrics: {
      oxygen_level: 74,
      co2_balance: 70,
      food_supply: 58,
      nutrient_cycle_efficiency: 71,
      risk_level: 24,
    },
    history: [],
  },
  selected_system: {
    crop: {
      name: "Lactuca sativa (Marul)",
      type: "crop",
      domain_score: 0.61,
      mission_fit_score: 0.83,
      risk_score: 0.12,
      support_system: "hybrid",
      metrics: {
        edible_yield: 0.2,
      },
      notes: ["low-risk crop layer"],
    },
    algae: {
      name: "Chlorella vulgaris",
      type: "algae",
      domain_score: 0.78,
      mission_fit_score: 0.8,
      risk_score: 0.33,
      metrics: {
        oxygen_contribution: 0.95,
      },
      notes: ["strong oxygen buffer"],
    },
    microbial: {
      name: "Saccharomyces boulardii",
      type: "microbial",
      domain_score: 0.72,
      mission_fit_score: 0.74,
      risk_score: 0.18,
      metrics: {
        waste_recycling_efficiency: 0.5,
      },
      notes: ["stable microbial support"],
    },
  },
  ranked_candidates: {
    crop: [],
    algae: [],
    microbial: [],
  },
  scores: {
    domain: {
      crop: { domain_score: 0.61, mission_fit_score: 0.83, risk_score: 0.12 },
      algae: { domain_score: 0.78, mission_fit_score: 0.8, risk_score: 0.33 },
      microbial: { domain_score: 0.72, mission_fit_score: 0.74, risk_score: 0.18 },
    },
    interaction: {
      synergy_score: 0.7,
      conflict_score: 0.22,
      complexity_penalty: 0.3,
      resource_overlap: 0.24,
      loop_closure_bonus: 0.74,
    },
    integrated: 2.39,
  },
  explanations: {
    executive_summary: "Simulation summary",
    system_reasoning: "System reasoning",
    tradeoffs: "Tradeoffs",
    weak_points: "Weak points",
  },
  ui_enhanced: {
    crop_note: "Crop note",
    algae_note: "Algae note",
    microbial_note: "Microbial note",
    executive_summary: "Custom simulation executive summary",
    adaptation_summary: "",
  },
  llm_analysis: {
    reasoning_summary: "Simulation critic summary",
    weaknesses: [],
    improvements: [],
    improvement_suggestions: [],
    alternative: {},
    alternative_configuration: {},
    second_pass: {},
    second_pass_decision: {},
  },
  mission_status: "WATCH",
  operational_note: "Operational note",
};

describe("Simulation page", () => {
  beforeEach(() => {
    vi.mocked(api.generateSimulationInsight).mockResolvedValue({
      kind: "simulation_intro",
      title: "AI Insight",
      summary: "AI intro summary",
      highlights: ["Expected oxygen support remains stable."],
      generated_by_ai: true,
      model_tier: "flash",
      model_name: "gemini-2.5-flash",
    });
    vi.mocked(api.stepMission).mockResolvedValue({
      ...session,
      mission_state: {
        ...session.mission_state,
        time: 1,
      },
      system_changes: [],
      risk_delta: 0,
      adaptation_summary: "Week 1 summary",
      events: null,
      request: {
        mission_id: session.mission_state.mission_id,
        time_step: 1,
      },
    } as never);
  });

  afterEach(() => {
    clearSimulationSession();
    vi.clearAllMocks();
  });

  it("shows an empty-state fallback when opened without a session", () => {
    render(
      <MemoryRouter initialEntries={["/simulation"]}>
        <Routes>
          <Route path="/simulation" element={<Simulation />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/No active simulation session was found\./i)).toBeInTheDocument();
  });

  it("renders the selected ecosystem stack from router state", async () => {
    render(
      <MemoryRouter initialEntries={[{ pathname: "/simulation", state: { session } }]}>
        <Routes>
          <Route path="/simulation" element={<Simulation />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("Ecosystem Simulation")).toBeInTheDocument();
    expect(screen.getByText("Lactuca Sativa (Marul)")).toBeInTheDocument();
    expect(screen.getByText("Chlorella Vulgaris")).toBeInTheDocument();
    expect(screen.getByText("Saccharomyces Boulardii")).toBeInTheDocument();
    expect(screen.getByText("Custom simulation executive summary")).toBeInTheDocument();
    expect(screen.getByText(/Current Week:/i)).toBeInTheDocument();
    expect(screen.getByText(/Recovered Water:/i)).toBeInTheDocument();
    expect(screen.getByText(/photosynthesis/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Next Week/i })).toBeInTheDocument();
    await waitFor(() => expect(api.generateSimulationInsight).toHaveBeenCalled());
    expect(screen.getByText("AI Insight")).toBeInTheDocument();
  });

  it("restores the latest simulation session from localStorage on refresh", async () => {
    saveSimulationSession(session, null);

    render(
      <MemoryRouter initialEntries={["/simulation"]}>
        <Routes>
          <Route path="/simulation" element={<Simulation />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("Lactuca Sativa (Marul)")).toBeInTheDocument();
    expect(screen.getByText("Deterministic Simulation")).toBeInTheDocument();
    expect(screen.getByText(/Planned Horizon:/i)).toBeInTheDocument();
    await waitFor(() => expect(api.generateSimulationInsight).toHaveBeenCalled());
    expect(screen.getByText("AI Insight")).toBeInTheDocument();
  });

  it("shows a strong failure banner when the simulation reaches a critical state", async () => {
    const failedSession: SimulationStartResponse = {
      ...session,
      mission_status: "CRITICAL",
      mission_state: {
        ...session.mission_state,
        end_reason: "risk_collapse",
        system_metrics: {
          ...session.mission_state.system_metrics,
          risk_level: 82,
        },
      },
    };
    vi.mocked(api.generateSimulationInsight).mockResolvedValueOnce({
      kind: "simulation_end",
      title: "AI Outcome Insight",
      summary: "AI end summary",
      highlights: ["System risk exceeded safe limits."],
      generated_by_ai: true,
      model_tier: "flash",
      model_name: "gemini-2.5-flash",
    });

    render(
      <MemoryRouter initialEntries={[{ pathname: "/simulation", state: { session: failedSession } }]}>
        <Routes>
          <Route path="/simulation" element={<Simulation />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("Simulation Over")).toBeInTheDocument();
    expect(screen.getByText("System Failure")).toBeInTheDocument();
    expect(screen.getByText("Run Again")).toBeInTheDocument();
    expect(screen.getByText(/^Final Risk Level$/i)).toBeInTheDocument();
    await waitFor(() => expect(api.generateSimulationInsight).toHaveBeenCalled());
    expect(screen.getByText("AI Outcome Insight")).toBeInTheDocument();
  });

  it("resets back to the initial simulation state when Run Again is selected", async () => {
    const failedSession: SimulationStartResponse = {
      ...session,
      mission_status: "CRITICAL",
      mission_state: {
        ...session.mission_state,
        time: 12,
        end_reason: "risk_collapse",
        resources: {
          water: 18,
          energy: 26,
          area: 62,
        },
        system_metrics: {
          ...session.mission_state.system_metrics,
          risk_level: 82,
        },
        history: [
          {
            time: 10,
            event: "water_drop",
            summary: "Water reserves tightened sharply.",
            risk_level: 68,
          },
          {
            time: 12,
            event: "contamination",
            summary: "Biological stress pushed the system beyond safe limits.",
            risk_level: 82,
          },
        ],
      },
    };

    saveSimulationSession(failedSession, session, session);

    render(
      <MemoryRouter initialEntries={["/simulation"]}>
        <Routes>
          <Route path="/simulation" element={<Simulation />} />
        </Routes>
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole("button", { name: /Run Again/i }));

    expect(screen.queryByText("Simulation Over")).not.toBeInTheDocument();
    expect(screen.getByText("Deterministic Simulation")).toBeInTheDocument();
    expect(screen.getByText(/Simulation Status: Running/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Next Week/i })).toBeInTheDocument();
    await waitFor(() => expect(api.generateSimulationInsight).toHaveBeenCalled());
    expect(screen.getByText("AI Insight")).toBeInTheDocument();
  });
});
