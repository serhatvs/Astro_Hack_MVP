import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import SimulationLauncher from "@/components/dashboard/SimulationLauncher";
import type { RecommendationResponse } from "@/lib/types";

const recommendation: RecommendationResponse = {
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
    mission_id: "mission-1",
    environment: "mars",
    duration: "long",
    goal: "balanced",
    constraints: {
      water: "medium",
      energy: "medium",
      area: "medium",
    },
    time: 0,
    max_weeks: 48,
    initial_risk_level: 26,
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
      oxygen_level: 72,
      co2_balance: 78,
      food_supply: 64,
      nutrient_cycle_efficiency: 70,
      risk_level: 26,
    },
    history: [],
  },
  selected_system: {
    crop: {
      name: "Lactuca sativa (Marul)",
      type: "crop",
      domain_score: 0.6,
      mission_fit_score: 0.84,
      risk_score: 0.15,
      support_system: "hybrid",
      metrics: {},
      notes: [],
    },
    algae: {
      name: "Chlorella vulgaris",
      type: "algae",
      domain_score: 0.78,
      mission_fit_score: 0.82,
      risk_score: 0.33,
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
    crop: [
      {
        name: "Lactuca sativa (Marul)",
        type: "crop",
        rank: 1,
        domain_score: 0.6,
        mission_fit_score: 0.84,
        risk_score: 0.15,
        combined_score: 0.82,
        support_system: "hybrid",
        summary: "Low-risk crop layer.",
        notes: [],
      },
    ],
    algae: [
      {
        name: "Chlorella vulgaris",
        type: "algae",
        rank: 1,
        domain_score: 0.78,
        mission_fit_score: 0.82,
        risk_score: 0.33,
        combined_score: 0.8,
        summary: "Strong oxygen buffer.",
        notes: [],
      },
    ],
    microbial: [
      {
        name: "Saccharomyces boulardii",
        type: "microbial",
        rank: 1,
        domain_score: 0.72,
        mission_fit_score: 0.75,
        risk_score: 0.18,
        combined_score: 0.77,
        summary: "Stable microbial support.",
        notes: [],
      },
    ],
  },
  scores: {
    domain: {
      crop: { domain_score: 0.6, mission_fit_score: 0.84, risk_score: 0.15 },
      algae: { domain_score: 0.78, mission_fit_score: 0.82, risk_score: 0.33 },
      microbial: { domain_score: 0.72, mission_fit_score: 0.75, risk_score: 0.18 },
    },
    interaction: {
      synergy_score: 0.7,
      conflict_score: 0.2,
      complexity_penalty: 0.25,
      resource_overlap: 0.2,
      loop_closure_bonus: 0.72,
    },
    integrated: 2.41,
  },
  explanations: {
    executive_summary: "Simulation-ready stack.",
    system_reasoning: "Balanced stack.",
    tradeoffs: "Moderate complexity.",
    weak_points: "Microbial risk remains visible.",
  },
  ui_enhanced: {
    crop_note: "Plant layer note.",
    algae_note: "Algae layer note.",
    microbial_note: "Microbial layer note.",
    executive_summary: "Executive summary.",
    adaptation_summary: "",
  },
  llm_analysis: {
    reasoning_summary: "Deterministic summary.",
    weaknesses: [],
    improvements: [],
    improvement_suggestions: [],
    alternative: {},
    alternative_configuration: {},
    second_pass: {},
    second_pass_decision: {},
  },
  top_crops: [],
  recommended_system: "hybrid",
  system_reason: "Balanced system.",
  system_reasoning: "Balanced system.",
  why_this_system: "Why this system.",
  tradeoff_summary: "Tradeoff summary.",
  resource_plan: {
    water_level: "medium",
    energy_level: "medium",
    area_usage: "medium",
    water_score: 0.62,
    energy_score: 0.64,
    area_score: 0.58,
    maintenance_score: 0.48,
    calorie_score: 0.44,
  },
  risk_analysis: {
    level: "moderate",
    score: 0.32,
    factors: ["water pressure"],
  },
  mission_status: "WATCH",
  executive_summary: "Executive summary.",
  operational_note: "Operational note.",
  explanation: "Explanation text.",
};

describe("SimulationLauncher", () => {
  it("stays disabled until a recommendation exists", () => {
    render(<SimulationLauncher recommendation={null} isStarting={false} onStart={vi.fn()} />);

    expect(screen.getByText(/Generate a mission plan first, then adjust the recommended biological layers/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /start simulation/i })).toBeDisabled();
  });

  it("prefills the recommended biological stack and starts with the defaults", () => {
    const onStart = vi.fn();

    render(<SimulationLauncher recommendation={recommendation} isStarting={false} onStart={onStart} />);

    expect(screen.getByText(/Lactuca Sativa \(Marul\) \+ Chlorella Vulgaris \+ Saccharomyces Boulardii/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /start simulation/i }));

    expect(onStart).toHaveBeenCalledWith({
      selected_crop: "Lactuca sativa (Marul)",
      selected_algae: "Chlorella vulgaris",
      selected_microbial: "Saccharomyces boulardii",
    });
  });
});
