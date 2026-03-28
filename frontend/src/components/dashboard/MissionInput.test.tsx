import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import MissionInput from "@/components/dashboard/MissionInput";

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
});
