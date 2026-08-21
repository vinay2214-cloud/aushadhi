import type { StockStatus } from "../../types/health-center";

const STYLES: Record<StockStatus, string> = {
  CRITICAL: "badge-critical",
  LOW: "badge-warning",
  MODERATE: "badge-neutral",
  GOOD: "badge-success",
};

export function StockStatusBadge({ status }: { status: StockStatus }) {
  return <span className={`badge-base ${STYLES[status]}`}>{status}</span>;
}
