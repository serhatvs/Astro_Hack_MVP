import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import CrisisPanel from "@/components/dashboard/CrisisPanel";
import type { RecommendationResponse, SimulationResponse } from "@/lib/types";

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
  top_crops: [
    {
      name: "lettuce",
      score: 0.9,
      reason: "Fast and stable.",
      selected_system: "hydroponic",
      strengths: ["Fast harvest cycle", "Low crew maintenance demand"],
      tradeoffs: ["Lower calorie density than staple crops"],
      metric_breakdown: {
        calorie: 0.3,
        water: 0.2,
        energy: 0.2,
        growth_time: 0.1,
        risk: 0.1,
        maintenance: 0.1,
      },
      compatibility_score: 0.88,
    },
  ],
  recommended_system: "hydroponic",
  system_reason: "Stable and simple.",
  system_reasoning: "Stable and simple.",
  why_this_system: "Hydroponic is the best fit because simplicity matters.",
  tradeoff_summary: "It trades water efficiency for simpler operations.",
  resource_plan: {
    water_level: "medium",
    energy_level: "low",
    area_usage: "compact",
    water_score: 0.4,
    energy_score: 0.3,
    area_score: 0.2,
    maintenance_score: 0.25,
    calorie_score: 0.35,
  },
  risk_analysis: {
    level: "moderate",
    score: 0.4,
    factors: ["operational maintenance load"],
  },
  mission_status: "WATCH",
  executive_summary: "Summary",
  operational_note: "Watch the system load.",
  explanation: "Summary Watch the system load.",
};

const simulation: SimulationResponse = {
  change_event: "yield_drop",
  changed_fields: ["top_crops", "recommended_system", "risk_analysis"],
  previous_top_crop: "spirulina",
  new_top_crop: "lettuce",
  ranking_diff: {
    spirulina: -1,
    lettuce: 1,
    potato: 0,
  },
  system_changed: true,
  previous_system: "hybrid",
  new_system: "hydroponic",
  risk_delta: "increased",
  risk_score_delta: 0.125,
  previous_mission_status: "NOMINAL",
  new_mission_status: "WATCH",
  updated_mission_profile: recommendation.mission_profile,
  updated_recommendation: recommendation,
  adaptation_summary: "Conditions changed and the system adapted.",
  reason: "Conditions changed and the system adapted.",
  adaptation_reason: "Conditions changed and the system adapted.",
};

describe("CrisisPanel", () => {
  it("renders simulation visibility details", () => {
    render(
      <CrisisPanel
        onSimulate={vi.fn()}
        disabled={false}
        isSimulating={false}
        hasRecommendation
        lastEvent="yield_drop"
        simulation={simulation}
      />
    );

    expect(screen.getByText("SYSTEM SHIFT")).toBeInTheDocument();
    expect(screen.getByText("Top Crop")).toBeInTheDocument();
    expect(screen.getAllByText("Spirulina").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Lettuce").length).toBeGreaterThan(0);
    expect(screen.getByText("Risk Delta")).toBeInTheDocument();
    expect(screen.getByText(/INCREASED/)).toBeInTheDocument();
    expect(screen.getByText("Ranking Diff")).toBeInTheDocument();
  });
});
