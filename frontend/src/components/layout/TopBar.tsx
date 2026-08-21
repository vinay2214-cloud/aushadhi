import { useRouterState } from "@tanstack/react-router";
import { PulsingDot } from "../shared/PulsingDot";
import { useUIStore } from "../../store/uiStore";

const TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/inventory": "Inventory",
  "/outbreaks": "Outbreaks",
  "/orders": "Purchase Orders",
  "/pipeline": "Pipeline",
  "/settings": "Settings",
};

const STREAM_LABEL: Record<string, string> = {
  connected: "Live stream connected",
  connecting: "Connecting stream…",
  disconnected: "Stream offline",
};

export function TopBar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const sseStatus = useUIStore((s) => s.sseStatus);

  const dotColor = sseStatus === "connected" ? "green" : sseStatus === "connecting" ? "amber" : "red";

  return (
    <header
      className="flex h-14 shrink-0 items-center justify-between px-6"
      style={{ backgroundColor: "#09090B", borderBottom: "1px solid rgba(255,255,255,0.06)" }}
    >
      <div>
        <h1 className="text-[15px] font-semibold tracking-tight text-[#FAFAFA]">
          {TITLES[pathname] ?? "AUSHADHI"}
        </h1>
        <p className="text-[11px] text-[#52525B]">Autonomous medicine supply intelligence</p>
      </div>
      <div
        className="flex items-center gap-2 rounded-md px-3 py-1.5"
        style={{ border: "1px solid var(--border-subtle)" }}
      >
        <PulsingDot color={dotColor} />
        <span className="text-[12px] text-[#A1A1AA]">{STREAM_LABEL[sseStatus]}</span>
      </div>
    </header>
  );
}
