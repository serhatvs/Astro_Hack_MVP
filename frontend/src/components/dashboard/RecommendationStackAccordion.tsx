import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { formatLabel, type LayerSummary } from "@/lib/mission-view";
import { useI18n } from "@/lib/i18n";

interface RecommendationStackAccordionProps {
  layers: LayerSummary[];
  emptyMessage: string;
}

const RecommendationStackAccordion = ({ layers, emptyMessage }: RecommendationStackAccordionProps) => {
  const { t } = useI18n();

  if (layers.length === 0) {
    return <p className="text-xs text-muted-foreground">{emptyMessage}</p>;
  }

  return (
    <Accordion
      type="multiple"
      defaultValue={[layers[0]?.type].filter(Boolean)}
      className="mt-2 rounded border border-glass-border/70 bg-muted/5"
    >
      {layers.map((layer) => (
        <AccordionItem
          key={layer.type}
          value={layer.type}
          className="border-b border-glass-border/70 last:border-b-0"
        >
          <AccordionTrigger className="px-3 py-3 text-left hover:no-underline">
            <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                  {layer.label}
                </p>
                <p className="truncate text-sm font-semibold text-foreground">{formatLabel(layer.name)}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono uppercase tracking-wider">
                {layer.rank ? (
                  <span className="rounded border border-neon-cyan/30 bg-neon-cyan/10 px-2 py-1 text-neon-cyan">
                    {t("current_rank")}: {layer.rank}
                  </span>
                ) : null}
                {layer.supportSystem ? (
                  <span className="rounded border border-neon-green/25 bg-neon-green/10 px-2 py-1 text-neon-green">
                    {formatLabel(layer.supportSystem)}
                  </span>
                ) : null}
              </div>
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-3 pb-3 pt-0">
            <div className="space-y-3 rounded border border-glass-border/60 bg-black/10 p-3">
              <p className="text-xs leading-relaxed text-foreground/80">{layer.summary}</p>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                <div className="rounded border border-glass-border/60 bg-muted/10 px-3 py-2">
                  <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                    {t("domain_score")}
                  </p>
                  <p className="mt-1 text-sm text-foreground">{layer.domainScore.toFixed(2)}</p>
                </div>
                <div className="rounded border border-glass-border/60 bg-muted/10 px-3 py-2">
                  <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                    {t("mission_fit")}
                  </p>
                  <p className="mt-1 text-sm text-foreground">{layer.missionFitScore.toFixed(2)}</p>
                </div>
                <div className="rounded border border-glass-border/60 bg-muted/10 px-3 py-2">
                  <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                    {t("risk")}
                  </p>
                  <p className="mt-1 text-sm text-foreground">{layer.riskScore.toFixed(2)}</p>
                </div>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
};

export default RecommendationStackAccordion;
