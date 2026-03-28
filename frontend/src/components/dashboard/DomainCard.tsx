import { motion } from "framer-motion";

import type { SelectedDomainSystem } from "@/lib/types";

interface DomainCardProps {
  domain: SelectedDomainSystem;
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

const DomainCard = ({ domain }: DomainCardProps) => {
  const style = domainStyles[domain.type];
  const metrics = Object.entries(domain.metrics).slice(0, 3);

  return (
    <div className="min-w-0 overflow-hidden rounded-xl">
      <motion.div
        layout
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -18 }}
        transition={{ duration: 0.35 }}
        whileHover={{ scale: 1.01, transition: { duration: 0.18 } }}
        className="gradient-border-card relative flex h-full w-full min-h-[260px] min-w-0 flex-col gap-3 overflow-hidden p-4 transition-shadow cursor-default hover:neon-glow-cyan"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <div className={`inline-flex rounded-md border px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider ${style.badge}`}>
              {style.title}
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

        {domain.support_system && (
          <div className="rounded border border-glass-border bg-muted/20 px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
            Support System: <span className="text-neon-cyan">{formatLabel(domain.support_system)}</span>
          </div>
        )}

        <div className="min-w-0 flex-1 space-y-1 overflow-auto pr-1 text-xs">
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
      </motion.div>
    </div>
  );
};

export default DomainCard;
