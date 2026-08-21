import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle, Beaker, Building2, ClipboardList, Gauge, Siren } from "lucide-react";
import { MetricCard } from "../components/shared/MetricCard";
import { OutbreakBanner } from "../components/dashboard/OutbreakBanner";
import { HealthCenterCard } from "../components/dashboard/HealthCenterCard";
import { AgentActivityFeed } from "../components/dashboard/AgentActivityFeed";
import { SimulateModal } from "../components/dashboard/SimulateModal";
import { LoadingSpinner, MetricCardSkeleton } from "../components/shared/LoadingSpinner";
import { ErrorState } from "../components/shared/ErrorState";
import { EmptyState } from "../components/shared/EmptyState";
import { useMetrics } from "../hooks/useMetrics";
import { useHealthCenters } from "../hooks/useHealthCenters";
import { useInventory } from "../hooks/useInventory";
import { useOutbreaks } from "../hooks/useOutbreaks";
import type { StockStatus } from "../types/health-center";

export const Route = createFileRoute("/_app/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — AUSHADHI Supply Intelligence" },
      {
        name: "description",
        content:
          "Live view of rural medicine stock health: critical stockouts, outbreak alerts and autonomous agent activity.",
      },
      { property: "og:title", content: "Dashboard — AUSHADHI Supply Intelligence" },
      {
        property: "og:description",
        content:
          "Live view of rural medicine stock health: critical stockouts, outbreak alerts and autonomous agent activity.",
      },
    ],
  }),
  component: DashboardPage,
});

const FILTERS = ["ALL", "CRITICAL", "LOW", "GOOD"] as const;
const ORDER: Record<StockStatus, number> = { CRITICAL: 0, LOW: 1, MODERATE: 2, GOOD: 3 };

function DashboardPage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("ALL");
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [simulateOpen, setSimulateOpen] = useState(false);

  const metrics = useMetrics();
  const centers = useHealthCenters({ limit: 100 });
  const inventory = useInventory({ limit: 500 });
  const outbreaks = useOutbreaks({ status: "ACTIVE", limit: 10 });

  const items = inventory.data?.data ?? [];
  const activeAlert = (outbreaks.data?.data ?? []).find((a) => !dismissed.includes(a.id));

  const visibleCenters = useMemo(() => {
    const list = centers.data?.data ?? [];
    const filtered =
      filter === "ALL" ? list : list.filter((c) => c.status.overall_stock_status === filter);
    return [...filtered].sort(
      (a, b) => ORDER[a.status.overall_stock_status] - ORDER[b.status.overall_stock_status],
    );
  }, [centers.data, filter]);

  const m = metrics.data;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        {metrics.isLoading ? (
          <MetricCardSkeleton count={5} />
        ) : (
          <>
        <MetricCard
          index={0}
          label="Critical Stockouts"
          value={m?.critical_stockouts ?? "—"}
          tone={m && m.critical_stockouts > 0 ? "red" : "slate"}
          icon={AlertTriangle}
          trend="live from SENTINEL"
        />
        <MetricCard
          index={1}
          label="Outbreak Alerts"
          value={m?.active_outbreak_alerts ?? "—"}
          tone={m && m.active_outbreak_alerts > 0 ? "orange" : "slate"}
          icon={Siren}
          trend="active clusters"
        />
        <MetricCard
          index={2}
          label="Centers Monitored"
          value={m?.centers_monitored ?? "—"}
          tone="emerald"
          icon={Building2}
          trend="reporting today"
        />
        <MetricCard
          index={3}
          label="Pending Orders"
          value={m?.pending_purchase_orders ?? "—"}
          tone="amber"
          icon={ClipboardList}
          trend="awaiting approval"
        />
        <MetricCard
          index={4}
          label="Data Quality"
          value={
            m ? `${Math.round((m.avg_data_quality_score > 1 ? 1 : m.avg_data_quality_score) * 100)}%` : "—"
          }
          tone="blue"
          icon={Gauge}
          trend="DQMS rolling average"
        />
          </>
        )}
      </div>

      {metrics.isError ? (
        <ErrorState
          title="Metrics unavailable"
          message="Could not reach the AUSHADHI API."
          onRetry={() => metrics.refetch()}
        />
      ) : null}

      {activeAlert ? (
        <OutbreakBanner
          alert={activeAlert}
          onDismiss={() => setDismissed((d) => [...d, activeAlert.id])}
        />
      ) : null}

      <div className="grid gap-6 lg:grid-cols-5">
        <section className="lg:col-span-3">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h2 className="card-label">Health Centers</h2>
            <div className="flex gap-1 rounded-md border border-white/[0.07] p-1">
              {FILTERS.map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`rounded-md px-2.5 py-1 text-[11px] font-medium ${
                    filter === f
                      ? "bg-white/[0.08] text-[#FAFAFA]"
                      : "text-[#71717A] hover:bg-white/[0.04] hover:text-[#A1A1AA]"
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          {centers.isLoading ? (
            <LoadingSpinner label="Loading health centers" rows={6} height={64} />
          ) : centers.isError ? (
            <ErrorState
              message="Health center data unavailable."
              onRetry={() => centers.refetch()}
            />
          ) : visibleCenters.length === 0 ? (
            <EmptyState title="No centers match this filter" />
          ) : (
            <div className="space-y-2">
              {visibleCenters.map((c, i) => (
                <HealthCenterCard key={c.id} center={c} items={items} index={i} />
              ))}
            </div>
          )}
        </section>

        <div className="lg:col-span-2">
          <AgentActivityFeed />
        </div>
      </div>

      <button
        onClick={() => setSimulateOpen(true)}
        className="fixed bottom-6 right-6 z-40 inline-flex items-center gap-2 rounded-md px-4 py-2.5 text-[12px] font-semibold transition-colors"
        style={{ backgroundColor: "#22C55E", color: "#09090B" }}
      >
        <Beaker className="size-4" />
        Simulate Stockout
      </button>

      {simulateOpen ? <SimulateModal onClose={() => setSimulateOpen(false)} /> : null}
    </div>
  );
}
