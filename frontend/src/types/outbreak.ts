export type RiskLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NONE";
export type OutbreakStatus = "ACTIVE" | "UNDER_RESPONSE" | "RESOLVED" | "FALSE_POSITIVE";

export interface OutbreakAlert {
  id: string;
  outbreak_detected: boolean;
  risk_level: RiskLevel;
  disease_indicators: string[];
  affected_center_ids: string[];
  geographic_cluster: string;
  key_evidence: Array<{
    medicine: string;
    normal_daily_consumption: number;
    current_daily_consumption: number;
    ratio: number;
    significance: "HIGH" | "MEDIUM" | "LOW";
  }>;
  confidence: number;
  outbreak_summary: string;
  recommended_actions: string[];
  status: OutbreakStatus;
  acknowledged_by: string | null;
  linked_po_ids: string[];
  district: string;
  created_at: string;
}
