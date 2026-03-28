import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from "recharts";

import type { CropRecommendation } from "@/lib/types";

interface CropCardProps {
  crop: CropRecommendation;
  rank: number;
  showChart?: boolean;
}

const rankColors: Record<number, { badge: string; label: string }> = {
  1: { badge: "bg-neon-gold/20 text-neon-gold border-neon-gold/40", label: "text-neon-gold" },
  2: { badge: "bg-foreground/10 text-foreground/70 border-foreground/20", label: "text-foreground/70" },
  3: { badge: "bg-neon-orange/20 text-neon-orange border-neon-orange/40", label: "text-neon-orange" },
};

const formatLabel = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

const CropCard = ({ crop, rank, showChart }: CropCardProps) => {
  const colors = rankColors[rank] || rankColors[3];
  const chartData = [
    { name: "Water", value: Math.round(crop.metric_breakdown.water * 100), color: "hsl(185, 100%, 50%)" },
    { name: "Energy", value: Math.round(crop.metric_breakdown.energy * 100), color: "hsl(45, 100%, 55%)" },
    { name: "Yield", value: Math.round(crop.metric_breakdown.calorie * 100), color: "hsl(145, 80%, 50%)" },
  ];
  const missionFit = Math.round(crop.compatibility_score * 100);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4, delay: rank * 0.1 }}
      whileHover={{ scale: 1.015, transition: { duration: 0.2 } }}
      className="gradient-border-card relative flex h-full min-h-[260px] min-w-0 flex-col gap-2 overflow-hidden p-4 transition-shadow cursor-default hover:neon-glow-cyan"
    >
      <div className="flex items-start justify-between gap-2">
        <div className={`px-2 py-0.5 rounded-md border text-xs font-mono font-bold ${colors.badge}`}>
          #{rank}
        </div>
        <div className="min-w-0 text-right">
          <p className="text-[9px] font-mono uppercase text-muted-foreground">Mission Fit</p>
          <p className="text-lg font-mono font-bold neon-text-cyan">{missionFit}%</p>
        </div>
      </div>

      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="min-w-0 break-words text-lg font-bold tracking-wide">{formatLabel(crop.name)}</h3>
          <span className="max-w-full rounded border border-glass-border px-2 py-0.5 text-[9px] font-mono uppercase text-muted-foreground">
            {formatLabel(crop.selected_system)}
          </span>
        </div>
        <p className="text-xs font-mono text-muted-foreground">Score: {crop.score.toFixed(2)}</p>
        <p className="break-words text-[11px] leading-relaxed text-foreground/80">{crop.reason}</p>
      </div>

      <div className="min-w-0 flex-1 space-y-0.5 overflow-hidden text-xs">
        {crop.strengths.map((strength) => (
          <p key={strength} className="break-words text-neon-green">+ {strength}</p>
        ))}
        {crop.tradeoffs.map((tradeoff) => (
          <p key={tradeoff} className="break-words text-neon-orange">- {tradeoff}</p>
        ))}
      </div>

      {showChart ? (
        <div className="mt-1 h-20 min-h-[5rem]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} barSize={14}>
              <XAxis dataKey="name" tick={{ fontSize: 9, fill: "hsl(220,10%,55%)" }} axisLine={false} tickLine={false} />
              <YAxis hide domain={[0, 100]} />
              <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                {chartData.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} fillOpacity={0.7} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="mt-auto space-y-1">
          {chartData.map((entry) => (
            <div key={entry.name} className="space-y-0.5">
              <div className="flex justify-between text-[10px] font-mono text-muted-foreground">
                <span>{entry.name}</span>
                <span>{entry.value}%</span>
              </div>
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all duration-700" style={{ width: `${entry.value}%`, backgroundColor: entry.color }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
};

export default CropCard;
