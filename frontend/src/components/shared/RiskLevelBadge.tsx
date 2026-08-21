import type { RiskLevel } from "../../types/outbreak";

const STYLES: Record<RiskLevel, string> = {
  CRITICAL: "badge-critical",
  HIGH: "badge-outbreak",
  MEDIUM: "badge-warning",
  LOW: "badge-neutral",
  NONE: "badge-neutral",
};

export function RiskLevelBadge({ level }: { level: RiskLevel }) {
  return <span className={`badge-base ${STYLES[level]} uppercase`}>{level}</span>;
}
