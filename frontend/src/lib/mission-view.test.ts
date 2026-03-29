import { describe, expect, it } from "vitest";

import { getRecommendationAiState } from "@/lib/mission-view";

describe("getRecommendationAiState", () => {
  it("returns reranked status when backend reports a rerank", () => {
    const state = getRecommendationAiState({
      ai_status: {
        status: "reranked",
        provider: "gemini",
        reviewed: true,
        selection_changed: true,
        message: "AI reranked the shortlisted mission stacks before finalizing the recommendation.",
      },
    });

    expect(state.active).toBe(true);
    expect(state.label).toBe("AI reranked");
  });

  it("returns fallback status when backend reports deterministic fallback", () => {
    const state = getRecommendationAiState({
      ai_status: {
        status: "fallback",
        provider: "deterministic",
        reviewed: false,
        selection_changed: false,
        message: "AI rerank unavailable. Deterministic shortlist result is being shown.",
      },
    });

    expect(state.active).toBe(false);
    expect(state.label).toBe("AI fallback");
  });
});
