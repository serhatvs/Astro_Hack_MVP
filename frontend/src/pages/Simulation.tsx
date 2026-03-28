import { useEffect, useMemo, useState } from "react";
import { ArrowDownRight, ArrowLeft, ArrowRight, ArrowUpRight, FlaskConical, Loader2, Orbit, Play, ShieldAlert, Waves, Zap } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { stepMission } from "@/lib/api";
import { buildLayerSummaries, formatLabel, getExecutiveSummary } from "@/lib/mission-view";
import { loadSimulationSession, saveSimulationSession, type SimulationSession } from "@/lib/simulation-session";
import type {
  MissionEventsPayload,
  MissionStatus,
} from "@/lib/types";

interface SimulationRouteState {
  session?: SimulationSession;
}

const statusClass = (status: MissionStatus) => {
  if (status === "CRITICAL") {
    return "border-neon-red/40 bg-neon-red/15 text-neon-red";
  }
  if (status === "WATCH") {
    return "border-neon-orange/40 bg-neon-orange/15 text-neon-orange";
  }
  return "border-neon-green/40 bg-neon-green/15 text-neon-green";
};

const parseOptionalNumber = (value: string): number | undefined => {
  const trimmed = value.trim();
  if (!trimmed) {
    return undefined;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : undefined;
};

const hasSimulationSessionShape = (value: unknown): value is SimulationSession => {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return Boolean(candidate.mission_state && candidate.selected_system && candidate.ranked_candidates);
};

const parseSystemChange = (value: string) => {
  const [rawKind, rawTransition] = value.split(":", 2);
  if (!rawKind || !rawTransition || !rawTransition.includes("->")) {
    return null;
  }

  const [from, to] = rawTransition.split("->", 2);
  return {
    kind: rawKind,
    from: from || "",
    to: to || "",
  };
};

const Simulation = () => {
  const location = useLocation();
  const initialBundle = useMemo(() => {
    const state = (location.state as SimulationRouteState | null)?.session;
    if (hasSimulationSessionShape(state)) {
      return {
        current: state,
        previous: null,
      };
    }
    return loadSimulationSession();
  }, [location.state]);

  const [session, setSession] = useState<SimulationSession | null>(initialBundle?.current ?? null);
  const [previousSession, setPreviousSession] = useState<SimulationSession | null>(initialBundle?.previous ?? null);
  const [timeStep, setTimeStep] = useState("1");
  const [waterDrop, setWaterDrop] = useState("");
  const [energyDrop, setEnergyDrop] = useState("");
  const [contamination, setContamination] = useState("");
  const [yieldDrop, setYieldDrop] = useState("");
  const [isApplyingStep, setIsApplyingStep] = useState(false);

  useEffect(() => {
    if (!session) {
      return;
    }
    saveSimulationSession(session, previousSession);
  }, [previousSession, session]);

  if (!session) {
    return (
      <div className="min-h-screen w-full bg-background p-3">
        <div className="mx-auto flex min-h-[calc(100vh-1.5rem)] max-w-[1200px] items-center justify-center">
          <div className="glass-panel flex w-full max-w-2xl flex-col gap-4 overflow-hidden p-6 text-center">
            <div className="space-y-2">
              <h1 className="text-lg font-bold tracking-wide neon-text-cyan">Ecosystem Simulation</h1>
              <p className="text-sm text-muted-foreground">
                No active simulation session was found. Start from the mission planner to choose a biological stack
                and launch a new ecosystem simulation.
              </p>
            </div>
            <div className="flex justify-center">
              <Button asChild className="bg-primary text-primary-foreground hover:bg-primary/90">
                <Link to="/">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back To Mission Planner
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const layerSummaries = buildLayerSummaries(session);
  const previousLayerSummaries = previousSession ? buildLayerSummaries(previousSession) : [];
  const cropLayer = layerSummaries.find((layer) => layer.type === "crop");
  const missionState = session.mission_state;
  const latestEvents = "events" in session ? session.events ?? null : null;
  const systemChanges = "system_changes" in session ? session.system_changes : [];
  const parsedSystemChanges = systemChanges
    .map(parseSystemChange)
    .filter((item): item is NonNullable<ReturnType<typeof parseSystemChange>> => Boolean(item));
  const riskDelta = "risk_delta" in session ? session.risk_delta : null;
  const executiveSummary = getExecutiveSummary(session);
  const reasoningSummary =
    session.llm_analysis?.reasoning_summary ||
    session.explanations?.system_reasoning ||
    "Deterministic simulation analysis is active for this ecosystem session.";
  const improvementCues = session.llm_analysis?.improvements ?? [];
  const alternativeText =
    Object.values(session.llm_analysis?.alternative ?? {})
      .slice(0, 2)
      .join(" / ") || "None suggested";
  const adaptationSummary =
    ("adaptation_summary" in session ? session.adaptation_summary : "") ||
    session.ui_enhanced?.adaptation_summary ||
    "Simulation initialized with the selected biological stack. Apply mission events to see how the loop responds.";
  const currentRisk = missionState.system_metrics.risk_level;
  const previousRisk =
    typeof riskDelta === "number"
      ? Math.max(0, currentRisk - riskDelta)
      : previousSession?.mission_state.system_metrics.risk_level ?? null;
  const riskTrend =
    riskDelta === null
      ? "Baseline"
      : riskDelta > 0.05
        ? "Increased"
        : riskDelta < -0.05
          ? "Decreased"
          : "Stable";
  const previousPlantSystem =
    previousLayerSummaries.find((layer) => layer.type === "crop")?.supportSystem ||
    parsedSystemChanges.find((item) => item.kind === "grow_system")?.from ||
    null;
  const currentPlantSystem = cropLayer?.supportSystem || parsedSystemChanges.find((item) => item.kind === "grow_system")?.to || null;
  const previousStackLabel =
    previousLayerSummaries.length > 0
      ? previousLayerSummaries.map((layer) => formatLabel(layer.name)).join(" + ")
      : layerSummaries.length > 0 && parsedSystemChanges.some((item) => ["crop", "algae", "microbial"].includes(item.kind))
        ? layerSummaries
            .map((layer) => {
              const change = parsedSystemChanges.find((item) => item.kind === layer.type);
              return formatLabel(change?.from || layer.name);
            })
            .join(" + ")
        : null;
  const currentStackLabel =
    layerSummaries.length > 0
      ? layerSummaries.map((layer) => formatLabel(layer.name)).join(" + ")
      : "Unavailable";
  const humanSystemChanges = parsedSystemChanges.map((item) => {
    const label = item.kind === "grow_system" ? "Plant system" : `${formatLabel(item.kind)} layer`;
    return `${label}: ${formatLabel(item.from)} -> ${formatLabel(item.to)}`;
  });

  const metricCards = [
    { label: "Oxygen Level", value: missionState.system_metrics.oxygen_level, accent: "bg-neon-cyan" },
    { label: "CO2 Balance", value: missionState.system_metrics.co2_balance, accent: "bg-neon-green" },
    { label: "Food Supply", value: missionState.system_metrics.food_supply, accent: "bg-neon-gold" },
    {
      label: "Nutrient Cycle Efficiency",
      value: missionState.system_metrics.nutrient_cycle_efficiency,
      accent: "bg-neon-orange",
    },
    { label: "Risk Level", value: missionState.system_metrics.risk_level, accent: "bg-neon-red" },
  ];
  const layerTransitions = previousSession
    ? layerSummaries
        .map((layer) => {
          const previous = buildLayerSummaries(previousSession).find((item) => item.type === layer.type);
          if (!previous) {
            return null;
          }
          return {
            label: layer.label,
            previousName: previous.name,
            currentName: layer.name,
            previousRank: previous.rank,
            currentRank: layer.rank,
            changed: previous.name !== layer.name || previous.rank !== layer.rank,
          };
        })
        .filter((item): item is NonNullable<typeof item> => Boolean(item))
    : [];

  const handleApplyStep = async () => {
    const parsedTimeStep = Math.max(1, Math.min(365, Number.parseInt(timeStep || "1", 10) || 1));
    const parsedWater = parseOptionalNumber(waterDrop);
    const parsedEnergy = parseOptionalNumber(energyDrop);
    const parsedContamination = parseOptionalNumber(contamination);
    const parsedYield = parseOptionalNumber(yieldDrop);

    const events: MissionEventsPayload = {};
    if (parsedWater !== undefined) {
      events.water_drop = parsedWater;
    }
    if (parsedEnergy !== undefined) {
      events.energy_drop = parsedEnergy;
    }
    if (parsedContamination !== undefined) {
      events.contamination = parsedContamination;
    }
    if (parsedYield !== undefined) {
      events.yield_variation = -Math.abs(parsedYield);
    }

    setIsApplyingStep(true);
    try {
      const currentSession = session;
      const response = await stepMission({
        mission_id: missionState.mission_id,
        time_step: parsedTimeStep,
        events: Object.keys(events).length > 0 ? events : undefined,
      });
      setPreviousSession(currentSession);
      setSession(response);
      saveSimulationSession(response, currentSession);
      setWaterDrop("");
      setEnergyDrop("");
      setContamination("");
      setYieldDrop("");
      toast.success("Simulation step applied", {
        description: response.adaptation_summary,
      });
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Unable to advance the simulation.";
      toast.error("Simulation step failed", { description: message });
    } finally {
      setIsApplyingStep(false);
    }
  };

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-background p-3">
      <div className="mx-auto flex min-h-[calc(100vh-1.5rem)] w-full max-w-[1800px] flex-col gap-3">
        <div className="glass-panel overflow-hidden p-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-neon-cyan blink" />
                <h1 className="text-sm font-bold font-mono uppercase tracking-[0.28em] neon-text-cyan">
                  Ecosystem Simulation
                </h1>
                <span className={`rounded border px-2 py-0.5 text-[10px] font-mono ${statusClass(session.mission_status)}`}>
                  {session.mission_status}
                </span>
              </div>
              <p className="max-w-4xl text-sm text-foreground/80">
                {executiveSummary || "Simulation session is active."}
              </p>
              <div className="flex flex-wrap gap-3 text-[11px] font-mono text-muted-foreground">
                <span>Environment: <span className="text-foreground">{formatLabel(missionState.environment)}</span></span>
                <span>Duration: <span className="text-foreground">{formatLabel(missionState.duration)}</span></span>
                <span>Goal: <span className="text-foreground">{formatLabel(missionState.goal)}</span></span>
                <span>Time: <span className="text-foreground">{missionState.time} day(s)</span></span>
                <span>
                  Mode: <span className="text-neon-green">Deterministic Simulation</span>
                </span>
                <span>
                  Plant system:{" "}
                  <span className="text-neon-cyan">
                    {formatLabel(cropLayer?.supportSystem || "unknown")}
                  </span>
                </span>
              </div>
            </div>

            <div className="flex shrink-0 items-start gap-2">
              <div className="rounded-lg border border-neon-orange/25 bg-neon-orange/5 px-3 py-2 text-right">
                <p className="text-[9px] font-mono uppercase tracking-wider text-neon-orange">Operational Note</p>
                <p className="mt-1 max-w-sm text-xs leading-relaxed text-foreground/75">{session.operational_note}</p>
              </div>
              <Button asChild variant="outline" className="border-glass-border bg-muted/20 text-foreground hover:bg-muted/35">
                <Link to="/">
                  <ArrowLeft className="h-4 w-4" />
                  Back
                </Link>
              </Button>
            </div>
          </div>
        </div>

        <div className="glass-panel flex min-w-0 flex-col gap-4 overflow-hidden p-4">
          <div className="flex items-center gap-2">
            <Orbit className="h-4 w-4 text-neon-cyan" />
            <h2 className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
              Active Ecosystem Stack
            </h2>
          </div>
          <div className="space-y-3">
            {layerSummaries.length > 0 ? (
              layerSummaries.map((layer) => (
                <div
                  key={`${layer.type}-${layer.name}-${missionState.time}`}
                  className="rounded-lg border border-glass-border bg-black/10 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 space-y-1">
                      <div className={`inline-flex rounded-md border px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider ${layer.accentClass}`}>
                        {layer.label}
                      </div>
                      <h3 className="text-lg font-semibold text-foreground">{formatLabel(layer.name)}</h3>
                      <p className="max-w-4xl text-sm leading-relaxed text-foreground/78">{layer.summary}</p>
                    </div>
                    <div className="grid min-w-[180px] grid-cols-2 gap-2 text-right text-[10px] font-mono text-muted-foreground">
                      <div>
                        <p>Mission Fit</p>
                        <p className="text-sm text-foreground">{Math.round(layer.missionFitScore * 100)}%</p>
                      </div>
                      <div>
                        <p>Risk</p>
                        <p className="text-sm text-foreground">{Math.round(layer.riskScore * 100)}%</p>
                      </div>
                      <div>
                        <p>Domain Score</p>
                        <p className="text-sm text-foreground">{layer.domainScore.toFixed(2)}</p>
                      </div>
                      <div>
                        <p>Current Rank</p>
                        <p className="text-sm text-foreground">{layer.rank ? `#${layer.rank}` : "N/A"}</p>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center gap-3 text-[10px] font-mono text-muted-foreground">
                    {layer.type === "crop" && (
                      <span>
                        Support system:{" "}
                        <span className="text-neon-cyan">
                          {formatLabel(layer.supportSystem || "unknown")}
                        </span>
                      </span>
                    )}
                    <span>
                      Ranked candidates available:{" "}
                      <span className="text-foreground">{session.ranked_candidates?.[layer.type]?.length ?? 0}</span>
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-lg border border-glass-border bg-black/10 p-4 text-sm text-muted-foreground">
                Selected ecosystem detail fields were incomplete, so the simulation is falling back to metrics and
                mission-state data only.
              </div>
            )}
          </div>
        </div>

        <div className="grid auto-rows-[minmax(260px,1fr)] grid-cols-1 gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="glass-panel flex min-h-[260px] min-w-0 flex-col gap-3 overflow-hidden p-4">
            <div className="flex items-center gap-2">
              <Orbit className="h-4 w-4 text-neon-cyan" />
              <h2 className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
                Current System Metrics
              </h2>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1">
              {metricCards.map((metric) => (
                <div key={metric.label} className="rounded-lg border border-glass-border bg-muted/10 p-3">
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                      {metric.label}
                    </span>
                    <span className="text-sm font-mono text-foreground">{Math.round(metric.value)}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div className={`h-full rounded-full ${metric.accent}`} style={{ width: `${metric.value}%` }} />
                  </div>
                </div>
              ))}
            </div>
            <div className="rounded-lg border border-glass-border bg-muted/10 px-3 py-2 text-[11px] font-mono text-muted-foreground">
              Constraints now run at water={formatLabel(missionState.constraints.water)}, energy=
              {formatLabel(missionState.constraints.energy)}, area={formatLabel(missionState.constraints.area)}.
            </div>
          </div>

          <div className="glass-panel flex min-h-[260px] min-w-0 flex-col gap-3 overflow-hidden p-4">
            <div className="flex items-center gap-2">
              <Play className="h-4 w-4 text-neon-orange" />
              <h2 className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
                Event Controls
              </h2>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <label className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Time Step</label>
                <Input value={timeStep} onChange={(event) => setTimeStep(event.target.value)} type="number" min={1} max={365} className="h-9 border-glass-border bg-muted/50" />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-mono uppercase tracking-wider text-neon-cyan">Water Drop</label>
                <Input value={waterDrop} onChange={(event) => setWaterDrop(event.target.value)} type="number" min={0} max={100} className="h-9 border-glass-border bg-muted/50" placeholder="0-100" />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-mono uppercase tracking-wider text-neon-gold">Energy Drop</label>
                <Input value={energyDrop} onChange={(event) => setEnergyDrop(event.target.value)} type="number" min={0} max={100} className="h-9 border-glass-border bg-muted/50" placeholder="0-100" />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-mono uppercase tracking-wider text-neon-red">Contamination</label>
                <Input value={contamination} onChange={(event) => setContamination(event.target.value)} type="number" min={0} max={100} className="h-9 border-glass-border bg-muted/50" placeholder="0-100" />
              </div>
              <div className="space-y-1 sm:col-span-2">
                <label className="text-[10px] font-mono uppercase tracking-wider text-neon-purple">Yield Drop</label>
                <Input value={yieldDrop} onChange={(event) => setYieldDrop(event.target.value)} type="number" min={0} max={100} className="h-9 border-glass-border bg-muted/50" placeholder="Percent reduction applied to the active crop layer" />
              </div>
            </div>

            <div className="rounded-lg border border-glass-border bg-black/10 px-3 py-2 text-xs text-muted-foreground">
              Enter only the events you want to apply. Leaving all event fields empty will still advance the mission by
              the selected time step.
            </div>

            <Button
              type="button"
              onClick={handleApplyStep}
              disabled={isApplyingStep}
              className="mt-auto h-10 bg-primary font-bold uppercase tracking-wider text-primary-foreground hover:bg-primary/90"
            >
              {isApplyingStep ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FlaskConical className="mr-2 h-4 w-4" />}
              {isApplyingStep ? "Applying Step" : "Apply Simulation Step"}
            </Button>
          </div>
        </div>

        <div className="grid auto-rows-[minmax(220px,1fr)] grid-cols-1 gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="glass-panel flex min-h-[220px] min-w-0 flex-col gap-3 overflow-hidden p-4">
            <div className="flex items-center gap-2">
              <Waves className="h-4 w-4 text-neon-cyan" />
              <h2 className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
                Adaptation & Results
              </h2>
            </div>
            <div className="rounded-lg border border-glass-border bg-terminal/40 p-3">
              <p className="text-xs leading-relaxed text-foreground/80">{adaptationSummary}</p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Risk Shift</p>
                <p className="mt-2 text-sm font-mono text-foreground">
                  {previousRisk !== null ? `${previousRisk.toFixed(2)}% -> ${currentRisk.toFixed(2)}%` : `${currentRisk.toFixed(2)}%`}
                </p>
                <p className={`mt-1 text-xs font-mono ${riskTrend === "Increased" ? "text-neon-red" : riskTrend === "Decreased" ? "text-neon-green" : "text-muted-foreground"}`}>
                  {riskTrend}
                </p>
              </div>
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Plant System</p>
                <p className="mt-2 text-sm font-mono text-foreground">
                  {previousPlantSystem ? `${formatLabel(previousPlantSystem)} -> ${formatLabel(currentPlantSystem || "unknown")}` : formatLabel(currentPlantSystem || "unknown")}
                </p>
                <p className="mt-1 text-xs font-mono text-muted-foreground">
                  {previousPlantSystem && previousPlantSystem !== currentPlantSystem ? "System shifted" : "System held"}
                </p>
              </div>
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Stack Transition</p>
                <p className="mt-2 text-xs leading-relaxed text-foreground">
                  {previousStackLabel ? `${previousStackLabel} -> ${currentStackLabel}` : currentStackLabel}
                </p>
                <p className="mt-1 text-xs font-mono text-muted-foreground">
                  {previousStackLabel && previousStackLabel !== currentStackLabel ? "Layer change detected" : "Current stack active"}
                </p>
              </div>
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Current Time</p>
                <p className="mt-2 text-lg font-mono text-foreground">{missionState.time} day(s)</p>
                <p className="mt-1 text-xs font-mono text-muted-foreground">
                  {latestEvents ? Object.values(latestEvents).filter((value) => value !== null && value !== undefined).length : 0} active event(s)
                </p>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-auto rounded-lg border border-glass-border bg-muted/10 p-3">
              <p className="mb-2 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">System Changes</p>
              {humanSystemChanges.length > 0 ? (
                <div className="space-y-2 text-xs text-foreground/80">
                  {humanSystemChanges.map((change) => (
                    <p key={change}>{change}</p>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">
                  No configuration change has been required yet. The current biological stack is still holding.
                </p>
              )}
            </div>

            <div className="min-h-0 overflow-auto rounded-lg border border-glass-border bg-muted/10 p-3">
              <p className="mb-2 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Layer Changes</p>
              {layerTransitions.some((item) => item.changed) ? (
                <div className="space-y-2 text-xs text-foreground/80">
                  {layerTransitions
                    .filter((item) => item.changed)
                    .map((item) => {
                      const rankDirection =
                        item.previousRank !== null && item.currentRank !== null
                          ? item.currentRank < item.previousRank
                            ? "up"
                            : item.currentRank > item.previousRank
                              ? "down"
                              : "same"
                          : "same";
                      return (
                        <div key={item.label} className="rounded border border-glass-border/70 bg-black/10 p-2">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                              {item.label}
                            </span>
                            {rankDirection === "up" ? (
                              <span className="inline-flex items-center gap-1 text-neon-green">
                                <ArrowUpRight className="h-3 w-3" />
                                Rank improved
                              </span>
                            ) : rankDirection === "down" ? (
                              <span className="inline-flex items-center gap-1 text-neon-red">
                                <ArrowDownRight className="h-3 w-3" />
                                Rank dropped
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-muted-foreground">
                                <ArrowRight className="h-3 w-3" />
                                Re-evaluated
                              </span>
                            )}
                          </div>
                          <p className="mt-1">
                            {formatLabel(item.previousName)} <ArrowRight className="mx-1 inline h-3 w-3" />
                            {formatLabel(item.currentName)}
                          </p>
                          <p className="mt-1 text-muted-foreground">
                            Rank {item.previousRank ? `#${item.previousRank}` : "N/A"}{" "}
                            <ArrowRight className="mx-1 inline h-3 w-3" />
                            {item.currentRank ? `#${item.currentRank}` : "N/A"}
                          </p>
                        </div>
                      );
                    })}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">
                  No layer switch or visible rank shift has occurred yet in this simulation session.
                </p>
              )}
            </div>
          </div>

          <div className="glass-panel flex min-h-[220px] min-w-0 flex-col gap-3 overflow-hidden p-4">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-neon-orange" />
              <h2 className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
                Deterministic Analysis & Event Trace
              </h2>
            </div>

            <div className="rounded-lg border border-glass-border bg-terminal p-3">
              <p className="text-xs font-mono leading-relaxed text-foreground/80">
                {reasoningSummary}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Active Events</p>
                {latestEvents ? (
                  <div className="mt-2 space-y-1 text-xs text-foreground/80">
                    {Object.entries(latestEvents)
                      .filter(([, value]) => value !== null && value !== undefined)
                      .map(([key, value]) => (
                        <p key={key}>
                          {formatLabel(key)}: <span className="text-foreground">{String(value)}</span>
                        </p>
                      ))}
                  </div>
                ) : (
                  <p className="mt-2 text-xs text-muted-foreground">No events applied yet in this simulation session.</p>
                )}
              </div>

              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Stability Cues</p>
                <div className="mt-2 space-y-1 text-xs text-foreground/80">
                  {improvementCues.slice(0, 3).map((item) => (
                    <p key={item}>{item}</p>
                  ))}
                  {improvementCues.length === 0 && (
                    <p className="text-muted-foreground">No additional deterministic stability cue was raised for the current state.</p>
                  )}
                </div>
              </div>
            </div>

            <div className="mt-auto grid grid-cols-1 gap-2 text-[11px] font-mono text-muted-foreground sm:grid-cols-2">
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p>Mission ID</p>
                <p className="mt-1 break-all text-foreground">{missionState.mission_id}</p>
              </div>
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p>Reference Concept</p>
                <p className="mt-1 text-foreground">
                  {alternativeText}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="glass-panel flex min-h-[120px] min-w-0 flex-col gap-2 overflow-hidden p-3">
            <div className="flex items-center gap-2">
              <Waves className="h-4 w-4 text-neon-cyan" />
              <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Water Margin</span>
            </div>
            <p className="text-2xl font-mono text-foreground">{Math.round(missionState.resources.water)}%</p>
          </div>
          <div className="glass-panel flex min-h-[120px] min-w-0 flex-col gap-2 overflow-hidden p-3">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-neon-gold" />
              <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Energy Margin</span>
            </div>
            <p className="text-2xl font-mono text-foreground">{Math.round(missionState.resources.energy)}%</p>
          </div>
          <div className="glass-panel flex min-h-[120px] min-w-0 flex-col gap-2 overflow-hidden p-3">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-neon-purple" />
              <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Area Margin</span>
            </div>
            <p className="text-2xl font-mono text-foreground">{Math.round(missionState.resources.area)}%</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Simulation;
