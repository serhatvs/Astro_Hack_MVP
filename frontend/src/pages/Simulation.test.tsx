import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { clearSimulationSession, saveSimulationSession } from "@/lib/simulation-session";
import Simulation from "@/pages/Simulation";
import type { SimulationStartResponse } from "@/lib/types";

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
    resources: {
      water: 62,
      energy: 62,
      area: 62,
    },
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
  afterEach(() => {
    clearSimulationSession();
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

  it("renders the selected ecosystem stack from router state", () => {
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
    expect(screen.getByRole("button", { name: /Next Week/i })).toBeInTheDocument();
  });

  it("restores the latest simulation session from localStorage on refresh", () => {
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
    expect(screen.getByText(/Mission Horizon:/i)).toBeInTheDocument();
  });

  it("shows a strong failure banner when the simulation reaches a critical state", () => {
    const failedSession: SimulationStartResponse = {
      ...session,
      mission_status: "CRITICAL",
      mission_state: {
        ...session.mission_state,
        system_metrics: {
          ...session.mission_state.system_metrics,
          risk_level: 82,
        },
      },
    };

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
  });

  it("resets back to the initial simulation state when Run Again is selected", () => {
    const failedSession: SimulationStartResponse = {
      ...session,
      mission_status: "CRITICAL",
      mission_state: {
        ...session.mission_state,
        time: 12,
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
  });
});
