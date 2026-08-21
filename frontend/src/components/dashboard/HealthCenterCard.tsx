import { useState } from "react";
import { AlertTriangle, ChevronDown } from "lucide-react";
import { DataQualityBar } from "../shared/DataQualityBar";
import { TimeAgo } from "../shared/TimeAgo";
import { DaysUntilStockout } from "../shared/DaysUntilStockout";
import { ConsumptionRatioDisplay } from "../shared/ConsumptionRatioDisplay";
import type { HealthCenter, StockStatus } from "../../types/health-center";
import type { InventoryItem } from "../../types/inventory";

const BAR: Record<StockStatus, string> = {
  CRITICAL: "#EF4444",
  LOW: "#F59E0B",
  MODERATE: "#3B82F6",
  GOOD: "#22C55E",
};

export function HealthCenterCard({
  center,
  items,
  index = 0,
}: {
  center: HealthCenter;
  items: InventoryItem[];
  index?: number;
}) {
  const [open, setOpen] = useState(false);
  const centerItems = items.filter((i) => i.center_id === center.id);
  const hasAnomaly = centerItems.some((i) => i.anomaly_flag);
  const top3 = [...centerItems]
    .filter((i) => i.urgency === "CRITICAL" || i.urgency === "LOW")
    .sort((a, b) => (a.days_until_stockout ?? 999) - (b.days_until_stockout ?? 999))
    .slice(0, 3);

  return (
    <div
      className="au-rise overflow-hidden rounded-lg"
      style={{
        backgroundColor: "#111113",
        border: "1px solid var(--border-subtle)",
        animationDelay: `${index * 40}ms`,
      }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex h-16 w-full items-center gap-3 pr-4 text-left transition-colors hover:bg-white/[0.03]"
      >
        <span
          className="h-16 w-1 shrink-0"
          style={{ backgroundColor: BAR[center.status.overall_stock_status] }}
        />

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-[14px] font-medium text-[#FAFAFA]">{center.name}</span>
            <span className="shrink-0 rounded bg-white/[0.06] px-1.5 py-0.5 font-mono text-[10px] text-slate-500">
              {center.type}
            </span>
            {hasAnomaly ? <AlertTriangle className="size-3.5 shrink-0" color="#F97316" /> : null}
          </div>
          <p className="truncate text-[12px] text-slate-600">
            {center.subdistrict}, {center.district} · <TimeAgo date={center.status.last_checked} />
          </p>
        </div>

        {center.status.critical_items_count > 0 ? (
          <span className="badge-base badge-critical shrink-0 tabular-nums">
            {center.status.critical_items_count} critical
          </span>
        ) : null}

        <div className="w-[60px] shrink-0">
          <DataQualityBar score={center.status.data_quality_score} showValue={false} />
        </div>
        <span className="w-8 shrink-0 text-right font-mono text-[11px] tabular-nums text-slate-500">
          {Math.round(
            center.status.data_quality_score > 1
              ? center.status.data_quality_score
              : center.status.data_quality_score * 100,
          )}
        </span>

        <ChevronDown
          className={`size-4 shrink-0 text-slate-600 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open ? (
        <div className="au-fade border-t border-white/[0.06] px-5 py-4">
          {top3.length === 0 ? (
            <p className="text-[13px] text-slate-600">No critical or low stock items.</p>
          ) : (
            <table className="w-full text-left text-[13px]">
              <thead className="card-label">
                <tr>
                  <th className="pb-1 font-medium">Medicine</th>
                  <th className="pb-1 font-medium">Stock</th>
                  <th className="pb-1 font-medium">Days left</th>
                  <th className="pb-1 font-medium">Ratio</th>
                </tr>
              </thead>
              <tbody>
                {top3.map((i) => (
                  <tr key={i.medicine_id} className="border-t border-white/[0.05]">
                    <td className="py-1.5 text-slate-300">{i.medicine_name}</td>
                    <td className="py-1.5 font-mono tabular-nums text-slate-400">
                      {i.stock_percentage.toFixed(0)}%
                    </td>
                    <td className="py-1.5">
                      <DaysUntilStockout days={i.days_until_stockout} />
                    </td>
                    <td className="py-1.5">
                      <ConsumptionRatioDisplay ratio={i.consumption_ratio} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ) : null}
    </div>
  );
}
