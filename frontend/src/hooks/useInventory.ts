import { useQuery } from "@tanstack/react-query";
import { fetchInventory, type InventoryFilters } from "../api/inventory";

export function useInventory(filters: InventoryFilters = {}) {
  return useQuery({
    queryKey: ["inventory", filters],
    queryFn: () => fetchInventory(filters),
  });
}
