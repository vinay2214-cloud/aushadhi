export function DaysUntilStockout({ days }: { days: number | null | undefined }) {
  if (days == null) return <span className="text-slate-600">—</span>;
  const color = days < 7 ? "text-red-400" : days < 14 ? "text-amber-400" : "text-slate-300";
  return (
    <span className={`font-mono text-xs font-semibold ${color}`}>
      {days} day{days === 1 ? "" : "s"}
    </span>
  );
}
