import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import MissionInput from "@/components/dashboard/MissionInput";
import LiveTelemetry from "@/components/dashboard/LiveTelemetry";
import CropCard from "@/components/dashboard/CropCard";
import SystemPanel from "@/components/dashboard/SystemPanel";
import CrisisPanel from "@/components/dashboard/CrisisPanel";
import AIReasoning from "@/components/dashboard/AIReasoning";
import SystemTerminal from "@/components/dashboard/SystemTerminal";
import { recommendMission, simulateMission } from "@/lib/api";
import type {
  ApiStatus,
  BackendGoal,
  ChangeEvent,
  ConstraintLevel,
  CrisisType,
  Duration,
  Environment,
  MissionPayload,
  RecommendationResponse,
  SimulationResponse,
  TerminalEntry,
  UiGoal,
} from "@/lib/types";

const goalMap: Record<UiGoal, BackendGoal> = {
  balanced: "balanced",
  calorie: "calorie_max",
  water: "water_efficiency",
  low_maintenance: "low_maintenance",
};

const crisisEventMap: Record<CrisisType, ChangeEvent> = {
  water: "water_drop",
  energy: "energy_drop",
  yield: "yield_drop",
};

const formatLabel = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

const timestamped = (text: string) => `[${new Date().toLocaleTimeString("en-GB")}] ${text}`;

