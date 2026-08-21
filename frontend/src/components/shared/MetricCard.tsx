import type { LucideIcon } from "lucide-react";

type Tone = "red" | "orange" | "emerald" | "amber" | "blue" | "slate";

const DOT: Record<Tone, string> = {
  red: "#EF4444",
  orange: "#F97316",
  emerald: "#22C55E",
  amber: "#F59E0B",
  blue: "#3B82F6",
  slate: "#52525B",
};

export function MetricCard({
  label,
  value,
  tone = "slate",
  icon: Icon,
  hint,
  trend,
  index = 0,
}: {
  label: string;
  value: string | number;
  tone?: Tone;
  icon?: LucideIcon;
  hint?: string;
  trend?: string;
  index?: number;
}) {
  return (
    <div
      className="au-rise panel-card transition-colors hover:bg-[#161618]"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="card-label">{label}</p>
        {Icon ? <Icon className="size-4 text-[#52525B]" /> : null}
      </div>

      <div className="mt-3 flex items-center gap-2">
        <span
          className="inline-block size-1.5 shrink-0 rounded-full"
          style={{ backgroundColor: DOT[tone] }}
        />
        <p className="data-number">{value}</p>
      </div>

      {trend ? <p className="mt-1.5 text-[11px] text-[#52525B]">{trend}</p> : null}
      {hint ? <p className="mt-1 text-[11px] text-[#52525B]">{hint}</p> : null}
    </div>
  );
}
