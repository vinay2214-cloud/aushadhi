import client from "./client";
import { ENDPOINTS } from "../constants/api";
import type { POPriority, POStatus, PurchaseOrder } from "../types/purchase-order";
import type { PaginatedResponse } from "../types/api";
import { normalizeList } from "../lib/api-normalize";

export interface PurchaseOrderFilters {
  status?: POStatus;
  priority?: POPriority;
  limit?: number;
  offset?: number;
}

export async function fetchPurchaseOrders(
  filters: PurchaseOrderFilters = {},
): Promise<PaginatedResponse<PurchaseOrder>> {
  const { data } = await client.get(ENDPOINTS.purchaseOrders, { params: filters });
  return normalizeList<PurchaseOrder>(data);
}

const ACTION_PATH: Record<string, string> = {
  APPROVED: "approve",
  CANCELLED: "reject",
  DISPATCHED: "dispatch",
  DELIVERED: "deliver",
};

export async function updatePurchaseOrderStatus(id: string, status: POStatus) {
  const action = ACTION_PATH[status];
  const { data } = await client.patch<PurchaseOrder>(
    `${ENDPOINTS.purchaseOrders}/${id}/${action ?? "status"}`,
    action ? undefined : { status },
  );
  return data;
}

export async function createPurchaseOrder(payload: {
  health_center_id: string;
  medicine_name: string;
  requested_quantity: number;
  priority: POPriority;
}) {
  const { data } = await client.post<PurchaseOrder>(ENDPOINTS.purchaseOrders, payload);
  return data;
}
