import { useEffect, useMemo, useState } from "react";
import { ArrowDownRight, ArrowLeft, ArrowRight, ArrowUpRight, FlaskConical, Loader2, Orbit, Play, ShieldAlert, Waves, Zap } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { stepMission } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { buildLayerSummaries, formatLabel, getExecutiveSummary } from "@/lib/mission-view";
import { loadSimulationSession, saveSimulationSession, type SimulationSession } from "@/lib/simulation-session";
import type { MissionEventsPayload, MissionStatus } from "@/lib/types";

interface SimulationRouteState {
  session?: SimulationSession;
}

type SimulationStatusLabel = "running" | "complete" | "failure";
type EndReasonKey = "water_depleted" | "energy_depleted" | "risk_collapse" | "duration_complete";

const statusClass = (status: MissionStatus) => {
  if (status === "CRITICAL") {
    return "border-neon-red/40 bg-neon-red/15 text-neon-red";
  }
  if (status === "WATCH") {
    return "border-neon-orange/40 bg-neon-orange/15 text-neon-orange";
  }
  return "border-neon-green/40 bg-neon-green/15 text-neon-green";
};

const durationWeekTargets = {
  short: 12,
  medium: 24,
  long: 48,
} as const;
const WEEKLY_STEP = 1;

const formatPercentish = (value?: number | null) => {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return null;
  }
  const normalized = value <= 1 ? value * 100 : value;
  return `${Math.round(normalized)}%`;
};

