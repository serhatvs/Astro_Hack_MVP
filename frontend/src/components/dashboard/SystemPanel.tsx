import { Cpu } from "lucide-react";

import type { RecommendationResponse, SimulationResponse } from "@/lib/types";

interface SystemPanelProps {
  recommendation: RecommendationResponse | null;
  simulation: SimulationResponse | null;
  isLoading: boolean;
}

const formatLabel = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

const toPercent = (value: number) => `${Math.round(value * 100)}%`;
const toWidth = (value: number) => `${Math.max(6, Math.round(value * 100))}%`;

const SystemPanel = ({ recommendation, simulation, isLoading }: SystemPanelProps) => {
  if (!recommendation) {
    return (
      <div className="glass-panel flex h-full w-full min-h-[260px] min-w-0 flex-col overflow-hidden p-3 space-y-3">
        <h3 className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">System & Resources</h3>
        <div className="flex min-h-0 flex-1 items-center justify-center text-center">
          <p className="text-xs font-mono text-muted-foreground">
            {isLoading ? "Requesting mission plan from the backend..." : "Generate a mission plan to view the selected system, resources, and risk posture."}
          </p>
        </div>
      </div>
    );
  }

  const {
    recommended_system,
    system_reasoning,
    why_this_system,
    tradeoff_summary,
    operational_note,
    mission_status,
    resource_plan,
    risk_analysis,
  } = recommendation;
  const riskColor =
    risk_analysis.level === "high"
      ? "bg-neon-red/20 text-neon-red border-neon-red/40"
      : risk_analysis.level === "moderate"
        ? "bg-neon-orange/20 text-neon-orange border-neon-orange/40"
        : "bg-neon-green/20 text-neon-green border-neon-green/40";
  const statusColor =
    mission_status === "CRITICAL"
      ? "bg-neon-red/20 text-neon-red border-neon-red/40"
      : mission_status === "WATCH"
        ? "bg-neon-orange/20 text-neon-orange border-neon-orange/40"
        : "bg-neon-green/20 text-neon-green border-neon-green/40";

  const resources = [
    { label: "Water Usage", level: resource_plan.water_level.toUpperCase(), color: "bg-neon-cyan", width: toWidth(resource_plan.water_score) },
    { label: "Energy Usage", level: resource_plan.energy_level.toUpperCase(), color: "bg-neon-gold", width: toWidth(resource_plan.energy_score) },
    { label: "Area Required", level: resource_plan.area_usage.toUpperCase(), color: "bg-neon-purple", width: toWidth(resource_plan.area_score) },
  ];

  return (
    <div className="glass-panel flex h-full w-full min-h-[260px] min-w-0 flex-col overflow-hidden p-3 space-y-3">
      <h3 className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">System & Resources</h3>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <Cpu className="h-4 w-4 text-neon-cyan" />
          <span className="break-words font-mono text-sm font-bold neon-text-cyan">{formatLabel(recommended_system).toUpperCase()}</span>
        </div>
        {simulation && (
          <span className={`px-2 py-0.5 rounded border text-[10px] font-mono ${simulation.system_changed ? "border-neon-orange/50 text-neon-orange" : "border-glass-border text-muted-foreground"}`}>
            {simulation.system_changed ? "SYSTEM SHIFT" : "SYSTEM STABLE"}
          </span>
        )}
      </div>

      <p className="break-words text-[11px] leading-relaxed text-foreground/75">{system_reasoning}</p>

      <div className="space-y-2">
        {resources.map((resource) => (
          <div key={resource.label} className="space-y-0.5">
            <div className="flex justify-between text-[10px] font-mono text-muted-foreground">
              <span>{resource.label}</span>
              <span>{resource.level}</span>
            </div>
            <div className="h-1.5 bg-muted rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${resource.color} transition-all duration-700`} style={{ width: resource.width }} />
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-2 text-[10px] font-mono text-muted-foreground sm:grid-cols-2">
        <div className="rounded border border-glass-border p-2">
          <p>Calorie Output</p>
          <p className="text-neon-green text-sm">{toPercent(resource_plan.calorie_score)}</p>
        </div>
        <div className="rounded border border-glass-border p-2">
          <p>Maintenance Load</p>
          <p className="text-neon-gold text-sm">{toPercent(resource_plan.maintenance_score)}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <div className={`inline-block px-2 py-0.5 rounded border text-[10px] font-mono font-bold ${statusColor}`}>
          STATUS: {mission_status}
        </div>
        <div className={`inline-block px-2 py-0.5 rounded border text-[10px] font-mono font-bold ${riskColor}`}>
          RISK: {risk_analysis.level.toUpperCase()} ({toPercent(risk_analysis.score)})
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-1 overflow-auto pr-1">
        <div className="rounded border border-glass-border p-2">
          <p className="text-[9px] uppercase tracking-wide text-muted-foreground">Why This System</p>
          <p className="mt-1 break-words text-[10px] leading-relaxed text-foreground/75">{why_this_system}</p>
        </div>
        <div className="rounded border border-glass-border p-2">
          <p className="text-[9px] uppercase tracking-wide text-muted-foreground">Tradeoff Summary</p>
          <p className="mt-1 break-words text-[10px] leading-relaxed text-foreground/75">{tradeoff_summary}</p>
        </div>
        <div className="rounded border border-neon-orange/25 bg-neon-orange/5 p-2">
          <p className="text-[9px] uppercase tracking-wide text-neon-orange">Operational Note</p>
          <p className="mt-1 break-words text-[10px] leading-relaxed text-foreground/75">{operational_note}</p>
        </div>
        {risk_analysis.factors.slice(0, 2).map((factor) => (
          <p key={factor} className="text-[10px] font-mono text-muted-foreground">
            - {factor}
          </p>
        ))}
      </div>

      {simulation && (
        <p className="break-words text-[10px] font-mono text-muted-foreground">
          {simulation.system_changed
            ? `System moved from ${formatLabel(simulation.previous_system || "unknown")} to ${formatLabel(simulation.new_system || "unknown")}.`
            : `Latest adaptation kept ${formatLabel(simulation.new_system || recommended_system)} as the primary system.`}
        </p>
      )}
    </div>
  );
};

export default SystemPanel;
