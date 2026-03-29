import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import MissionInput from "@/components/dashboard/MissionInput";
import type { DemoCase } from "@/lib/types";

const demoCase: DemoCase = {
  name: "Demo Scenario: Strong System",
  description: "Stable preset.",
  expected_outcome: "Expected outcome: full mission completion.",
  environment: "mars",
  duration: "long",
  constraints: {
    water: "low",
    energy: "low",
    area: "low",
  },
  goal: "balanced",
  selected_stack: {
    selected_crop: "Lactuca sativa (Marul)",
    selected_algae: "Chlorella vulgaris",
    selected_microbial: "Saccharomyces boulardii",
  },
};

describe("MissionInput", () => {
  it("renders explicit constraint semantics", () => {
    render(
      <MissionInput
        environment="mars"
        setEnvironment={vi.fn()}
        duration="long"
        setDuration={vi.fn()}
        waterConstraint="low"
        setWaterConstraint={vi.fn()}
        energyConstraint="medium"
        setEnergyConstraint={vi.fn()}
        areaConstraint="high"
        setAreaConstraint={vi.fn()}
        goal="balanced"
        setGoal={vi.fn()}
        onGenerate={vi.fn()}
        isLoading={false}
      />
    );

    expect(screen.getByText("Water Constraint")).toBeInTheDocument();
    expect(screen.getByText("Energy Constraint")).toBeInTheDocument();
    expect(screen.getByText("Area Constraint")).toBeInTheDocument();
    expect(
      screen.getByText("Low means fewer limitations. High means stronger constraints.")
    ).toBeInTheDocument();
  });

  it("renders demo scenarios and loads one on demand", async () => {
    const onLoadDemoCase = vi.fn();

    render(
      <MissionInput
        environment="mars"
        setEnvironment={vi.fn()}
        duration="long"
        setDuration={vi.fn()}
        waterConstraint="low"
        setWaterConstraint={vi.fn()}
        energyConstraint="medium"
        setEnergyConstraint={vi.fn()}
        areaConstraint="high"
        setAreaConstraint={vi.fn()}
        goal="balanced"
        setGoal={vi.fn()}
        onGenerate={vi.fn()}
        onLoadDemoCase={onLoadDemoCase}
        demoCases={[demoCase]}
        activeDemoCaseName={null}
        isLoading={false}
      />
    );

    expect(screen.getByText("Demo Scenarios")).toBeInTheDocument();
    expect(screen.getByText("Demo Scenario: Strong System")).toBeInTheDocument();
    expect(screen.getByText("Expected outcome: full mission completion.")).toBeInTheDocument();

    screen.getByRole("button", { name: "Load Scenario" }).click();

    expect(onLoadDemoCase).toHaveBeenCalledWith(demoCase);
  });
});
