import type { ReactNode } from "react";
import { useRouterState } from "@tanstack/react-router";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { useSSE } from "../../hooks/useSSE";

export function AppLayout({ children }: { children: ReactNode }) {
  useSSE();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="flex min-h-screen" style={{ backgroundColor: "#09090B", color: "#FAFAFA" }}>
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main key={pathname} className="au-fade flex-1 overflow-x-hidden p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
