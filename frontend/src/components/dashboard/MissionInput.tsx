import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

interface MissionInputProps {
  environment: string;
  setEnvironment: (v: string) => void;
  duration: string;
  setDuration: (v: string) => void;
  waterLimit: number[];
  setWaterLimit: (v: number[]) => void;
  energyLimit: number[];
  setEnergyLimit: (v: number[]) => void;
  areaLimit: number[];
  setAreaLimit: (v: number[]) => void;
  goal: string;
  setGoal: (v: string) => void;
  onGenerate: () => void;
  isLoading: boolean;
}

const MissionInput = ({
  environment, setEnvironment,
  duration, setDuration,
  waterLimit, setWaterLimit,
  energyLimit, setEnergyLimit,
  areaLimit, setAreaLimit,
  goal, setGoal,
  onGenerate, isLoading,
}: MissionInputProps) => {
  const constraintLevel = (value: number) => {
    if (value <= 33) {
      return "LOW";
    }
    if (value <= 66) {
      return "MEDIUM";
    }
    return "HIGH";
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="space-y-1">
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

        <div className="space-y-1">
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

        <div className="space-y-1">
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

        <div className="flex items-end">
          <Button
            onClick={onGenerate}
            disabled={isLoading}
            className="w-full h-8 bg-primary text-primary-foreground font-bold text-sm uppercase tracking-wider pulse-glow hover:bg-primary/90 transition-all"
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Generate Plan"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="space-y-1">
          <div className="flex justify-between">
            <label className="text-xs font-mono uppercase tracking-wider text-neon-cyan">Water Limit</label>
            <span className="text-xs font-mono text-neon-cyan">{waterLimit[0]}% | {constraintLevel(waterLimit[0])}</span>
          </div>
          <Slider value={waterLimit} onValueChange={setWaterLimit} max={100} step={1}
            className="[&_[role=slider]]:bg-neon-cyan [&_[role=slider]]:border-neon-cyan [&_.range]:bg-neon-cyan/50" />
        </div>
        <div className="space-y-1">
          <div className="flex justify-between">
            <label className="text-xs font-mono uppercase tracking-wider text-neon-gold">Energy Limit</label>
            <span className="text-xs font-mono text-neon-gold">{energyLimit[0]}% | {constraintLevel(energyLimit[0])}</span>
          </div>
          <Slider value={energyLimit} onValueChange={setEnergyLimit} max={100} step={1}
            className="[&_[role=slider]]:bg-neon-gold [&_[role=slider]]:border-neon-gold [&_.range]:bg-neon-gold/50" />
        </div>
        <div className="space-y-1">
          <div className="flex justify-between">
            <label className="text-xs font-mono uppercase tracking-wider text-neon-purple">Area Limit</label>
            <span className="text-xs font-mono text-neon-purple">{areaLimit[0]}% | {constraintLevel(areaLimit[0])}</span>
          </div>
          <Slider value={areaLimit} onValueChange={setAreaLimit} max={100} step={1}
            className="[&_[role=slider]]:bg-neon-purple [&_[role=slider]]:border-neon-purple [&_.range]:bg-neon-purple/50" />
        </div>
      </div>
    </div>
  );
};

export default MissionInput;
