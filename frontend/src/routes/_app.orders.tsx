import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Siren, Truck } from "lucide-react";
import { LoadingSpinner } from "../components/shared/LoadingSpinner";
import { ErrorState } from "../components/shared/ErrorState";
import { EmptyState } from "../components/shared/EmptyState";
import { TimeAgo } from "../components/shared/TimeAgo";
import { formatINR } from "../components/shared/IndianRupee";
import { usePurchaseOrders } from "../hooks/usePurchaseOrders";
import { updatePurchaseOrderStatus } from "../api/purchase-orders";
import type { POPriority, POStatus } from "../types/purchase-order";

export const Route = createFileRoute("/_app/orders")({
  head: () => ({
    meta: [
      { title: "Purchase Orders — AUSHADHI" },
      {
        name: "description",
        content:
          "Autonomously generated medicine purchase orders with routing, cost and approval workflow.",
      },
      { property: "og:title", content: "Purchase Orders — AUSHADHI" },
      {
        property: "og:description",
        content: "Agent-generated purchase orders awaiting approval and dispatch.",
      },
    ],
  }),
  component: OrdersPage,
});

const TABS: Array<{ label: string; value: POStatus | "ALL" }> = [
  { label: "Pending", value: "PENDING_APPROVAL" },
  { label: "Approved", value: "APPROVED" },
  { label: "Dispatched", value: "DISPATCHED" },
  { label: "Delivered", value: "DELIVERED" },
  { label: "All", value: "ALL" },
];

const PRIORITY: Record<POPriority, string> = {
  CRITICAL: "badge-critical",
  HIGH: "badge-warning",
  MEDIUM: "badge-warning",
  LOW: "badge-neutral",
};

const STEPS: POStatus[] = ["PENDING_APPROVAL", "APPROVED", "DISPATCHED", "DELIVERED"];
const STEP_LABEL: Record<string, string> = {
  PENDING_APPROVAL: "Generated",
  APPROVED: "Approved",
  DISPATCHED: "Dispatched",
  DELIVERED: "Delivered",
};

const NEXT_ACTION: Partial<Record<POStatus, { label: string; next: POStatus }>> = {
  PENDING_APPROVAL: { label: "Approve", next: "APPROVED" },
  APPROVED: { label: "Dispatch", next: "DISPATCHED" },
  DISPATCHED: { label: "Mark delivered", next: "DELIVERED" },
};

