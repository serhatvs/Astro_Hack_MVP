import { useMemo, useState } from "react";
import { ArrowLeft, FlaskConical, Loader2, Orbit, Play, ShieldAlert, Waves, Zap } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { toast } from "sonner";

import DomainCard from "@/components/dashboard/DomainCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { stepMission } from "@/lib/api";
import type {
  MissionEventsPayload,
  MissionStepResponse,
  MissionStatus,
  SimulationStartResponse,
} from "@/lib/types";

type SimulationSession = MissionStepResponse | SimulationStartResponse;

interface SimulationRouteState {
  session?: SimulationStartResponse;
}

const uiNoteKeyByDomain = {
  crop: "crop_note",
  algae: "algae_note",
  microbial: "microbial_note",
} as const;

const formatLabel = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

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

const isSimulationStartResponse = (value: unknown): value is SimulationStartResponse => {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return Boolean(candidate.mission_state && candidate.selected_system && candidate.ranked_candidates);
};

const Simulation = () => {
  const location = useLocation();
  const initialSession = useMemo(() => {
    const state = (location.state as SimulationRouteState | null)?.session;
    return isSimulationStartResponse(state) ? state : null;
  }, [location.state]);

  const [session, setSession] = useState<SimulationSession | null>(initialSession);
  const [timeStep, setTimeStep] = useState("1");
  const [waterDrop, setWaterDrop] = useState("");
  const [energyDrop, setEnergyDrop] = useState("");
  const [contamination, setContamination] = useState("");
  const [yieldDrop, setYieldDrop] = useState("");
  const [isApplyingStep, setIsApplyingStep] = useState(false);

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

  const selectedStack = [
    session.selected_system.crop,
    session.selected_system.algae,
    session.selected_system.microbial,
  ];
  const missionState = session.mission_state;
  const latestEvents = "events" in session ? session.events ?? null : null;
  const systemChanges = "system_changes" in session ? session.system_changes : [];
  const riskDelta = "risk_delta" in session ? session.risk_delta : null;
  const adaptationSummary =
    ("adaptation_summary" in session ? session.adaptation_summary : "") ||
    session.ui_enhanced.adaptation_summary ||
    "Simulation initialized with the selected biological stack. Apply mission events to see how the loop responds.";

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
      const response = await stepMission({
        mission_id: missionState.mission_id,
        time_step: parsedTimeStep,
        events: Object.keys(events).length > 0 ? events : undefined,
      });
      setSession(response);
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
                {session.ui_enhanced.executive_summary || session.explanations.executive_summary}
              </p>
              <div className="flex flex-wrap gap-3 text-[11px] font-mono text-muted-foreground">
                <span>Environment: <span className="text-foreground">{formatLabel(missionState.environment)}</span></span>
                <span>Duration: <span className="text-foreground">{formatLabel(missionState.duration)}</span></span>
                <span>Goal: <span className="text-foreground">{formatLabel(missionState.goal)}</span></span>
                <span>Time: <span className="text-foreground">{missionState.time} day(s)</span></span>
                <span>
                  Plant system:{" "}
                  <span className="text-neon-cyan">
                    {formatLabel(session.selected_system.crop.support_system || "unknown")}
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

        <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 xl:grid-cols-3">
          {selectedStack.map((domain) => (
            <DomainCard
              key={`${domain.type}-${domain.name}-${missionState.time}`}
              domain={domain}
              rankedCandidates={session.ranked_candidates[domain.type]}
              summaryOverride={session.ui_enhanced[uiNoteKeyByDomain[domain.type]]}
            />
          ))}
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

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Risk Delta</p>
                <p className={`mt-2 text-lg font-mono ${riskDelta !== null && riskDelta > 0 ? "text-neon-red" : riskDelta !== null && riskDelta < 0 ? "text-neon-green" : "text-foreground"}`}>
                  {riskDelta !== null ? `${riskDelta >= 0 ? "+" : ""}${riskDelta.toFixed(3)}` : "N/A"}
                </p>
              </div>
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Current Time</p>
                <p className="mt-2 text-lg font-mono text-foreground">{missionState.time} day(s)</p>
              </div>
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Last Event Count</p>
                <p className="mt-2 text-lg font-mono text-foreground">
                  {latestEvents ? Object.values(latestEvents).filter((value) => value !== null && value !== undefined).length : 0}
                </p>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-auto rounded-lg border border-glass-border bg-muted/10 p-3">
              <p className="mb-2 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">System Changes</p>
              {systemChanges.length > 0 ? (
                <div className="space-y-2 text-xs text-foreground/80">
                  {systemChanges.map((change) => (
                    <p key={change}>{change}</p>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">
                  No configuration change has been required yet. The current biological stack is still holding.
                </p>
              )}
            </div>
          </div>

          <div className="glass-panel flex min-h-[220px] min-w-0 flex-col gap-3 overflow-hidden p-4">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-neon-orange" />
              <h2 className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
                Critic & Event Trace
              </h2>
            </div>

            <div className="rounded-lg border border-glass-border bg-terminal p-3">
              <p className="text-xs font-mono leading-relaxed text-foreground/80">
                {session.llm_analysis.reasoning_summary}
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
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Improvement Cues</p>
                <div className="mt-2 space-y-1 text-xs text-foreground/80">
                  {session.llm_analysis.improvements.slice(0, 3).map((item) => (
                    <p key={item}>{item}</p>
                  ))}
                  {session.llm_analysis.improvements.length === 0 && (
                    <p className="text-muted-foreground">No additional refinement cue was raised for the current state.</p>
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
                <p>Alternative Concept</p>
                <p className="mt-1 text-foreground">
                  {Object.values(session.llm_analysis.alternative).slice(0, 2).join(" / ") || "None suggested"}
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
