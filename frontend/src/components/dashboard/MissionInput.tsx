import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import type { ConstraintLevel } from "@/lib/types";

interface MissionInputProps {
  environment: string;
  setEnvironment: (v: string) => void;
  duration: string;
  setDuration: (v: string) => void;
  waterConstraint: ConstraintLevel;
  setWaterConstraint: (v: ConstraintLevel) => void;
  energyConstraint: ConstraintLevel;
  setEnergyConstraint: (v: ConstraintLevel) => void;
  areaConstraint: ConstraintLevel;
  setAreaConstraint: (v: ConstraintLevel) => void;
  goal: string;
  setGoal: (v: string) => void;
  onGenerate: () => void;
  isLoading: boolean;
}

const MissionInput = ({
  environment, setEnvironment,
  duration, setDuration,
  waterConstraint, setWaterConstraint,
  energyConstraint, setEnergyConstraint,
  areaConstraint, setAreaConstraint,
  goal, setGoal,
  onGenerate, isLoading,
}: MissionInputProps) => {
  const formatConstraint = (value: ConstraintLevel) =>
    value.replace(/\b\w/g, (char) => char.toUpperCase());

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="min-w-0 space-y-1">
          <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Environment</label>
          <Select value={environment} onValueChange={setEnvironment}>
            <SelectTrigger className="bg-muted/50 border-glass-border text-foreground h-8 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-card border-glass-border">
              <SelectItem value="mars">Mars</SelectItem>
              <SelectItem value="moon">Moon</SelectItem>
              <SelectItem value="iss">ISS</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="min-w-0 space-y-1">
          <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Duration</label>
          <Select value={duration} onValueChange={setDuration}>
            <SelectTrigger className="bg-muted/50 border-glass-border text-foreground h-8 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-card border-glass-border">
              <SelectItem value="short">Short (3 mo)</SelectItem>
              <SelectItem value="medium">Medium (6 mo)</SelectItem>
              <SelectItem value="long">Long (12+ mo)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="min-w-0 space-y-1">
          <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Optimization Goal</label>
          <Select value={goal} onValueChange={setGoal}>
            <SelectTrigger className="bg-muted/50 border-glass-border text-foreground h-8 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-card border-glass-border">
              <SelectItem value="balanced">Balanced</SelectItem>
              <SelectItem value="calorie">Calorie Max</SelectItem>
              <SelectItem value="water">Water Efficiency</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex min-w-0 items-end">
          <Button
            onClick={onGenerate}
            disabled={isLoading}
            className="w-full h-8 bg-primary text-primary-foreground font-bold text-sm uppercase tracking-wider pulse-glow hover:bg-primary/90 transition-all"
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Generate Plan"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="min-w-0 space-y-1">
          <div className="flex justify-between gap-2">
            <label className="text-xs font-mono uppercase tracking-wider text-neon-cyan">Water Constraint</label>
            <span className="text-xs font-mono text-neon-cyan">{formatConstraint(waterConstraint)}</span>
          </div>
          <Select value={waterConstraint} onValueChange={(value) => setWaterConstraint(value as ConstraintLevel)}>
            <SelectTrigger className="h-9 border-glass-border bg-muted/50 text-sm text-foreground">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-glass-border bg-card">
              <SelectItem value="low">Low</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="high">High</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="min-w-0 space-y-1">
          <div className="flex justify-between gap-2">
            <label className="text-xs font-mono uppercase tracking-wider text-neon-gold">Energy Constraint</label>
            <span className="text-xs font-mono text-neon-gold">{formatConstraint(energyConstraint)}</span>
          </div>
          <Select value={energyConstraint} onValueChange={(value) => setEnergyConstraint(value as ConstraintLevel)}>
            <SelectTrigger className="h-9 border-glass-border bg-muted/50 text-sm text-foreground">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-glass-border bg-card">
              <SelectItem value="low">Low</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="high">High</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="min-w-0 space-y-1">
          <div className="flex justify-between gap-2">
            <label className="text-xs font-mono uppercase tracking-wider text-neon-purple">Area Constraint</label>
            <span className="text-xs font-mono text-neon-purple">{formatConstraint(areaConstraint)}</span>
          </div>
          <Select value={areaConstraint} onValueChange={(value) => setAreaConstraint(value as ConstraintLevel)}>
            <SelectTrigger className="h-9 border-glass-border bg-muted/50 text-sm text-foreground">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-glass-border bg-card">
              <SelectItem value="low">Low</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="high">High</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <p className="text-[11px] font-mono text-muted-foreground">
        Low means fewer limitations. High means stronger constraints.
      </p>
    </div>
  );
};

export default MissionInput;
