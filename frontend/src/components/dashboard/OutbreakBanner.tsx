import { Link } from "@tanstack/react-router";
import { ArrowRight, X } from "lucide-react";
import type { OutbreakAlert } from "../../types/outbreak";

export function OutbreakBanner({
  alert,
  onDismiss,
}: {
  alert: OutbreakAlert;
  onDismiss: () => void;
}) {
  return (
    <div
      className="flex flex-wrap items-center justify-between gap-4"
      style={{
        backgroundColor: "rgba(249, 115, 22, 0.06)",
        borderLeft: "3px solid #F97316",
        padding: "12px 20px",
      }}
    >
      <div className="flex min-w-0 flex-1 items-center gap-3">
        {/* The one deliberately long animation in the product: 2s, infinite. */}
        <span
          className="outbreak-pulse inline-block size-2 shrink-0 rounded-full"
          style={{ backgroundColor: "#F97316" }}
        />
        <span
          className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.06em]"
          style={{ color: "#F97316" }}
        >
          Outbreak Alert
        </span>
        <p className="min-w-0 text-[14px] text-[#FAFAFA]">{alert.outbreak_summary}</p>
      </div>

      <div className="flex shrink-0 items-center gap-4">
        <span className="font-mono text-[11px] tabular-nums text-[#52525B]">
          {(alert.confidence * 100).toFixed(0)}% confidence
        </span>
        <Link
          to="/outbreaks"
          className="inline-flex items-center gap-1.5 text-[13px] font-medium"
          style={{ color: "#F97316" }}
        >
          View Details <ArrowRight className="size-3.5" />
        </Link>
        <button
          onClick={onDismiss}
          aria-label="Dismiss alert"
          className="rounded p-1 text-[#52525B] hover:bg-white/[0.06] hover:text-[#A1A1AA]"
        >
          <X className="size-4" />
        </button>
      </div>
    </div>
  );
}
