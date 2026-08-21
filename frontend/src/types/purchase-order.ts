export type POStatus = "PENDING_APPROVAL" | "APPROVED" | "DISPATCHED" | "DELIVERED" | "CANCELLED";
export type POPriority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface POLineItem {
  medicine_name: string;
  requested_quantity: number;
  unit: string;
  total_cost_inr: number;
  urgency?: string;
  days_until_stockout: number;
}

export interface PurchaseOrder {
  id: string;
  po_number: string;
  health_center_id: string;
  health_center_name: string;
  district: string;
  warehouse_name: string;
  warehouse_distance_km: number;
  estimated_delivery_hours: number;
  priority: POPriority;
  line_items: POLineItem[];
  total_cost_inr: number;
  status: POStatus;
  outbreak_linked: boolean;
  created_at: string;
}
