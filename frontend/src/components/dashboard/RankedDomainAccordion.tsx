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
          const strengths = deriveStrengths(candidate);
          const tradeoffs = deriveTradeoffs(candidate);

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
                    ) : (
                      <p className="mt-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                        {title}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono uppercase tracking-wider">
                    <span className="rounded border border-neon-green/25 bg-neon-green/10 px-2 py-1 text-neon-green">
                      Score: {candidate.combined_score.toFixed(2)}
                    </span>
                    <span className="rounded border border-glass-border/70 bg-muted/20 px-2 py-1 text-muted-foreground">
                      Mission Fit: {(candidate.mission_fit_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-3 pb-3 pt-0">
                <div className="space-y-3 rounded border border-glass-border/60 bg-black/10 p-3">
                  <p className="text-xs leading-relaxed text-foreground/80">
                    {candidate.summary || strengths[0] || "Candidate remains viable for the active mission profile."}
                  </p>

                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    <div className="rounded border border-neon-green/20 bg-neon-green/5 px-3 py-2">
                      <p className="text-[10px] font-mono uppercase tracking-wider text-neon-green">Strengths</p>
                      <div className="mt-2 space-y-1">
                        {strengths.map((strength) => (
                          <p key={strength} className="text-xs text-foreground/80">
                            + {strength}
                          </p>
                        ))}
                      </div>
                    </div>

                    <div className="rounded border border-neon-orange/20 bg-neon-orange/5 px-3 py-2">
                      <p className="text-[10px] font-mono uppercase tracking-wider text-neon-orange">Tradeoffs</p>
                      <div className="mt-2 space-y-1">
                        {tradeoffs.map((tradeoff) => (
                          <p key={tradeoff} className="text-xs text-foreground/80">
                            - {tradeoff}
                          </p>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    <MetricStat label="Combined" value={candidate.combined_score} />
                    <MetricStat label="Mission Fit" value={candidate.mission_fit_score} />
                    <MetricStat label="Domain" value={candidate.domain_score} />
                    <MetricStat label="Risk" value={candidate.risk_score} />
                    <MetricStat label="Stability" value={1 - candidate.risk_score} />
                    <MetricStat label="Support" value={deriveSupportScore(candidate)} />
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

const deriveStrengths = (candidate: RankedDomainCandidate): string[] => {
  const base = candidate.notes.slice(0, 2).map(normalizeNote);
  if (base.length > 0) {
    return base;
  }

  return [
    candidate.summary || "Sustains useful subsystem support under the current mission profile.",
    candidate.mission_fit_score >= 0.75
      ? "Matches the mission envelope with solid baseline fit."
      : "Remains a viable alternate within the ranked shortlist.",
  ];
};

const deriveTradeoffs = (candidate: RankedDomainCandidate): string[] => {
  const tradeoffs: string[] = [];

  if (candidate.risk_score >= 0.35) {
    tradeoffs.push("Higher operational risk will need tighter monitoring.");
  } else if (candidate.risk_score >= 0.2) {
    tradeoffs.push("Moderate risk exposure still needs consistent tuning.");
  } else {
    tradeoffs.push("Low-risk profile still depends on stable subsystem control.");
  }

  if (candidate.mission_fit_score < 0.75) {
    tradeoffs.push("Mission fit trails the leading option under this profile.");
  } else if (candidate.combined_score < 0.8) {
    tradeoffs.push("Overall margin is workable but narrower than the top pick.");
  } else if (!candidate.support_system) {
    tradeoffs.push("Best results depend on the rest of the biological stack staying balanced.");
  }

  return tradeoffs.slice(0, 2);
};

const deriveSupportScore = (candidate: RankedDomainCandidate) => {
  const noteScore = Math.min(1, 0.45 + candidate.notes.length * 0.12);
  const fitBonus = candidate.mission_fit_score * 0.35;
  return Math.max(0, Math.min(1, noteScore * 0.65 + fitBonus));
};

const normalizeNote = (note: string) => {
  const trimmed = note.trim();
  if (!trimmed) {
    return trimmed;
  }

  return trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
};

export default RankedDomainAccordion;
