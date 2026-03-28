import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, ChevronUp } from "lucide-react";

import type { RankedDomainCandidate, SelectedDomainSystem } from "@/lib/types";

interface DomainCardProps {
  domain: SelectedDomainSystem;
  rankedCandidates?: RankedDomainCandidate[];
  summaryOverride?: string | null;
}

const domainStyles: Record<SelectedDomainSystem["type"], { badge: string; accent: string; title: string }> = {
  crop: {
    badge: "border-neon-green/40 bg-neon-green/15 text-neon-green",
    accent: "bg-neon-green",
    title: "Plant Layer",
  },
  algae: {
    badge: "border-neon-cyan/40 bg-neon-cyan/15 text-neon-cyan",
    accent: "bg-neon-cyan",
    title: "Algae Layer",
  },
  microbial: {
    badge: "border-neon-orange/40 bg-neon-orange/15 text-neon-orange",
    accent: "bg-neon-orange",
    title: "Microbial Layer",
  },
};

const formatLabel = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

const DomainCard = ({ domain, rankedCandidates = [], summaryOverride = null }: DomainCardProps) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const style = domainStyles[domain.type];
  const metrics = Object.entries(domain.metrics).slice(0, 3);
  const canExpand = rankedCandidates.length > 0;
  const selectedSummary = summaryOverride?.trim() || null;

  return (
    <div className="min-w-0 overflow-hidden rounded-xl">
      <motion.div
        layout
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -18 }}
        transition={{ duration: 0.35 }}
        whileHover={{ scale: 1.01, transition: { duration: 0.18 } }}
        className="gradient-border-card relative flex w-full min-h-[260px] min-w-0 flex-col gap-3 overflow-hidden p-4 transition-shadow cursor-default hover:neon-glow-cyan"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <div className={`inline-flex rounded-md border px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider ${style.badge}`}>
                {style.title}
              </div>
              <div className="inline-flex rounded-md border border-glass-border bg-muted/20 px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider text-foreground/80">
                Selected
              </div>
            </div>
            <h3 className="break-words text-lg font-bold tracking-wide">{formatLabel(domain.name)}</h3>
          </div>
          <div className="text-right">
            <p className="text-[9px] font-mono uppercase text-muted-foreground">Mission Fit</p>
            <p className="text-lg font-mono font-bold neon-text-cyan">{Math.round(domain.mission_fit_score * 100)}%</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-muted-foreground">
          <div>
            <p className="uppercase">Domain Score</p>
            <p className="text-sm text-foreground">{domain.domain_score.toFixed(2)}</p>
          </div>
          <div>
            <p className="uppercase">Risk</p>
            <p className="text-sm text-foreground">{Math.round(domain.risk_score * 100)}%</p>
          </div>
        </div>

        {selectedSummary && (
          <div className="rounded-lg border border-glass-border bg-muted/20 px-3 py-2 text-xs text-foreground/85">
            {selectedSummary}
          </div>
        )}

        {domain.support_system && (
          <div className="rounded border border-glass-border bg-muted/20 px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
            Support System: <span className="text-neon-cyan">{formatLabel(domain.support_system)}</span>
          </div>
        )}

        <div className="min-w-0 space-y-1 text-xs">
          {domain.notes.length > 0 ? (
            domain.notes.map((note) => (
              <p key={note} className="break-words text-foreground/80">
                {note}
              </p>
            ))
          ) : (
            <p className="text-muted-foreground">No additional operational notes for this layer.</p>
          )}
        </div>

        <div className="mt-auto space-y-1">
          {metrics.map(([metricName, metricValue]) => {
            const value = Math.round(metricValue * 100);
            return (
              <div key={metricName} className="space-y-0.5">
                <div className="flex justify-between gap-2 text-[10px] font-mono text-muted-foreground">
                  <span className="truncate">{formatLabel(metricName)}</span>
                  <span>{value}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                  <div className={`h-full rounded-full ${style.accent}`} style={{ width: `${value}%` }} />
                </div>
              </div>
            );
          })}
        </div>

        {canExpand && (
          <button
            type="button"
            onClick={() => setIsExpanded((previousState) => !previousState)}
            className="inline-flex w-fit items-center gap-2 rounded-md border border-glass-border bg-muted/20 px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-foreground/85 transition-colors hover:border-glass-highlight hover:bg-muted/35"
          >
            {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            {isExpanded ? "Collapse Candidates" : "Expand Candidates"}
          </button>
        )}

        <AnimatePresence initial={false}>
          {isExpanded && canExpand && (
            <motion.div
              key="ranked-domain-list"
              layout
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.22 }}
              className="overflow-hidden rounded-lg border border-glass-border/80 bg-black/10"
            >
              <div className="border-b border-glass-border/60 px-3 py-2 text-[10px] font-mono uppercase tracking-[0.22em] text-muted-foreground">
                Full Ranked {style.title}
              </div>
              <div className="space-y-2 p-3">
                {rankedCandidates.map((candidate) => {
                  const isSelected = candidate.name === domain.name;
                  return (
                    <div
                      key={`${candidate.type}-${candidate.name}`}
                      className={`rounded-lg border px-3 py-2 ${
                        isSelected
                          ? "border-glass-highlight bg-muted/25 shadow-[0_0_0_1px_rgba(34,211,238,0.18)]"
                          : "border-glass-border/70 bg-muted/10"
                      }`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                              #{candidate.rank}
                            </span>
                            <span className="break-words text-sm font-semibold text-foreground">
                              {formatLabel(candidate.name)}
                            </span>
                            {isSelected && (
                              <span className={`rounded-md border px-1.5 py-0.5 text-[9px] font-mono uppercase tracking-wider ${style.badge}`}>
                                Current Selection
                              </span>
                            )}
                          </div>
                          {candidate.summary && (
                            <p className="mt-1 break-words text-xs text-foreground/75">{candidate.summary}</p>
                          )}
                          {candidate.support_system && (
                            <p className="mt-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                              Support: <span className="text-neon-cyan">{formatLabel(candidate.support_system)}</span>
                            </p>
                          )}
                        </div>
                        <div className="min-w-[108px] text-right text-[10px] font-mono text-muted-foreground">
                          <p>
                            Fit <span className="text-foreground">{Math.round(candidate.mission_fit_score * 100)}%</span>
                          </p>
                          <p>
                            Combined <span className="text-foreground">{candidate.combined_score.toFixed(2)}</span>
                          </p>
                          <p>
                            Risk <span className="text-foreground">{Math.round(candidate.risk_score * 100)}%</span>
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};

export default DomainCard;
