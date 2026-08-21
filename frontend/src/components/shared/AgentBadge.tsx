import type { AgentName } from "../../types/agent";

const STYLES: Record<AgentName, string> = {
  SENTINEL: "bg-slate-500/20 text-slate-300 border border-slate-500/30",
  DQMS: "bg-blue-500/20 text-blue-400 border border-blue-500/30",
  FORECAST: "bg-purple-500/20 text-purple-400 border border-purple-500/30",
  PROCUREMENT: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
  ALERT: "bg-orange-600/20 text-orange-400 border border-orange-600/30",
};

export function AgentBadge({ agent }: { agent: AgentName }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold tracking-wider ${STYLES[agent]}`}
    >
      {agent}
    </span>
  );
}
