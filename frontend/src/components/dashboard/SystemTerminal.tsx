import { useEffect, useRef } from "react";

import type { ApiStatus, TerminalEntry } from "@/lib/types";

interface SystemTerminalProps {
  entries: TerminalEntry[];
  apiStatus: ApiStatus;
}

const statusStyles: Record<ApiStatus, string> = {
  idle: "text-muted-foreground border-glass-border",
  loading: "text-neon-cyan border-neon-cyan/40",
  ready: "text-neon-green border-neon-green/40",
  warning: "text-neon-orange border-neon-orange/40",
  error: "text-neon-red border-neon-red/40",
};

const lineStyles: Record<TerminalEntry["level"], string> = {
  info: "text-neon-green/70",
  warn: "text-neon-orange",
  success: "text-neon-cyan",
  error: "text-neon-red",
};

const SystemTerminal = ({ entries, apiStatus }: SystemTerminalProps) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [entries]);

  return (
    <div className="terminal-window flex h-full min-h-[260px] min-w-0 flex-col overflow-hidden p-2">
      <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-neon-red" />
          <span className="w-2 h-2 rounded-full bg-neon-gold" />
          <span className="w-2 h-2 rounded-full bg-neon-green" />
          <span className="text-[9px] font-mono text-muted-foreground ml-1">system_log.out</span>
        </div>
        <span className={`px-2 py-0.5 rounded border text-[9px] font-mono uppercase ${statusStyles[apiStatus]}`}>
          {apiStatus}
        </span>
      </div>
      <div ref={containerRef} className="min-h-0 flex-1 overflow-auto space-y-0.5">
        {entries.map((entry, index) => (
          <p key={`${entry.text}-${index}`} className={`break-words text-[10px] font-mono leading-tight ${lineStyles[entry.level]}`}>
            {entry.text}
          </p>
        ))}
        <span className="text-neon-green/70 text-[10px] font-mono blink">|</span>
      </div>
    </div>
  );
};

export default SystemTerminal;
