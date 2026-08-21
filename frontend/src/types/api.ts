export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

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
