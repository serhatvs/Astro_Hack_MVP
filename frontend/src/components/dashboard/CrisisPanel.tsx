import { useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { ChangeEvent, CrisisType } from "@/lib/types";

interface CrisisPanelProps {
  onSimulate: (type: CrisisType) => void;
  disabled: boolean;
  isSimulating: boolean;
  hasRecommendation: boolean;
  lastEvent: ChangeEvent | null;
}

const formatEvent = (value: ChangeEvent) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

const CrisisPanel = ({ onSimulate, disabled, isSimulating, hasRecommendation, lastEvent }: CrisisPanelProps) => {
  const [crisisType, setCrisisType] = useState<CrisisType>("water");

  return (
    <div className="glass-panel p-3 space-y-3 h-full flex flex-col">
      <h3 className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Crisis Simulation</h3>

      <div className="flex-1 flex flex-col justify-center gap-3">
        <Select value={crisisType} onValueChange={(value) => setCrisisType(value as CrisisType)}>
          <SelectTrigger className="bg-muted/50 border-glass-border text-foreground h-8 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-card border-glass-border">
            <SelectItem value="water">Water Decrease</SelectItem>
            <SelectItem value="energy">Energy Drop</SelectItem>
            <SelectItem value="yield">Yield Drop</SelectItem>
          </SelectContent>
        </Select>

        <Button
          onClick={() => onSimulate(crisisType)}
          variant="outline"
          disabled={disabled}
          className="w-full border-neon-red/50 text-neon-red hover:bg-neon-red/10 hover:text-neon-red font-mono uppercase text-xs tracking-wider transition-all"
          style={!disabled ? { boxShadow: "0 0 12px hsl(0 85% 55% / 0.25)" } : {}}
        >
          {isSimulating ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <AlertTriangle className="h-3.5 w-3.5 mr-1.5" />}
          {isSimulating ? "Recalculating" : "Simulate Crisis"}
        </Button>

        {!hasRecommendation && (
          <p className="text-[10px] font-mono text-muted-foreground text-center">
            Generate a mission plan first to unlock runtime adaptation.
          </p>
        )}

        {lastEvent && hasRecommendation && (
          <p className="text-[10px] font-mono text-neon-orange text-center animate-pulse">
            Last event: {formatEvent(lastEvent)}
          </p>
        )}
      </div>
    </div>
  );
};

export default CrisisPanel;
