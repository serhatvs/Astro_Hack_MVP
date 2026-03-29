import { useEffect, useMemo, useState } from "react";
import { Loader2, Play } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { RecommendationResponse } from "@/lib/types";

interface SimulationLauncherSelection {
  selected_crop: string;
  selected_algae: string;
  selected_microbial: string;
}

interface SimulationLauncherProps {
  recommendation: RecommendationResponse | null;
  isStarting: boolean;
  onStart: (selection: SimulationLauncherSelection) => void;
}

const formatLabel = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

const SimulationLauncher = ({ recommendation, isStarting, onStart }: SimulationLauncherProps) => {
  const [selectedCrop, setSelectedCrop] = useState("");
  const [selectedAlgae, setSelectedAlgae] = useState("");
  const [selectedMicrobial, setSelectedMicrobial] = useState("");

  const cropOptions = recommendation?.ranked_candidates?.crop ?? [];
  const algaeOptions = recommendation?.ranked_candidates?.algae ?? [];
  const microbialOptions = recommendation?.ranked_candidates?.microbial ?? [];
  const isReady = Boolean(
    recommendation &&
      selectedCrop &&
      selectedAlgae &&
      selectedMicrobial &&
      cropOptions.length &&
      algaeOptions.length &&
      microbialOptions.length,
  );

  useEffect(() => {
    setSelectedCrop(recommendation?.selected_system?.crop.name ?? "");
    setSelectedAlgae(recommendation?.selected_system?.algae.name ?? "");
    setSelectedMicrobial(recommendation?.selected_system?.microbial.name ?? "");
  }, [
    recommendation?.selected_system?.crop.name,
    recommendation?.selected_system?.algae.name,
    recommendation?.selected_system?.microbial.name,
  ]);

  const selectedSummary = useMemo(() => {
    if (!isReady) {
      return null;
    }
    return `${formatLabel(selectedCrop)} + ${formatLabel(selectedAlgae)} + ${formatLabel(selectedMicrobial)}`;
  }, [isReady, selectedCrop, selectedAlgae, selectedMicrobial]);

  return (
    <div className="glass-panel flex w-full min-h-[220px] min-w-0 flex-col gap-4 overflow-hidden p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h3 className="text-[11px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
            Start Simulation
          </h3>
          <p className="max-w-3xl text-xs text-foreground/75">
            Validate the recommended ecosystem over time. Adjust the crop, algae, and microbial layers before launch.
          </p>
        </div>
        <div className="rounded border border-glass-border bg-muted/20 px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
          {recommendation ? "Plan ready" : "Generate plan first"}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-4">
        <div className="min-w-0 space-y-1">
          <label className="text-[10px] font-mono uppercase tracking-widest text-neon-green">Crop Layer</label>
          <Select value={selectedCrop} onValueChange={setSelectedCrop} disabled={!recommendation || isStarting}>
            <SelectTrigger className="h-9 border-glass-border bg-muted/50 text-sm text-foreground">
              <SelectValue placeholder="Choose crop" />
            </SelectTrigger>
            <SelectContent className="border-glass-border bg-card">
              {cropOptions.map((candidate) => (
                <SelectItem key={`crop-${candidate.name}`} value={candidate.name}>
                  {formatLabel(candidate.name)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="min-w-0 space-y-1">
          <label className="text-[10px] font-mono uppercase tracking-widest text-neon-cyan">Algae Layer</label>
          <Select value={selectedAlgae} onValueChange={setSelectedAlgae} disabled={!recommendation || isStarting}>
            <SelectTrigger className="h-9 border-glass-border bg-muted/50 text-sm text-foreground">
              <SelectValue placeholder="Choose algae" />
            </SelectTrigger>
            <SelectContent className="border-glass-border bg-card">
              {algaeOptions.map((candidate) => (
                <SelectItem key={`algae-${candidate.name}`} value={candidate.name}>
                  {formatLabel(candidate.name)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="min-w-0 space-y-1">
          <label className="text-[10px] font-mono uppercase tracking-widest text-neon-orange">
            Microbial Layer
          </label>
          <Select
            value={selectedMicrobial}
            onValueChange={setSelectedMicrobial}
            disabled={!recommendation || isStarting}
          >
            <SelectTrigger className="h-9 border-glass-border bg-muted/50 text-sm text-foreground">
              <SelectValue placeholder="Choose microbial support" />
            </SelectTrigger>
            <SelectContent className="border-glass-border bg-card">
              {microbialOptions.map((candidate) => (
                <SelectItem key={`microbial-${candidate.name}`} value={candidate.name}>
                  {formatLabel(candidate.name)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex min-w-0 items-end">
          <Button
            type="button"
            disabled={!isReady || isStarting}
            onClick={() =>
              onStart({
                selected_crop: selectedCrop,
                selected_algae: selectedAlgae,
                selected_microbial: selectedMicrobial,
              })
            }
            className="h-9 w-full bg-primary font-bold uppercase tracking-wider text-primary-foreground pulse-glow hover:bg-primary/90"
          >
            {isStarting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
            {isStarting ? "Starting Simulation" : "Start Simulation"}
          </Button>
        </div>
      </div>

      <div className="rounded-lg border border-glass-border bg-black/10 px-3 py-2">
        {selectedSummary ? (
          <div className="space-y-1">
            <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Launch Stack</p>
            <p className="text-sm text-foreground/85">{selectedSummary}</p>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            Generate a mission plan first, then adjust the recommended biological layers before starting the
            validation run.
          </p>
        )}
      </div>
    </div>
  );
};

export default SimulationLauncher;
