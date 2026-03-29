import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { useI18n } from "@/lib/i18n";
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
  const { t } = useI18n();
  const formatConstraint = (value: ConstraintLevel) => t(`constraint_${value}`);

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <div className="min-w-0 space-y-1">
          <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground">{t("environment")}</label>
          <Select value={environment} onValueChange={setEnvironment}>
            <SelectTrigger className="bg-muted/50 border-glass-border text-foreground h-8 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-card border-glass-border">
              <SelectItem value="mars">{t("environment_mars")}</SelectItem>
              <SelectItem value="moon">{t("environment_moon")}</SelectItem>
              <SelectItem value="iss">{t("environment_iss")}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="min-w-0 space-y-1">
          <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground">{t("duration")}</label>
          <Select value={duration} onValueChange={setDuration}>
            <SelectTrigger className="bg-muted/50 border-glass-border text-foreground h-8 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-card border-glass-border">
              <SelectItem value="short">{t("duration_short")}</SelectItem>
              <SelectItem value="medium">{t("duration_medium")}</SelectItem>
              <SelectItem value="long">{t("duration_long")}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="min-w-0 space-y-1">
          <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground">{t("optimization_goal")}</label>
          <Select value={goal} onValueChange={setGoal}>
            <SelectTrigger className="bg-muted/50 border-glass-border text-foreground h-8 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-card border-glass-border">
              <SelectItem value="balanced">{t("goal_balanced")}</SelectItem>
              <SelectItem value="calorie">{t("goal_calorie")}</SelectItem>
              <SelectItem value="water">{t("goal_water")}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="min-w-0 space-y-1">
          <div className="flex justify-between gap-2">
            <label className="text-xs font-mono uppercase tracking-wider text-neon-cyan">{t("water_constraint")}</label>
            <span className="text-xs font-mono text-neon-cyan">{formatConstraint(waterConstraint)}</span>
          </div>
          <Select value={waterConstraint} onValueChange={(value) => setWaterConstraint(value as ConstraintLevel)}>
            <SelectTrigger className="h-9 border-glass-border bg-muted/50 text-sm text-foreground">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-glass-border bg-card">
              <SelectItem value="low">{t("constraint_low")}</SelectItem>
              <SelectItem value="medium">{t("constraint_medium")}</SelectItem>
              <SelectItem value="high">{t("constraint_high")}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="min-w-0 space-y-1">
          <div className="flex justify-between gap-2">
            <label className="text-xs font-mono uppercase tracking-wider text-neon-gold">{t("energy_constraint")}</label>
            <span className="text-xs font-mono text-neon-gold">{formatConstraint(energyConstraint)}</span>
          </div>
          <Select value={energyConstraint} onValueChange={(value) => setEnergyConstraint(value as ConstraintLevel)}>
            <SelectTrigger className="h-9 border-glass-border bg-muted/50 text-sm text-foreground">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-glass-border bg-card">
              <SelectItem value="low">{t("constraint_low")}</SelectItem>
              <SelectItem value="medium">{t("constraint_medium")}</SelectItem>
              <SelectItem value="high">{t("constraint_high")}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="min-w-0 space-y-1">
          <div className="flex justify-between gap-2">
            <label className="text-xs font-mono uppercase tracking-wider text-neon-purple">{t("area_constraint")}</label>
            <span className="text-xs font-mono text-neon-purple">{formatConstraint(areaConstraint)}</span>
          </div>
          <Select value={areaConstraint} onValueChange={(value) => setAreaConstraint(value as ConstraintLevel)}>
            <SelectTrigger className="h-9 border-glass-border bg-muted/50 text-sm text-foreground">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-glass-border bg-card">
              <SelectItem value="low">{t("constraint_low")}</SelectItem>
              <SelectItem value="medium">{t("constraint_medium")}</SelectItem>
              <SelectItem value="high">{t("constraint_high")}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <p className="text-[11px] font-mono text-muted-foreground">
        {t("constraint_helper")}
      </p>

      <div className="mt-3 flex justify-end border-t border-glass-border/60 pt-3">
        <Button
          onClick={onGenerate}
          disabled={isLoading}
          className="h-9 w-full sm:w-auto sm:min-w-[220px] bg-primary text-primary-foreground font-bold text-sm uppercase tracking-wider pulse-glow hover:bg-primary/90 transition-all"
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : t("generate_plan")}
        </Button>
      </div>
    </div>
  );
};

export default MissionInput;
