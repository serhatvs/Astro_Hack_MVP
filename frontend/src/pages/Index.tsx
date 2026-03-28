import { useState } from "react";
import { Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import MissionInput from "@/components/dashboard/MissionInput";
import LiveTelemetry from "@/components/dashboard/LiveTelemetry";
import SimulationLauncher from "@/components/dashboard/SimulationLauncher";
import { recommendMission, startSimulation } from "@/lib/api";
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
  const layerSummaries = buildLayerSummaries(currentRecommendation);
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
        "the selected stack";

      toast.success("Mission plan generated", {
        description: `${formatLabel(leadLabel)} is ready for the selected mission profile.`,
      });
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Unable to reach the backend.";
      setError(message);
      toast.error("Recommendation failed", { description: message });
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
      toast.error("Generate a mission plan first", {
        description: "A simulation needs the current mission recommendation and candidate lists as its starting point.",
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
      const message = requestError instanceof Error ? requestError.message : "Unable to start the ecosystem simulation.";
      toast.error("Simulation launch failed", { description: message });
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
                  TUA Astro-Tarim Karar Motoru
                </h1>
              </div>
              <span className="rounded border border-glass-border px-1.5 py-0.5 text-[9px] font-mono text-muted-foreground">
                v1.1
              </span>
            </div>
            <div className="hidden w-full max-w-sm shrink-0 lg:block">
              <LiveTelemetry />
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
              <p className="break-words text-xs font-mono text-neon-red">Backend error: {error}</p>
            </div>
          )}
        </div>

        {hasRecommendation && currentRecommendation && (
          <div className="glass-panel flex min-w-0 flex-col gap-4 overflow-hidden p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <h2 className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
                  Mission Summary
                </h2>
                <p className="max-w-4xl text-sm text-foreground/80">
                  {executiveSummary || "Recommendation prepared. Adjust the ecosystem layers below before starting the simulation."}
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
                  Gemini
                </span>
                <span className={geminiUsed ? "text-neon-cyan" : "text-muted-foreground"}>
                  {geminiUsed ? "Gemini kullanildi" : "Gemini kullanilmadi"}
                </span>
                <span>
                  Integrated score:{" "}
                  <span className="text-neon-cyan">
                    {currentRecommendation.scores?.integrated?.toFixed(2) ?? "N/A"}
                  </span>
                </span>
                <span>
                  Plant system:{" "}
                  <span className="text-neon-cyan">
                    {formatLabel(currentRecommendation.recommended_system).toUpperCase()}
                  </span>
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1.3fr_0.7fr]">
              <div className="rounded-lg border border-glass-border bg-black/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                  Prepared Ecosystem Seed
                </p>
                <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {layerSummaries.length > 0 ? (
                    layerSummaries.map((layer) => (
                      <div key={layer.type} className="rounded border border-glass-border/70 bg-muted/10 px-3 py-2">
                        <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                          {layer.label}
                        </p>
                        <p className="mt-1 text-sm font-semibold text-foreground">{formatLabel(layer.name)}</p>
                        <p className="mt-1 text-xs text-foreground/75">{layer.summary}</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      The recommendation exists, but stack detail fields were missing. The simulation launcher below can
                      still use the available mission output safely.
                    </p>
                  )}
                </div>
              </div>

              <div className="rounded-lg border border-neon-orange/25 bg-neon-orange/5 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-neon-orange">Operational Note</p>
                <p className="mt-2 text-xs leading-relaxed text-foreground/80">
                  {currentRecommendation.operational_note ||
                    "The recommendation is ready. Launch simulation to stress the loop and inspect adaptation."}
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
                  Requesting recommendation from the backend and preparing a simulation-ready mission seed...
                </p>
              </>
            ) : (
              <p className="text-sm font-mono text-muted-foreground">
                Configure the mission above and click Generate Plan. The recommendation will be stored internally and
                used to prefill the simulation launcher below.
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
