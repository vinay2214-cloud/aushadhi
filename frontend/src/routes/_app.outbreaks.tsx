import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Check, ChevronDown, ShieldCheck } from "lucide-react";
import { RiskLevelBadge } from "../components/shared/RiskLevelBadge";
import { LoadingSpinner } from "../components/shared/LoadingSpinner";
import { ErrorState } from "../components/shared/ErrorState";
import { EmptyState } from "../components/shared/EmptyState";
import { TimeAgo } from "../components/shared/TimeAgo";
import { useOutbreaks } from "../hooks/useOutbreaks";
import { acknowledgeOutbreak, resolveOutbreak } from "../api/outbreaks";
import type { OutbreakStatus } from "../types/outbreak";

export const Route = createFileRoute("/_app/outbreaks")({
  head: () => ({
    meta: [
      { title: "Outbreak Intelligence — AUSHADHI" },
      {
        name: "description",
        content:
          "Geographic clusters, consumption evidence and recommended response actions for detected disease outbreaks.",
      },
      { property: "og:title", content: "Outbreak Intelligence — AUSHADHI" },
      {
        property: "og:description",
        content: "Disease outbreak clusters detected from medicine consumption anomalies.",
      },
    ],
  }),
  component: OutbreaksPage,
});

const TABS: Array<{ label: string; value: OutbreakStatus | "ALL" }> = [
  { label: "Active", value: "ACTIVE" },
  { label: "Under response", value: "UNDER_RESPONSE" },
  { label: "Resolved", value: "RESOLVED" },
  { label: "All", value: "ALL" },
];

const ACCENT: Record<string, string> = {
  CRITICAL: "#EF4444",
  HIGH: "#F97316",
  MEDIUM: "#F59E0B",
  LOW: "#3B82F6",
  NONE: "#52525B",
};

function ConfidenceRing({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const r = 18;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative size-12 shrink-0">
      <svg viewBox="0 0 44 44" className="size-12 -rotate-90">
        <circle cx="22" cy="22" r={r} fill="none" stroke="#1A1A1E" strokeWidth="3" />
        <circle
          cx="22"
          cy="22"
          r={r}
          fill="none"
          stroke="#0A84FF"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - value)}
          className="transition-all duration-500"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center font-mono text-[11px] tabular-nums text-slate-200">
        {pct}
      </span>
    </div>
  );
}

