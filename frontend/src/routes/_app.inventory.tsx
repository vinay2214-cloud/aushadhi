import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle } from "lucide-react";
import { LoadingSpinner } from "../components/shared/LoadingSpinner";
import { ErrorState } from "../components/shared/ErrorState";
import { EmptyState } from "../components/shared/EmptyState";
import { DaysUntilStockout } from "../components/shared/DaysUntilStockout";
import { ConsumptionRatioDisplay } from "../components/shared/ConsumptionRatioDisplay";
import { useInventory } from "../hooks/useInventory";
import { useHealthCenters } from "../hooks/useHealthCenters";
/**
 * Heatmap columns. Keyed by medicine_id — the previous version keyed the
 * lookup on medicine_name and queried it with short display labels ("ORS"),
 * which never matched the API's names ("ORS Packets (WHO Formula)"), so every
 * cell fell through to "—" even with a full inventory loaded.
 */
const MEDICINE_COLUMNS = [
  { id: "med_ors_001", label: "ORS" },
  { id: "med_zinc_001", label: "Zinc" },
  { id: "med_ivns_001", label: "IV Saline" },
  { id: "med_paracetamol_001", label: "Paracetamol" },
  { id: "med_metronidazole_001", label: "Metronidazole" },
  { id: "med_chloroquine_001", label: "Chloroquine" },
] as const;
import type { InventoryItem } from "../types/inventory";

export const Route = createFileRoute("/_app/inventory")({
  head: () => ({
    meta: [
      { title: "Inventory Heatmap — AUSHADHI" },
      {
        name: "description",
        content:
          "Medicine stock levels across every health center, with stockout runway and consumption anomaly detection.",
      },
      { property: "og:title", content: "Inventory Heatmap — AUSHADHI" },
      {
        property: "og:description",
        content: "Medicine stock levels across every health center with anomaly detection.",
      },
    ],
  }),
  component: InventoryPage,
});

function stockColor(pct: number) {
  if (pct < 15) return "#EF4444"; // CRITICAL
  if (pct < 30) return "#F59E0B"; // LOW
  if (pct < 50) return "#A1A1AA"; // MONITOR — between LOW and OK
  return "#22C55E"; // OK
}

