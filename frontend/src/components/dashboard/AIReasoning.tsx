interface AIReasoningProps {
  message: string | null;
  isAdaptive: boolean;
  error: string | null;
}

const defaultText =
  "Mission-control reasoning will appear here after the backend generates a recommendation. Use the mission inputs above, then trigger a crisis simulation to show how the plan adapts.";

const AIReasoning = ({ message, isAdaptive, error }: AIReasoningProps) => {
  const bodyText = error || message || defaultText;
  const textColor = error ? "text-neon-red" : isAdaptive ? "text-neon-orange" : "text-foreground/80";

  return (
    <div className="glass-panel p-3 space-y-2 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <h3 className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
          {isAdaptive ? "Adaptive Reasoning" : "System Reasoning"}
        </h3>
        <span className={`text-[9px] font-mono uppercase px-2 py-0.5 rounded border ${isAdaptive ? "border-neon-orange/50 text-neon-orange" : "border-glass-border text-muted-foreground"}`}>
          {error ? "Backend Error" : isAdaptive ? "Runtime Update" : "Mission Planning"}
        </span>
      </div>

      <div className="flex-1 bg-terminal rounded-lg p-3 border border-glass-border overflow-auto">
        <p className={`text-xs font-mono leading-relaxed ${textColor}`}>{bodyText}</p>
      </div>
    </div>
  );
};

export default AIReasoning;
