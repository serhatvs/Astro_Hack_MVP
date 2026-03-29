import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { formatLabel } from "@/lib/mission-view";
import type { CropRecommendation } from "@/lib/types";

interface RankedCropAccordionProps {
  crops: CropRecommendation[];
  emptyMessage: string;
}

const RankedCropAccordion = ({ crops, emptyMessage }: RankedCropAccordionProps) => {
  if (crops.length === 0) {
    return <p className="text-xs text-muted-foreground">{emptyMessage}</p>;
  }

  return (
    <Accordion
      type="multiple"
      defaultValue={["crop-rank-1"]}
      className="mt-2 rounded border border-glass-border/70 bg-muted/5"
    >
      {crops.map((crop, index) => {
        const rank = index + 1;
        return (
          <AccordionItem
            key={`${crop.name}-${rank}`}
            value={`crop-rank-${rank}`}
            className="border-b border-glass-border/70 last:border-b-0"
          >
            <AccordionTrigger className="px-3 py-3 text-left hover:no-underline">
              <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded border border-neon-cyan/30 bg-neon-cyan/10 px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-neon-cyan">
                      #{rank}
                    </span>
                    <p className="truncate text-sm font-semibold text-foreground">{formatLabel(crop.name)}</p>
                  </div>
                  <p className="mt-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                    {formatLabel(crop.selected_system)}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono uppercase tracking-wider">
                  <span className="rounded border border-neon-green/25 bg-neon-green/10 px-2 py-1 text-neon-green">
                    Score: {crop.score.toFixed(2)}
                  </span>
                  <span className="rounded border border-glass-border/70 bg-muted/20 px-2 py-1 text-muted-foreground">
                    Mission Fit: {(crop.compatibility_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-3 pb-3 pt-0">
              <div className="space-y-3 rounded border border-glass-border/60 bg-black/10 p-3">
                <p className="text-xs leading-relaxed text-foreground/80">{crop.reason}</p>

                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <div className="rounded border border-neon-green/20 bg-neon-green/5 px-3 py-2">
                    <p className="text-[10px] font-mono uppercase tracking-wider text-neon-green">Strengths</p>
                    <div className="mt-2 space-y-1">
                      {crop.strengths.map((strength) => (
                        <p key={strength} className="text-xs text-foreground/80">
                          + {strength}
                        </p>
                      ))}
                    </div>
                  </div>

                  <div className="rounded border border-neon-orange/20 bg-neon-orange/5 px-3 py-2">
                    <p className="text-[10px] font-mono uppercase tracking-wider text-neon-orange">Tradeoffs</p>
                    <div className="mt-2 space-y-1">
                      {crop.tradeoffs.map((tradeoff) => (
                        <p key={tradeoff} className="text-xs text-foreground/80">
                          - {tradeoff}
                        </p>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  <MetricStat label="Calorie" value={crop.metric_breakdown.calorie} />
                  <MetricStat label="Water" value={crop.metric_breakdown.water} />
                  <MetricStat label="Energy" value={crop.metric_breakdown.energy} />
                  <MetricStat label="Growth Time" value={crop.metric_breakdown.growth_time} />
                  <MetricStat label="Risk" value={crop.metric_breakdown.risk} />
                  <MetricStat label="Maintenance" value={crop.metric_breakdown.maintenance} />
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>
        );
      })}
    </Accordion>
  );
};

const MetricStat = ({ label, value }: { label: string; value: number }) => (
  <div className="rounded border border-glass-border/60 bg-muted/10 px-3 py-2">
    <div className="flex items-center justify-between gap-2 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
      <span className="truncate">{label}</span>
      <span>{Math.round(value * 100)}%</span>
    </div>
    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
      <div
        className="h-full rounded-full bg-neon-cyan transition-all duration-500"
        style={{ width: `${Math.max(0, Math.min(100, Math.round(value * 100)))}%` }}
      />
    </div>
  </div>
);

export default RankedCropAccordion;
