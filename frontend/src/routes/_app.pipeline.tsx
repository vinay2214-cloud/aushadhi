import { createFileRoute } from "@tanstack/react-router";
import { Workflow } from "lucide-react";
import { LoadingSpinner } from "../components/shared/LoadingSpinner";
import { ErrorState } from "../components/shared/ErrorState";
import { EmptyState } from "../components/shared/EmptyState";
import { TimeAgo } from "../components/shared/TimeAgo";
import { useAgentLogs, useAgents } from "../hooks/useAgents";
import type { AgentName } from "../types/agent";

export const Route = createFileRoute("/_app/pipeline")({
  head: () => ({
    meta: [
      { title: "Agent Pipeline — AUSHADHI" },
      {
        name: "description",
        content:
          "Health and execution timeline of the SENTINEL, DQMS, FORECAST, PROCUREMENT and ALERT agents.",
      },
      { property: "og:title", content: "Agent Pipeline — AUSHADHI" },
      {
        property: "og:description",
        content: "Execution timeline and health of the autonomous supply agents.",
      },
    ],
  }),
  component: PipelinePage,
});

const AGENT_ORDER: AgentName[] = ["SENTINEL", "DQMS", "FORECAST", "PROCUREMENT", "ALERT"];

const AGENT_COLOR: Record<AgentName, string> = {
  SENTINEL: "#71717A",
  DQMS: "#3B82F6",
  FORECAST: "#A855F7",
  PROCUREMENT: "#22C55E",
  ALERT: "#F97316",
};

const HEALTH_DOT: Record<string, string> = {
  HEALTHY: "#22C55E",
  DEGRADED: "#F59E0B",
  FAILING: "#EF4444",
  DOWN: "#EF4444",
  IDLE: "#52525B",
};

const STATUS_COLOR: Record<string, string> = {
  COMPLETED: "#22C55E",
  STARTED: "#3B82F6",
  RETRYING: "#F59E0B",
  FAILED: "#EF4444",
};

/** Simple connector between two pipeline nodes. */
function FlowArrow() {
  return (
    <svg
      width="28"
      height="8"
      viewBox="0 0 28 8"
      className="hidden shrink-0 xl:block"
      aria-hidden="true"
    >
      <line x1="0" y1="4" x2="20" y2="4" stroke="rgba(255,255,255,0.14)" strokeWidth="1" />
      <path d="M20 1 L26 4 L20 7 Z" fill="rgba(255,255,255,0.24)" />
    </svg>
  );
}

function PipelinePage() {
  const agents = useAgents();
  const logs = useAgentLogs({ limit: 60 });

  const agentList = agents.data ?? [];
  const logList = logs.data?.data ?? [];

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-[20px] font-semibold tracking-tight text-[#FAFAFA]">Agent Pipeline</h1>
        <p className="text-[13px] text-[#52525B]">
          Five-stage autonomous supply intelligence loop
        </p>
      </header>

      <section>
        <h2 className="card-label mb-3">Flow</h2>
        {agents.isLoading ? (
          <LoadingSpinner label="Loading agents" rows={1} height={96} />
        ) : agents.isError ? (
          <ErrorState message="Agent status unavailable." onRetry={() => agents.refetch()} />
        ) : (
          <div className="flex flex-col items-stretch gap-3 xl:flex-row xl:items-center">
            {AGENT_ORDER.map((name, idx) => {
              const agent = agentList.find((a) => a.name === name);
              const status = agent?.status ?? "IDLE";
              return (
                <div key={name} className="contents">
                  <div
                    className="au-rise shrink-0 rounded-lg p-4 xl:w-[120px]"
                    style={{
                      backgroundColor: "#111113",
                      border: "1px solid var(--border-subtle)",
                      animationDelay: `${idx * 40}ms`,
                    }}
                  >
                    <div className="flex items-center justify-center gap-1.5">
                      <span
                        className="inline-block size-1.5 shrink-0 rounded-full"
                        style={{ backgroundColor: HEALTH_DOT[status] ?? "#52525B" }}
                      />
                      <span
                        className="font-mono text-[11px] font-semibold tracking-wider"
                        style={{ color: AGENT_COLOR[name] }}
                      >
                        {name}
                      </span>
                    </div>
                    <p className="mt-2 text-center text-[11px] text-[#A1A1AA]">{status}</p>
                    <p className="mt-0.5 text-center text-[10px] text-[#52525B]">
                      <TimeAgo date={agent?.last_run} />
                    </p>
                  </div>
                  {idx < AGENT_ORDER.length - 1 ? <FlowArrow /> : null}
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section>
        <h2 className="card-label mb-3">Agent Log</h2>
        {logs.isLoading ? (
          <LoadingSpinner label="Loading agent logs" rows={8} />
        ) : logs.isError ? (
          <ErrorState message="Agent log history unavailable." onRetry={() => logs.refetch()} />
        ) : logList.length === 0 ? (
          <EmptyState
            icon={Workflow}
            title="Pipeline is watching"
            message="No agent activity recorded yet — the next cycle will appear here."
          />
        ) : (
          <div
            className="overflow-x-auto rounded-lg"
            style={{ border: "1px solid var(--border-subtle)" }}
          >
            <table className="w-full min-w-[720px] text-left font-mono text-[12px]">
              <thead className="sticky top-0 z-10">
                <tr style={{ backgroundColor: "#111113" }}>
                  {["Agent", "Action", "Center", "Status", "Duration", "Time"].map((h) => (
                    <th
                      key={h}
                      className="card-label px-4 py-2.5"
                      style={{ borderBottom: "1px solid var(--border-subtle)" }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {logList.map((log, i) => (
                  <tr
                    key={log.id}
                    className="h-10 hover:bg-white/[0.03]"
                    style={{ backgroundColor: i % 2 === 0 ? "#09090B" : "#0D0D0F" }}
                  >
                    <td
                      className="px-4 font-semibold tracking-wider"
                      style={{ color: AGENT_COLOR[log.agent_name] ?? "#A1A1AA" }}
                    >
                      {log.agent_name}
                    </td>
                    <td className="max-w-[220px] truncate px-4 text-[#D4D4D8]">{log.action}</td>
                    <td className="px-4 text-[#52525B]">
                      {log.center_name ?? log.center_id ?? "system"}
                    </td>
                    <td className="px-4" style={{ color: STATUS_COLOR[log.status] ?? "#A1A1AA" }}>
                      {log.status}
                    </td>
                    <td className="px-4 tabular-nums text-[#52525B]">
                      {log.duration_ms != null ? `${log.duration_ms} ms` : "—"}
                    </td>
                    <td className="px-4 text-[#52525B]">
                      <TimeAgo date={log.created_at} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
