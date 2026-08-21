import { Link, useRouterState } from "@tanstack/react-router";
import {
  Boxes,
  ClipboardList,
  LayoutDashboard,
  Settings,
  Bug,
  Workflow,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { useUIStore } from "../../store/uiStore";
import { AushdhiLogo, AushdhiMark } from "../shared/AushdhiLogo";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/inventory", label: "Inventory", icon: Boxes },
  { to: "/outbreaks", label: "Outbreaks", icon: Bug },
  { to: "/orders", label: "Purchase Orders", icon: ClipboardList },
  { to: "/pipeline", label: "Pipeline", icon: Workflow },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

const EXPANDED_WIDTH = 216;
const COLLAPSED_WIDTH = 56;

export function Sidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  const toggle = useUIStore((s) => s.toggleSidebar);

  return (
    <aside
      className="flex shrink-0 flex-col transition-[width] duration-200 ease-out"
      style={{
        width: collapsed ? COLLAPSED_WIDTH : EXPANDED_WIDTH,
        backgroundColor: "#09090B",
        borderRight: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      <div className={`py-5 ${collapsed ? "px-0 text-center" : "px-3"}`}>
        {collapsed ? (
          <AushdhiMark size={20} className="mx-auto text-[#22C55E]" />
        ) : (
          <>
            <AushdhiLogo size="md" showTagline={false} />
            <Link
              to="/"
              className="mt-2 block text-[11px] text-[#3F3F46] transition-colors hover:text-[#71717A]"
            >
              ← Back to Overview
            </Link>
          </>
        )}
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 px-2">
        {NAV.map(({ to, label, icon: Icon }) => {
          const active = pathname === to || pathname.startsWith(`${to}/`);
          return (
            <Link
              key={to}
              to={to}
              title={label}
              className={`flex h-9 items-center gap-3 rounded-md text-[13px] font-medium ${
                collapsed ? "justify-center px-0" : "px-3"
              }`}
              style={
                active
                  ? {
                      backgroundColor: "rgba(255,255,255,0.08)",
                      color: "#FFFFFF",
                      borderLeft: "2px solid #22C55E",
                      paddingLeft: collapsed ? undefined : 10,
                    }
                  : { color: "#71717A", borderLeft: "2px solid transparent" }
              }
              onMouseEnter={(e) => {
                if (!active) e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.04)";
              }}
              onMouseLeave={(e) => {
                if (!active) e.currentTarget.style.backgroundColor = "transparent";
              }}
            >
              <Icon className="size-4 shrink-0" />
              {collapsed ? null : <span className="truncate">{label}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="px-2 pb-3">
        <button
          onClick={toggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={`flex h-9 w-full items-center gap-2 rounded-md text-[#52525B] hover:bg-white/[0.04] hover:text-[#A1A1AA] ${
            collapsed ? "justify-center px-0" : "px-3"
          }`}
        >
          {collapsed ? (
            <ChevronsRight className="size-4" />
          ) : (
            <>
              <ChevronsLeft className="size-4" />
              <span className="text-[11px]">Collapse</span>
            </>
          )}
        </button>
        {collapsed ? null : (
          <p className="mt-2 px-3 text-[10px] text-[#52525B]">Powered by Gemini 3.5</p>
        )}
      </div>
    </aside>
  );
}
