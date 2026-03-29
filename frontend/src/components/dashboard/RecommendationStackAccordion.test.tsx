import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RecommendationStackAccordion from "@/components/dashboard/RecommendationStackAccordion";
import type { LayerSummary } from "@/lib/mission-view";
import { I18nProvider } from "@/lib/i18n";

const layers: LayerSummary[] = [
  {
    type: "crop",
    label: "Crop Layer",
    accentClass: "text-neon-green",
    name: "solanum_lycopersicum",
    summary: "Tomato remains the lead food layer.",
    domainScore: 0.91,
    missionFitScore: 0.88,
    riskScore: 0.24,
    supportSystem: "hybrid",
    rank: 1,
  },
  {
    type: "algae",
    label: "Algae Layer",
    accentClass: "text-neon-cyan",
    name: "chlorella_vulgaris",
    summary: "Chlorella supports oxygen and biomass.",
    domainScore: 0.83,
    missionFitScore: 0.8,
    riskScore: 0.22,
    supportSystem: null,
    rank: 1,
  },
];

describe("RecommendationStackAccordion", () => {
  it("renders layers as expandable items", () => {
    render(
      <I18nProvider>
        <RecommendationStackAccordion layers={layers} emptyMessage="Missing stack" />
      </I18nProvider>,
    );

    expect(screen.getByRole("button", { name: /crop layer/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /algae layer/i })).toBeInTheDocument();
    expect(screen.getByText("Tomato remains the lead food layer.")).toBeInTheDocument();
    expect(screen.getByText("Domain Score")).toBeInTheDocument();
  });

  it("renders a safe empty state", () => {
    render(
      <I18nProvider>
        <RecommendationStackAccordion layers={[]} emptyMessage="Missing stack" />
      </I18nProvider>,
    );

    expect(screen.getByText("Missing stack")).toBeInTheDocument();
  });
});
