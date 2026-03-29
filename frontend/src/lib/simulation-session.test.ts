import { afterEach, describe, expect, it } from "vitest";

import {
  clearSimulationSession,
  isSimulationSessionTerminal,
  loadActiveSimulationSession,
  saveSimulationSession,
  type SimulationSession,
} from "@/lib/simulation-session";


const session: SimulationSession = {
  mission_profile: {
    environment: "mars",
    duration: "long",
    constraints: {
      water: "medium",
      energy: "medium",
      area: "medium",
    },
    goal: "balanced",
  },
  mission_state: {
    mission_id: "session-1",
    environment: "mars",
    duration: "long",
    goal: "balanced",
    constraints: {
      water: "medium",
      energy: "medium",
      area: "medium",
    },
    time: 1,
    max_weeks: 48,
    initial_risk_level: 20,
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
      oxygen_level: 70,
      co2_balance: 68,
      food_supply: 66,
      nutrient_cycle_efficiency: 72,
      risk_level: 20,
    },
    history: [],
  },
  selected_system: {
    crop: {
      name: "Lactuca sativa (Marul)",
      type: "crop",
      domain_score: 0.6,
      mission_fit_score: 0.82,
      risk_score: 0.12,
      support_system: "hybrid",
      metrics: {},
      notes: [],
    },
    algae: {
      name: "Chlorella vulgaris",
      type: "algae",
      domain_score: 0.78,
      mission_fit_score: 0.8,
      risk_score: 0.3,
      metrics: {},
      notes: [],
    },
    microbial: {
      name: "Saccharomyces boulardii",
      type: "microbial",
      domain_score: 0.72,
      mission_fit_score: 0.75,
      risk_score: 0.18,
      metrics: {},
      notes: [],
    },
  },
  ranked_candidates: {
    crop: [],
    algae: [],
    microbial: [],
  },
  scores: {
    domain: {
      crop: { domain_score: 0.6, mission_fit_score: 0.82, risk_score: 0.12 },
      algae: { domain_score: 0.78, mission_fit_score: 0.8, risk_score: 0.3 },
      microbial: { domain_score: 0.72, mission_fit_score: 0.75, risk_score: 0.18 },
    },
    interaction: {
      synergy_score: 0.7,
      conflict_score: 0.2,
      complexity_penalty: 0.25,
      resource_overlap: 0.22,
      loop_closure_bonus: 0.74,
    },
    integrated: 2.35,
  },
  explanations: {
    executive_summary: "Summary",
    system_reasoning: "Reasoning",
    tradeoffs: "Tradeoffs",
    weak_points: "Weak points",
  },
  ui_enhanced: {
    crop_note: "Crop note",
    algae_note: "Algae note",
    microbial_note: "Microbial note",
    executive_summary: "Executive summary",
    adaptation_summary: "",
  },
  llm_analysis: {
    reasoning_summary: "Deterministic summary",
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


describe("simulation-session", () => {
  afterEach(() => {
    clearSimulationSession();
  });

  it("loads an active session when the stored run is still in progress", () => {
    saveSimulationSession(session, null);

    expect(loadActiveSimulationSession()?.current.mission_state.mission_id).toBe("session-1");
    expect(isSimulationSessionTerminal(session)).toBe(false);
  });

  it("treats ended sessions as inactive", () => {
    saveSimulationSession(
      {
        ...session,
        mission_state: {
          ...session.mission_state,
          end_reason: "duration_complete",
        },
      },
      null,
    );

    expect(loadActiveSimulationSession()).toBeNull();
  });
});
