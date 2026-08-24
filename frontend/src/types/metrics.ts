export interface DashboardMetrics {
  centers_monitored: number;
  critical_stockouts: number;
  active_outbreak_alerts: number;
  pending_purchase_orders: number;
  avg_data_quality_score: number;
  total_pos_generated_today: number;
  total_pos_value_inr: number;
  pipeline_last_run: string;
}

export interface DataQualityReport {
  center_id: string;
  center_name: string;
  score: number;
  valid_records: number;
  rejected_records: number;
  warnings: number;
}

export interface SystemConfig {
  districts_monitored: number;
  centers_monitored: number;
  medicines_tracked: number;
  last_pipeline_run: string | null;
  /** The model actually answering — gemma_model when the fallback is on. */
  active_model: string;
  gemma_fallback_enabled: boolean;
  gemini_model?: string;
  gemma_model?: string;
}

/**
 * Body of PATCH /api/v1/config. The stored toggle is `use_gemma_fallback`;
 * SystemConfig reports it back as the derived `gemma_fallback_enabled`.
 */
export interface ConfigPatch {
  use_gemma_fallback?: boolean;
}
