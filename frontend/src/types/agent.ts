export type AgentName = "SENTINEL" | "DQMS" | "FORECAST" | "PROCUREMENT" | "ALERT";

export interface AgentLog {
  id: string;
  center_id: string | null;
  center_name?: string | null;
  agent_name: AgentName;
  action: string;
  status: "STARTED" | "COMPLETED" | "FAILED" | "RETRYING";
  duration_ms: number | null;
  key_output: string;
  gemini_call?: boolean;
  created_at: string;
}

export interface AgentStatus {
  name: AgentName;
  status: "HEALTHY" | "DEGRADED" | "DOWN";
  last_run: string | null;
  runs_today: number;
  avg_duration_ms: number | null;
  headline_metric?: { label: string; value: string | number };
}

export interface PipelineRunStep {
  agent_name: AgentName;
  status: "STARTED" | "COMPLETED" | "FAILED" | "RETRYING";
  duration_ms: number | null;
  key_output?: string;
}

export interface PipelineRun {
  id: string;
  started_at: string;
  duration_seconds: number | null;
  centers_processed: number;
  alerts_generated: number;
  pos_created: number;
  steps: PipelineRunStep[];
  logs?: AgentLog[];
}
