import client from "./client";
import { ENDPOINTS } from "../constants/api";
import type { DashboardMetrics, DataQualityReport, SystemConfig } from "../types/metrics";
import { unwrapArray } from "../lib/api-normalize";

export async function fetchMetrics() {
  const { data } = await client.get<DashboardMetrics>(ENDPOINTS.metrics);
  return data;
}

export async function fetchDataQuality(): Promise<DataQualityReport[]> {
  // GET /api/v1/data-quality -> { centers: [...], district_average, total_centers, ... }
  // The rows carry data_quality_score; the UI reads `score`.
  const { data } = await client.get(ENDPOINTS.dataQuality);
  return unwrapArray<Record<string, unknown>>(data, "centers").map((row) => ({
    ...(row as unknown as DataQualityReport),
    score: Number(row["data_quality_score"] ?? row["score"] ?? 0),
  }));
}

export async function fetchConfig() {
  const { data } = await client.get<SystemConfig>(ENDPOINTS.config);
  return data;
}

export async function updateConfig(payload: Partial<SystemConfig>) {
  const { data } = await client.patch<SystemConfig>(ENDPOINTS.config, payload);
  return data;
}

export async function testConnection() {
  const { data } = await client.get(ENDPOINTS.health);
  return data;
}

export async function resetDemo() {
  const { data } = await client.post(ENDPOINTS.resetDemo);
  return data;
}