const Index = () => {
  const [environment, setEnvironment] = useState<Environment>("mars");
  const [duration, setDuration] = useState<Duration>("long");
  const [waterConstraint, setWaterConstraint] = useState<ConstraintLevel>("high");
  const [energyConstraint, setEnergyConstraint] = useState<ConstraintLevel>("medium");
  const [areaConstraint, setAreaConstraint] = useState<ConstraintLevel>("medium");
  const [goal, setGoal] = useState<UiGoal>("balanced");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null);
  const [simulation, setSimulation] = useState<SimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [terminalEntries, setTerminalEntries] = useState<TerminalEntry[]>([
    { level: "info", text: timestamped("Mission control ready. Configure a mission profile and generate a plan.") },
  ]);

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

  const currentRecommendation = simulation?.updated_recommendation ?? recommendation;
  const currentMission = simulation?.updated_mission_profile ?? recommendation?.mission_profile ?? buildMissionPayload();
  const crops = currentRecommendation?.top_crops ?? [];
  const hasRecommendation = Boolean(currentRecommendation);
  const isAdaptive = Boolean(simulation);
  const apiStatus: ApiStatus = error
    ? "error"
    : isGenerating || isSimulating
      ? "loading"
      : simulation
        ? "warning"
        : currentRecommendation
          ? "ready"
          : "idle";

  const appendTerminalEntries = (...entries: TerminalEntry[]) => {
    setTerminalEntries((previousEntries) => [...previousEntries, ...entries]);
  };

  const handleGenerate = async () => {
    const missionPayload = buildMissionPayload();

    setError(null);
    setIsGenerating(true);
    setSimulation(null);
    setTerminalEntries([
      { level: "info", text: timestamped(`POST /recommend -> ${missionPayload.environment.toUpperCase()} ${missionPayload.duration.toUpperCase()} mission submitted`) },
      {
        level: "info",
        text: timestamped(
          `Constraints -> water=${missionPayload.constraints.water} energy=${missionPayload.constraints.energy} area=${missionPayload.constraints.area} goal=${missionPayload.goal}`,
        ),
      },
    ]);

    try {
      const response = await recommendMission(missionPayload);
      setRecommendation(response);

      appendTerminalEntries(
        {
          level: "success",
          text: timestamped(`Top crops -> ${response.top_crops.map((crop) => formatLabel(crop.name)).join(", ")}`),
        },
        {
          level: "info",
          text: timestamped(
            `Primary system -> ${formatLabel(response.recommended_system)} | Status -> ${response.mission_status} | Risk -> ${response.risk_analysis.level.toUpperCase()}`,
          ),
        },
        {
          level: "info",
          text: timestamped(`Executive summary -> ${response.executive_summary}`),
        },
      );

      toast.success("Mission plan generated", {
        description: `${formatLabel(response.top_crops[0].name)} ranked first for the selected mission profile.`,
      });
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Unable to reach the backend.";
      setError(message);
      appendTerminalEntries({ level: "error", text: timestamped(`Recommendation failed -> ${message}`) });
      toast.error("Recommendation failed", { description: message });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCrisis = async (type: CrisisType) => {
    if (!currentRecommendation) {
      toast.error("Generate a mission plan first", {
        description: "The dashboard needs a baseline recommendation before it can simulate adaptation.",
      });
      return;
    }

    const changeEvent = crisisEventMap[type];
    const affectedCrop = type === "yield" ? currentRecommendation.top_crops[0]?.name : undefined;

    setError(null);
    setIsSimulating(true);
    appendTerminalEntries(
      { level: "warn", text: timestamped(`Crisis event -> ${changeEvent}`) },
      {
        level: "info",
        text: timestamped(
          affectedCrop ? `Applying direct yield penalty to ${formatLabel(affectedCrop)}` : "Recalculating mission priorities",
        ),
      },
    );

    try {
      const response = await simulateMission({
        mission_profile: currentMission,
        change_event: changeEvent,
        affected_crop: affectedCrop,
        previous_recommendation: currentRecommendation,
      });

      setSimulation(response);

      appendTerminalEntries(
        {
          level: response.risk_delta === "increased" ? "warn" : "success",
          text: timestamped(
            `Top crop -> ${formatLabel(response.previous_top_crop || "n/a")} => ${formatLabel(response.new_top_crop || "n/a")}`,
          ),
        },
        {
          level: response.system_changed ? "warn" : "info",
          text: timestamped(
            `System -> ${formatLabel(response.previous_system || "n/a")} => ${formatLabel(response.new_system || "n/a")} | Risk delta -> ${response.risk_delta} (${response.risk_score_delta >= 0 ? "+" : ""}${response.risk_score_delta.toFixed(3)})`,
          ),
        },
        {
          level: "info",
          text: timestamped(
            `Mission status -> ${response.previous_mission_status} => ${response.new_mission_status}`,
          ),
        },
        {
          level: "info",
          text: timestamped(`Adaptation summary -> ${response.adaptation_summary}`),
        },
      );

      toast.warning("Crisis simulation updated", {
        description: response.adaptation_summary,
      });
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Unable to run simulation.";
      setError(message);
      appendTerminalEntries({ level: "error", text: timestamped(`Simulation failed -> ${message}`) });
      toast.error("Simulation failed", { description: message });
    } finally {
      setIsSimulating(false);
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
              {hasRecommendation ? "Optimal Crop Selection" : "Awaiting Mission Plan"}
            </h2>
            {currentRecommendation && (
              <span className="text-[10px] font-mono text-muted-foreground">
                Primary system:{" "}
                <span className="text-neon-cyan">
                  {formatLabel(currentRecommendation.recommended_system).toUpperCase()}
                </span>
              </span>
            )}
          </div>

          <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {crops.length > 0 ? (
              <AnimatePresence mode="popLayout">
                {crops.map((crop, index) => (
                  <CropCard
                    key={`${crop.name}-${simulation?.change_event || "base"}`}
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
                      Requesting recommendation from the backend and computing the top crop mix...
                    </p>
                  </>
                ) : (
                  <p className="text-sm font-mono text-muted-foreground">
                    Select the mission profile above and click Generate Plan to populate live crop recommendations.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="grid auto-rows-[minmax(260px,1fr)] grid-cols-1 gap-3 md:grid-cols-2 2xl:grid-cols-4">
          <div className="min-h-[260px] min-w-0 overflow-hidden rounded-xl">
            <SystemPanel recommendation={currentRecommendation} simulation={simulation} isLoading={isGenerating || isSimulating} />
          </div>
          <div className="min-h-[260px] min-w-0 overflow-hidden rounded-xl">
            <CrisisPanel
              onSimulate={handleCrisis}
              disabled={!hasRecommendation || isGenerating || isSimulating}
              isSimulating={isSimulating}
              hasRecommendation={hasRecommendation}
              lastEvent={simulation?.change_event || null}
              simulation={simulation}
            />
          </div>
          <div className="min-h-[260px] min-w-0 overflow-hidden rounded-xl">
            <AIReasoning
              message={simulation?.adaptation_summary || currentRecommendation?.executive_summary || null}
              isAdaptive={isAdaptive}
              error={error}
            />
          </div>
          <div className="min-h-[260px] min-w-0 overflow-hidden rounded-xl">
            <SystemTerminal entries={terminalEntries} apiStatus={apiStatus} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Index;
