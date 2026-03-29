import { useState } from "react";
import { Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import MissionInput from "@/components/dashboard/MissionInput";
import LiveTelemetry from "@/components/dashboard/LiveTelemetry";
import LanguageToggle from "@/components/LanguageToggle";
import SimulationLauncher from "@/components/dashboard/SimulationLauncher";
import { recommendMission, startSimulation } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { buildLayerSummaries, formatLabel, getExecutiveSummary, isGeminiUsed } from "@/lib/mission-view";
import { saveSimulationSession } from "@/lib/simulation-session";
import type {
  BackendGoal,
  ConstraintLevel,
  Duration,
  Environment,
  MissionPayload,
  RecommendationResponse,
  UiGoal,
} from "@/lib/types";

const goalMap: Record<UiGoal, BackendGoal> = {
  balanced: "balanced",
  calorie: "calorie_max",
  water: "water_efficiency",
  low_maintenance: "low_maintenance",
};

const Index = () => {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [environment, setEnvironment] = useState<Environment>("mars");
  const [duration, setDuration] = useState<Duration>("long");
  const [waterConstraint, setWaterConstraint] = useState<ConstraintLevel>("high");
  const [energyConstraint, setEnergyConstraint] = useState<ConstraintLevel>("medium");
  const [areaConstraint, setAreaConstraint] = useState<ConstraintLevel>("medium");
  const [goal, setGoal] = useState<UiGoal>("balanced");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isStartingSimulation, setIsStartingSimulation] = useState(false);
  const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const buildMissionPayload = (): MissionPayload => ({
    environment,
    duration,
    constraints: {
      water: waterConstraint,
      energy: energyConstraint,
      area: areaConstraint,
    },
    goal: goalMap[goal],
  });

  const currentRecommendation = recommendation;
  const geminiUsed = isGeminiUsed(currentRecommendation?.llm_analysis?.reasoning_summary);
  const layerSummaries = buildLayerSummaries(currentRecommendation, t);
  const executiveSummary = getExecutiveSummary(currentRecommendation);
  const hasRecommendation = Boolean(currentRecommendation);

  const handleGenerate = async () => {
    const missionPayload = buildMissionPayload();

    setError(null);
    setIsGenerating(true);

    try {
      const response = await recommendMission(missionPayload);
      setRecommendation(response);
      const leadLabel =
        response.selected_system?.crop?.name ||
        response.top_crops?.[0]?.name ||
        t("launch_stack").toLowerCase();

      toast.success(t("mission_plan_generated"), {
        description: t("mission_plan_generated_desc", { stack: formatLabel(leadLabel) }),
      });
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : t("unable_to_reach_backend");
      setError(message);
      toast.error(t("recommendation_failed"), { description: message });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleStartSimulation = async (selection: {
    selected_crop: string;
    selected_algae: string;
    selected_microbial: string;
  }) => {
    if (!currentRecommendation) {
      toast.error(t("generate_plan_first"), {
        description: t("simulation_start_requires_plan"),
      });
      return;
    }

    setIsStartingSimulation(true);
    try {
      const session = await startSimulation({
        mission_profile: currentRecommendation.mission_profile,
        ...selection,
      });
      saveSimulationSession(session, null);
      navigate("/simulation", { state: { session } });
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : t("unable_to_start_simulation");
      toast.error(t("simulation_launch_failed"), { description: message });
    } finally {
      setIsStartingSimulation(false);
    }
  };

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-background p-3">
      <div className="mx-auto flex min-h-[calc(100vh-1.5rem)] w-full max-w-[1800px] flex-col gap-3">
        <div className="glass-panel overflow-hidden p-3">
          <div className="mb-2 flex flex-wrap items-start justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex min-w-0 items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-neon-green blink" />
                <h1 className="truncate text-sm font-bold font-mono uppercase tracking-widest neon-text-cyan">
                  {t("app_title")}
                </h1>
              </div>
              <span className="rounded border border-glass-border px-1.5 py-0.5 text-[9px] font-mono text-muted-foreground">
                v1.1
              </span>
            </div>
            <div className="flex w-full items-center justify-end gap-3 lg:w-auto">
              <LanguageToggle />
              <div className="hidden w-full max-w-sm shrink-0 lg:block">
                <LiveTelemetry />
              </div>
            </div>
          </div>

          <MissionInput
            environment={environment}
            setEnvironment={setEnvironment}
            duration={duration}
            setDuration={setDuration}
            waterConstraint={waterConstraint}
            setWaterConstraint={setWaterConstraint}
            energyConstraint={energyConstraint}
            setEnergyConstraint={setEnergyConstraint}
            areaConstraint={areaConstraint}
            setAreaConstraint={setAreaConstraint}
            goal={goal}
            setGoal={setGoal}
            onGenerate={handleGenerate}
            isLoading={isGenerating}
          />

          {error && (
            <div className="mt-3 rounded border border-neon-red/40 bg-neon-red/10 px-3 py-2">
              <p className="break-words text-xs font-mono text-neon-red">{t("backend_error")}: {error}</p>
            </div>
          )}
        </div>

        {hasRecommendation && currentRecommendation && (
          <div className="glass-panel flex min-w-0 flex-col gap-4 overflow-hidden p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <h2 className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
                  {t("mission_summary")}
                </h2>
                <p className="max-w-4xl text-sm text-foreground/80">
                  {executiveSummary || t("recommendation_prepared")}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono text-muted-foreground">
                <span
                  className={`rounded border px-1.5 py-0.5 uppercase tracking-wider ${
                    geminiUsed
                      ? "border-neon-cyan/40 bg-neon-cyan/10 text-neon-cyan"
                      : "border-glass-border bg-muted/20 text-muted-foreground"
                  }`}
                >
                  {t("ai_insight")}
                </span>
                <span className={geminiUsed ? "text-neon-cyan" : "text-muted-foreground"}>
                  {geminiUsed ? t("enabled") : t("fallback")}
                </span>
                <span>
                  {t("integrated_score")}:{" "}
                  <span className="text-neon-cyan">
                    {currentRecommendation.scores?.integrated?.toFixed(2) ?? t("n_a")}
                  </span>
                </span>
                <span>
                  {t("plant_system")}:{" "}
                  <span className="text-neon-cyan">
                    {formatLabel(currentRecommendation.recommended_system).toUpperCase()}
                  </span>
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1.3fr_0.7fr]">
              <div className="rounded-lg border border-glass-border bg-black/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                  {t("recommended_validation_stack")}
                </p>
                <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {layerSummaries.length > 0 ? (
                    layerSummaries.map((layer) => (
                      <div key={layer.type} className="rounded border border-glass-border/70 bg-muted/10 px-3 py-2">
                        <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                          {t(`${layer.type}_layer`)}
                        </p>
                        <p className="mt-1 text-sm font-semibold text-foreground">{formatLabel(layer.name)}</p>
                        <p className="mt-1 text-xs text-foreground/75">{layer.summary}</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      {t("recommendation_missing_stack")}
                    </p>
                  )}
                </div>
              </div>

              <div className="rounded-lg border border-neon-orange/25 bg-neon-orange/5 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-neon-orange">{t("operational_note")}</p>
                <p className="mt-2 text-xs leading-relaxed text-foreground/80">
                  {currentRecommendation.operational_note || t("recommendation_ready_note")}
                </p>
              </div>
            </div>
          </div>
        )}

        {!hasRecommendation && (
          <div className="glass-panel flex min-h-[180px] flex-col items-center justify-center gap-3 overflow-hidden p-6 text-center">
            {isGenerating ? (
              <>
                <Loader2 className="h-8 w-8 animate-spin text-neon-cyan" />
                <p className="text-sm font-mono text-foreground/80">
                  {t("preparing_recommendation")}
                </p>
              </>
            ) : (
              <p className="text-sm font-mono text-muted-foreground">
                {t("configure_mission_prompt")}
              </p>
            )}
          </div>
        )}

        <div className="min-w-0 overflow-hidden rounded-xl">
          <SimulationLauncher
            recommendation={currentRecommendation}
            isStarting={isStartingSimulation}
            onStart={handleStartSimulation}
          />
        </div>
      </div>
    </div>
  );
};

export default Index;
