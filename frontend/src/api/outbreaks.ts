import client from "./client";
import { ENDPOINTS } from "../constants/api";
import type { OutbreakAlert, OutbreakStatus } from "../types/outbreak";
import type { PaginatedResponse } from "../types/api";
import { normalizeList } from "../lib/api-normalize";

export interface OutbreakFilters {
  status?: OutbreakStatus;
  limit?: number;
  offset?: number;
}

export async function fetchOutbreaks(
  filters: OutbreakFilters = {},
): Promise<PaginatedResponse<OutbreakAlert>> {
  const { data } = await client.get(ENDPOINTS.outbreaks, { params: filters });
  return normalizeList<OutbreakAlert>(data);
}

export async function acknowledgeOutbreak(id: string) {
  const { data } = await client.patch<OutbreakAlert>(`${ENDPOINTS.outbreaks}/${id}/acknowledge`);
  return data;
}

export async function resolveOutbreak(id: string) {
  const { data } = await client.patch<OutbreakAlert>(`${ENDPOINTS.outbreaks}/${id}/resolve`);
  return data;
}

export async function simulateOutbreak(payload?: Record<string, unknown>) {
  const { data } = await client.post(ENDPOINTS.simulateOutbreak, payload ?? {});
  return data;
}
