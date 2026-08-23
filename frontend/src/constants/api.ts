import { getPublicConfig } from "./runtime-config";

/**
 * API origin resolution.
 *
 * The base URL comes from `public.config.js`: NITRO_API_BASE_URL at runtime on
 * the server (serialised into the SSR'd HTML for the browser), else the
 * build-time VITE_API_BASE_URL. When neither is set it falls back to the
 * local backend port -- the dev server runs on :8080 or :5173 and FastAPI
 * answers on :8000 in both cases.
 */
const LOCAL_BACKEND_URL = "http://localhost:8000";
const LOCAL_DEV_ORIGINS = ["http://localhost:8080", "http://localhost:5173", "http://localhost:3000"];

function resolveBaseUrl(configured: string): string {
  const trimmed = configured.trim().replace(/\/+$/, "");
  // public.config.js already substitutes LOCAL_BACKEND_URL when nothing is
  // configured, so that exact value means "unset" and hands over to the
  // origin heuristics below (which resolve to the same URL in local dev).
  if (trimmed && trimmed !== LOCAL_BACKEND_URL) return trimmed;

  if (typeof window !== "undefined") {
    const origin = window.location.origin;
    // Served from a local dev server -> the API is the backend on :8000.
    if (LOCAL_DEV_ORIGINS.includes(origin)) return LOCAL_BACKEND_URL;
    // Deployed together behind one origin -> same-origin requests.
    if (!origin.startsWith("http://localhost")) return origin;
  }

  return LOCAL_BACKEND_URL;
}

/**
 * Read on every call, not once at module load. The browser gets its values
 * from the global that `RootShell` writes into the SSR'd HTML, and this module
 * is imported by code that can evaluate before that script has run — a
 * snapshot taken then would freeze in the empty build-time fallback and every
 * request would go out with `X-API-Key: ""` (a 401 the dashboard reports as
 * "Could not reach AUSHADHI API").
 */
export function getApiBaseUrl(): string {
  return resolveBaseUrl(getPublicConfig().apiBaseUrl);
}

export function getApiKey(): string {
  return getPublicConfig().apiKey || "";
}

/** Snapshots, for display only — request paths must call the getters above. */
export const API_BASE_URL = getApiBaseUrl();
export const API_KEY = getApiKey();

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
