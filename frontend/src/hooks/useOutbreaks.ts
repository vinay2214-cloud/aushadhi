import { useQuery } from "@tanstack/react-query";
import { fetchOutbreaks, type OutbreakFilters } from "../api/outbreaks";

export function useOutbreaks(filters: OutbreakFilters = {}) {
  return useQuery({
    queryKey: ["outbreaks", filters],
    queryFn: () => fetchOutbreaks(filters),
  });
}
