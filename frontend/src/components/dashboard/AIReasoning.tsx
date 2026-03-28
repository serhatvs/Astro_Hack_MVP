interface AIReasoningProps {
  message: string | null;
  isAdaptive: boolean;
  error: string | null;
}

const defaultText =
  "A deterministic mission summary will appear here after the backend generates a recommendation. Use the mission inputs above, then trigger a crisis simulation to show how the plan adapts.";

const AIReasoning = ({ message, isAdaptive, error }: AIReasoningProps) => {
  const bodyText = error || message || defaultText;
  const textColor = error ? "text-neon-red" : isAdaptive ? "text-neon-orange" : "text-foreground/80";

  return (
    <div className="glass-panel flex h-full min-h-[260px] min-w-0 flex-col overflow-hidden p-3 space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
          {isAdaptive ? "Adaptation Summary" : "Mission Summary"}
        </h3>
        <span className={`text-[9px] font-mono uppercase px-2 py-0.5 rounded border ${isAdaptive ? "border-neon-orange/50 text-neon-orange" : "border-glass-border text-muted-foreground"}`}>
          {error ? "Backend Error" : isAdaptive ? "Runtime Update" : "Deterministic Report"}
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-auto rounded-lg border border-glass-border bg-terminal p-3">
        <p className={`break-words text-xs font-mono leading-relaxed ${textColor}`}>{bodyText}</p>
      </div>
    </div>
  );
};

export default AIReasoning;
