import { Sparkles, Play, Activity } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { AgentBadge } from "../shared/AgentBadge";
import { PulsingDot } from "../shared/PulsingDot";
import { TimeAgo } from "../shared/TimeAgo";
import { LoadingSpinner } from "../shared/LoadingSpinner";
import { ErrorState } from "../shared/ErrorState";
import { EmptyState } from "../shared/EmptyState";
import { useAgentLogs } from "../../hooks/useAgents";
import { runSentinel } from "../../api/agents";

export function AgentActivityFeed() {
  const { data, isLoading, isError, refetch } = useAgentLogs({ limit: 30 });
  const queryClient = useQueryClient();

  const run = useMutation({
    mutationFn: runSentinel,
    onSuccess: () => {
      toast.success("Pipeline run triggered");
      queryClient.invalidateQueries({ queryKey: ["agent-logs"] });
    },
    onError: () => toast.error("Could not start pipeline"),
  });

  const logs = data?.data ?? [];

  return (
    <section
      className="rounded-lg"
      style={{ backgroundColor: "#111113", border: "1px solid var(--border-subtle)" }}
    >
      <div className="flex items-center justify-between gap-3 border-b border-white/[0.06] px-4 py-3">
        <div className="flex items-center gap-2">
          <PulsingDot color="green" />
          <h2 className="card-label">Agent Pipeline</h2>
        </div>
        <button
          onClick={() => run.mutate()}
          disabled={run.isPending}
          className="inline-flex items-center gap-1.5 rounded-md bg-white/[0.06] px-2.5 py-1.5 text-[12px] font-medium text-[#FAFAFA] hover:bg-white/[0.1] disabled:opacity-50"
        >
          <Play className="size-3.5" color="#22C55E" />
          {run.isPending ? "Starting…" : "Run Pipeline Now"}
        </button>
      </div>

      <div className="max-h-[640px] overflow-y-auto">
        {isLoading ? (
          <div className="p-4">
            <LoadingSpinner label="Loading agent activity" rows={6} height={44} />
          </div>
        ) : isError ? (
          <div className="p-4">
            <ErrorState message="Agent log stream unavailable." onRetry={() => refetch()} />
          </div>
        ) : logs.length === 0 ? (
          <div className="p-4">
            <EmptyState
              icon={Activity}
              title="Pipeline is watching"
              message="No agent activity yet — run the pipeline to see steps."
            />
          </div>
        ) : (
          <ul className="divide-y divide-white/[0.05]">
            {logs.map((log) => (
              <li key={log.id} className="au-fade flex gap-3 px-4 py-2.5 hover:bg-white/[0.03]">
                <AgentBadge agent={log.agent_name} />
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-1 font-mono text-[12px] text-slate-300">
                    <span className="truncate">{log.action}</span>
                    {log.gemini_call ? (
                      <Sparkles className="size-3 shrink-0" color="#A855F7" />
                    ) : null}
                  </p>
                  <p className="truncate font-mono text-[11px] text-slate-600">
                    {log.center_name ?? log.center_id ?? "system"} · {log.key_output}
                  </p>
                </div>
                <TimeAgo date={log.created_at} className="shrink-0 text-[11px] text-slate-600" />
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
