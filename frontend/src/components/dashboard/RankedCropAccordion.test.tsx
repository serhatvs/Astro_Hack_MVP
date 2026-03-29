import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RankedCropAccordion from "@/components/dashboard/RankedCropAccordion";
import type { CropRecommendation } from "@/lib/types";

const crops: CropRecommendation[] = [
  {
    name: "Solanum lycopersicum (Dwarf Domates)",
    score: 0.91,
    reason: "Best balanced option for the mission profile.",
    selected_system: "hybrid",
    strengths: ["High nutrient value", "Strong crew acceptance"],
    tradeoffs: ["Needs moderate maintenance"],
    metric_breakdown: {
      calorie: 0.72,
      water: 0.58,
      energy: 0.55,
      growth_time: 0.57,
      risk: 0.31,
      maintenance: 0.49,
    },
    compatibility_score: 0.88,
  },
  {
    name: "Lactuca sativa (Marul)",
    score: 0.84,
    reason: "Fast and reliable fallback crop.",
    selected_system: "hydroponic",
    strengths: ["Low risk", "Fast growth"],
    tradeoffs: ["Low calorie yield"],
    metric_breakdown: {
      calorie: 0.1,
      water: 0.42,
      energy: 0.34,
      growth_time: 0.24,
      risk: 0.28,
      maintenance: 0.34,
    },
    compatibility_score: 0.8,
  },
];

describe("RankedCropAccordion", () => {
  it("renders ranked crop candidates as expandable items", () => {
    render(<RankedCropAccordion crops={crops} emptyMessage="Missing crops" />);

    expect(screen.getByRole("button", { name: /#1/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /#2/i })).toBeInTheDocument();
    expect(screen.getByText("Best balanced option for the mission profile.")).toBeInTheDocument();
    expect(screen.getByText("Strengths")).toBeInTheDocument();
    expect(screen.getByText("Tradeoffs")).toBeInTheDocument();
  });

  it("renders a safe empty state", () => {
    render(<RankedCropAccordion crops={[]} emptyMessage="Missing crops" />);

    expect(screen.getByText("Missing crops")).toBeInTheDocument();
  });
});
