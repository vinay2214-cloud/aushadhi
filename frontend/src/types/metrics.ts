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
  active_model: string;
  gemma_fallback_enabled: boolean;
}
