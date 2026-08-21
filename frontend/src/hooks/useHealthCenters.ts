import { useQuery } from "@tanstack/react-query";
import {
  fetchHealthCenter,
  fetchHealthCenters,
  type HealthCenterFilters,
} from "../api/health-centers";

export function useHealthCenters(filters: HealthCenterFilters = {}) {
  return useQuery({
    queryKey: ["health-centers", filters],
    queryFn: () => fetchHealthCenters(filters),
  });
}

export function useHealthCenter(id: string | null) {
  return useQuery({
    queryKey: ["health-center", id],
    queryFn: () => fetchHealthCenter(id as string),
    enabled: Boolean(id),
  });
}
