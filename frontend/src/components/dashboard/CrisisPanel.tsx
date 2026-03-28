import { useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, ArrowDownRight, ArrowRight, ArrowUpRight, Loader2, Minus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { ChangeEvent, CrisisType, SimulationResponse } from "@/lib/types";

interface CrisisPanelProps {
  onSimulate: (type: CrisisType) => void;
  disabled: boolean;
  isSimulating: boolean;
  hasRecommendation: boolean;
  lastEvent: ChangeEvent | null;
  simulation: SimulationResponse | null;
}

const formatEvent = (value: ChangeEvent) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

const formatLabel = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

const CrisisPanel = ({
  onSimulate,
  disabled,
  isSimulating,
  hasRecommendation,
  lastEvent,
  simulation,
}: CrisisPanelProps) => {
  const [crisisType, setCrisisType] = useState<CrisisType>("water");

  const rankingChanges = simulation
    ? Object.entries(simulation.ranking_diff)
        .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
        .slice(0, 3)
    : [];

  const riskDeltaClass =
    simulation?.risk_delta === "increased"
      ? "border-neon-red/40 text-neon-red"
      : simulation?.risk_delta === "decreased"
        ? "border-neon-green/40 text-neon-green"
        : "border-glass-border text-muted-foreground";

  return (
    <div className="glass-panel flex h-full w-full min-h-[260px] min-w-0 flex-col overflow-hidden p-3 space-y-3">
      <h3 className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Crisis Simulation</h3>

      <div className="flex flex-col gap-3">
        <Select value={crisisType} onValueChange={(value) => setCrisisType(value as CrisisType)}>
          <SelectTrigger className="h-8 border-glass-border bg-muted/50 text-sm text-foreground">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="border-glass-border bg-card">
            <SelectItem value="water">Water Decrease</SelectItem>
            <SelectItem value="energy">Energy Drop</SelectItem>
            <SelectItem value="yield">Yield Drop</SelectItem>
          </SelectContent>
        </Select>

        <Button
          onClick={() => onSimulate(crisisType)}
          variant="outline"
          disabled={disabled}
          className="w-full border-neon-red/50 font-mono text-xs uppercase tracking-wider text-neon-red transition-all hover:bg-neon-red/10 hover:text-neon-red"
          style={!disabled ? { boxShadow: "0 0 12px hsl(0 85% 55% / 0.25)" } : {}}
        >
          {isSimulating ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : (
            <AlertTriangle className="mr-1.5 h-3.5 w-3.5" />
          )}
          {isSimulating ? "Recalculating" : "Simulate Crisis"}
        </Button>

        {!hasRecommendation && (
          <p className="text-center text-[10px] font-mono text-muted-foreground">
            Generate a mission plan first to unlock runtime adaptation.
          </p>
        )}

        {lastEvent && hasRecommendation && (
          <p className="text-center text-[10px] font-mono text-neon-orange animate-pulse">
            Last event: {formatEvent(lastEvent)}
          </p>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        {simulation ? (
          <motion.div
            key={`${simulation.change_event}-${simulation.new_top_crop ?? "none"}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className="flex h-full flex-col gap-2 overflow-hidden rounded-lg border border-glass-border/70 bg-terminal/40 p-3"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-[10px] font-mono uppercase tracking-wide text-muted-foreground">Latest Impact</span>
              <span
                className={`rounded border px-2 py-0.5 text-[10px] font-mono ${
                  simulation.system_changed
                    ? "border-neon-orange/50 text-neon-orange"
                    : "border-glass-border text-muted-foreground"
                }`}
              >
                {simulation.system_changed ? "SYSTEM SHIFT" : "SYSTEM STABLE"}
              </span>
            </div>

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <div className="rounded border border-glass-border p-2">
                <p className="text-[9px] uppercase tracking-wide text-muted-foreground">Top Crop</p>
                <div className="mt-1 flex items-center gap-1 text-xs font-mono">
                  <span className="text-foreground/80">{formatLabel(simulation.previous_top_crop || "n/a")}</span>
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <span className="text-neon-cyan">{formatLabel(simulation.new_top_crop || "n/a")}</span>
                </div>
              </div>

              <div className="rounded border border-glass-border p-2">
                <p className="text-[9px] uppercase tracking-wide text-muted-foreground">Mission Status</p>
                <div className="mt-1 flex items-center gap-1 text-xs font-mono">
                  <span className="text-foreground/80">{simulation.previous_mission_status}</span>
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <span className="text-neon-orange">{simulation.new_mission_status}</span>
                </div>
              </div>

              <div className="rounded border border-glass-border p-2">
                <p className="text-[9px] uppercase tracking-wide text-muted-foreground">Primary System</p>
                <div className="mt-1 flex items-center gap-1 text-xs font-mono">
                  <span className="text-foreground/80">{formatLabel(simulation.previous_system || "n/a")}</span>
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <span className={simulation.system_changed ? "text-neon-orange" : "text-neon-cyan"}>
                    {formatLabel(simulation.new_system || "n/a")}
                  </span>
                </div>
              </div>

              <div className="rounded border border-glass-border p-2">
                <p className="text-[9px] uppercase tracking-wide text-muted-foreground">Risk Delta</p>
                <span className={`mt-1 inline-flex rounded border px-2 py-0.5 text-[10px] font-mono ${riskDeltaClass}`}>
                  {simulation.risk_delta.toUpperCase()} ({simulation.risk_score_delta >= 0 ? "+" : ""}
                  {simulation.risk_score_delta.toFixed(3)})
                </span>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-auto rounded border border-glass-border p-2">
              <p className="mb-2 text-[9px] uppercase tracking-wide text-muted-foreground">Ranking Diff</p>
              <div className="space-y-1">
                {rankingChanges.map(([name, change]) => {
                  const icon =
                    change > 0 ? (
                      <ArrowUpRight className="h-3 w-3 text-neon-green" />
                    ) : change < 0 ? (
                      <ArrowDownRight className="h-3 w-3 text-neon-red" />
                    ) : (
                      <Minus className="h-3 w-3 text-muted-foreground" />
                    );
                  const valueClass =
                    change > 0
                      ? "text-neon-green"
                      : change < 0
                        ? "text-neon-red"
                        : "text-muted-foreground";

                  return (
                    <div key={name} className="flex items-center justify-between gap-2 text-[10px] font-mono">
                      <span className="truncate text-foreground/80">{formatLabel(name)}</span>
                      <span className={`inline-flex items-center gap-1 ${valueClass}`}>
                        {icon}
                        {change > 0 ? `+${change}` : change}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </motion.div>
        ) : (
          <div className="flex h-full min-h-[160px] items-center justify-center rounded-lg border border-dashed border-glass-border p-3 text-center">
            <p className="text-[10px] font-mono text-muted-foreground">
              Simulate a crisis to compare the previous and updated crop ranking, system choice, risk, and mission
              status.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CrisisPanel;