function OutbreaksPage() {
  const [tab, setTab] = useState<OutbreakStatus | "ALL">("ACTIVE");
  const [collapsed, setCollapsed] = useState<string[]>([]);
  const queryClient = useQueryClient();
  const { data, isLoading, isError, refetch } = useOutbreaks(
    tab === "ALL" ? { limit: 50 } : { status: tab, limit: 50 },
  );

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["outbreaks"] });
    queryClient.invalidateQueries({ queryKey: ["metrics"] });
  };

  const ack = useMutation({
    mutationFn: acknowledgeOutbreak,
    onSuccess: () => {
      toast.success("Alert acknowledged");
      invalidate();
    },
    onError: () => toast.error("Could not acknowledge alert"),
  });

  const resolve = useMutation({
    mutationFn: resolveOutbreak,
    onSuccess: () => {
      toast.success("Alert resolved");
      invalidate();
    },
    onError: () => toast.error("Could not resolve alert"),
  });

  const alerts = data?.data ?? [];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-[20px] font-semibold tracking-tight text-slate-100">
          Outbreak Intelligence
        </h1>
        <p className="text-[13px] text-slate-500">
          Clusters inferred from abnormal medicine consumption patterns
        </p>
      </header>

      <div className="flex gap-1 rounded-lg border border-white/[0.07] p-1 text-[13px]">
        {TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => setTab(t.value)}
            className={`rounded-lg px-3 py-1.5 font-medium ${
              tab === t.value
                ? "bg-white/[0.08] text-slate-100"
                : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <LoadingSpinner label="Loading outbreak alerts" rows={4} height={140} />
      ) : isError ? (
        <ErrorState message="Outbreak data unavailable." onRetry={() => refetch()} />
      ) : alerts.length === 0 ? (
        <EmptyState
          icon={ShieldCheck}
          title="No active outbreaks"
          message="Consumption patterns are within expected ranges."
        />
      ) : (
        <div className="space-y-4">
          {alerts.map((a, idx) => {
            const isOpen = !collapsed.includes(a.id);
            return (
              <article
                key={a.id}
                className="au-rise group overflow-hidden rounded-lg border border-white/[0.07] bg-[#111113]"
                style={{ animationDelay: `${idx * 50}ms`, borderLeft: `3px solid ${ACCENT[a.risk_level]}` }}
              >
                <div className="flex items-center gap-4 p-5">
                  <ConfidenceRing value={a.confidence} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <RiskLevelBadge level={a.risk_level} />
                      <h2 className="text-[15px] font-semibold text-slate-100">
                        {a.geographic_cluster}
                      </h2>
                      <span className="rounded-full bg-white/[0.05] px-2 py-0.5 text-[11px] text-slate-500">
                        {a.status.replace("_", " ")}
                      </span>
                    </div>
                    <p className="mt-1 truncate text-[13px] text-slate-500">{a.outbreak_summary}</p>
                  </div>
                  <TimeAgo date={a.created_at} className="shrink-0 text-[11px] text-slate-600" />
                  <button
                    onClick={() =>
                      setCollapsed((c) =>
                        c.includes(a.id) ? c.filter((x) => x !== a.id) : [...c, a.id],
                      )
                    }
                    aria-label={isOpen ? "Collapse" : "Expand"}
                    className="rounded p-1 text-slate-600 hover:bg-white/[0.06] hover:text-slate-300"
                  >
                    <ChevronDown
                      className={`size-4 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
                    />
                  </button>
                </div>

                {isOpen ? (
                  <div className="au-fade border-t border-white/[0.06] p-5">
                    <div className="flex flex-wrap gap-1.5">
                      {a.disease_indicators.map((d) => (
                        <span
                          key={d}
                          className="rounded-full border border-orange-600/30 bg-orange-600/15 px-2 py-0.5 text-[11px] text-orange-300"
                        >
                          {d}
                        </span>
                      ))}
                      <span className="rounded-full bg-white/[0.05] px-2 py-0.5 text-[11px] text-slate-500">
                        {a.affected_center_ids.length} centers affected
                      </span>
                    </div>

                    {a.key_evidence.length > 0 ? (
                      <table className="mt-4 w-full text-left text-[13px]">
                        <thead className="card-label">
                          <tr>
                            <th className="pb-1 font-medium">Medicine</th>
                            <th className="pb-1 font-medium">Ratio</th>
                            <th className="pb-1 font-medium">Significance</th>
                          </tr>
                        </thead>
                        <tbody>
                          {a.key_evidence.map((e) => (
                            <tr key={e.medicine} className="border-t border-white/[0.05]">
                              <td className="py-1.5 text-slate-300">{e.medicine}</td>
                              <td className="py-1.5 font-mono font-semibold tabular-nums text-red-400">
                                {e.ratio.toFixed(1)}x
                              </td>
                              <td className="py-1.5 font-mono tabular-nums text-slate-500">
                                {e.normal_daily_consumption} → {e.current_daily_consumption} /day
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : null}

                    {a.recommended_actions.length > 0 ? (
                      <ul className="mt-4 space-y-1.5">
                        {a.recommended_actions.map((r) => (
                          <li key={r} className="flex gap-2 text-[13px] text-slate-400">
                            <Check className="mt-1 size-3.5 shrink-0 text-emerald-500" />
                            {r}
                          </li>
                        ))}
                      </ul>
                    ) : null}

                    <div className="mt-4 flex flex-wrap gap-2 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
                      {a.status === "ACTIVE" ? (
                        <button
                          onClick={() => ack.mutate(a.id)}
                          disabled={ack.isPending}
                          className="rounded-lg bg-orange-600 px-3 py-1.5 text-[12px] font-semibold text-slate-950 hover:bg-orange-500 disabled:opacity-50"
                        >
                          Acknowledge
                        </button>
                      ) : null}
                      {a.status !== "RESOLVED" ? (
                        <button
                          onClick={() => resolve.mutate(a.id)}
                          disabled={resolve.isPending}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.07] px-3 py-1.5 text-[12px] font-medium text-slate-300 hover:bg-white/[0.06] disabled:opacity-50"
                        >
                          <ShieldCheck className="size-3.5" />
                          Resolve
                        </button>
                      ) : null}
                    </div>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
