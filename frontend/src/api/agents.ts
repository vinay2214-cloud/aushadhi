import client from "./client";
import { ENDPOINTS } from "../constants/api";
import type { AgentLog, AgentName, AgentStatus, PipelineRun } from "../types/agent";
import type { PaginatedResponse } from "../types/api";
import { normalizeList, unwrapArray } from "../lib/api-normalize";

export async function fetchAgents(): Promise<AgentStatus[]> {
  // GET /api/v1/agents/status -> { agents: [...], window_hours, generated_at }
  const { data } = await client.get(ENDPOINTS.agents);
  return unwrapArray<AgentStatus>(data, "agents");
}

export interface AgentLogFilters {
  agent_name?: AgentName;
  limit?: number;
  offset?: number;
}

/**
 * The backend stores each run as { input, output } maps rather than a flat
 * `key_output` string, so summarise the output into the one-line description
 * the log table renders.
 */
function summariseOutput(output: Record<string, unknown> | undefined): string {
  if (!output) return "";
  const parts: string[] = [];
  const push = (key: string, label: string) => {
    const value = output[key];
    if (typeof value === "number") parts.push(`${value} ${label}`);
  };
  push("centers_alerting", "centers alerting");
  push("total_critical_items", "critical");
  push("valid_records", "records valid");
  push("rejected_records", "rejected");
  push("forecasts_generated", "forecasts");
  push("notifications_sent", "notifications");
  if (Array.isArray(output["purchase_orders"])) parts.push(`${output["purchase_orders"].length} POs`);
  const outbreak = output["outbreak"] as Record<string, unknown> | undefined;
  if (outbreak?.["outbreak_detected"]) {
    parts.push(`outbreak ${String(outbreak["risk_level"] ?? "")}`.trim());
  }
  return parts.join(" · ");
}

export async function fetchAgentLogs(
  filters: AgentLogFilters = {},
): Promise<PaginatedResponse<AgentLog>> {
  const { data } = await client.get(ENDPOINTS.agentLogs, { params: filters });
  const page = normalizeList<Record<string, unknown>>(data);
  return {
    ...page,
    data: page.data.map((raw): AgentLog => {
      const output = raw["output"] as Record<string, unknown> | undefined;
      return {
        ...(raw as unknown as AgentLog),
        key_output: (raw["key_output"] as string) ?? summariseOutput(output),
        gemini_call: Boolean(raw["gemini_prompt"] ?? raw["gemini_response"] ?? output?.["outbreak"]),
      };
    }),
  };
}

export async function fetchPipelineRuns(limit = 10) {
  const { data } = await client.get<PaginatedResponse<PipelineRun>>(ENDPOINTS.pipelineRuns, {
    params: { limit },
  });
  return data;
}

export async function runSentinel() {
  const { data } = await client.post(ENDPOINTS.runSentinel);
  return data;
}

/**
 * Runs all five agents back to back inside the API process instead of handing
 * the cycle to Pub/Sub, so the Pipeline page fills in from one click rather
 * than depending on subscriber delivery timing.
 */
export async function runFullPipeline() {
  const { data } = await client.post(ENDPOINTS.runFullPipeline);
  return data;
}
