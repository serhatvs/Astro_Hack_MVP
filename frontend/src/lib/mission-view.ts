import type {
  MissionStepResponse,
  RankedCandidatesBundle,
  RecommendationResponse,
  SimulationStartResponse,
  UIEnhancedNarrative,
} from "@/lib/types";

type DomainType = "crop" | "algae" | "microbial";

type SelectedSystemLike = {
  selected_system?: RecommendationResponse["selected_system"];
  ranked_candidates?: RankedCandidatesBundle;
  ui_enhanced?: UIEnhancedNarrative;
};

export interface LayerSummary {
  type: DomainType;
  label: string;
  accentClass: string;
  name: string;
  summary: string;
  domainScore: number;
  missionFitScore: number;
  riskScore: number;
  supportSystem?: string | null;
  rank: number | null;
}

export const uiNoteKeyByDomain = {
  crop: "crop_note",
  algae: "algae_note",
  microbial: "microbial_note",
} as const;

const domainLabels: Record<DomainType, string> = {
  crop: "Crop Layer",
  algae: "Algae Layer",
  microbial: "Microbial Layer",
};

const domainAccentClasses: Record<DomainType, string> = {
  crop: "text-neon-green border-neon-green/30 bg-neon-green/10",
  algae: "text-neon-cyan border-neon-cyan/30 bg-neon-cyan/10",
  microbial: "text-neon-orange border-neon-orange/30 bg-neon-orange/10",
};

export const formatLabel = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

export const isGeminiUsed = (reasoningSummary?: string | null) =>
  Boolean(reasoningSummary?.trim().endsWith(" -gemini"));

export const getExecutiveSummary = (
  response?: RecommendationResponse | SimulationStartResponse | MissionStepResponse | null,
) =>
  response?.ui_enhanced?.executive_summary?.trim() ||
  ("executive_summary" in (response || {}) && typeof response?.executive_summary === "string"
    ? response.executive_summary
    : "") ||
  response?.explanations?.executive_summary ||
  "";

export const buildLayerSummaries = (source?: SelectedSystemLike | null): LayerSummary[] => {
  if (!source?.selected_system) {
    return [];
  }

  return (["crop", "algae", "microbial"] as const).map((type) => {
    const selected = source.selected_system?.[type];
    const ranked = source.ranked_candidates?.[type] ?? [];
    const uiSummary = source.ui_enhanced?.[uiNoteKeyByDomain[type]]?.trim();
    const noteSummary = selected?.notes?.filter(Boolean).slice(0, 2).join(". ");
    const summary =
      uiSummary ||
      (noteSummary ? `${noteSummary}${noteSummary.endsWith(".") ? "" : "."}` : "") ||
      `${formatLabel(selected?.name || type)} remains active in the ${domainLabels[type].toLowerCase()}.`;
    const rankIndex = ranked.findIndex((candidate) => candidate.name === selected?.name);

    return {
      type,
      label: domainLabels[type],
      accentClass: domainAccentClasses[type],
      name: selected?.name || formatLabel(type),
      summary,
      domainScore: selected?.domain_score ?? 0,
      missionFitScore: selected?.mission_fit_score ?? 0,
      riskScore: selected?.risk_score ?? 0,
      supportSystem: selected?.support_system ?? null,
      rank: rankIndex >= 0 ? rankIndex + 1 : null,
    };
  });
};
