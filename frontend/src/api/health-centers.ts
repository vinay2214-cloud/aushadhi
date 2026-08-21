import client from "./client";
import { ENDPOINTS } from "../constants/api";
import type { HealthCenter, StockStatus } from "../types/health-center";
import type { PaginatedResponse } from "../types/api";
import { normalizeList } from "../lib/api-normalize";

export interface HealthCenterFilters {
  district?: string;
  status?: StockStatus;
  limit?: number;
  offset?: number;
}

export async function fetchHealthCenters(
  filters: HealthCenterFilters = {},
): Promise<PaginatedResponse<HealthCenter>> {
  const { data } = await client.get(ENDPOINTS.healthCenters, { params: filters });
  return normalizeList<HealthCenter>(data);
}

export async function fetchHealthCenter(id: string) {
  const { data } = await client.get<HealthCenter>(`${ENDPOINTS.healthCenters}/${id}`);
  return data;
}
