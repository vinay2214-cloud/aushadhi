export function DataQualityBar({ score, showValue = true }: { score: number; showValue?: boolean }) {
  const value = score > 1 ? score : score * 100;
  const color = value > 90 ? "bg-emerald-500" : value >= 70 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full transition-all duration-300 ${color}`}
          style={{ width: `${Math.min(100, value)}%` }}
        />
      </div>
      {showValue ? (
        <span className="shrink-0 font-mono text-[11px] tabular-nums text-slate-400">
          {value.toFixed(0)}%
        </span>
      ) : null}
    </div>
  );
}
