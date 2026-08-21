/**
 * API origin resolution.
 *
 * VITE_API_BASE_URL is the source of truth. When it is absent (a plain
 * `bun run dev` with no .env.local), fall back to the backend's local port:
 * the dev server runs on :8080 or :5173, and the FastAPI backend answers on
 * :8000 in both cases.
 */
const ENV_BASE_URL = import.meta.env["VITE_API_BASE_URL"] as string | undefined;

const LOCAL_BACKEND_URL = "http://localhost:8000";
const LOCAL_DEV_ORIGINS = ["http://localhost:8080", "http://localhost:5173", "http://localhost:3000"];

function resolveBaseUrl(): string {
  if (ENV_BASE_URL && ENV_BASE_URL.trim()) return ENV_BASE_URL.trim().replace(/\/+$/, "");

  if (typeof window !== "undefined") {
    const origin = window.location.origin;
    // Served from a local dev server -> the API is the backend on :8000.
    if (LOCAL_DEV_ORIGINS.includes(origin)) return LOCAL_BACKEND_URL;
    // Deployed together behind one origin -> same-origin requests.
    if (!origin.startsWith("http://localhost")) return origin;
  }

  return LOCAL_BACKEND_URL;
}

export const API_BASE_URL = resolveBaseUrl();
export const API_KEY = (import.meta.env["VITE_API_KEY"] as string | undefined) ?? "";

export const ENDPOINTS = {
  health: "/health",
  metrics: "/api/v1/metrics",
  healthCenters: "/api/v1/health-centers",
  inventory: "/api/v1/inventory",
  outbreaks: "/api/v1/outbreaks",
  purchaseOrders: "/api/v1/purchase-orders",
  agents: "/api/v1/agents/status",
  agentLogs: "/api/v1/agent-logs",
  pipelineRuns: "/api/v1/pipeline-runs",
  dataQuality: "/api/v1/data-quality",
  config: "/api/v1/config",
  stream: "/api/v1/stream",
  runSentinel: "/api/v1/internal/run-sentinel",
  simulateOutbreak: "/api/v1/internal/simulate-outbreak",
  resetDemo: "/api/v1/internal/reset-demo",
};

export const KEY_MEDICINES = [
  "ORS",
  "Zinc",
  "IV Saline",
  "Paracetamol",
  "Metronidazole",
  "Chloroquine",
];