function InventoryPage() {
  const [query, setQuery] = useState("");
  const [criticalOnly, setCriticalOnly] = useState(false);
  const [selected, setSelected] = useState<InventoryItem | null>(null);

  const inventory = useInventory({ limit: 500 });
  const centers = useHealthCenters({ limit: 500 });

  const items = inventory.data?.data ?? [];
  const centerList = centers.data?.data ?? [];

  const stockMap = useMemo(() => {
    const map: Record<string, InventoryItem> = {};
    for (const item of items) {
      map[`${item.center_id}_${item.medicine_id}`] = item;
    }
    return map;
  }, [items]);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return centerList.filter((c) => {
      if (q && !c.name.toLowerCase().includes(q) && !c.district.toLowerCase().includes(q))
        return false;
      if (criticalOnly && c.status.critical_items_count === 0) return false;
      return true;
    });
  }, [centerList, query, criticalOnly]);

  const critical = useMemo(
    () =>
      [...items]
        .filter((i) => i.urgency === "CRITICAL")
        .sort((a, b) => (a.days_until_stockout ?? 999) - (b.days_until_stockout ?? 999))
        .slice(0, 12),
    [items],
  );

  const isLoading = inventory.isLoading || centers.isLoading;
  const isError = inventory.isError || centers.isError;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[20px] font-semibold tracking-tight text-[#FAFAFA]">
            Inventory Heatmap
          </h1>
          <p className="text-[13px] text-slate-500">
            Stock percentage per medicine across monitored centers
          </p>
        </div>
        <div className="flex items-center gap-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search center or district…"
            className="w-56 rounded-md border border-white/[0.07] bg-[#111113] px-3 py-2 text-[13px] text-[#FAFAFA] outline-none placeholder:text-[#52525B] focus:border-[#3B82F6]"
          />
          <label className="flex items-center gap-2 text-[13px] text-slate-400">
            <input
              type="checkbox"
              checked={criticalOnly}
              onChange={(e) => setCriticalOnly(e.target.checked)}
              className="size-3.5 accent-emerald-500"
            />
            Critical only
          </label>
        </div>
      </header>

      {isLoading ? (
        <LoadingSpinner label="Loading inventory" rows={9} height={40} />
      ) : isError ? (
        <ErrorState message="Inventory data unavailable." onRetry={() => inventory.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState title="No centers match your filters" />
      ) : (
        <div
          className="overflow-x-auto rounded-lg"
          style={{ border: "1px solid var(--border-subtle)", backgroundColor: "#09090B" }}
        >
          <table className="w-full min-w-[980px] text-left text-[13px]">
            <thead className="sticky top-0 z-10">
              <tr
                className="card-label"
                style={{
                  backgroundColor: "#111113",
                  borderBottom: "1px solid rgba(255,255,255,0.07)",
                }}
              >
                <th
                  className="sticky left-0 z-10 px-4 py-2.5 font-medium"
                  style={{ backgroundColor: "#111113" }}
                >
                  Health Center
                </th>
                {MEDICINE_COLUMNS.map((m) => (
                  <th key={m.id} className="px-3 py-2.5 font-medium">
                    {m.label}
                  </th>
                ))}
                <th className="w-20 px-3 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {rows.map((c, rowIdx) => {
                const zebra = rowIdx % 2 === 0 ? "#09090B" : "#0D0D0F";
                const firstItem = MEDICINE_COLUMNS.map((m) => stockMap[`${c.id}_${m.id}`]).find(
                  Boolean,
                );
                return (
                  <tr
                    key={c.id}
                    className="group h-10 hover:bg-white/[0.03]"
                    style={{ backgroundColor: zebra }}
                  >
                    <td
                      className="sticky left-0 h-10 max-w-[220px] truncate px-4"
                      style={{ backgroundColor: zebra }}
                    >
                      <span className="truncate font-medium text-[#FAFAFA]">{c.name}</span>
                      <span className="ml-2 text-[11px] text-[#52525B]">{c.district}</span>
                    </td>
                    {MEDICINE_COLUMNS.map((m) => {
                      const key = `${c.id}_${m.id}`;
                      const item = stockMap[key];
                      const stockPct = item?.stock_percentage ?? null;
                      // "—" only when this center genuinely has no row for the medicine.
                      if (!item || stockPct === null)
                        return (
                          <td key={m.id} className="px-3 text-[#52525B]">
                            —
                          </td>
                        );
                      return (
                        <td key={m.id} className="px-3">
                          <button
                            onClick={() => setSelected(item)}
                            className="flex items-center gap-2 text-left"
                          >
                            <span
                              className="font-mono text-[12px] tabular-nums"
                              style={{ color: stockColor(stockPct) }}
                            >
                              {stockPct.toFixed(0)}%
                            </span>
                            <span
                              className="h-1 w-[80px] shrink-0 overflow-hidden rounded-full"
                              style={{ backgroundColor: "#1A1A1E" }}
                            >
                              <span
                                className="block h-full rounded-full"
                                style={{
                                  width: `${Math.min(100, stockPct)}%`,
                                  backgroundColor: stockColor(stockPct),
                                }}
                              />
                            </span>
                            {item.anomaly_flag ? (
                              <AlertTriangle className="size-3 shrink-0" color="#F97316" />
                            ) : null}
                          </button>
                        </td>
                      );
                    })}
                    <td className="px-3 text-right">
                      {firstItem ? (
                        <button
                          onClick={() => setSelected(firstItem)}
                          className="rounded-md border border-white/[0.07] px-2 py-1 text-[11px] text-slate-300 opacity-0 transition-opacity hover:bg-white/[0.06] group-hover:opacity-100"
                        >
                          Details
                        </button>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <section>
        <h2 className="mb-3 text-sm font-semibold text-slate-100">Critical Items</h2>
        {critical.length === 0 ? (
          <EmptyState title="No critical items" message="All monitored stock is above threshold." />
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {critical.map((i) => (
              <div
                key={`${i.center_id}-${i.medicine_id}`}
                className="panel-card"
                style={{ borderColor: "#EF44443A" }}
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-slate-100">{i.medicine_name}</p>
                  <DaysUntilStockout days={i.days_until_stockout} />
                </div>
                <p className="mt-1 text-[11px] text-slate-500">
                  {centerList.find((c) => c.id === i.center_id)?.name ?? i.center_id}
                </p>
                <div className="mt-3 flex items-center justify-between font-mono text-[11px] text-slate-400">
                  <span>
                    {i.current_stock} / {i.maximum_capacity}
                  </span>
                  <ConsumptionRatioDisplay ratio={i.consumption_ratio} />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {selected ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-[#09090B]/80 p-4"
          onClick={() => setSelected(null)}
        >
          <div
            className="panel-card w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-sm font-semibold text-slate-100">{selected.medicine_name}</h3>
            <p className="text-[11px] text-slate-500">
              {centerList.find((c) => c.id === selected.center_id)?.name ?? selected.center_id}
            </p>
            <dl className="mt-4 space-y-2 text-xs">
              {[
                ["Current stock", `${selected.current_stock}`],
                ["Minimum threshold", `${selected.minimum_threshold}`],
                ["Maximum capacity", `${selected.maximum_capacity}`],
                ["Consumption today", `${selected.daily_consumption_today}`],
                ["7-day average", `${selected.seven_day_avg_consumption}`],
                ["Pending order qty", `${selected.pending_order_quantity}`],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between border-b border-slate-800/40 pb-1.5">
                  <dt className="text-slate-500">{k}</dt>
                  <dd className="font-mono text-slate-200">{v}</dd>
                </div>
              ))}
            </dl>
            <button
              onClick={() => setSelected(null)}
              className="mt-4 w-full rounded-md border border-slate-800 py-2 text-xs text-slate-300 hover:bg-slate-800"
            >
              Close
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
