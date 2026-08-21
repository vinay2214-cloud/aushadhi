import client from "./client";
import { ENDPOINTS } from "../constants/api";
import type { InventoryItem, InventoryUrgency } from "../types/inventory";
import type { PaginatedResponse } from "../types/api";
import { normalizeList } from "../lib/api-normalize";

export interface InventoryFilters {
  center_id?: string;
  urgency?: InventoryUrgency;
  medicine_id?: string;
  limit?: number;
  offset?: number;
}

export async function fetchInventory(
  filters: InventoryFilters = {},
): Promise<PaginatedResponse<InventoryItem>> {
  const { data } = await client.get(ENDPOINTS.inventory, { params: filters });
  return normalizeList<InventoryItem>(data);
}
