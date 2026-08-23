import axios from "axios";
import { getApiBaseUrl, getApiKey } from "../constants/api";

const client = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

/**
 * One diagnostic line per page load, never the key itself — enough to tell the
 * two failure modes apart in DevTools: a blank key means the runtime config
 * never reached the browser (NITRO_API_KEY unset on the frontend service, or
 * the SSR shell not injecting it), while a present key plus a 401 means the
 * backend's AUSHADHI_API_KEY differs from it.
 */
let logged = false;
function logKeyOnce(key: string) {
  if (logged || typeof window === "undefined") return;
  logged = true;
  const detail = { baseURL: getApiBaseUrl(), apiKeyPresent: key.length > 0, apiKeyLength: key.length };
  if (key) console.info("[aushadhi] api config", detail);
  else console.error("[aushadhi] X-API-Key is empty — requests will 401", detail);
}

client.interceptors.request.use((config) => {
  // Resolved per request: the runtime config global may not have existed when
  // this module was first evaluated.
  config.baseURL = getApiBaseUrl();
  const key = getApiKey();
  logKeyOnce(key);
  if (key) config.headers["X-API-Key"] = key;
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error.response?.status, error.response?.data);
    return Promise.reject(error);
  },
);

export default client;
