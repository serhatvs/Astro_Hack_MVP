import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { formatLabel } from "@/lib/mission-view";
import type { RankedDomainCandidate } from "@/lib/types";

interface RankedDomainAccordionProps {
  title: string;
  candidates: RankedDomainCandidate[];
  selectedName?: string | null;
  emptyMessage: string;
}

const domainAccentClasses: Record<RankedDomainCandidate["type"], string> = {
  crop: "border-neon-green/25 bg-neon-green/10 text-neon-green",
  algae: "border-neon-cyan/25 bg-neon-cyan/10 text-neon-cyan",
  microbial: "border-neon-orange/25 bg-neon-orange/10 text-neon-orange",
};

const RankedDomainAccordion = ({
  title,
  candidates,
  selectedName = null,
  emptyMessage,
}: RankedDomainAccordionProps) => {
  if (candidates.length === 0) {
    return (
      <div className="rounded-lg border border-glass-border bg-black/10 p-3">
        <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{title}</p>
        <p className="mt-3 text-xs text-muted-foreground">{emptyMessage}</p>
      </div>
    );
  }

  const accentClass = domainAccentClasses[candidates[0].type];

  return (
    <div className="rounded-lg border border-glass-border bg-black/10 p-3">
      <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{title}</p>
      <Accordion
        type="multiple"
        defaultValue={[`${candidates[0].type}-rank-1`]}
        className="mt-2 rounded border border-glass-border/70 bg-muted/5"
      >
        {candidates.map((candidate) => {
          const isSelected = candidate.name === selectedName;

          return (
            <AccordionItem
              key={`${candidate.type}-${candidate.name}`}
              value={`${candidate.type}-rank-${candidate.rank}`}
              className="border-b border-glass-border/70 last:border-b-0"
            >
              <AccordionTrigger className="px-3 py-3 text-left hover:no-underline">
                <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded border px-2 py-1 text-[10px] font-mono uppercase tracking-wider ${accentClass}`}>
                        #{candidate.rank}
                      </span>
                      <p className="truncate text-sm font-semibold text-foreground">{formatLabel(candidate.name)}</p>
                      {isSelected ? (
                        <span className="rounded border border-glass-border/70 bg-muted/20 px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                          Selected
                        </span>
                      ) : null}
                    </div>
                    {candidate.support_system ? (
                      <p className="mt-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                        {formatLabel(candidate.support_system)}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono uppercase tracking-wider">
                    <span className="rounded border border-glass-border/70 bg-muted/20 px-2 py-1 text-muted-foreground">
                      Fit: {(candidate.mission_fit_score * 100).toFixed(0)}%
                    </span>
                    <span className="rounded border border-glass-border/70 bg-muted/20 px-2 py-1 text-muted-foreground">
                      Combined: {candidate.combined_score.toFixed(2)}
                    </span>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-3 pb-3 pt-0">
                <div className="space-y-3 rounded border border-glass-border/60 bg-black/10 p-3">
                  {candidate.summary ? (
                    <p className="text-xs leading-relaxed text-foreground/80">{candidate.summary}</p>
                  ) : null}

                  {candidate.notes.length > 0 ? (
                    <div className="space-y-1">
                      {candidate.notes.map((note) => (
                        <p key={note} className="text-xs text-foreground/80">
                          {note}
                        </p>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">No additional notes for this candidate.</p>
                  )}

                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
                    <StatBox label="Domain" value={candidate.domain_score.toFixed(2)} />
                    <StatBox label="Mission Fit" value={`${(candidate.mission_fit_score * 100).toFixed(0)}%`} />
                    <StatBox label="Risk" value={`${(candidate.risk_score * 100).toFixed(0)}%`} />
                    <StatBox label="Combined" value={candidate.combined_score.toFixed(2)} />
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>
    </div>
  );
};

const StatBox = ({ label, value }: { label: string; value: string }) => (
  <div className="rounded border border-glass-border/60 bg-muted/10 px-3 py-2">
    <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{label}</p>
    <p className="mt-1 text-sm text-foreground">{value}</p>
  </div>
);

export default RankedDomainAccordion;
