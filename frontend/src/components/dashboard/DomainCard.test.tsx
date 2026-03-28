import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import DomainCard from "@/components/dashboard/DomainCard";
import type { RankedDomainCandidate, SelectedDomainSystem } from "@/lib/types";

const domain: SelectedDomainSystem = {
  name: "spinach",
  type: "crop",
  domain_score: 0.62,
  mission_fit_score: 0.83,
  risk_score: 0.09,
  support_system: "hybrid",
  metrics: {
    edible_yield: 0.06,
    calorie_density: 0.06,
    nutrient_density: 1.0,
  },
  notes: [
    "aligned with the mission environment",
    "supports closed-loop nutrient and gas recovery",
  ],
};

const rankedCandidates: RankedDomainCandidate[] = [
  {
    name: "spinach",
    type: "crop",
    rank: 1,
    domain_score: 0.62,
    mission_fit_score: 0.83,
    risk_score: 0.09,
    combined_score: 0.81,
    support_system: "hybrid",
    summary: "Spinach remains the current selection.",
    notes: ["aligned with the mission environment"],
  },
  {
    name: "lettuce",
    type: "crop",
    rank: 2,
    domain_score: 0.59,
    mission_fit_score: 0.79,
    risk_score: 0.12,
    combined_score: 0.76,
    support_system: "hybrid",
    summary: "Lettuce offers a lighter maintenance profile.",
    notes: ["fast harvest cycle"],
  },
];

describe("DomainCard", () => {
  it("expands and collapses ranked candidates inside the same card", async () => {
    render(
      <DomainCard
        domain={domain}
        rankedCandidates={rankedCandidates}
        summaryOverride="Spinach anchors the food layer for this mission."
      />
    );

    expect(screen.getByText("Spinach anchors the food layer for this mission.")).toBeInTheDocument();
    expect(screen.queryByText("Full Ranked Plant Layer")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /expand candidates/i }));

    expect(screen.getByText("Full Ranked Plant Layer")).toBeInTheDocument();
    expect(screen.getByText("#1")).toBeInTheDocument();
    expect(screen.getByText("#2")).toBeInTheDocument();
    expect(screen.getByText("Current Selection")).toBeInTheDocument();
    expect(screen.getByText("Lettuce offers a lighter maintenance profile.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /collapse candidates/i }));

    await waitFor(() => {
      expect(screen.queryByText("Full Ranked Plant Layer")).not.toBeInTheDocument();
    });
  });
});
