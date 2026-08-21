export function ConsumptionRatioDisplay({ ratio }: { ratio: number | null | undefined }) {
  if (ratio == null) return <span className="text-slate-600">—</span>;
  const color = ratio > 2 ? "text-red-400" : ratio > 1.3 ? "text-amber-400" : "text-emerald-400";
  return <span className={`font-mono text-xs font-semibold ${color}`}>{ratio.toFixed(1)}x</span>;
}