function OrdersPage() {
  const [tab, setTab] = useState<POStatus | "ALL">("PENDING_APPROVAL");
  const queryClient = useQueryClient();
  const { data, isLoading, isError, refetch } = usePurchaseOrders(
    tab === "ALL" ? { limit: 100 } : { status: tab, limit: 100 },
  );

  const mutate = useMutation({
    mutationFn: ({ id, status }: { id: string; status: POStatus }) =>
      updatePurchaseOrderStatus(id, status),
    onSuccess: (_d, v) => {
      toast.success(`Order ${v.status.toLowerCase().replace("_", " ")}`);
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      queryClient.invalidateQueries({ queryKey: ["metrics"] });
    },
    onError: () => toast.error("Could not update order"),
  });

  const orders = data?.data ?? [];
  const total = orders.reduce((s, o) => s + o.total_cost_inr, 0);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[20px] font-semibold tracking-tight text-slate-100">Purchase Orders</h1>
          <p className="text-[13px] text-slate-500">
            Generated autonomously by the PROCUREMENT agent
          </p>
        </div>
        <div className="rounded-lg border border-white/[0.07] bg-[#111113] px-4 py-2 text-right">
          <p className="card-label">Value in view</p>
          <p className="font-mono text-[15px] font-semibold tabular-nums text-slate-100">
            {formatINR(total)}
          </p>
        </div>
      </header>

      <div className="flex flex-wrap gap-1 rounded-lg border border-white/[0.07] p-1 text-[13px]">
        {TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => setTab(t.value)}
            className={`rounded-lg px-3 py-1.5 font-medium ${
              tab === t.value
                ? "bg-white/[0.08] text-slate-100"
                : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <LoadingSpinner label="Loading purchase orders" rows={5} height={120} />
      ) : isError ? (
        <ErrorState message="Purchase order data unavailable." onRetry={() => refetch()} />
      ) : orders.length === 0 ? (
        <EmptyState title="No orders in this state" />
      ) : (
        <div className="relative space-y-4 pl-6">
          <span className="absolute bottom-4 left-[7px] top-4 w-px bg-white/[0.08]" />
          {orders.map((po, idx) => {
            const action = NEXT_ACTION[po.status];
            const current = STEPS.indexOf(po.status);
            return (
              <article
                key={po.id}
                className="au-rise group relative rounded-lg border border-white/[0.07] bg-[#111113] p-5 transition-colors hover:bg-[#161618]"
                style={{ animationDelay: `${idx * 50}ms` }}
              >
                <span
                  className={`absolute -left-6 top-6 size-[9px] rounded-full ring-4 ring-[#0a0a0f] ${
                    po.priority === "CRITICAL" ? "bg-red-500" : "bg-slate-600"
                  }`}
                />
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[12px] font-semibold text-slate-200">
                    {po.po_number}
                  </span>
                  {po.outbreak_linked ? (
                    <span className="badge-base badge-outbreak inline-flex items-center gap-1">
                      <Siren className="size-3" /> OUTBREAK
                    </span>
                  ) : null}
                  <TimeAgo date={po.created_at} className="ml-auto text-[11px] text-slate-600" />
                </div>

                <p className="mt-2 text-[14px] font-medium text-slate-100">
                  {po.health_center_name}
                </p>
                <p className="flex items-center gap-1.5 text-[12px] text-slate-600">
                  <Truck className="size-3" />
                  {po.warehouse_name} · {po.warehouse_distance_km} km ·{" "}
                  {po.estimated_delivery_hours}h ETA
                </p>

                <div className="mt-4 flex flex-wrap items-center gap-2">
                  {STEPS.map((s, i) => (
                    <div key={s} className="flex items-center gap-2">
                      <span
                        className={`flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ${
                          i < current
                            ? "text-slate-500"
                            : i === current
                              ? "bg-emerald-500/15 text-emerald-400"
                              : "text-slate-700"
                        }`}
                      >
                        <span
                          className={`size-1.5 rounded-full ${
                            i <= current ? "bg-emerald-500" : "bg-slate-700"
                          }`}
                        />
                        {STEP_LABEL[s]}
                      </span>
                      {i < STEPS.length - 1 ? (
                        <span
                          className={`h-px w-4 ${i < current ? "bg-emerald-500/50" : "bg-white/[0.08]"}`}
                        />
                      ) : null}
                    </div>
                  ))}
                </div>

                <div className="mt-4 space-y-1.5">
                  {po.line_items.map((li) => (
                    <div
                      key={li.medicine_name}
                      className="flex items-center justify-between border-b border-white/[0.05] pb-1.5 text-[13px] last:border-0"
                    >
                      <span className="text-slate-300">
                        {li.medicine_name}
                        <span className="ml-2 font-mono text-[11px] tabular-nums text-slate-600">
                          {li.requested_quantity} {li.unit}
                        </span>
                      </span>
                      <span className="font-mono tabular-nums text-slate-500">
                        {formatINR(li.total_cost_inr)}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="mt-4 flex items-end justify-between gap-4">
                  <div>
                    <p className="card-label">Total cost</p>
                    <div className="flex items-center gap-2">
                      <span className="data-number text-slate-100">
                        {formatINR(po.total_cost_inr)}
                      </span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${PRIORITY[po.priority]}`}
                      >
                        {po.priority}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-2 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                    {po.status === "PENDING_APPROVAL" ? (
                      <button
                        onClick={() => mutate.mutate({ id: po.id, status: "CANCELLED" })}
                        disabled={mutate.isPending}
                        className="rounded-lg border border-white/[0.07] px-3 py-1.5 text-[12px] text-slate-400 hover:bg-white/[0.06] disabled:opacity-50"
                      >
                        Reject
                      </button>
                    ) : null}
                    {action ? (
                      <button
                        onClick={() => mutate.mutate({ id: po.id, status: action.next })}
                        disabled={mutate.isPending}
                        className="rounded-lg bg-emerald-500 px-3 py-1.5 text-[12px] font-semibold text-slate-950 hover:bg-emerald-400 disabled:opacity-50"
                      >
                        {action.label}
                      </button>
                    ) : (
                      <span className="rounded-lg bg-white/[0.05] px-2 py-1 text-[11px] text-slate-500">
                        {po.status}
                      </span>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
