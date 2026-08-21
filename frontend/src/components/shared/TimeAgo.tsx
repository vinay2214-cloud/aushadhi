import { formatDistanceToNowStrict } from "date-fns";

export function TimeAgo({ date, className = "" }: { date: string | null | undefined; className?: string }) {
  if (!date) return <span className={`text-slate-600 ${className}`}>—</span>;
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return <span className={`text-slate-600 ${className}`}>—</span>;
  return (
    <span className={className}>
      {formatDistanceToNowStrict(parsed, { addSuffix: true })
        .replace(" minutes", "m")
        .replace(" minute", "m")
        .replace(" hours", "h")
        .replace(" hour", "h")
        .replace(" seconds", "s")
        .replace(" second", "s")
        .replace(" days", "d")
        .replace(" day", "d")}
    </span>
  );
}
