import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { getApiBaseUrl, getApiKey } from "../constants/api";
import { useUIStore } from "../store/uiStore";

export type ConnectionStatus = "connecting" | "connected" | "disconnected";

/**
 * Reconnect backoff. The previous version retried every 3s unconditionally,
 * so a backend that was down (or restarting) got hammered — each attempt
 * opened a stream that spawned Firestore gRPC listener threads on the server
 * until it died with "can't start new thread". Backoff caps the damage; the
 * unmount guard stops React StrictMode's double-invoke from leaving an
 * orphaned socket behind.
 */
const BACKOFF_SCHEDULE_MS = [3_000, 6_000, 12_000, 30_000, 60_000] as const;

const isDev = import.meta.env.DEV;

function devLog(message: string, ...rest: unknown[]) {
  if (isDev) console.info(`[sse] ${message}`, ...rest);
}

export function useSSE() {
  const queryClient = useQueryClient();
  const setSseStatus = useUIStore((s) => s.setSseStatus);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("connecting");

  // Refs, not state: the connect loop reads these across renders and must never
  // re-run the effect (a re-run is what caused the reconnect storm).
  const sourceRef = useRef<EventSource | null>(null);
  const unmountedRef = useRef(false);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = useRef(0);

  useEffect(() => {
    if (typeof window === "undefined") return;

    unmountedRef.current = false;

    const setStatus = (next: ConnectionStatus) => {
      if (unmountedRef.current) return;
      setConnectionStatus((prev) => {
        if (prev !== next) devLog(`${prev} -> ${next}`);
        return next;
      });
      setSseStatus(next);
    };

    const scheduleReconnect = () => {
      if (unmountedRef.current) return;
      const delay =
        BACKOFF_SCHEDULE_MS[Math.min(attemptRef.current, BACKOFF_SCHEDULE_MS.length - 1)];
      attemptRef.current += 1;
      devLog(`reconnecting in ${delay}ms (attempt ${attemptRef.current})`);
      retryTimerRef.current = setTimeout(connect, delay);
    };

    function connect() {
      if (unmountedRef.current) return;

      setStatus("connecting");
      // Resolved at connect time so a reconnect picks up the runtime config
      // even if it landed after this module was first evaluated. EventSource
      // cannot set headers, so the key travels as a query param.
      const key = getApiKey();
      if (!key) console.error("[sse] api key is empty — the stream will be rejected");
      const url = `${getApiBaseUrl()}/api/v1/stream?api_key=${encodeURIComponent(key)}`;
      const source = new EventSource(url);
      sourceRef.current = source;

      source.onopen = () => {
        // A successful connection resets the backoff to the first step.
        attemptRef.current = 0;
        setStatus("connected");
      };

      source.addEventListener("inventory_updated", () => {
        queryClient.invalidateQueries({ queryKey: ["inventory"] });
        queryClient.invalidateQueries({ queryKey: ["health-centers"] });
      });

      source.addEventListener("outbreak_detected", (e) => {
        const data = JSON.parse((e as MessageEvent).data);
        toast.error(`Outbreak alert — ${data.risk_level}: ${data.outbreak_summary}`, {
          duration: 8000,
        });
        queryClient.invalidateQueries({ queryKey: ["outbreaks"] });
        queryClient.invalidateQueries({ queryKey: ["metrics"] });
      });

      source.addEventListener("purchase_order_created", (e) => {
        const data = JSON.parse((e as MessageEvent).data);
        toast.success(`PO ${data.po_number} created — ${data.health_center_name}`, {
          duration: 5000,
        });
        queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
        queryClient.invalidateQueries({ queryKey: ["metrics"] });
      });

      source.addEventListener("agent_step", () => {
        queryClient.invalidateQueries({ queryKey: ["agent-logs"] });
        queryClient.invalidateQueries({ queryKey: ["agents"] });
      });

      source.addEventListener("sentinel_cycle_started", () => {
        queryClient.invalidateQueries({ queryKey: ["agents"] });
      });

      source.addEventListener("pipeline_complete", () => {
        queryClient.invalidateQueries({ queryKey: ["metrics"] });
        queryClient.invalidateQueries({ queryKey: ["agents"] });
      });

      source.addEventListener("heartbeat", () => {
        // Keep-alive only — proves the stream is still live, no refetch needed.
      });

      source.onerror = () => {
        // EventSource retries on its own; close first so exactly one socket is
        // ever open and reconnection stays on our backoff schedule.
        source.close();
        sourceRef.current = null;
        setStatus("disconnected");
        scheduleReconnect();
      };
    }

    connect();

    return () => {
      unmountedRef.current = true;
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
      sourceRef.current?.close();
      sourceRef.current = null;
      devLog("closed (unmount)");
      setSseStatus("disconnected");
    };
  }, [queryClient, setSseStatus]);

  return { connectionStatus };
}
