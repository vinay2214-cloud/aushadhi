import { Outlet, createFileRoute } from "@tanstack/react-router";
import { AppLayout } from "../components/layout/AppLayout";

/**
 * Pathless layout route: everything under it keeps its URL (/dashboard,
 * /inventory, …) but renders inside AppLayout, which owns the sidebar, the
 * top bar and the SSE connection. The landing page at "/" sits outside this
 * layout, so it renders full-screen and opens no stream.
 */
export const Route = createFileRoute("/_app")({
  component: AppLayoutRoute,
});

function AppLayoutRoute() {
  return (
    <AppLayout>
      <Outlet />
    </AppLayout>
  );
}