const formatDeltaArrow = (delta?: number | null) => {
  if (typeof delta !== "number" || Number.isNaN(delta) || Math.abs(delta) < 0.01) {
    return {
      arrow: "->",
      tone: "text-muted-foreground",
      trendKey: "trend_stable",
      deltaLabel: null,
    };
  }

  if (delta > 0) {
    return {
      arrow: "^",
      tone: "text-neon-red",
      trendKey: "trend_increased",
      deltaLabel: `+${delta.toFixed(2)}`,
    };
  }

  return {
    arrow: "v",
    tone: "text-neon-green",
    trendKey: "trend_decreased",
    deltaLabel: delta.toFixed(2),
  };
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

const eventLabelKey = (key: keyof MissionEventsPayload) => {
  if (key === "water_drop") {
    return "water_drop";
  }
  if (key === "energy_drop") {
    return "energy_drop";
  }
  if (key === "contamination") {
    return "contamination";
  }
  return "yield_drop";
};

const formatEventLabel = (
  value: string,
  t: (key: string, values?: Record<string, string | number>) => string,
) => {
  if (value === "water_drop") {
    return t("water_drop");
  }
  if (value === "energy_drop") {
    return t("energy_drop");
  }
  if (value === "contamination") {
    return t("contamination");
  }
  if (value === "yield_variation" || value === "yield_drop") {
    return t("yield_drop");
  }
  return formatLabel(value);
};

const buildEventFeedback = (
  events: MissionEventsPayload | null | undefined,
  t: (key: string, values?: Record<string, string | number>) => string,
) => {
  if (!events) {
    return t("baseline_week_only");
  }

  const active = Object.entries(events).filter(([, value]) => value !== null && value !== undefined);
  if (active.length === 0) {
    return t("baseline_week_only");
  }

  const fragments = active.map(([key, value]) => {
    const label = t(eventLabelKey(key as keyof MissionEventsPayload));
    if (typeof value === "number") {
      return `${label} ${value}`;
    }
    return label;
  });

  return `${fragments.join(" | ")} ${t("applied_suffix")}`;
};

const buildImpactSnapshot = (
  events: MissionEventsPayload | null | undefined,
  riskDelta: number | null,
  systemChanged: boolean,
  t: (key: string, values?: Record<string, string | number>) => string,
) => {
  const fragments: string[] = [];

  if (events?.water_drop !== undefined) {
    fragments.push(t("impact_water_drop"));
  }
  if (events?.energy_drop !== undefined) {
    fragments.push(t("impact_energy_drop"));
  }
  if (events?.contamination !== undefined) {
    fragments.push(t("impact_contamination"));
  }
  if (events?.yield_variation !== undefined && events.yield_variation < 0) {
    fragments.push(t("impact_yield_drop"));
  }

  if (fragments.length === 0) {
    return t("impact_baseline");
  }

  const base = fragments.slice(0, 2).join(` ${t("and_connector")} `);
  const riskEffect =
    riskDelta === null
      ? t("risk_under_observation")
      : riskDelta > 0.05
        ? t("risk_pushed_upward")
        : riskDelta < -0.05
          ? t("risk_reduced_pressure")
          : t("risk_held_baseline");
  const systemEffect = systemChanged ? ` ${t("forcing_stack_adjustment")}` : "";

  return `${base}. ${riskEffect.charAt(0).toUpperCase()}${riskEffect.slice(1)}${systemEffect}.`;
};

const buildLayerInteractionHints = (
  type: "crop" | "algae" | "microbial",
  metrics: Record<string, number> | undefined,
  t: (key: string, values?: Record<string, string | number>) => string,
) => {
  if (!metrics) {
    return [];
  }

  const pickMetric = (...keys: string[]) => {
    for (const key of keys) {
      const value = metrics[key];
      const formatted = formatPercentish(typeof value === "number" ? value : null);
      if (formatted) {
        return formatted;
      }
    }
    return null;
  };

  if (type === "crop") {
    return [
      [t("yield_hint"), pickMetric("calorie_yield", "edible_yield")],
      [t("water_use_hint"), pickMetric("water_need")],
    ].filter((item): item is [string, string] => Boolean(item[1]));
  }

  if (type === "algae") {
    return [
      [t("o2_support_hint"), pickMetric("oxygen_contribution")],
      [t("biomass_hint"), pickMetric("biomass_production", "protein_potential")],
    ].filter((item): item is [string, string] => Boolean(item[1]));
  }

  return [
    [t("nutrient_loop_hint"), pickMetric("nutrient_conversion_capability", "loop_closure_contribution")],
    [t("recycling_hint"), pickMetric("waste_recycling_efficiency")],
  ].filter((item): item is [string, string] => Boolean(item[1]));
};

const resolveEndReason = (
  endReason: string | null | undefined,
  simulationStatus: SimulationStatusLabel,
  riskLevel: number,
  waterLevel: number,
  energyLevel: number,
  maxWeeks: number,
  t: (key: string, values?: Record<string, string | number>) => string,
): { key: EndReasonKey; text: string } | null => {
  if (simulationStatus === "running") {
    return null;
  }

  if (endReason === "water_depleted") {
    return {
      key: "water_depleted",
      text: t("end_reason_water"),
    };
  }

  if (endReason === "energy_depleted") {
    return {
      key: "energy_depleted",
      text: t("end_reason_energy"),
    };
  }

  if (endReason === "risk_collapse") {
    return {
      key: "risk_collapse",
      text: t("end_reason_risk"),
    };
  }

  if (endReason === "duration_complete") {
    return {
      key: "duration_complete",
      text: t("end_reason_duration", { weeks: maxWeeks }),
    };
  }

  if (waterLevel <= 0) {
    return {
      key: "water_depleted",
      text: t("end_reason_water"),
    };
  }

  if (energyLevel <= 0) {
    return {
      key: "energy_depleted",
      text: t("end_reason_energy"),
    };
  }

  if (simulationStatus === "failure" || riskLevel >= 80) {
    return {
      key: "risk_collapse",
      text: t("end_reason_risk"),
    };
  }

  return {
    key: "duration_complete",
    text: t("end_reason_duration", { weeks: maxWeeks }),
  };
};

const Simulation = () => {
  const { t } = useI18n();
  const location = useLocation();
  const navigate = useNavigate();
  const initialBundle = useMemo(() => {
    const state = (location.state as SimulationRouteState | null)?.session;
    if (hasSimulationSessionShape(state)) {
      return {
        current: state,
        previous: null,
        initial: state,
      };
    }
    return loadSimulationSession();
  }, [location.state]);

  const [session, setSession] = useState<SimulationSession | null>(initialBundle?.current ?? null);
  const [previousSession, setPreviousSession] = useState<SimulationSession | null>(initialBundle?.previous ?? null);
  const [initialSession, setInitialSession] = useState<SimulationSession | null>(initialBundle?.initial ?? initialBundle?.current ?? null);
  const [waterDrop, setWaterDrop] = useState("");
  const [energyDrop, setEnergyDrop] = useState("");
  const [contamination, setContamination] = useState("");
  const [yieldDrop, setYieldDrop] = useState("");
  const [isApplyingStep, setIsApplyingStep] = useState(false);
  const [showUpdateHighlight, setShowUpdateHighlight] = useState(false);

  useEffect(() => {
    if (!session) {
      return;
    }
    saveSimulationSession(session, previousSession, initialSession);
  }, [initialSession, previousSession, session]);

  useEffect(() => {
    if (!showUpdateHighlight) {
      return;
    }

    const timer = window.setTimeout(() => setShowUpdateHighlight(false), 1800);
    return () => window.clearTimeout(timer);
  }, [showUpdateHighlight]);

  if (!session) {
    return (
      <div className="min-h-screen w-full bg-background p-3">
        <div className="mx-auto flex min-h-[calc(100vh-1.5rem)] max-w-[1200px] items-center justify-center">
          <div className="glass-panel flex w-full max-w-2xl flex-col gap-4 overflow-hidden p-6 text-center">
            <div className="space-y-2">
              <h1 className="text-lg font-bold tracking-wide neon-text-cyan">{t("mission_validation_simulation")}</h1>
              <p className="text-sm text-muted-foreground">
                {t("no_active_simulation")}
              </p>
            </div>
            <div className="flex justify-center">
              <Button asChild className="bg-primary text-primary-foreground hover:bg-primary/90">
                <Link to="/">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  {t("back_to_mission_planner")}
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const layerSummaries = buildLayerSummaries(session, t);
  const previousLayerSummaries = previousSession ? buildLayerSummaries(previousSession, t) : [];
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
    t("deterministic_analysis_active");
  const improvementCues = session.llm_analysis?.improvements ?? [];
  const alternativeText =
    Object.values(session.llm_analysis?.alternative ?? {})
      .slice(0, 2)
      .join(" / ") || t("no_alternate_reference");
  const adaptationSummary =
    ("adaptation_summary" in session ? session.adaptation_summary : "") ||
    session.ui_enhanced?.adaptation_summary ||
    t("simulation_initialized");
  const maxWeeks = missionState.max_weeks ?? durationWeekTargets[missionState.duration];
  const recoveredWater = missionState.last_recovered_water ?? 0;
  const recoveryQueueSize = missionState.water_recovery_queue?.length ?? 0;
  const recoveryCycleWeeks = missionState.water_recovery_cycle_weeks ?? 0;
  const recoveryRate = missionState.water_recovery_rate ?? 0;
  const consumedEnergy = missionState.last_consumed_energy ?? 0;
  const solarEnergy = missionState.last_solar_energy ?? 0;
  const photosynthesisEnergy = missionState.last_photosynthesis_energy ?? 0;
  const currentRisk = missionState.system_metrics.risk_level;
  const initialRisk = missionState.initial_risk_level ?? currentRisk;
  const previousRisk =
    typeof riskDelta === "number"
      ? Math.max(0, currentRisk - riskDelta)
      : previousSession?.mission_state.system_metrics.risk_level ?? null;
  const simulationStatus: SimulationStatusLabel =
    missionState.end_reason === "water_depleted" ||
    missionState.end_reason === "energy_depleted" ||
    missionState.end_reason === "risk_collapse" ||
    currentRisk >= 85
      ? "failure"
      : missionState.end_reason === "duration_complete" || missionState.time >= maxWeeks
        ? "complete"
        : "running";
  const simulationStatusTone =
    simulationStatus === "failure"
      ? "border-neon-red/35 bg-neon-red/12 text-neon-red"
      : simulationStatus === "complete"
        ? "border-neon-green/35 bg-neon-green/12 text-neon-green"
        : "border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan";
  const endReason = resolveEndReason(
    missionState.end_reason,
    simulationStatus,
    currentRisk,
    missionState.resources.water,
    missionState.resources.energy,
    maxWeeks,
    t,
  );
  const endSummary =
    simulationStatus === "running"
      ? null
      : t("end_summary", {
          reason: endReason?.text || t("simulation_finished"),
          risk: currentRisk.toFixed(2),
          week: missionState.time,
          maxWeeks,
        });
  const riskTrendKey =
    riskDelta === null
      ? "trend_baseline"
      : riskDelta > 0.05
        ? "trend_increased"
        : riskDelta < -0.05
          ? "trend_decreased"
          : "trend_stable";
  const riskTrend = t(riskTrendKey);
  const riskDeltaIndicator = formatDeltaArrow(riskDelta);
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
      : t("unavailable");
  const humanSystemChanges = parsedSystemChanges.map((item) => {
    const label = item.kind === "grow_system" ? t("plant_system") : t(`${item.kind}_layer`);
    return `${label}: ${formatLabel(item.from)} -> ${formatLabel(item.to)}`;
  });
  const lastEventFeedback = buildEventFeedback(latestEvents, t);
  const impactSnapshot = buildImpactSnapshot(latestEvents, riskDelta, humanSystemChanges.length > 0, t);
  const recentTimeline = missionState.history.slice(-3).map((entry) => ({
    step: entry.time,
    event: entry.event,
    summary: entry.summary,
  }));
  const headerFacts = [
    {
      label: t("environment"),
      value: t(`environment_${missionState.environment}`),
      valueClass: "text-foreground",
    },
    {
      label: t("mission_duration"),
      value: t(`duration_${missionState.duration}`),
      valueClass: "text-foreground",
    },
    {
      label: t("current_week"),
      value: `${missionState.time} / ${maxWeeks}`,
      valueClass: "text-foreground",
    },
    {
      label: t("planned_horizon"),
      value: `${maxWeeks} ${t("weeks_unit")}`,
      valueClass: "text-foreground",
    },
    {
      label: t("mode"),
      value: t("deterministic_simulation"),
      valueClass: "text-neon-green",
    },
    {
      label: t("plant_system"),
      value: formatLabel(cropLayer?.supportSystem || t("unknown")),
      valueClass: "text-neon-cyan",
    },
  ];

  const metricCards = [
    {
      label: t("oxygen_level"),
      value: missionState.system_metrics.oxygen_level,
      previousValue: previousSession?.mission_state.system_metrics.oxygen_level ?? null,
      accent: "bg-neon-cyan",
    },
    {
      label: t("co2_balance"),
      value: missionState.system_metrics.co2_balance,
      previousValue: previousSession?.mission_state.system_metrics.co2_balance ?? null,
      accent: "bg-neon-green",
    },
    {
      label: t("food_supply"),
      value: missionState.system_metrics.food_supply,
      previousValue: previousSession?.mission_state.system_metrics.food_supply ?? null,
      accent: "bg-neon-gold",
    },
    {
      label: t("nutrient_cycle_efficiency"),
      value: missionState.system_metrics.nutrient_cycle_efficiency,
      previousValue: previousSession?.mission_state.system_metrics.nutrient_cycle_efficiency ?? null,
      accent: "bg-neon-orange",
    },
    {
      label: t("risk_level"),
      value: missionState.system_metrics.risk_level,
      previousValue: previousSession?.mission_state.system_metrics.risk_level ?? null,
      accent: "bg-neon-red",
    },
  ];
  const layerTransitions = previousSession
    ? layerSummaries
        .map((layer) => {
          const previous = buildLayerSummaries(previousSession, t).find((item) => item.type === layer.type);
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
        time_step: WEEKLY_STEP,
        events: Object.keys(events).length > 0 ? events : undefined,
      });
      setPreviousSession(currentSession);
      setSession(response);
      saveSimulationSession(response, currentSession, initialSession);
      setShowUpdateHighlight(true);
      setWaterDrop("");
      setEnergyDrop("");
      setContamination("");
      setYieldDrop("");
      toast.success(t("week_advanced"), {
        description: `${buildEventFeedback(Object.keys(events).length > 0 ? events : null, t)} ${response.adaptation_summary}`,
      });
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : t("unable_to_advance_simulation");
      toast.error(t("simulation_step_failed"), { description: message });
    } finally {
      setIsApplyingStep(false);
    }
  };

  const handleRunAgain = () => {
    if (!initialSession) {
      navigate("/");
      return;
    }

    setPreviousSession(null);
    setSession(initialSession);
    saveSimulationSession(initialSession, null, initialSession);
    setWaterDrop("");
    setEnergyDrop("");
    setContamination("");
    setYieldDrop("");
    setShowUpdateHighlight(false);
    toast.success(t("simulation_reset"), {
      description: t("simulation_reset_desc"),
    });
  };

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-background p-3">
      {simulationStatus !== "running" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/88 p-4 backdrop-blur-sm">
          <div
            className={`glass-panel flex w-full max-w-3xl flex-col gap-5 overflow-hidden border p-6 shadow-2xl ${
              simulationStatus === "failure"
                ? "border-neon-red/45 bg-background/95"
                : "border-neon-green/45 bg-background/95"
            }`}
          >
            <div className="space-y-3 text-center">
              <p className={`text-[11px] font-mono uppercase tracking-[0.28em] ${
                simulationStatus === "failure" ? "text-neon-red" : "text-neon-green"
              }`}>
                {t("simulation_over")}
              </p>
              <h2 className={`text-3xl font-bold tracking-wide ${
                simulationStatus === "failure" ? "text-neon-red" : "text-neon-green"
              }`}>
                {simulationStatus === "failure" ? t("system_failure") : t("simulation_complete")}
              </h2>
              <p className="mx-auto max-w-2xl text-sm leading-relaxed text-foreground/80">
                {endSummary}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-lg border border-glass-border bg-muted/10 p-4">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("survived_weeks")}</p>
                <p className="mt-2 text-2xl font-mono text-foreground">{missionState.time}</p>
              </div>
              <div className="rounded-lg border border-glass-border bg-muted/10 p-4">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("planned_duration")}</p>
                <p className="mt-2 text-lg font-mono text-foreground">{maxWeeks} {t("weeks_unit")}</p>
              </div>
              <div className="rounded-lg border border-glass-border bg-muted/10 p-4">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("final_risk_level")}</p>
                <p className={`mt-2 text-2xl font-mono ${
                  simulationStatus === "failure" ? "text-neon-red" : "text-neon-green"
                }`}>
                  {currentRisk.toFixed(2)}%
                </p>
              </div>
              <div className="rounded-lg border border-glass-border bg-muted/10 p-4">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("final_system_status")}</p>
                <p className="mt-2 text-lg font-mono text-foreground">{t(`mission_status_${session.mission_status.toLowerCase()}`)}</p>
              </div>
            </div>
            <div className="rounded-lg border border-glass-border bg-muted/10 p-4">
              <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("end_reason")}</p>
              <p className="mt-2 text-sm text-foreground">{endReason?.text || t("simulation_finished")}</p>
              <p className="mt-1 text-xs font-mono text-muted-foreground">
                {t("initial_to_final_risk", { initial: initialRisk.toFixed(2), final: currentRisk.toFixed(2) })}
              </p>
            </div>

            <div className="rounded-lg border border-glass-border bg-terminal/50 p-4">
              <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("final_deterministic_summary")}</p>
              <p className="mt-2 text-sm leading-relaxed text-foreground/80">{adaptationSummary}</p>
            </div>

            {recentTimeline.length > 0 && (
              <div className="rounded-lg border border-glass-border bg-muted/10 p-4">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("last_events")}</p>
                <div className="mt-2 space-y-2 text-sm text-foreground/80">
                  {recentTimeline.map((entry) => (
                    <p key={`${entry.step}-${entry.event}`}>
                      {t("week_label")} {entry.step}: {formatEventLabel(entry.event, t)}. {entry.summary}
                    </p>
                  ))}
                </div>
              </div>
            )}

            <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
              <Button
                type="button"
                onClick={handleRunAgain}
                className="h-11 bg-primary font-bold uppercase tracking-wider text-primary-foreground hover:bg-primary/90"
              >
                {t("run_again")}
              </Button>
              <Button asChild variant="outline" className="h-11 border-glass-border bg-muted/20 text-foreground hover:bg-muted/35">
                <Link to="/">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  {t("back_to_mission_planner")}
                </Link>
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className="mx-auto flex min-h-[calc(100vh-1.5rem)] w-full max-w-[1800px] flex-col gap-3">
        <div className="glass-panel overflow-hidden p-4">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div className="min-w-0 flex-1 space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <Button asChild variant="outline" className="h-9 border-glass-border bg-muted/20 text-foreground hover:bg-muted/35">
                  <Link to="/">
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    {t("back_to_mission_planner")}
                  </Link>
                </Button>
                <div className="h-2 w-2 rounded-full bg-neon-cyan blink" />
                <h1 className="text-sm font-bold font-mono uppercase tracking-[0.28em] neon-text-cyan">
                  {t("mission_validation_simulation")}
                </h1>
                <span className={`rounded border px-2 py-0.5 text-[10px] font-mono ${statusClass(session.mission_status)}`}>
                  {t(`mission_status_${session.mission_status.toLowerCase()}`)}
                </span>
                <span className={`rounded border px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider ${simulationStatusTone}`}>
                  {t("simulation_status")}: {simulationStatus === "failure" ? t("system_failure") : simulationStatus === "complete" ? t("simulation_complete") : t("running")}
                </span>
              </div>

              <p className="max-w-4xl text-sm text-foreground/80">
                {executiveSummary || t("validation_session_active")}
              </p>

              <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
                {headerFacts.map((item) => (
                  <div key={item.label} className="rounded-lg border border-glass-border bg-muted/10 px-3 py-2">
                    <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{item.label}:</p>
                    <p className={`mt-1 text-sm font-mono ${item.valueClass}`}>{item.value}</p>
                  </div>
                ))}
              </div>

              <div className="rounded-lg border border-glass-border bg-muted/10 px-3 py-2 text-xs">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("last_weekly_event")}</p>
                <p className="mt-1 text-foreground/85">{lastEventFeedback}</p>
              </div>
            </div>

            <div className="w-full shrink-0 xl:max-w-sm">
              <div className="rounded-lg border border-neon-orange/25 bg-neon-orange/5 px-3 py-3">
                <p className="text-[9px] font-mono uppercase tracking-wider text-neon-orange">{t("operational_note")}</p>
                <p className="mt-2 text-xs leading-relaxed text-foreground/75">
                  {session.operational_note}
                </p>
                <p className="mt-3 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                  {t("goal")}
                </p>
                <p className="mt-1 text-xs text-foreground/80">{t(`goal_${missionState.goal}`)}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="glass-panel flex min-w-0 flex-col gap-4 overflow-hidden p-4">
          <div className="flex items-center gap-2">
              <Orbit className="h-4 w-4 text-neon-cyan" />
              <h2 className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
                {t("active_ecosystem_stack")}
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
                        {t(`${layer.type}_layer`)}
                      </div>
                      <h3 className="text-lg font-semibold text-foreground">{formatLabel(layer.name)}</h3>
                      <p className="max-w-4xl text-sm leading-relaxed text-foreground/78">{layer.summary}</p>
                      {buildLayerInteractionHints(layer.type, session.selected_system?.[layer.type]?.metrics, t).length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {buildLayerInteractionHints(layer.type, session.selected_system?.[layer.type]?.metrics, t).map(([label, value]) => (
                            <span
                              key={`${layer.type}-${label}`}
                              className="rounded border border-glass-border/70 bg-muted/10 px-2 py-1 text-[10px] font-mono text-muted-foreground"
                            >
                              {label}: <span className="text-foreground">{value}</span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="grid min-w-[180px] grid-cols-2 gap-2 text-right text-[10px] font-mono text-muted-foreground">
                      <div>
                        <p>{t("mission_fit")}</p>
                        <p className="text-sm text-foreground">{Math.round(layer.missionFitScore * 100)}%</p>
                      </div>
                      <div>
                        <p>{t("risk")}</p>
                        <p className="text-sm text-foreground">{Math.round(layer.riskScore * 100)}%</p>
                      </div>
                      <div>
                        <p>{t("domain_score")}</p>
                        <p className="text-sm text-foreground">{layer.domainScore.toFixed(2)}</p>
                      </div>
                      <div>
                        <p>{t("current_rank")}</p>
                        <p className="text-sm text-foreground">{layer.rank ? `#${layer.rank}` : t("n_a")}</p>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center gap-3 text-[10px] font-mono text-muted-foreground">
                    {layer.type === "crop" && (
                      <span>
                        {t("support_system")}:{" "}
                        <span className="text-neon-cyan">
                          {formatLabel(layer.supportSystem || t("unknown"))}
                        </span>
                      </span>
                    )}
                    <span>
                      {t("ranked_candidates_available")}:{" "}
                      <span className="text-foreground">{session.ranked_candidates?.[layer.type]?.length ?? 0}</span>
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-lg border border-glass-border bg-black/10 p-4 text-sm text-muted-foreground">
                {t("selected_detail_incomplete")}
              </div>
            )}
          </div>
        </div>

        <div className="grid auto-rows-[minmax(260px,1fr)] grid-cols-1 gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="glass-panel flex min-h-[260px] min-w-0 flex-col gap-3 overflow-hidden p-4">
            <div className="flex items-center gap-2">
              <Orbit className="h-4 w-4 text-neon-cyan" />
              <h2 className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
                {t("system_metrics")}
              </h2>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1">
              {metricCards.map((metric) => (
                <div
                  key={metric.label}
                  className={`rounded-lg border border-glass-border bg-muted/10 p-3 ${
                    showUpdateHighlight && metric.previousValue !== null && Math.abs(metric.value - metric.previousValue) >= 0.01
                      ? "ring-1 ring-neon-cyan/40"
                      : ""
                  }`}
                >
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                      {metric.label}
                    </span>
                    <span className="text-sm font-mono text-foreground">{Math.round(metric.value)}%</span>
                  </div>
                  {metric.previousValue !== null && (
                    <div className="mb-2 flex items-center justify-between gap-2 text-[10px] font-mono">
                      <span className="text-muted-foreground">
                        {Math.round(metric.previousValue)}% {"->"} {Math.round(metric.value)}%
                      </span>
                      <span className={formatDeltaArrow(metric.value - metric.previousValue).tone}>
                        {formatDeltaArrow(metric.value - metric.previousValue).arrow} {formatDeltaArrow(metric.value - metric.previousValue).label}
                      </span>
                    </div>
                  )}
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div className={`h-full rounded-full ${metric.accent}`} style={{ width: `${metric.value}%` }} />
                  </div>
                </div>
              ))}
            </div>
            <div className="rounded-lg border border-glass-border bg-muted/10 px-3 py-2 text-[11px] font-mono text-muted-foreground">
              {t("constraints_now", {
                water: t(`constraint_${missionState.constraints.water}`),
                energy: t(`constraint_${missionState.constraints.energy}`),
                area: t(`constraint_${missionState.constraints.area}`),
              })}
            </div>
          </div>

          <div className="glass-panel flex min-h-[260px] min-w-0 flex-col gap-3 overflow-hidden p-4">
            <div className="flex items-center gap-2">
              <Play className="h-4 w-4 text-neon-orange" />
              <h2 className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
                {t("event_controls")}
              </h2>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <label className="text-[10px] font-mono uppercase tracking-wider text-neon-cyan">{t("water_drop")}</label>
                <Input value={waterDrop} onChange={(event) => setWaterDrop(event.target.value)} type="number" min={0} max={100} className="h-9 border-glass-border bg-muted/50" placeholder="0-100" />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-mono uppercase tracking-wider text-neon-gold">{t("energy_drop")}</label>
                <Input value={energyDrop} onChange={(event) => setEnergyDrop(event.target.value)} type="number" min={0} max={100} className="h-9 border-glass-border bg-muted/50" placeholder="0-100" />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-mono uppercase tracking-wider text-neon-red">{t("contamination")}</label>
                <Input value={contamination} onChange={(event) => setContamination(event.target.value)} type="number" min={0} max={100} className="h-9 border-glass-border bg-muted/50" placeholder="0-100" />
              </div>
              <div className="space-y-1 sm:col-span-2">
                <label className="text-[10px] font-mono uppercase tracking-wider text-neon-purple">{t("yield_drop")}</label>
                <Input value={yieldDrop} onChange={(event) => setYieldDrop(event.target.value)} type="number" min={0} max={100} className="h-9 border-glass-border bg-muted/50" placeholder={t("yield_drop_placeholder")} />
              </div>
            </div>

            <div className="rounded-lg border border-glass-border bg-black/10 px-3 py-2 text-xs text-muted-foreground">
              {t("baseline_load_helper")}
            </div>
            <div
              className={`rounded-lg border px-3 py-2 text-xs ${
                showUpdateHighlight
                  ? "border-neon-cyan/35 bg-neon-cyan/8 text-neon-cyan"
                  : "border-glass-border bg-muted/10 text-muted-foreground"
              }`}
            >
              {lastEventFeedback}
            </div>

            <Button
              type="button"
              onClick={handleApplyStep}
              disabled={isApplyingStep || simulationStatus !== "running"}
              className="mt-auto h-10 bg-primary font-bold uppercase tracking-wider text-primary-foreground hover:bg-primary/90"
            >
              {isApplyingStep ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FlaskConical className="mr-2 h-4 w-4" />}
              {isApplyingStep ? t("advancing_week") : simulationStatus === "running" ? t("next_week") : t("simulation_closed")}
            </Button>
          </div>
        </div>

        <div className="grid auto-rows-[minmax(220px,1fr)] grid-cols-1 gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="glass-panel flex min-h-[220px] min-w-0 flex-col gap-3 overflow-hidden p-4">
            <div className="flex items-center gap-2">
              <Waves className="h-4 w-4 text-neon-cyan" />
              <h2 className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
                {t("weekly_outcome")}
              </h2>
            </div>
            <div
              className={`rounded-lg border px-3 py-2 text-xs leading-relaxed ${
                showUpdateHighlight
                  ? "border-neon-cyan/35 bg-neon-cyan/8 text-foreground"
                  : "border-glass-border bg-muted/10 text-foreground/80"
              }`}
            >
              <span className="font-mono uppercase tracking-wider text-neon-cyan">{t("impact_snapshot")}:</span>{" "}
              {impactSnapshot}
            </div>
            <div
              className={`rounded-lg border bg-terminal/40 p-3 ${
                showUpdateHighlight ? "border-neon-cyan/35" : "border-glass-border"
              }`}
            >
              <p className="mb-2 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                {t("week_summary", { week: missionState.time })}
              </p>
              <p className="text-xs leading-relaxed text-foreground/80">{adaptationSummary}</p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className={`rounded-lg border border-glass-border bg-muted/10 p-3 ${showUpdateHighlight ? "ring-1 ring-neon-cyan/40" : ""}`}>
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("cumulative_risk")}</p>
                <p className="mt-2 text-sm font-mono text-foreground">
                  {previousRisk !== null ? `${previousRisk.toFixed(2)}% -> ${currentRisk.toFixed(2)}%` : `${currentRisk.toFixed(2)}%`}
                </p>
                <p className="mt-1 text-[10px] font-mono text-muted-foreground">
                  {t("start_baseline")}: {initialRisk.toFixed(2)}%
                </p>
                <p className={`mt-1 text-xs font-mono ${riskDeltaIndicator.tone}`}>
                  {riskTrend}
                  {riskDeltaIndicator.deltaLabel && (
                    <span className="ml-2">
                      {riskDeltaIndicator.arrow} {riskDeltaIndicator.deltaLabel}
                    </span>
                  )}
                </p>
              </div>
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("plant_system")}</p>
                <p className="mt-2 text-sm font-mono text-foreground">
                  {previousPlantSystem ? `${formatLabel(previousPlantSystem)} -> ${formatLabel(currentPlantSystem || t("unknown"))}` : formatLabel(currentPlantSystem || t("unknown"))}
                </p>
                <p className="mt-1 text-xs font-mono text-muted-foreground">
                  {previousPlantSystem && previousPlantSystem !== currentPlantSystem ? t("system_shifted") : t("system_held")}
                </p>
              </div>
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("stack_transition")}</p>
                <p className="mt-2 text-xs leading-relaxed text-foreground">
                  {previousStackLabel ? `${previousStackLabel} -> ${currentStackLabel}` : currentStackLabel}
                </p>
                <p className="mt-1 text-xs font-mono text-muted-foreground">
                  {previousStackLabel && previousStackLabel !== currentStackLabel ? t("layer_change_detected") : t("current_stack_retained")}
                </p>
              </div>
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("current_week")}</p>
                <p className="mt-2 text-lg font-mono text-foreground">{missionState.time} / {maxWeeks}</p>
                <p className="mt-1 text-xs font-mono text-muted-foreground">
                  {t("active_weekly_events", {
                    count: latestEvents ? Object.values(latestEvents).filter((value) => value !== null && value !== undefined).length : 0,
                  })}
                </p>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-auto rounded-lg border border-glass-border bg-muted/10 p-3">
              <p className="mb-2 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("system_changes")}</p>
              {humanSystemChanges.length > 0 ? (
                <div className="space-y-2 text-xs text-foreground/80">
                  {humanSystemChanges.map((change) => (
                    <p key={change}>{change}</p>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">
                  {t("no_stack_reconfiguration")}
                </p>
              )}
            </div>

            <div className="min-h-0 overflow-auto rounded-lg border border-glass-border bg-muted/10 p-3">
              <p className="mb-2 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("layer_changes")}</p>
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
                                {t("rank_improved")}
                              </span>
                            ) : rankDirection === "down" ? (
                              <span className="inline-flex items-center gap-1 text-neon-red">
                                <ArrowDownRight className="h-3 w-3" />
                                {t("rank_dropped")}
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-muted-foreground">
                                <ArrowRight className="h-3 w-3" />
                                {t("reevaluated")}
                              </span>
                            )}
                          </div>
                          <p className="mt-1">
                            {formatLabel(item.previousName)} <ArrowRight className="mx-1 inline h-3 w-3" />
                            {formatLabel(item.currentName)}
                          </p>
                        <p className="mt-1 text-muted-foreground">
                            {t("rank_label")} {item.previousRank ? `#${item.previousRank}` : t("n_a")}{" "}
                            <ArrowRight className="mx-1 inline h-3 w-3" />
                            {item.currentRank ? `#${item.currentRank}` : t("n_a")}
                          </p>
                        </div>
                      );
                    })}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">
                  {t("no_layer_shift")}
                </p>
              )}
            </div>
          </div>

          <div className="glass-panel flex min-h-[220px] min-w-0 flex-col gap-3 overflow-hidden p-4">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-neon-orange" />
              <h2 className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
                {t("state_trace")}
              </h2>
            </div>

            <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
              <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                {t("validation_brief")}
              </p>
              <p className="mt-2 text-xs leading-relaxed text-foreground/85">
                {executiveSummary || t("validation_brief_default")}
              </p>
            </div>

            <div className="rounded-lg border border-glass-border bg-terminal p-3">
              <p className="text-xs font-mono leading-relaxed text-foreground/80">
                {reasoningSummary}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("active_events")}</p>
                {latestEvents ? (
                  <div className="mt-2 space-y-1 text-xs text-foreground/80">
                    {Object.entries(latestEvents)
                      .filter(([, value]) => value !== null && value !== undefined)
                      .map(([key, value]) => (
                        <p key={key}>
                          {t(eventLabelKey(key as keyof MissionEventsPayload))}: <span className="text-foreground">{String(value)}</span>
                        </p>
                      ))}
                  </div>
                ) : (
                  <p className="mt-2 text-xs text-muted-foreground">{t("no_events_applied")}</p>
                )}
              </div>

              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("stability_cues")}</p>
                <div className="mt-2 space-y-1 text-xs text-foreground/80">
                  {improvementCues.slice(0, 3).map((item) => (
                    <p key={item}>{item}</p>
                  ))}
                  {improvementCues.length === 0 && (
                    <p className="text-muted-foreground">{t("no_stability_cue")}</p>
                  )}
                </div>
              </div>
            </div>

            <div className="mt-auto grid grid-cols-1 gap-2 text-[11px] font-mono text-muted-foreground sm:grid-cols-2">
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p>{t("mission_id")}</p>
                <p className="mt-1 break-all text-foreground">{missionState.mission_id}</p>
              </div>
              <div className="rounded-lg border border-glass-border bg-muted/10 p-3">
                <p>{t("reference_note")}</p>
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
              <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("water_margin")}</span>
            </div>
            <p className="text-2xl font-mono text-foreground">{Math.round(missionState.resources.water)}%</p>
            {previousSession && (
              <p className={`text-xs font-mono ${formatDeltaArrow(missionState.resources.water - previousSession.mission_state.resources.water).tone}`}>
                {Math.round(previousSession.mission_state.resources.water)}% {"->"} {Math.round(missionState.resources.water)}%{" "}
                {formatDeltaArrow(missionState.resources.water - previousSession.mission_state.resources.water).arrow}
              </p>
            )}
            <p className="text-xs font-mono text-neon-cyan">
              {t("recovered_water")}: {recoveredWater.toFixed(2)}%
            </p>
            <p className="text-[10px] font-mono text-muted-foreground">
              {t("recovery_queue", {
                count: recoveryQueueSize,
                weeks: recoveryCycleWeeks,
                rate: Math.round(recoveryRate * 100),
              })}
            </p>
          </div>
          <div className="glass-panel flex min-h-[120px] min-w-0 flex-col gap-2 overflow-hidden p-3">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-neon-gold" />
              <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("energy_margin")}</span>
            </div>
            <p className="text-2xl font-mono text-foreground">{Math.round(missionState.resources.energy)}%</p>
            {previousSession && (
              <p className={`text-xs font-mono ${formatDeltaArrow(missionState.resources.energy - previousSession.mission_state.resources.energy).tone}`}>
                {Math.round(previousSession.mission_state.resources.energy)}% {"->"} {Math.round(missionState.resources.energy)}%{" "}
                {formatDeltaArrow(missionState.resources.energy - previousSession.mission_state.resources.energy).arrow}
              </p>
            )}
            <p className="text-xs font-mono text-neon-gold">
              {t("energy_flow", {
                load: consumedEnergy.toFixed(2),
                solar: solarEnergy.toFixed(2),
                photo: photosynthesisEnergy.toFixed(2),
              })}
            </p>
          </div>
          <div className="glass-panel flex min-h-[120px] min-w-0 flex-col gap-2 overflow-hidden p-3">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-neon-purple" />
              <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{t("area_margin")}</span>
            </div>
            <p className="text-2xl font-mono text-foreground">{Math.round(missionState.resources.area)}%</p>
            {previousSession && (
              <p className={`text-xs font-mono ${formatDeltaArrow(missionState.resources.area - previousSession.mission_state.resources.area).tone}`}>
                {Math.round(previousSession.mission_state.resources.area)}% {"->"} {Math.round(missionState.resources.area)}%{" "}
                {formatDeltaArrow(missionState.resources.area - previousSession.mission_state.resources.area).arrow}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Simulation;
