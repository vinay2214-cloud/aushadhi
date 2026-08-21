import { useQuery } from "@tanstack/react-query";
import { fetchPurchaseOrders, type PurchaseOrderFilters } from "../api/purchase-orders";

export function usePurchaseOrders(filters: PurchaseOrderFilters = {}) {
  return useQuery({
    queryKey: ["purchase-orders", filters],
    queryFn: () => fetchPurchaseOrders(filters),
  });
}
