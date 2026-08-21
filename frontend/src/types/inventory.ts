export type InventoryUrgency = "CRITICAL" | "LOW" | "MONITOR" | "OK";

export interface InventoryItem {
  center_id: string;
  medicine_id: string;
  medicine_name: string;
  current_stock: number;
  minimum_threshold: number;
  maximum_capacity: number;
  stock_percentage: number;
  urgency: InventoryUrgency;
  days_until_stockout: number | null;
  daily_consumption_today: number;
  seven_day_avg_consumption: number;
  consumption_ratio: number;
  anomaly_flag: boolean;
  anomaly_ratio: number | null;
  pending_order_quantity: number;
  last_updated: string;
}
