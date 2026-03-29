import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RankedDomainAccordion from "@/components/dashboard/RankedDomainAccordion";
import type { RankedDomainCandidate } from "@/lib/types";

const candidates: RankedDomainCandidate[] = [
  {
    name: "Chlorella vulgaris",
    type: "algae",
    rank: 1,
    domain_score: 0.82,
    mission_fit_score: 0.85,
    risk_score: 0.19,
    combined_score: 0.88,
    summary: "Strong oxygen and biomass support.",
    notes: ["Stable photobioreactor profile."],
  },
  {
    name: "Dunaliella salina",
    type: "algae",
    rank: 2,
    domain_score: 0.71,
    mission_fit_score: 0.69,
    risk_score: 0.33,
    combined_score: 0.74,
    summary: "Higher stress tolerance, lower baseline fit.",
    notes: [],
  },
];

describe("RankedDomainAccordion", () => {
  it("renders ranked candidates and highlights the selected one", () => {
    render(
      <RankedDomainAccordion
        title="Algae Layer"
        candidates={candidates}
        selectedName="Chlorella vulgaris"
        emptyMessage="Missing candidates"
      />,
    );

    expect(screen.getByRole("button", { name: /chlorella vulgaris/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /dunaliella salina/i })).toBeInTheDocument();
    expect(screen.getByText("Selected")).toBeInTheDocument();
    expect(screen.getByText("Strong oxygen and biomass support.")).toBeInTheDocument();
  });

  it("renders a safe empty state", () => {
    render(
      <RankedDomainAccordion
        title="Microbial Layer"
        candidates={[]}
        selectedName={null}
        emptyMessage="Missing candidates"
      />,
    );

    expect(screen.getByText("Missing candidates")).toBeInTheDocument();
  });
});
