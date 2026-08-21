import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Loader2, Play, RotateCcw, Wifi } from "lucide-react";
import { LoadingSpinner } from "../components/shared/LoadingSpinner";
import { ErrorState } from "../components/shared/ErrorState";
import { DataQualityBar } from "../components/shared/DataQualityBar";
import { TimeAgo } from "../components/shared/TimeAgo";
import { fetchConfig, fetchDataQuality, resetDemo, testConnection } from "../api/metrics";
import { runSentinel } from "../api/agents";
import { API_BASE_URL } from "../constants/api";
import { useUIStore } from "../store/uiStore";

export const Route = createFileRoute("/_app/settings")({
  head: () => ({
    meta: [
      { title: "Settings & Demo Controls — AUSHADHI" },
      {
        name: "description",
        content:
          "System configuration, data quality reporting and demo controls for the AUSHADHI supply intelligence platform.",
      },
      { property: "og:title", content: "Settings & Demo Controls — AUSHADHI" },
      {
        property: "og:description",
        content: "System configuration, data quality reporting and demo controls.",
      },
    ],
  }),
  component: SettingsPage,
});

function SettingsPage() {
  const queryClient = useQueryClient();
  const sseConnected = useUIStore((s) => s.sseConnected);

  const config = useQuery({ queryKey: ["config"], queryFn: fetchConfig });
  const quality = useQuery({ queryKey: ["data-quality"], queryFn: fetchDataQuality });

  const reset = useMutation({
    mutationFn: resetDemo,
    onSuccess: () => {
      toast.success("Demo data reset");
      queryClient.invalidateQueries();
    },
    onError: () => toast.error("Reset failed"),
  });

  const run = useMutation({
    mutationFn: runSentinel,
    onSuccess: () => toast.success("Pipeline run triggered"),
    onError: () => toast.error("Could not start pipeline"),
  });

  const ping = useMutation({
    mutationFn: testConnection,
    onSuccess: () => toast.success("API reachable"),
    onError: () => toast.error("API unreachable"),
  });

  const c = config.data;
  const reports = quality.data ?? [];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-[20px] font-semibold tracking-tight text-slate-100">Settings</h1>
        <p className="text-[13px] text-slate-500">System configuration and demo controls</p>
      </header>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-white/[0.07] bg-[#111113] p-5">
          <h2 className="card-label">System</h2>
          {config.isLoading ? (
            <LoadingSpinner label="Loading configuration" />
          ) : config.isError ? (
            <div className="mt-3">
              <ErrorState message="Config unavailable." onRetry={() => config.refetch()} />
            </div>
          ) : (
            <dl className="mt-4 space-y-2 text-xs">
              {[
                ["API base URL", API_BASE_URL],
                ["Live stream", sseConnected ? "CONNECTED" : "DISCONNECTED"],
                ["Districts monitored", String(c?.districts_monitored ?? "—")],
                ["Centers monitored", String(c?.centers_monitored ?? "—")],
                ["Medicines tracked", String(c?.medicines_tracked ?? "—")],
                ["Active model", c?.active_model ?? "—"],
                ["Gemma fallback", c?.gemma_fallback_enabled ? "Enabled" : "Disabled"],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 border-b border-white/[0.07] pb-1.5">
                  <dt className="text-slate-500">{k}</dt>
                  <dd className="truncate font-mono text-slate-200">{v}</dd>
                </div>
              ))}
              <div className="flex justify-between gap-4 pt-1">
                <dt className="text-slate-500">Last pipeline run</dt>
                <dd className="font-mono text-slate-200">
                  <TimeAgo date={c?.last_pipeline_run} />
                </dd>
              </div>
            </dl>
          )}
        </div>

        <div className="rounded-lg border border-white/[0.07] bg-[#111113] p-5">
          <h2 className="card-label">Demo Controls</h2>
          <div className="mt-4 space-y-3">
            <button
              onClick={() => run.mutate()}
              disabled={run.isPending}
              className="flex w-full items-center justify-center gap-2 rounded-md bg-emerald-500 px-3 py-2 text-xs font-semibold text-slate-950 hover:bg-emerald-400 disabled:opacity-50"
            >
              {run.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Play className="size-3.5" />
              )}
              Run pipeline now
            </button>
            <button
              onClick={() => ping.mutate()}
              disabled={ping.isPending}
              className="flex w-full items-center justify-center gap-2 rounded-md border border-white/[0.10] px-3 py-2 text-[12px] font-medium text-slate-300 hover:bg-white/[0.06] disabled:opacity-50"
            >
              <Wifi className="size-3.5" />
              Test API connection
            </button>
            <button
              onClick={() => {
                if (confirm("Reset all demo data to its initial state?")) reset.mutate();
              }}
              disabled={reset.isPending}
              className="flex w-full items-center justify-center gap-2 rounded-md border border-red-500/40 px-3 py-2 text-xs font-medium text-red-400 hover:bg-red-500/10 disabled:opacity-50"
            >
              <RotateCcw className="size-3.5" />
              Reset demo data
            </button>
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-white/[0.07] bg-[#111113] p-5">
        <h2 className="card-label">Data Quality by Center</h2>
        {quality.isLoading ? (
          <div className="mt-4">
            <LoadingSpinner label="Loading data quality" rows={5} />
          </div>
        ) : quality.isError ? (
          <div className="mt-3">
            <ErrorState message="Data quality report unavailable." onRetry={() => quality.refetch()} />
          </div>
        ) : (
          <div className="mt-4 grid gap-x-8 gap-y-3 md:grid-cols-2">
            {reports.map((r) => {
              const value = r.score > 1 ? r.score : r.score * 100;
              const tone =
                value > 90 ? "text-emerald-400" : value >= 70 ? "text-amber-400" : "text-red-400";
              return (
                <div key={r.center_id} className="flex items-center gap-3">
                  <span className="w-44 shrink-0 truncate text-[13px] text-slate-300">
                    {r.center_name}
                  </span>
                  <div className="min-w-0 flex-1">
                    <DataQualityBar score={r.score} showValue={false} />
                  </div>
                  <span className={`w-10 shrink-0 text-right font-mono text-[12px] tabular-nums ${tone}`}>
                    {value.toFixed(0)}%
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
