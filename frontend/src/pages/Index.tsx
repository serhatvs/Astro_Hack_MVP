import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import MissionInput from "@/components/dashboard/MissionInput";
import LiveTelemetry from "@/components/dashboard/LiveTelemetry";
import CropCard from "@/components/dashboard/CropCard";
import DomainCard from "@/components/dashboard/DomainCard";
import SimulationLauncher from "@/components/dashboard/SimulationLauncher";
import { recommendMission, startSimulation } from "@/lib/api";
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

const formatLabel = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

const uiNoteKeyByDomain = {
  crop: "crop_note",
  algae: "algae_note",
  microbial: "microbial_note",
} as const;

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
  const crops = currentRecommendation?.top_crops ?? [];
  const geminiReasoningSummary = currentRecommendation?.llm_analysis?.reasoning_summary?.trim() ?? "";
  const geminiUsed = geminiReasoningSummary.endsWith(" -gemini");
  const selectedStack = currentRecommendation?.selected_system
    ? [
        currentRecommendation.selected_system.crop,
        currentRecommendation.selected_system.algae,
        currentRecommendation.selected_system.microbial,
      ]
    : [];
  const visibleCards = selectedStack.length === 3 ? selectedStack : crops;
  const showingIntegratedStack = selectedStack.length === 3;
  const hasRecommendation = Boolean(currentRecommendation);

  const handleGenerate = async () => {
    const missionPayload = buildMissionPayload();

    setError(null);
    setIsGenerating(true);

    try {
      const response = await recommendMission(missionPayload);
      setRecommendation(response);

      toast.success("Mission plan generated", {
        description: `${formatLabel(response.top_crops[0].name)} ranked first for the selected mission profile.`,
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

        <div className="flex min-h-0 flex-1 flex-col">
          <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2 px-1">
            <h2 className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
              {hasRecommendation
                ? showingIntegratedStack
                  ? "Selected Biological Stack"
                  : "Optimal Crop Selection"
                : "Awaiting Mission Plan"}
            </h2>
            {currentRecommendation && (
              <div className="flex flex-wrap items-center justify-end gap-2 text-[10px] font-mono text-muted-foreground">
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
                {showingIntegratedStack ? (
                  <>
                    Integrated score:{" "}
                    <span className="text-neon-cyan">
                      {currentRecommendation.scores?.integrated?.toFixed(2) ?? "N/A"}
                    </span>
                    {" | "}Plant system:{" "}
                    <span className="text-neon-cyan">
                      {formatLabel(currentRecommendation.recommended_system).toUpperCase()}
                    </span>
                  </>
                ) : (
                  <>
                    Primary system:{" "}
                    <span className="text-neon-cyan">
                      {formatLabel(currentRecommendation.recommended_system).toUpperCase()}
                    </span>
                  </>
                )}
              </div>
            )}
          </div>

          <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {visibleCards.length > 0 ? (
              <AnimatePresence mode="popLayout">
                {showingIntegratedStack
                  ? selectedStack.map((domain) => (
                      <DomainCard
                        key={`${domain.type}-${domain.name}-base`}
                        domain={domain}
                        rankedCandidates={currentRecommendation?.ranked_candidates?.[domain.type] ?? []}
                        summaryOverride={currentRecommendation?.ui_enhanced?.[uiNoteKeyByDomain[domain.type]] ?? null}
                      />
                    ))
                  : crops.map((crop, index) => (
                      <CropCard
                        key={`${crop.name}-base`}
                        crop={crop}
                        rank={index + 1}
                        showChart={index === 0}
                      />
                    ))}
              </AnimatePresence>
            ) : (
              <div className="glass-panel col-span-full flex min-h-[280px] flex-col items-center justify-center gap-3 overflow-hidden p-6 text-center">
                {isGenerating ? (
                  <>
                    <Loader2 className="h-8 w-8 animate-spin text-neon-cyan" />
                    <p className="text-sm font-mono text-foreground/80">
                      Requesting recommendation from the backend and computing the integrated biological stack...
                    </p>
                  </>
                ) : (
                  <p className="text-sm font-mono text-muted-foreground">
                    Select the mission profile above and click Generate Plan to populate the crop, algae, and microbial stack.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

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
